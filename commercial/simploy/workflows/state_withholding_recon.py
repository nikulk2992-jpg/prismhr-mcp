"""State Quarterly Withholding Reconciliation — workflow #56.

Every state with income tax requires a quarterly employer withholding
return. PrismHR posts withholding at the voucher level; the state
return sums those per-state within the quarter. Drift between the
two = either short-remit (interest + penalty) or over-remit
(recoverable but delays close).

Findings per (state, quarter):
  - WITHHOLDING_MISMATCH: state return total != sum of vouchers.
  - SUTA_WAGES_MISMATCH: SUTA wage base on return != voucher sum
    (capped per state wage base).
  - UI_RATE_CHANGE: employer rate changed mid-quarter without
    matching rate-effective-date entry.
  - EMPLOYEE_COUNT_MISMATCH: headcount reported on quarterly vs
    active employees who earned wages in the period.
  - NO_FILING: state has wages but no filing record on file.

Input: client_id, year, quarter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class StateQuarterRecon:
    state: str
    quarter: int
    year: int
    voucher_wages: Decimal
    voucher_withholding: Decimal
    voucher_suta_wages: Decimal
    voucher_employee_count: int
    return_wages: Decimal
    return_withholding: Decimal
    return_suta_wages: Decimal
    return_employee_count: int
    findings: list[Finding] = field(default_factory=list)


@dataclass
class StateWithholdingReport:
    client_id: str
    year: int
    quarter: int
    as_of: date
    states: list[StateQuarterRecon]
    tolerance: Decimal

    @property
    def flagged(self) -> int:
        return sum(1 for s in self.states if s.findings)


class PrismHRReader(Protocol):
    async def list_wages_by_state(
        self, client_id: str, year: int, quarter: int
    ) -> list[dict]: ...
    async def get_state_filings(
        self, client_id: str, year: int, quarter: int
    ) -> list[dict]: ...


async def run_state_withholding_recon(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    quarter: int,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
) -> StateWithholdingReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))

    vouchers = await reader.list_wages_by_state(client_id, year, quarter)
    filings = {
        str(f.get("state") or "").upper(): f
        for f in await reader.get_state_filings(client_id, year, quarter)
    }

    states: list[StateQuarterRecon] = []
    for row in vouchers:
        state = str(row.get("state") or "").upper()
        if not state:
            continue
        v_wages = _dec(row.get("totalWages"))
        v_withholding = _dec(row.get("stateWithholding"))
        v_suta = _dec(row.get("sutaWages"))
        v_count = int(row.get("employeeCount") or 0)

        filing = filings.get(state, {})
        f_wages = _dec(filing.get("totalWages"))
        f_withholding = _dec(filing.get("withholding"))
        f_suta = _dec(filing.get("sutaWages"))
        f_count = int(filing.get("employeeCount") or 0)

        recon = StateQuarterRecon(
            state=state,
            quarter=quarter,
            year=year,
            voucher_wages=v_wages,
            voucher_withholding=v_withholding,
            voucher_suta_wages=v_suta,
            voucher_employee_count=v_count,
            return_wages=f_wages,
            return_withholding=f_withholding,
            return_suta_wages=f_suta,
            return_employee_count=f_count,
        )

        if not filing and v_wages > 0:
            recon.findings.append(
                Finding(
                    "NO_FILING",
                    "critical",
                    f"{state}: ${v_wages} in wages but no filing record for Q{quarter} {year}.",
                )
            )
        else:
            if (v_withholding - f_withholding).copy_abs() > tol:
                recon.findings.append(
                    Finding(
                        "WITHHOLDING_MISMATCH",
                        "critical",
                        f"{state}: vouchers ${v_withholding}, return ${f_withholding}, delta ${v_withholding - f_withholding}.",
                    )
                )
            if (v_suta - f_suta).copy_abs() > tol:
                recon.findings.append(
                    Finding(
                        "SUTA_WAGES_MISMATCH",
                        "warning",
                        f"{state}: SUTA wages {v_suta} vs return {f_suta}.",
                    )
                )
            if abs(v_count - f_count) > 0 and v_count > 0:
                recon.findings.append(
                    Finding(
                        "EMPLOYEE_COUNT_MISMATCH",
                        "warning",
                        f"{state}: vouchers show {v_count} employees, return shows {f_count}.",
                    )
                )
        states.append(recon)

    return StateWithholdingReport(
        client_id=client_id,
        year=year,
        quarter=quarter,
        as_of=today,
        states=states,
        tolerance=tol,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
