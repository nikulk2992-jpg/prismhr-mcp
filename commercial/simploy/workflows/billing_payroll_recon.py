"""Billing-vs-Payroll Reconciliation (client level) — workflow #34.

Per PrismHR's Accounting chapter: the billing side of the ledger
(client invoices) must tie to the payroll side (vouchers) for every
period. Drift is either revenue leakage (billed < payroll) or PEO
cost inflation (billed > payroll without justification).

Distinct from workflow #5 (per-enrollee plan-level wash audit) —
this one aggregates to the CLIENT+PERIOD level for controller review.

Findings per (client, month):
  - UNDERBILLED: billing total < payroll total beyond tolerance.
  - OVERBILLED: billing total > payroll total beyond tolerance (and
    no known surcharge explains it).
  - ZERO_BILL_WITH_PAYROLL: billing shows $0 for a month where
    payroll > 0 — invoice never ran.
  - BILLING_NO_PAYROLL: billing > 0 with no payroll in that month.
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
class MonthRecon:
    year: int
    month: int
    payroll_total: Decimal
    billing_total: Decimal
    findings: list[Finding] = field(default_factory=list)

    @property
    def delta(self) -> Decimal:
        return self.billing_total - self.payroll_total


@dataclass
class BillingPayrollReconReport:
    client_id: str
    year: int
    as_of: date
    months: list[MonthRecon]
    tolerance: Decimal

    @property
    def flagged(self) -> int:
        return sum(1 for m in self.months if m.findings)


class PrismHRReader(Protocol):
    async def billing_totals_by_month(self, client_id: str, year: int) -> dict[int, Decimal]: ...
    async def payroll_totals_by_month(self, client_id: str, year: int) -> dict[int, Decimal]: ...


async def run_billing_payroll_recon(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
    tolerance: Decimal | str | float = "50.00",
) -> BillingPayrollReconReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))

    billing = await reader.billing_totals_by_month(client_id, year)
    payroll = await reader.payroll_totals_by_month(client_id, year)

    months: list[MonthRecon] = []
    for m in range(1, 13):
        p = Decimal(billing.get(m, 0))
        q = Decimal(payroll.get(m, 0))
        recon = MonthRecon(year=year, month=m, payroll_total=q, billing_total=p)

        if q > tol and p == 0:
            recon.findings.append(
                Finding(
                    "ZERO_BILL_WITH_PAYROLL",
                    "critical",
                    f"Month {m}: payroll ${q}, billing $0 — invoice did not run.",
                )
            )
        elif p > tol and q == 0:
            recon.findings.append(
                Finding(
                    "BILLING_NO_PAYROLL",
                    "warning",
                    f"Month {m}: billing ${p}, payroll $0 — check for manual billing entry.",
                )
            )
        else:
            delta = p - q
            if delta < -tol:
                recon.findings.append(
                    Finding(
                        "UNDERBILLED",
                        "critical",
                        f"Month {m}: billing ${p} vs payroll ${q} (short ${-delta}).",
                    )
                )
            elif delta > tol:
                recon.findings.append(
                    Finding(
                        "OVERBILLED",
                        "warning",
                        f"Month {m}: billing ${p} vs payroll ${q} (over ${delta}).",
                    )
                )
        months.append(recon)

    return BillingPayrollReconReport(
        client_id=client_id,
        year=year,
        as_of=today,
        months=months,
        tolerance=tol,
    )
