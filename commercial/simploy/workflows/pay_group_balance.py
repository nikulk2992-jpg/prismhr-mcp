"""Pay Group Employee Balance — workflow #42.

Every active employee should be assigned to exactly one pay group so
they receive the right paycheck frequency + timing. This workflow
identifies employees in the wrong pay group (e.g., FT in a weekly
group when company is biweekly) or straddling groups.

Findings:
  - UNEXPECTED_FREQUENCY: employee pay group has a frequency that
    doesn't match the employee's employment-type default (e.g. FT
    assigned to weekly when company standard is biweekly).
  - INACTIVE_PAY_GROUP: employee pointing to a pay group marked inactive.
  - ORPHANED_GROUP: pay group with zero active employees (dead group).
  - UNDERSTAFFED_GROUP: pay group with < threshold employees (maybe
    consolidate with a sibling group).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class PayGroupBalanceAudit:
    pay_group_id: str
    frequency: str
    active_status: bool
    employee_count: int
    findings: list[Finding] = field(default_factory=list)


@dataclass
class PayGroupBalanceReport:
    client_id: str
    as_of: date
    audits: list[PayGroupBalanceAudit]
    mismatches: list[dict]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings) + (1 if self.mismatches else 0)


class PrismHRReader(Protocol):
    async def list_pay_groups_with_employees(
        self, client_id: str
    ) -> list[dict]: ...
    async def default_frequency_for_employment_type(
        self, client_id: str, employment_type: str
    ) -> str: ...


async def run_pay_group_balance(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    understaffed_threshold: int = 3,
) -> PayGroupBalanceReport:
    today = as_of or date.today()

    groups = await reader.list_pay_groups_with_employees(client_id)

    audits: list[PayGroupBalanceAudit] = []
    mismatches: list[dict] = []

    for g in groups:
        pg = str(g.get("payGroupId") or g.get("groupId") or "")
        freq = str(g.get("frequency") or g.get("payPeriod") or "").upper()
        active = bool(g.get("active", True))
        employees = g.get("employees") or []
        count = len(employees)

        audit = PayGroupBalanceAudit(
            pay_group_id=pg,
            frequency=freq,
            active_status=active,
            employee_count=count,
        )

        if count == 0 and active:
            audit.findings.append(
                Finding("ORPHANED_GROUP", "info", f"Pay group {pg} has no active employees.")
            )
        if count > 0 and not active:
            audit.findings.append(
                Finding(
                    "INACTIVE_PAY_GROUP",
                    "critical",
                    f"Pay group {pg} marked inactive but has {count} employees.",
                )
            )
        if 0 < count < understaffed_threshold:
            audit.findings.append(
                Finding(
                    "UNDERSTAFFED_GROUP",
                    "warning",
                    f"Pay group {pg} has only {count} employees — consider consolidation.",
                )
            )

        for emp in employees:
            eid = str(emp.get("employeeId") or "")
            etype = str(emp.get("employmentType") or "").upper()
            if etype:
                default = (await reader.default_frequency_for_employment_type(client_id, etype)).upper()
                if default and default != freq:
                    mismatches.append({
                        "employeeId": eid,
                        "payGroup": pg,
                        "groupFrequency": freq,
                        "employmentType": etype,
                        "expectedFrequency": default,
                    })

        audits.append(audit)

    if mismatches:
        # Attach a single summary finding to the first audit as a pointer
        # (detailed list is in the mismatches attribute).
        audits[0].findings.append(
            Finding(
                "UNEXPECTED_FREQUENCY",
                "warning",
                f"{len(mismatches)} employees in pay groups whose frequency doesn't match their employment-type default. See report.mismatches.",
            )
        )

    return PayGroupBalanceReport(
        client_id=client_id, as_of=today, audits=audits, mismatches=mismatches
    )
