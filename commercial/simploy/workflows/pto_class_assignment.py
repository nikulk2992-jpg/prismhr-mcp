"""PTO Class Assignment Sanity — workflow #47.

Per PrismHR: each employee gets a PTO class that drives accrual +
cap. Common failures: anniversary-date bumps don't run, new hires
stuck on default / part-time class, PTO class points to a plan that
was retired.

Findings:
  - MISSING_PTO_CLASS: active employee has no class assigned.
  - STALE_ANNIVERSARY_BUMP: tenure indicates a bumped accrual tier
    but the employee's class wasn't updated.
  - CLASS_POINTS_TO_RETIRED_PLAN: class references a PTO plan no
    longer on file.
  - UNUSUAL_CLASS_FOR_EMPLOYMENT_TYPE: FT employee on a part-time
    PTO class or vice versa.
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
class PTOClassAudit:
    employee_id: str
    employment_type: str
    hire_date: date | None
    current_class: str
    expected_class: str
    findings: list[Finding] = field(default_factory=list)


@dataclass
class PTOClassReport:
    client_id: str
    as_of: date
    audits: list[PTOClassAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_employees_with_pto_class(
        self, client_id: str
    ) -> list[dict]: ...
    async def get_retired_pto_plans(self, client_id: str) -> set[str]: ...
    async def expected_pto_class_for_tenure(
        self, client_id: str, employment_type: str, years_of_service: int
    ) -> str: ...


async def run_pto_class_assignment(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
) -> PTOClassReport:
    today = as_of or date.today()
    rows = await reader.list_employees_with_pto_class(client_id)
    retired_plans = await reader.get_retired_pto_plans(client_id)

    audits: list[PTOClassAudit] = []
    for r in rows:
        eid = str(r.get("employeeId") or "")
        etype = str(r.get("employmentType") or "").upper()
        hire = _parse(r.get("hireDate") or r.get("lastHireDate"))
        class_code = str(r.get("ptoClass") or "").upper()
        plan_id = str(r.get("ptoPlanId") or "")

        audit = PTOClassAudit(
            employee_id=eid,
            employment_type=etype,
            hire_date=hire,
            current_class=class_code,
            expected_class="",
        )

        if not class_code:
            audit.findings.append(
                Finding("MISSING_PTO_CLASS", "critical", "No PTO class assigned.")
            )
        else:
            if plan_id and plan_id in retired_plans:
                audit.findings.append(
                    Finding(
                        "CLASS_POINTS_TO_RETIRED_PLAN",
                        "critical",
                        f"Class {class_code} references retired plan {plan_id}.",
                    )
                )

            if etype and hire:
                years = (today - hire).days // 365
                expected = (
                    await reader.expected_pto_class_for_tenure(client_id, etype, years)
                ).upper()
                audit.expected_class = expected
                if expected and expected != class_code:
                    audit.findings.append(
                        Finding(
                            "STALE_ANNIVERSARY_BUMP",
                            "warning",
                            f"After {years}y service on a {etype} track, expected class {expected}; employee on {class_code}.",
                        )
                    )

            ft_signals = ("FT" in class_code or "FULL" in class_code)
            pt_signals = ("PT" in class_code or "PART" in class_code)
            if etype in {"FT", "FULLTIME", "FULL_TIME"} and pt_signals:
                audit.findings.append(
                    Finding(
                        "UNUSUAL_CLASS_FOR_EMPLOYMENT_TYPE",
                        "warning",
                        f"FT employee on part-time-style class {class_code}.",
                    )
                )
            if etype in {"PT", "PARTTIME", "PART_TIME"} and ft_signals:
                audit.findings.append(
                    Finding(
                        "UNUSUAL_CLASS_FOR_EMPLOYMENT_TYPE",
                        "warning",
                        f"PT employee on FT-style class {class_code}.",
                    )
                )

        audits.append(audit)

    return PTOClassReport(client_id=client_id, as_of=today, audits=audits)


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
