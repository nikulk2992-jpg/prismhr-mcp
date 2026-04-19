"""Terminated Employee Cleanup — workflow #4.

Post-termination checklist. Catches the cleanup tasks that fall
through the cracks and turn into surprise penalties, comp issues, or
PEO liability months later.

Findings per recently-terminated employee:
  - NO_FINAL_CHECK: no final paycheck voucher within 14 days of
    termination.
  - DEDUCTIONS_STILL_ACTIVE: scheduled deductions marked active on a
    termed employee.
  - BENEFITS_STILL_ACTIVE: benefit confirmation shows active coverage
    past termination.
  - NO_COBRA_RECORD: active benefits on file + no COBRA enrollee record.
  - PTO_NOT_PAID_OUT: positive PTO balance with no payout deduction.
  - ACH_STILL_ON_FILE: direct deposit record not retired.
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
class TerminatedEmployeeAudit:
    employee_id: str
    termination_date: date | None
    days_since_term: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)


@dataclass
class TerminatedCleanupReport:
    client_id: str
    as_of: date
    audits: list[TerminatedEmployeeAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_terminated_employees(
        self, client_id: str, lookback_days: int
    ) -> list[dict]: ...
    async def has_final_voucher(
        self, client_id: str, employee_id: str, term_date: date
    ) -> bool: ...
    async def get_scheduled_deductions(
        self, client_id: str, employee_id: str
    ) -> list[dict]: ...
    async def active_benefits(
        self, client_id: str, employee_id: str, as_of: date
    ) -> list[str]: ...
    async def has_cobra_record(self, client_id: str, employee_id: str) -> bool: ...
    async def get_pto_balance(
        self, client_id: str, employee_id: str
    ) -> Decimal: ...
    async def has_active_ach(self, client_id: str, employee_id: str) -> bool: ...


async def run_terminated_cleanup(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    lookback_days: int = 60,
    final_check_window: int = 14,
) -> TerminatedCleanupReport:
    today = as_of or date.today()
    termed = await reader.list_terminated_employees(client_id, lookback_days)
    audits: list[TerminatedEmployeeAudit] = []

    for emp in termed:
        eid = str(emp.get("employeeId") or "")
        if not eid:
            continue
        term = _parse(emp.get("statusDate") or emp.get("terminationDate"))
        days = (today - term).days if term else -1
        audit = TerminatedEmployeeAudit(
            employee_id=eid, termination_date=term, days_since_term=days
        )

        if term and days >= final_check_window:
            has_final = await reader.has_final_voucher(client_id, eid, term)
            if not has_final:
                audit.findings.append(
                    Finding(
                        "NO_FINAL_CHECK",
                        "critical",
                        f"Terminated {days}d ago; no final voucher within {final_check_window}d.",
                    )
                )

        deds = await reader.get_scheduled_deductions(client_id, eid)
        active_deds = [str(d.get("deductionCode") or d.get("code") or "") for d in deds if d.get("active", True)]
        if active_deds:
            audit.findings.append(
                Finding(
                    "DEDUCTIONS_STILL_ACTIVE",
                    "critical",
                    f"{len(active_deds)} active deduction(s) on termed employee: {active_deds[:3]}.",
                )
            )

        benefits = await reader.active_benefits(client_id, eid, today)
        if benefits:
            audit.findings.append(
                Finding(
                    "BENEFITS_STILL_ACTIVE",
                    "critical",
                    f"Active benefit plans on termed employee: {benefits[:3]}.",
                )
            )
            if not await reader.has_cobra_record(client_id, eid):
                audit.findings.append(
                    Finding(
                        "NO_COBRA_RECORD",
                        "critical",
                        "Benefits active but no COBRA enrollee record created.",
                    )
                )

        pto = await reader.get_pto_balance(client_id, eid)
        if pto > Decimal("0"):
            audit.findings.append(
                Finding(
                    "PTO_NOT_PAID_OUT",
                    "warning",
                    f"{pto} hours of PTO on final record (state law may require payout).",
                )
            )

        if await reader.has_active_ach(client_id, eid):
            audit.findings.append(
                Finding(
                    "ACH_STILL_ON_FILE",
                    "warning",
                    "Direct deposit record not retired.",
                )
            )

        audits.append(audit)

    return TerminatedCleanupReport(client_id=client_id, as_of=today, audits=audits)


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
