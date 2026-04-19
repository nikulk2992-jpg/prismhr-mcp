"""1095-C Value Consistency Audit — workflow #55.

The ACA Configuration Integrity workflow (#13) catches setup errors
before the build. This one catches PrismHR's own generation bugs
AFTER the 1095-C register has been built: cases where the posted
code doesn't match reality (the employee was actually enrolled, was
full-time, etc).

Common PrismHR 1095-C defects we check for:

  CODE_1H_WITH_COVERAGE
    Line 14 = 1H (no offer of MEC) for a month where the employee
    WAS enrolled in coverage per getBenefitConfirmationList.
    4980H(b) penalty exposure + IRS reject risk.

  CODE_1H_FULL_TIME_MONTH
    Line 14 = 1H for a month where the employee was counted as a
    full-time employee. 4980H(a) penalty.

  SAFE_HARBOR_CONFLICT
    Line 16 = 2C (enrolled in coverage offered) for a month where
    Line 14 = 1H. Self-contradictory.

  LINE15_POPULATED_ON_NONSHARE_CODE
    Line 15 (employee share) > 0 for a code that requires line 15
    blank: 1A (qualifying offer), 1F (non-MEC), 1G (not FT),
    1H (no offer).

  LINE16_BLANK_ON_OFFER
    Line 14 in {1A,1B,1C,1D,1E,1J,1K} but Line 16 safe harbor blank.

  CODE_CHANGE_WITHOUT_EVENT
    Line 14 value changed month-to-month without a corresponding
    hire / rehire / termination event on the employee record.

  ICHRA_CODE_INVALID_YEAR
    Line 14 in {1L..1S} for a report year before 2020.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

# Offer codes that REQUIRE line 15 (employee share) populated
_SHARE_REQUIRED = {"1B", "1C", "1D", "1E", "1J", "1K", "1L", "1M", "1N", "1O", "1P", "1Q"}
# Codes that REQUIRE line 15 empty
_SHARE_FORBIDDEN = {"1A", "1F", "1G", "1H"}
# Codes that REQUIRE line 16 safe harbor
_HARBOR_REQUIRED = {"1A", "1B", "1C", "1D", "1E", "1J", "1K"}
# ICHRA codes (2020+)
_ICHRA_CODES = {"1L", "1M", "1N", "1O", "1P", "1Q", "1R", "1S"}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class Employee1095CAudit:
    employee_id: str
    form_exists: bool = False
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)


@dataclass
class Form1095CReport:
    client_id: str
    year: int
    as_of: date
    employees: list[Employee1095CAudit]

    @property
    def total(self) -> int:
        return len(self.employees)

    @property
    def flagged(self) -> int:
        return sum(1 for e in self.employees if e.findings)


class PrismHRReader(Protocol):
    async def list_employees_with_1095c(
        self, client_id: str, year: int
    ) -> list[dict]: ...
    async def get_1095c_monthly(
        self, client_id: str, employee_id: str, year: int
    ) -> dict: ...
    async def get_benefit_enrollment_months(
        self, client_id: str, employee_id: str, year: int
    ) -> dict[int, bool]: ...
    async def get_employment_events(
        self, client_id: str, employee_id: str, year: int
    ) -> list[dict]: ...


async def run_1095c_consistency_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
) -> Form1095CReport:
    today = as_of or date.today()
    roster = await reader.list_employees_with_1095c(client_id, year)

    audits: list[Employee1095CAudit] = []
    for row in roster:
        eid = str(row.get("employeeId") or "")
        if not eid:
            continue
        audit = Employee1095CAudit(employee_id=eid, form_exists=True)

        monthly = await reader.get_1095c_monthly(client_id, eid, year)
        line14 = _normalize_months(monthly.get("line14") or monthly.get("offerCodes"))
        line15 = _normalize_months(monthly.get("line15") or monthly.get("employeeShare"))
        line16 = _normalize_months(monthly.get("line16") or monthly.get("safeHarborCodes"))

        enrolled = await reader.get_benefit_enrollment_months(client_id, eid, year)
        events = await reader.get_employment_events(client_id, eid, year)

        # Months when the employee had a life event (hire, term, rehire).
        event_months: set[int] = set()
        for ev in events:
            dt = _parse(ev.get("statusDate") or ev.get("effectiveDate") or ev.get("eventDate"))
            if dt and dt.year == year:
                event_months.add(dt.month)

        # ICHRA year check
        if year < 2020:
            for m, code in line14.items():
                if str(code).upper() in _ICHRA_CODES:
                    audit.findings.append(
                        Finding(
                            "ICHRA_CODE_INVALID_YEAR",
                            "critical",
                            f"Month {m}: ICHRA code {code} used for pre-2020 report year.",
                        )
                    )

        prev_code = None
        for m in range(1, 13):
            code = (line14.get(m) or "").strip().upper()
            share = line15.get(m)
            harbor = (line16.get(m) or "").strip().upper()

            # 1H with coverage
            if code == "1H" and enrolled.get(m, False):
                audit.findings.append(
                    Finding(
                        "CODE_1H_WITH_COVERAGE",
                        "critical",
                        f"Month {m}: Line 14 = 1H but employee was enrolled in coverage.",
                    )
                )

            # Safe harbor conflict: 1H + 2C
            if code == "1H" and harbor == "2C":
                audit.findings.append(
                    Finding(
                        "SAFE_HARBOR_CONFLICT",
                        "critical",
                        f"Month {m}: 1H (no offer) but Line 16 = 2C (enrolled).",
                    )
                )

            # Line 15 populated on no-share code
            if code in _SHARE_FORBIDDEN:
                amt = _dec(share)
                if amt > 0:
                    audit.findings.append(
                        Finding(
                            "LINE15_POPULATED_ON_NONSHARE_CODE",
                            "critical",
                            f"Month {m}: {code} should have Line 15 blank, got ${amt}.",
                        )
                    )

            # Safe harbor required but missing
            if code in _HARBOR_REQUIRED and not harbor:
                audit.findings.append(
                    Finding(
                        "LINE16_BLANK_ON_OFFER",
                        "critical",
                        f"Month {m}: Line 14 = {code} requires Line 16 safe harbor code.",
                    )
                )

            # Code change without event
            if prev_code is not None and code and code != prev_code:
                if m not in event_months and (m - 1) not in event_months:
                    audit.findings.append(
                        Finding(
                            "CODE_CHANGE_WITHOUT_EVENT",
                            "warning",
                            f"Month {m}: Line 14 changed {prev_code}->{code} with no employment event.",
                        )
                    )
            if code:
                prev_code = code

        audits.append(audit)

    return Form1095CReport(
        client_id=client_id, year=year, as_of=today, employees=audits
    )


def _normalize_months(raw) -> dict[int, object]:  # type: ignore[no-untyped-def]
    """Accept dict {"1": code} or list [(m, code)]; return int-keyed dict."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        out: dict[int, object] = {}
        for k, v in raw.items():
            try:
                out[int(k)] = v
            except (TypeError, ValueError):
                continue
        return out
    if isinstance(raw, list):
        out = {}
        for i, v in enumerate(raw, start=1):
            out[i] = v
        return out
    return {}


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
