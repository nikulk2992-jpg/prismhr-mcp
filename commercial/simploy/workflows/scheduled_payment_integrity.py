"""Scheduled-Payment Integrity — workflow #10.

Scheduled payments (one-time bonuses, retro adjustments, special pays)
are flagged on the employee record and expected to land in the next
payroll cycle. Common failure: scheduled payment sits on the record
for weeks without executing because the effective date slipped, the
pay code got deactivated, or the batch ran before the effective date.

Findings:
  - OVERDUE: scheduled effective date past N days without execution.
  - DEACTIVATED_PAY_CODE: scheduled payment references a pay code
    that's currently inactive.
  - NEGATIVE_AMOUNT_NO_APPROVER: negative (claw-back) scheduled
    payment without an approver.
  - AFTER_TERM: scheduled effective date past the employee's
    termination date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class ScheduledPaymentAudit:
    payment_id: str
    employee_id: str
    effective_date: date | None
    amount: Decimal
    pay_code: str
    executed: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ScheduledPaymentReport:
    client_id: str
    as_of: date
    audits: list[ScheduledPaymentAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_scheduled_payments(self, client_id: str) -> list[dict]: ...
    async def is_pay_code_active(self, client_id: str, code: str) -> bool: ...
    async def get_termination_date(
        self, client_id: str, employee_id: str
    ) -> date | None: ...


async def run_scheduled_payment_integrity(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    overdue_days: int = 7,
) -> ScheduledPaymentReport:
    today = as_of or date.today()
    rows = await reader.list_scheduled_payments(client_id)

    audits: list[ScheduledPaymentAudit] = []
    for r in rows:
        pid = str(r.get("paymentId") or r.get("id") or "")
        eid = str(r.get("employeeId") or "")
        eff = _parse(r.get("effectiveDate"))
        amt = _dec(r.get("amount"))
        code = str(r.get("payCode") or r.get("paycode") or "")
        executed = bool(r.get("executed") or r.get("isPosted"))
        approver = str(r.get("approver") or "").strip()

        audit = ScheduledPaymentAudit(
            payment_id=pid,
            employee_id=eid,
            effective_date=eff,
            amount=amt,
            pay_code=code,
            executed=executed,
        )

        if eff and not executed and (today - eff).days > overdue_days:
            audit.findings.append(
                Finding(
                    "OVERDUE",
                    "critical",
                    f"Effective {eff.isoformat()}, {(today - eff).days}d past without execution.",
                )
            )
        if code and not await reader.is_pay_code_active(client_id, code):
            audit.findings.append(
                Finding(
                    "DEACTIVATED_PAY_CODE",
                    "critical",
                    f"Pay code {code} is inactive — schedule will not fire.",
                )
            )
        if amt < 0 and not approver:
            audit.findings.append(
                Finding(
                    "NEGATIVE_AMOUNT_NO_APPROVER",
                    "critical",
                    f"Negative scheduled payment ${amt} with no approver.",
                )
            )
        term = await reader.get_termination_date(client_id, eid) if eid else None
        if eff and term and eff > term:
            audit.findings.append(
                Finding(
                    "AFTER_TERM",
                    "warning",
                    f"Scheduled effective {eff.isoformat()} past termination {term.isoformat()}.",
                )
            )
        audits.append(audit)

    return ScheduledPaymentReport(client_id=client_id, as_of=today, audits=audits)


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
