"""Client Go-Live Readiness — workflow #40.

Runs the Simploy onboarding checklist against a newly-created client
and flags every setup gap that would block or disrupt first payroll.
Derived from the PrismHR Client Details + Pay Groups + Benefit Plans
setup chapters.

Findings:
  - NO_PAY_GROUP: client has no pay group configured.
  - NO_PAYROLL_SCHEDULE: pay group exists but no schedule attached.
  - NO_OWNERSHIP: client has no ownership/FEIN information.
  - NO_LOCATION_DETAILS: client missing required location data.
  - NO_SUTA_STATE: client has no SUTA state tax registration.
  - NO_ACTIVE_EMPLOYEES: no active employees on payroll.
  - NO_BENEFIT_PLANS: client has no benefit plans set up (may be
    intentional; warning not critical).
  - NO_RETIREMENT_PLAN: client has no retirement plan (warning).
"""

from __future__ import annotations

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
class GoLiveReadinessReport:
    client_id: str
    as_of: date
    checklist: dict[str, bool]
    findings: list[Finding] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)

    @property
    def score(self) -> float:
        if not self.checklist:
            return 0.0
        done = sum(1 for v in self.checklist.values() if v)
        return round(done / len(self.checklist) * 100.0, 1)


class PrismHRReader(Protocol):
    async def get_client_master(self, client_id: str) -> dict: ...
    async def get_client_ownership(self, client_id: str) -> dict: ...
    async def get_pay_groups(self, client_id: str) -> list[dict]: ...
    async def get_payroll_schedule(self, client_id: str) -> list[dict]: ...
    async def get_client_location_details(self, client_id: str) -> dict: ...
    async def count_active_employees(self, client_id: str) -> int: ...
    async def get_benefit_plans(self, client_id: str) -> list[dict]: ...
    async def get_retirement_plan_list(self, client_id: str) -> list[dict]: ...


async def run_client_golive_readiness(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
) -> GoLiveReadinessReport:
    today = as_of or date.today()

    client_master = await reader.get_client_master(client_id)
    ownership = await reader.get_client_ownership(client_id)
    pay_groups = await reader.get_pay_groups(client_id)
    schedule = await reader.get_payroll_schedule(client_id)
    location = await reader.get_client_location_details(client_id)
    employee_count = await reader.count_active_employees(client_id)
    benefit_plans = await reader.get_benefit_plans(client_id)
    retirement_plans = await reader.get_retirement_plan_list(client_id)

    checklist = {
        "client_master": bool(client_master),
        "ownership": bool(ownership.get("fein") or ownership.get("federalEin")),
        "pay_group": bool(pay_groups),
        "payroll_schedule": bool(schedule),
        "location_details": bool(location.get("state")),
        "suta_state": bool(location.get("sutaState") or location.get("state")),
        "active_employees": employee_count > 0,
        "benefit_plans": bool(benefit_plans),
        "retirement_plan": bool(retirement_plans),
    }

    findings: list[Finding] = []

    if not checklist["pay_group"]:
        findings.append(Finding("NO_PAY_GROUP", "critical", "Client has no pay group configured."))
    if not checklist["payroll_schedule"]:
        findings.append(
            Finding("NO_PAYROLL_SCHEDULE", "critical", "No payroll schedule attached — first run will fail.")
        )
    if not checklist["ownership"]:
        findings.append(Finding("NO_OWNERSHIP", "critical", "Missing FEIN / ownership info."))
    if not checklist["location_details"]:
        findings.append(Finding("NO_LOCATION_DETAILS", "critical", "No client location details."))
    if not checklist["suta_state"]:
        findings.append(
            Finding("NO_SUTA_STATE", "critical", "No SUTA state tax registration recorded.")
        )
    if not checklist["active_employees"]:
        findings.append(
            Finding(
                "NO_ACTIVE_EMPLOYEES",
                "warning",
                "No active employees — client not ready for payroll without hires.",
            )
        )
    if not checklist["benefit_plans"]:
        findings.append(
            Finding("NO_BENEFIT_PLANS", "warning", "No benefit plans set up (may be intentional).")
        )
    if not checklist["retirement_plan"]:
        findings.append(
            Finding("NO_RETIREMENT_PLAN", "warning", "No retirement plan set up (may be intentional).")
        )

    return GoLiveReadinessReport(
        client_id=client_id,
        as_of=today,
        checklist=checklist,
        findings=findings,
    )
