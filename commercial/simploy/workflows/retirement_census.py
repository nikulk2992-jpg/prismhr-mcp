"""Retirement Census Generator — workflow #23.

Annual 401(k) non-discrimination testing requires a full participant
census: every employee, active + terminated, with YTD comp, deferrals,
match, hours, ownership info. Produces the data packet that feeds
into ADP / ACP / 410(b) testing + Form 5500.

Output: structured census rows + a flag list of problem records that
the TPA will reject.

Findings:
  - MISSING_HIRE_DATE: participant has no hire date on file.
  - NEGATIVE_WAGES: YTD gross reported as negative.
  - MISSING_DOB: needed for testing buckets.
  - OWNERSHIP_MISSING: >5% owners must be flagged; any participant
    whose ownership status is blank gets flagged for review.
  - HCE_COMP_INCONSISTENT: flagged as Highly Compensated Employee
    but YTD comp < IRS HCE threshold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

# IRS HCE compensation threshold
_HCE_THRESHOLD_2026 = Decimal("155000")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class CensusRow:
    employee_id: str
    first_name: str
    last_name: str
    ssn: str
    dob: date | None
    hire_date: date | None
    termination_date: date | None
    ytd_gross: Decimal
    ytd_deferral_pretax: Decimal
    ytd_deferral_roth: Decimal
    ytd_employer_match: Decimal
    hours: Decimal
    hce_flag: bool
    key_employee: bool
    owner_pct: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class RetirementCensusReport:
    client_id: str
    year: int
    as_of: date
    plan_id: str
    rows: list[CensusRow]
    hce_threshold: Decimal

    @property
    def total_participants(self) -> int:
        return len(self.rows)

    @property
    def flagged(self) -> int:
        return sum(1 for r in self.rows if r.findings)


class PrismHRReader(Protocol):
    async def list_all_participants(
        self, client_id: str, plan_id: str, year: int
    ) -> list[dict]: ...


async def run_retirement_census(
    reader: PrismHRReader,
    *,
    client_id: str,
    plan_id: str,
    year: int,
    as_of: date | None = None,
    hce_threshold: Decimal | None = None,
) -> RetirementCensusReport:
    today = as_of or date.today()
    threshold = hce_threshold or _HCE_THRESHOLD_2026
    rows = await reader.list_all_participants(client_id, plan_id, year)

    census: list[CensusRow] = []
    for r in rows:
        eid = str(r.get("employeeId") or "")
        hire = _parse(r.get("hireDate"))
        term = _parse(r.get("terminationDate"))
        dob = _parse(r.get("dob") or r.get("birthDate"))
        ytd_gross = _dec(r.get("ytdGross") or r.get("grossWages"))
        hce_flag = bool(r.get("hce"))
        key = bool(r.get("keyEmployee"))
        owner_pct = _dec(r.get("ownerPct"))

        row = CensusRow(
            employee_id=eid,
            first_name=str(r.get("firstName") or ""),
            last_name=str(r.get("lastName") or ""),
            ssn=str(r.get("ssn") or "").replace("-", ""),
            dob=dob,
            hire_date=hire,
            termination_date=term,
            ytd_gross=ytd_gross,
            ytd_deferral_pretax=_dec(r.get("ytdDeferralPretax")),
            ytd_deferral_roth=_dec(r.get("ytdDeferralRoth")),
            ytd_employer_match=_dec(r.get("ytdEmployerMatch")),
            hours=_dec(r.get("hours")),
            hce_flag=hce_flag,
            key_employee=key,
            owner_pct=owner_pct,
        )

        if not hire:
            row.findings.append(
                Finding("MISSING_HIRE_DATE", "critical", "No hire date on file.")
            )
        if not dob:
            row.findings.append(
                Finding("MISSING_DOB", "warning", "No DOB — needed for testing age buckets.")
            )
        if ytd_gross < 0:
            row.findings.append(
                Finding("NEGATIVE_WAGES", "critical", f"YTD gross {ytd_gross} is negative.")
            )
        if r.get("ownerPct") in (None, ""):
            row.findings.append(
                Finding("OWNERSHIP_MISSING", "warning", "Ownership % blank — required for >5% owner check.")
            )
        if hce_flag and ytd_gross > 0 and ytd_gross < threshold:
            row.findings.append(
                Finding(
                    "HCE_COMP_INCONSISTENT",
                    "warning",
                    f"Flagged HCE but YTD ${ytd_gross} < threshold ${threshold}.",
                )
            )

        census.append(row)

    return RetirementCensusReport(
        client_id=client_id,
        year=year,
        as_of=today,
        plan_id=plan_id,
        rows=census,
        hce_threshold=threshold,
    )


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
