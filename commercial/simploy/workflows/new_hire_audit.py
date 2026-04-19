"""New Hire Onboarding Audit — workflow #1.

Pulls new hires at a client within a lookback window and flags missing
required setup:
  - no SSN
  - no home address
  - E-Verify status not cleared
  - no scheduled deductions on file (informational)
  - garnishment present but setup flag incomplete

I-9 expiration tracking is intentionally NOT included in this v1 —
`getEverifyStatus` in our verified surface exposes the E-Verify case
status but not a reliable I-9 document expiration field across all
tenants. Add once we verify which field ships the expiration date.

Input: client_id, lookback_days.
Output: structured per-employee findings with severity and remediation.

Data sources (all verified reads against the OSS core's catalog):
  - employee.v1.getEmployeeList      (roster + hire dates)
  - employee.v1.getEmployee          (detail incl. SSN)
  - employee.v1.getAddressInfo       (address)
  - employee.v1.getEverifyStatus     (E-Verify case status)
  - employee.v1.getScheduledDeductions
  - employee.v1.checkForGarnishments
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol


Severity = str  # "critical" | "warning" | "info"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class EmployeeAudit:
    employee_id: str
    first_name: str
    last_name: str
    hire_date: date | None
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)


@dataclass
class NewHireAuditReport:
    client_id: str
    as_of: date
    lookback_days: int
    employees: list[EmployeeAudit]

    @property
    def total(self) -> int:
        return len(self.employees)

    @property
    def passed(self) -> int:
        return sum(1 for e in self.employees if e.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed


class PrismHRReader(Protocol):
    """Minimal read surface needed by this workflow.

    The commercial server wires this to the OSS core's `PrismHRClient`;
    tests stub it with an in-memory fake.
    """

    async def get_employee_list(self, client_id: str, hired_since: date) -> list[dict]: ...
    async def get_employee(self, client_id: str, employee_id: str) -> dict: ...
    async def get_address(self, client_id: str, employee_id: str) -> dict: ...
    async def get_everify(self, client_id: str, employee_id: str) -> dict: ...
    async def get_scheduled_deductions(self, client_id: str, employee_id: str) -> dict: ...
    async def check_garnishments(self, client_id: str, employee_id: str) -> dict: ...


async def run_new_hire_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    lookback_days: int = 30,
    as_of: date | None = None,
) -> NewHireAuditReport:
    """Execute the new-hire audit and return a structured report.

    Pure orchestration — all PrismHR I/O goes through `reader`. No
    direct HTTP here so unit tests can exercise logic offline.
    """
    today = as_of or date.today()
    hired_since = today - timedelta(days=lookback_days)

    roster = await reader.get_employee_list(client_id, hired_since)
    audits: list[EmployeeAudit] = []
    for emp in roster:
        eid = emp["employeeId"]
        audit = EmployeeAudit(
            employee_id=eid,
            first_name=emp.get("firstName", ""),
            last_name=emp.get("lastName", ""),
            hire_date=_parse_date(emp.get("hireDate")),
        )

        # Detail + gates
        detail = await reader.get_employee(client_id, eid)
        if not detail.get("ssn"):
            audit.findings.append(Finding("MISSING_SSN", "critical", "No SSN on file."))

        addr = await reader.get_address(client_id, eid)
        if not addr.get("line1"):
            audit.findings.append(Finding("MISSING_ADDRESS", "critical", "Home address not set."))

        ev = await reader.get_everify(client_id, eid)
        ev_status = (ev.get("everifyStatus") or "").upper()
        if ev_status not in {"AUTHORIZED", "EMPLOYMENT_AUTHORIZED"}:
            audit.findings.append(
                Finding(
                    "EVERIFY_NOT_CLEARED",
                    "critical" if ev_status in {"", "TNC", "FNC"} else "warning",
                    f"E-Verify status is {ev_status or 'UNSET'}.",
                )
            )

        deds = await reader.get_scheduled_deductions(client_id, eid)
        if not (deds.get("scheduledDeductions") or []):
            audit.findings.append(
                Finding("NO_DEDUCTIONS_SCHEDULED", "info", "No scheduled deductions yet (may be expected).")
            )

        garn = await reader.check_garnishments(client_id, eid)
        if garn.get("hasGarnishments") and not garn.get("setupComplete"):
            audit.findings.append(
                Finding(
                    "GARNISHMENT_SETUP_INCOMPLETE",
                    "critical",
                    "Garnishment present but setup flag is not complete.",
                )
            )

        audits.append(audit)

    return NewHireAuditReport(
        client_id=client_id,
        as_of=today,
        lookback_days=lookback_days,
        employees=audits,
    )


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None
