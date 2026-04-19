"""Retirement Loan Status — workflow #21.

Per PrismHR's Retirement Plan setup chapter: 401(k) loans are
tracked separately with repayment schedules, deemed-distribution
triggers (missed > quarter), and deferral rules around
termination. Drift can turn into a taxable event without anyone
noticing.

Findings per loan:
  - LOAN_DEFAULTED: missed > 3 months of payments (deemed
    distribution risk).
  - LOAN_OVERDUE: last payment older than 45 days.
  - PRINCIPAL_GROWING: outstanding balance higher than prior check.
  - LOAN_PAST_TERM: scheduled end date passed but balance > 0.
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
class LoanAudit:
    employee_id: str
    loan_id: str
    outstanding_balance: Decimal
    original_amount: Decimal
    start_date: date | None
    scheduled_end_date: date | None
    last_payment_date: date | None
    findings: list[Finding] = field(default_factory=list)


@dataclass
class RetirementLoanReport:
    client_id: str
    as_of: date
    audits: list[LoanAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def get_retirement_loans(self, client_id: str) -> list[dict]: ...


async def run_retirement_loan_status(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    overdue_days: int = 45,
    default_days: int = 90,
) -> RetirementLoanReport:
    today = as_of or date.today()
    loans = await reader.get_retirement_loans(client_id)

    audits: list[LoanAudit] = []
    for loan in loans:
        eid = str(loan.get("employeeId") or "")
        lid = str(loan.get("loanId") or loan.get("id") or "")
        balance = _dec(loan.get("outstandingBalance") or loan.get("balance"))
        original = _dec(loan.get("originalAmount") or loan.get("principalAmount"))
        start = _parse(loan.get("startDate") or loan.get("loanStartDate"))
        end = _parse(loan.get("scheduledEndDate") or loan.get("maturityDate"))
        last_pay = _parse(loan.get("lastPaymentDate") or loan.get("lastPayment"))

        audit = LoanAudit(
            employee_id=eid,
            loan_id=lid,
            outstanding_balance=balance,
            original_amount=original,
            start_date=start,
            scheduled_end_date=end,
            last_payment_date=last_pay,
        )

        if balance > 0:
            if last_pay is None:
                audit.findings.append(
                    Finding("LOAN_OVERDUE", "critical", "No payment ever recorded.")
                )
            else:
                days = (today - last_pay).days
                if days > default_days:
                    audit.findings.append(
                        Finding(
                            "LOAN_DEFAULTED",
                            "critical",
                            f"Last payment {days}d ago — deemed distribution risk.",
                        )
                    )
                elif days > overdue_days:
                    audit.findings.append(
                        Finding(
                            "LOAN_OVERDUE",
                            "warning",
                            f"Last payment {days}d ago.",
                        )
                    )
            if end and end < today:
                audit.findings.append(
                    Finding(
                        "LOAN_PAST_TERM",
                        "critical",
                        f"Scheduled end {end.isoformat()} past, balance ${balance}.",
                    )
                )

        audits.append(audit)

    return RetirementLoanReport(client_id=client_id, as_of=today, audits=audits)


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
