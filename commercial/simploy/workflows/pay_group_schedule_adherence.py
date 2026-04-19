"""Pay Group Schedule Adherence — workflow #9.

Every pay group has a schedule: pay period end → call-in date → pay
date. Missing the call-in or run cadence = late paychecks.

Findings per pay group:
  - LATE_CALL_IN: current period past call-in date but batch not yet
    initialized.
  - LATE_FINALIZE: batch past its process date and not yet POSTCOMP.
  - SCHEDULE_OUT_OF_DATE: schedule effective date > 1 year ago —
    stale, annual update recommended.
  - NO_SCHEDULE: pay group defined but no schedule attached.
  - EMPLOYEES_WITHOUT_PAY_GROUP: active employees with no pay group
    assignment (payroll can't run for them).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class PayGroupAudit:
    pay_group_id: str
    schedule_id: str
    schedule_effective: date | None
    current_period_end: date | None
    call_in_date: date | None
    pay_date: date | None
    batch_status: str
    employees_in_group: int
    findings: list[Finding] = field(default_factory=list)


@dataclass
class PayGroupAdherenceReport:
    client_id: str
    as_of: date
    audits: list[PayGroupAudit]
    orphan_employees: list[str]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings) + (1 if self.orphan_employees else 0)


class PrismHRReader(Protocol):
    async def list_pay_groups(self, client_id: str) -> list[dict]: ...
    async def employees_without_pay_group(
        self, client_id: str
    ) -> list[str]: ...


async def run_pay_group_schedule_adherence(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    stale_schedule_days: int = 365,
) -> PayGroupAdherenceReport:
    today = as_of or date.today()
    rows = await reader.list_pay_groups(client_id)
    orphans = await reader.employees_without_pay_group(client_id)

    audits: list[PayGroupAudit] = []
    for r in rows:
        pg = str(r.get("payGroupId") or r.get("groupId") or "")
        sched = str(r.get("scheduleId") or "")
        sched_eff = _parse(r.get("scheduleEffectiveDate"))
        period_end = _parse(r.get("currentPeriodEnd"))
        call_in = _parse(r.get("callInDate") or r.get("callInDueDate"))
        pay_date = _parse(r.get("payDate"))
        status = str(r.get("currentBatchStatus") or "").upper()
        emp_count = int(r.get("employeeCount") or 0)

        audit = PayGroupAudit(
            pay_group_id=pg,
            schedule_id=sched,
            schedule_effective=sched_eff,
            current_period_end=period_end,
            call_in_date=call_in,
            pay_date=pay_date,
            batch_status=status,
            employees_in_group=emp_count,
        )

        if not sched:
            audit.findings.append(
                Finding("NO_SCHEDULE", "critical", f"Pay group {pg} has no schedule attached.")
            )
        if call_in and today > call_in and status in {"", "TS.READY", "TS.ENTRY"}:
            audit.findings.append(
                Finding(
                    "LATE_CALL_IN",
                    "critical",
                    f"Call-in date was {call_in.isoformat()}; batch not initialized.",
                )
            )
        if pay_date and today > pay_date and status not in {"POSTCOMP", "COMP", "PRINTCOMP"}:
            audit.findings.append(
                Finding(
                    "LATE_FINALIZE",
                    "critical",
                    f"Pay date {pay_date.isoformat()} past; batch status {status}.",
                )
            )
        if sched_eff and (today - sched_eff).days > stale_schedule_days:
            audit.findings.append(
                Finding(
                    "SCHEDULE_OUT_OF_DATE",
                    "warning",
                    f"Schedule effective {sched_eff.isoformat()} — over {stale_schedule_days}d old.",
                )
            )

        audits.append(audit)

    return PayGroupAdherenceReport(
        client_id=client_id, as_of=today, audits=audits, orphan_employees=orphans
    )


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
