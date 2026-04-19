"""Dependent Coverage Age-Out — workflow #18.

ACA + most employer plans require dropping dependents from coverage
at age 26 (or whenever the plan specifies). Missing the transition =
silent premium overpayment + potential audit exposure.

Findings:
  - AGED_OUT: dependent currently past the plan age threshold but
    still listed on active coverage.
  - AGING_OUT_90D: dependent turns the threshold age in next 90d.
  - AGING_OUT_30D: within 30d — urgent notice window.
  - NO_DOB_ON_FILE: dependent with no DOB — cannot evaluate.
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
class DependentAgeAudit:
    employee_id: str
    dependent_id: str
    dependent_name: str
    dependent_dob: date | None
    current_age: int | None
    age_threshold: int
    findings: list[Finding] = field(default_factory=list)


@dataclass
class DependentAgeOutReport:
    client_id: str
    as_of: date
    audits: list[DependentAgeAudit]

    @property
    def total(self) -> int:
        return len(self.audits)

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_covered_dependents(self, client_id: str) -> list[dict]: ...


async def run_dependent_age_out(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    age_threshold: int = 26,
    warning_days: int = 90,
    urgent_days: int = 30,
) -> DependentAgeOutReport:
    today = as_of or date.today()
    deps = await reader.list_covered_dependents(client_id)

    audits: list[DependentAgeAudit] = []
    for d in deps:
        dep_id = str(d.get("dependentId") or d.get("id") or "")
        eid = str(d.get("employeeId") or "")
        name = str(d.get("name") or f"{d.get('firstName','')} {d.get('lastName','')}").strip()
        dob = _parse(d.get("dob") or d.get("birthDate"))

        audit = DependentAgeAudit(
            employee_id=eid,
            dependent_id=dep_id,
            dependent_name=name,
            dependent_dob=dob,
            current_age=None,
            age_threshold=age_threshold,
        )

        if dob is None:
            audit.findings.append(
                Finding("NO_DOB_ON_FILE", "warning", "Dependent has no DOB — cannot compute age-out.")
            )
            audits.append(audit)
            continue

        # Compute current age + date of next birthday reaching threshold.
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        audit.current_age = age
        threshold_birthday = date(dob.year + age_threshold, dob.month, dob.day)
        days_to_threshold = (threshold_birthday - today).days

        if age >= age_threshold:
            audit.findings.append(
                Finding(
                    "AGED_OUT",
                    "critical",
                    f"Dependent is {age} (threshold {age_threshold}) — drop coverage.",
                )
            )
        elif 0 <= days_to_threshold <= urgent_days:
            audit.findings.append(
                Finding(
                    "AGING_OUT_30D",
                    "critical",
                    f"Dependent turns {age_threshold} in {days_to_threshold}d on {threshold_birthday.isoformat()}.",
                )
            )
        elif 0 <= days_to_threshold <= warning_days:
            audit.findings.append(
                Finding(
                    "AGING_OUT_90D",
                    "warning",
                    f"Dependent turns {age_threshold} in {days_to_threshold}d — send notice.",
                )
            )

        audits.append(audit)

    return DependentAgeOutReport(client_id=client_id, as_of=today, audits=audits)


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
