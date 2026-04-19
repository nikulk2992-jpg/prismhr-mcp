"""ACA Configuration Integrity — workflow #8.

Per PrismHR's ACA User Guide (Ch. 11): "Coding issues are a common
source of configuration/data errors within PrismHR. The most common
of these errors are related to incomplete medical plan setup." This
workflow catches the config+data errors that would otherwise produce
penalty-bearing 1094-C / 1095-C submissions:

  4980H(a): $2,320 per FT employee per month MEC miss
  4980H(b): $3,480 per individual offered non-MEC
  Failure to file/furnish: up to $270 per incorrect 1095-C

Findings:
  - MEC_INDICATOR_NO: 1094-C has a month marked "No" for MEC — review
    before submission or risk 4980H(a) penalties.
  - SAFE_HARBOR_MISSING: 1095-C has a month with an offer code (14)
    but no safe harbor code (16). Penalty-bearing gap.
  - FT_NO_MEC_OFFER: employee was FT in a month but MEC count is 0 —
    failing the 95% threshold.
  - SECTION125_FLAG_MISSING: medical plan has no section125 flag,
    which can break MEC indicator calculations at rebuild time.
  - OFFER_CODE_1G_WITH_LINE15_16: offer code 1G must leave lines 15
    and 16 blank; flag if populated.

Input: client_id, year.
Output: per-month + per-employee findings.
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
class MonthAudit:
    month: int
    mec_indicator: str
    ft_count: int
    mec_count: int
    findings: list[Finding] = field(default_factory=list)


@dataclass
class EmployeeACAAudit:
    employee_id: str
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ACAIntegrityReport:
    client_id: str
    year: int
    as_of: date
    months: list[MonthAudit]
    employees: list[EmployeeACAAudit]

    @property
    def critical_count(self) -> int:
        n = 0
        for m in self.months:
            n += sum(1 for f in m.findings if f.severity == "critical")
        for e in self.employees:
            n += sum(1 for f in e.findings if f.severity == "critical")
        return n


class PrismHRReader(Protocol):
    async def get_1094_data(self, client_id: str, year: int) -> dict: ...
    async def get_aca_offered_employees(self, client_id: str, year: int) -> list[dict]: ...
    async def get_monthly_aca_info(self, client_id: str, year: int) -> list[dict]: ...
    async def get_1095c_years(self, client_id: str, employee_id: str) -> dict: ...


async def run_aca_integrity(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
) -> ACAIntegrityReport:
    today = as_of or date.today()

    form1094 = await reader.get_1094_data(client_id, year)
    offered = await reader.get_aca_offered_employees(client_id, year)
    monthly_rows = await reader.get_monthly_aca_info(client_id, year)

    # Normalize monthly records into a dict keyed by month
    monthly_by_month: dict[int, dict] = {}
    for row in monthly_rows:
        m = int(row.get("month") or row.get("monthNumber") or 0)
        if 1 <= m <= 12:
            monthly_by_month[m] = row

    # Build month audits
    month_audits: list[MonthAudit] = []
    mec_indicators = form1094.get("mecIndicator") or form1094.get("mecIndicators") or {}
    if isinstance(mec_indicators, list):
        mec_indicators = {
            int(r.get("month") or 0): r.get("indicator") or r.get("value")
            for r in mec_indicators
            if isinstance(r, dict)
        }

    for m in range(1, 13):
        raw_ind = mec_indicators.get(m) if isinstance(mec_indicators, dict) else None
        ind = str(raw_ind or "").strip().upper()
        month_row = monthly_by_month.get(m, {})
        ft_count = int(month_row.get("fullTimeCount") or month_row.get("ftCount") or 0)
        mec_count = int(month_row.get("mecCount") or 0)

        audit = MonthAudit(
            month=m,
            mec_indicator=ind,
            ft_count=ft_count,
            mec_count=mec_count,
        )
        if ind == "NO" or ind == "N":
            audit.findings.append(
                Finding(
                    "MEC_INDICATOR_NO",
                    "critical",
                    f"1094-C month {m}: MEC Indicator is No. Review before submission (4980H(a) risk).",
                )
            )
        # 95% rule: if FT > 0 and MEC < 95% of FT, flag
        if ft_count > 0:
            threshold = ft_count * 0.95
            if mec_count < threshold:
                audit.findings.append(
                    Finding(
                        "MEC_BELOW_95_PCT",
                        "critical",
                        f"Month {m}: FT={ft_count}, MEC={mec_count} (below 95% threshold).",
                    )
                )
        month_audits.append(audit)

    # Build employee audits from ACAOfferedEmployees + 1095c
    emp_audits: list[EmployeeACAAudit] = []
    for row in offered:
        eid = str(row.get("employeeId") or "")
        if not eid:
            continue
        audit = EmployeeACAAudit(employee_id=eid)
        offer_codes = row.get("offerCodes") or row.get("line14") or {}
        safe_harbors = row.get("safeHarborCodes") or row.get("line16") or {}
        line15 = row.get("employeeShare") or row.get("line15") or {}

        if isinstance(offer_codes, dict):
            for month_str, code in offer_codes.items():
                code = str(code or "").strip().upper()
                sh = ""
                if isinstance(safe_harbors, dict):
                    sh = str(safe_harbors.get(month_str) or "").strip().upper()

                # Code in [1A, 1B, 1C, 1D, 1E, 1J, 1K] expects line 16 present
                if code in {"1A", "1B", "1C", "1D", "1E", "1J", "1K"} and not sh:
                    audit.findings.append(
                        Finding(
                            "SAFE_HARBOR_MISSING",
                            "critical",
                            f"Month {month_str}: offer code {code} but line 16 is blank.",
                        )
                    )
                # 1G must have lines 15 and 16 blank
                if code == "1G":
                    if isinstance(line15, dict) and line15.get(month_str):
                        audit.findings.append(
                            Finding(
                                "OFFER_CODE_1G_LINE15_POPULATED",
                                "warning",
                                f"Month {month_str}: 1G but line 15 populated.",
                            )
                        )
                    if sh:
                        audit.findings.append(
                            Finding(
                                "OFFER_CODE_1G_LINE16_POPULATED",
                                "warning",
                                f"Month {month_str}: 1G but line 16 populated.",
                            )
                        )
        if audit.findings:
            emp_audits.append(audit)

    return ACAIntegrityReport(
        client_id=client_id,
        year=year,
        as_of=today,
        months=month_audits,
        employees=emp_audits,
    )
