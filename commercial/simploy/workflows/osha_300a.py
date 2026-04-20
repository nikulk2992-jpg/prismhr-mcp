"""OSHA 300A Summary Assist — workflow #29.

Employers with 10+ employees in covered industries must post Form
300A summary (Feb 1 – Apr 30) and e-file to OSHA by Mar 2. The
form summarizes the year's Form 300 log:
- Total cases
- Cases with days away / restriction / transfer (DART)
- Cases with medical-only treatment
- Total DART days
- Total case-count days
- Breakdown by injury/illness type

PrismHR stores incident data; this workflow produces the 300A
numbers + flags common inconsistencies.

Findings:
  - CASE_COUNT_INCONSISTENT: sum of type-breakdown != total cases.
  - MISSING_INCIDENT_TYPE: incident with no type code.
  - DAYS_AWAY_WITHOUT_CASE: days-away reported on a case marked
    medical-only.
  - NEGATIVE_COUNT: any count field < 0.
  - UNDER_10_EMPLOYEES: reminder — 300A not required if < 10 FTE.
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
class OSHA300ASummary:
    total_cases: int
    cases_with_days_away: int
    cases_with_restriction_transfer: int
    cases_medical_only: int
    total_dart_days: int
    total_case_days: int
    total_employees: int
    total_hours_worked: Decimal
    by_type: dict[str, int]
    findings: list[Finding] = field(default_factory=list)


@dataclass
class OSHA300AReport:
    client_id: str
    year: int
    as_of: date
    summary: OSHA300ASummary


class PrismHRReader(Protocol):
    async def get_osha300a_stats(
        self, client_id: str, year: int
    ) -> dict: ...


async def run_osha_300a_assist(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
) -> OSHA300AReport:
    today = as_of or date.today()
    raw = await reader.get_osha300a_stats(client_id, year)

    total_cases = int(raw.get("totalCases") or 0)
    days_away = int(raw.get("casesWithDaysAway") or 0)
    restriction_transfer = int(raw.get("casesWithRestriction") or 0)
    medical_only = int(raw.get("casesMedicalOnly") or 0)
    dart_days = int(raw.get("totalDartDays") or 0)
    case_days = int(raw.get("totalCaseDays") or 0)
    employees = int(raw.get("totalEmployees") or 0)
    hours = _dec(raw.get("totalHoursWorked"))
    by_type = {k: int(v) for k, v in (raw.get("byType") or {}).items()}

    summary = OSHA300ASummary(
        total_cases=total_cases,
        cases_with_days_away=days_away,
        cases_with_restriction_transfer=restriction_transfer,
        cases_medical_only=medical_only,
        total_dart_days=dart_days,
        total_case_days=case_days,
        total_employees=employees,
        total_hours_worked=hours,
        by_type=by_type,
    )

    if employees < 10:
        summary.findings.append(
            Finding(
                "UNDER_10_EMPLOYEES",
                "info",
                f"Only {employees} employees — Form 300A posting typically not required.",
            )
        )

    type_sum = sum(by_type.values())
    if by_type and type_sum != total_cases:
        summary.findings.append(
            Finding(
                "CASE_COUNT_INCONSISTENT",
                "critical",
                f"Type breakdown sums to {type_sum}, but total cases = {total_cases}.",
            )
        )

    for count_val, label in (
        (total_cases, "totalCases"),
        (days_away, "casesWithDaysAway"),
        (dart_days, "totalDartDays"),
        (case_days, "totalCaseDays"),
    ):
        if count_val < 0:
            summary.findings.append(
                Finding("NEGATIVE_COUNT", "critical", f"{label} is negative ({count_val}).")
            )

    if medical_only > 0 and days_away > 0:
        # Cases labeled medical-only should not count toward days-away
        if raw.get("daysAwayIncludedOnMedicalOnly"):
            summary.findings.append(
                Finding(
                    "DAYS_AWAY_WITHOUT_CASE",
                    "critical",
                    "Medical-only cases reporting days-away — recategorize or zero out the days.",
                )
            )

    # Missing-type check
    missing_type = int(raw.get("incidentsMissingType") or 0)
    if missing_type > 0:
        summary.findings.append(
            Finding(
                "MISSING_INCIDENT_TYPE",
                "warning",
                f"{missing_type} incident(s) have no type code.",
            )
        )

    return OSHA300AReport(client_id=client_id, year=year, as_of=today, summary=summary)


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
