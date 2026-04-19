"""Prepay-vs-Liability Sweep — workflow #35.

Per PrismHR's Accounting chapter: when a client is on prepay, each
month's premiums go into a prepay benefit account first, then the
"sweep" transfers them into the liability account on the first of
the following month. Missed or mis-sized sweeps show up as stale
prepay balances or double-booked liability.

Findings per (client, month):
  - SWEEP_NOT_PERFORMED: prepay balance > 0 on second day of next
    month (sweep should have run).
  - SWEEP_UNDER: amount swept < prepay balance by > tolerance.
  - SWEEP_OVER: amount swept > prepay balance by > tolerance.
  - PREPAY_BALANCE_GROWING: prepay balance 3 months in a row
    without a completed sweep.
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
class MonthSweepAudit:
    year: int
    month: int
    prepay_balance: Decimal
    sweep_amount: Decimal
    sweep_completed_on: date | None
    findings: list[Finding] = field(default_factory=list)


@dataclass
class PrepayLiabilityReport:
    client_id: str
    year: int
    as_of: date
    months: list[MonthSweepAudit]
    tolerance: Decimal

    @property
    def flagged(self) -> int:
        return sum(1 for m in self.months if m.findings)


class PrismHRReader(Protocol):
    async def get_prepay_balances_by_month(
        self, client_id: str, year: int
    ) -> dict[int, Decimal]: ...
    async def get_sweeps_by_month(
        self, client_id: str, year: int
    ) -> dict[int, dict]: ...


async def run_prepay_liability_sweep(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
) -> PrepayLiabilityReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))

    balances = await reader.get_prepay_balances_by_month(client_id, year)
    sweeps = await reader.get_sweeps_by_month(client_id, year)

    months: list[MonthSweepAudit] = []
    consecutive_stale = 0
    for m in range(1, 13):
        prepay = Decimal(balances.get(m, Decimal("0")))
        sweep = sweeps.get(m, {})
        sweep_amt = _dec(sweep.get("amount"))
        sweep_date = _parse(sweep.get("completedOn"))

        audit = MonthSweepAudit(
            year=year,
            month=m,
            prepay_balance=prepay,
            sweep_amount=sweep_amt,
            sweep_completed_on=sweep_date,
        )

        # Only evaluate months whose "sweep window" (first week of m+1) is past.
        window_past = (year, m) < (today.year, today.month) or (
            (year, m) == (today.year, today.month - 1) if today.day >= 7 else False
        )

        if window_past and prepay > tol and sweep_date is None:
            audit.findings.append(
                Finding(
                    "SWEEP_NOT_PERFORMED",
                    "critical",
                    f"Month {m}: prepay balance ${prepay} not swept to liability.",
                )
            )
            consecutive_stale += 1
        else:
            delta = sweep_amt - prepay
            if sweep_date is not None:
                if delta < -tol:
                    audit.findings.append(
                        Finding(
                            "SWEEP_UNDER",
                            "critical",
                            f"Month {m}: prepay ${prepay}, swept ${sweep_amt} (short ${-delta}).",
                        )
                    )
                elif delta > tol:
                    audit.findings.append(
                        Finding(
                            "SWEEP_OVER",
                            "warning",
                            f"Month {m}: swept ${sweep_amt} > prepay ${prepay} by ${delta}.",
                        )
                    )
                consecutive_stale = 0

        if consecutive_stale >= 3:
            audit.findings.append(
                Finding(
                    "PREPAY_BALANCE_GROWING",
                    "critical",
                    f"{consecutive_stale} consecutive months without a completed sweep.",
                )
            )

        months.append(audit)

    return PrepayLiabilityReport(
        client_id=client_id, year=year, as_of=today, months=months, tolerance=tol
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
