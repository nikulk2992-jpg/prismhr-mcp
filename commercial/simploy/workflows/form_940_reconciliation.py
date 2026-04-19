"""940 Annual FUTA Reconciliation — workflow #57.

IRS Form 940 is the annual federal unemployment tax return. FUTA
rate is 6.0% on the first $7,000 of wages per employee per year,
usually reduced to 0.6% via the state credit (2.4% offset when
the state is credit-certified + deposits on time).

Findings:
  - FUTA_WAGES_MISMATCH: sum of capped FUTA wages != 940 Line 4/5.
  - FUTA_TAX_MISMATCH: calculated tax != 940 reported tax.
  - CREDIT_REDUCTION_STATE_MISSING: state is on the IRS credit-
    reduction list but 940 Part 3 doesn't reflect it (extra 0.3%
    per year in the reduced state).
  - NO_940_RECORD: wages paid but no 940 on file.
  - EXCESSIVE_WAGES_PER_EMPLOYEE: capped wages > $7,000 for a
    single employee (data error — should be clamped per employee).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

_FUTA_CAP_PER_EMPLOYEE = Decimal("7000")
_FUTA_RATE_GROSS = Decimal("0.060")
_FUTA_RATE_NET = Decimal("0.006")  # with full state credit


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class Form940Recon:
    year: int
    voucher_total_wages: Decimal
    voucher_futa_wages: Decimal  # capped at $7K/employee
    calc_futa_tax_net: Decimal
    reported_futa_wages: Decimal
    reported_futa_tax: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class Form940Report:
    client_id: str
    year: int
    as_of: date
    recon: Form940Recon
    tolerance: Decimal


class PrismHRReader(Protocol):
    async def list_employee_annual_wages(
        self, client_id: str, year: int
    ) -> list[dict]: ...
    async def get_form940(self, client_id: str, year: int) -> dict: ...
    async def list_credit_reduction_states(self, year: int) -> list[str]: ...
    async def list_employer_states(self, client_id: str, year: int) -> list[str]: ...


async def run_form_940_reconciliation(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
) -> Form940Report:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))

    annual_rows = await reader.list_employee_annual_wages(client_id, year)
    total_wages = Decimal("0")
    futa_wages = Decimal("0")
    per_emp_issues: list[str] = []
    for r in annual_rows:
        eid = str(r.get("employeeId") or "")
        wages = _dec(r.get("totalWages") or r.get("grossWages"))
        capped = min(wages, _FUTA_CAP_PER_EMPLOYEE)
        total_wages += wages
        futa_wages += capped
        # If the record *itself* reports a FUTA wage above $7K per
        # employee, that's an upstream data error.
        reported_capped = _dec(r.get("futaWages"))
        if reported_capped > _FUTA_CAP_PER_EMPLOYEE + tol:
            per_emp_issues.append(eid)

    calc_tax = (futa_wages * _FUTA_RATE_NET).quantize(Decimal("0.01"))

    form940 = await reader.get_form940(client_id, year)
    reported_wages = _dec(form940.get("totalTaxableFutaWages") or form940.get("line5"))
    reported_tax = _dec(form940.get("futaTaxBeforeAdjustments") or form940.get("line12"))

    recon = Form940Recon(
        year=year,
        voucher_total_wages=total_wages,
        voucher_futa_wages=futa_wages,
        calc_futa_tax_net=calc_tax,
        reported_futa_wages=reported_wages,
        reported_futa_tax=reported_tax,
    )

    if not form940 and total_wages > 0:
        recon.findings.append(
            Finding(
                "NO_940_RECORD",
                "critical",
                f"Total wages ${total_wages} but no Form 940 on file.",
            )
        )
    else:
        if (reported_wages - futa_wages).copy_abs() > tol:
            recon.findings.append(
                Finding(
                    "FUTA_WAGES_MISMATCH",
                    "critical",
                    f"940 FUTA wages ${reported_wages}, calc ${futa_wages}.",
                )
            )
        if (reported_tax - calc_tax).copy_abs() > tol:
            recon.findings.append(
                Finding(
                    "FUTA_TAX_MISMATCH",
                    "critical",
                    f"940 FUTA tax ${reported_tax}, calc ${calc_tax}.",
                )
            )

    if per_emp_issues:
        recon.findings.append(
            Finding(
                "EXCESSIVE_WAGES_PER_EMPLOYEE",
                "warning",
                f"{len(per_emp_issues)} employees have FUTA wages > $7,000 in source data.",
            )
        )

    # Credit-reduction states
    cr_states = {s.upper() for s in await reader.list_credit_reduction_states(year)}
    employer_states = {s.upper() for s in await reader.list_employer_states(client_id, year)}
    affected = cr_states & employer_states
    if affected:
        part3 = form940.get("part3CreditReductionStates") or []
        declared = {str(s).upper() for s in part3}
        missing = affected - declared
        if missing:
            recon.findings.append(
                Finding(
                    "CREDIT_REDUCTION_STATE_MISSING",
                    "critical",
                    f"Operating in credit-reduction state(s) {sorted(missing)} — Part 3 reduction not declared.",
                )
            )

    return Form940Report(
        client_id=client_id,
        year=year,
        as_of=today,
        recon=recon,
        tolerance=tol,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
