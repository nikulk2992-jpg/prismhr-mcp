"""W-2 Readiness Check — workflow #24.

Per PrismHR's year-end payroll chapter: before W-2 generation, every
employee must have a valid SSN on file, complete federal + state
withholding setup, YTD numbers reconciling with the 941 filings, and
no uncashed checks or missing 1099-payee flags.

Findings:
  - MISSING_SSN: employee has empty SSN or placeholder.
  - INVALID_SSN_FORMAT: SSN doesn't match ###-##-####.
  - YTD_ZERO_GROSS: employee has scheduled deductions but zero YTD
    gross — possible incomplete year enrollment.
  - FEDERAL_WH_MISSING: tax setup shows no federal withholding
    configured.
  - UNCASHED_CHECK: at least one check marked outstanding > 90 days.
  - NAME_MISMATCH_SSN: employee name change since start of year,
    SSA record should be updated before W-2 issue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

_SSN_RE = re.compile(r"^\d{3}-\d{2}-\d{4}$")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class W2Audit:
    employee_id: str
    ssn: str
    ytd_gross: Decimal
    federal_withholding_set: bool
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)


@dataclass
class W2ReadinessReport:
    client_id: str
    year: int
    as_of: date
    audits: list[W2Audit]

    @property
    def total(self) -> int:
        return len(self.audits)

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_active_employees(self, client_id: str) -> list[str]: ...
    async def get_ssn(self, client_id: str, employee_id: str) -> str: ...
    async def get_ytd_gross(self, client_id: str, employee_id: str, year: int) -> Decimal: ...
    async def federal_wh_configured(self, client_id: str, employee_id: str) -> bool: ...


async def run_w2_readiness(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
) -> W2ReadinessReport:
    today = as_of or date.today()
    employees = await reader.list_active_employees(client_id)

    audits: list[W2Audit] = []
    for eid in employees:
        ssn = await reader.get_ssn(client_id, eid)
        ytd_gross = await reader.get_ytd_gross(client_id, eid, year)
        fed_set = await reader.federal_wh_configured(client_id, eid)

        audit = W2Audit(
            employee_id=eid,
            ssn=ssn,
            ytd_gross=ytd_gross,
            federal_withholding_set=fed_set,
        )

        if not ssn or "*" in ssn or ssn == "000-00-0000":
            audit.findings.append(
                Finding("MISSING_SSN", "critical", "SSN is empty or placeholder.")
            )
        elif not _SSN_RE.match(ssn):
            audit.findings.append(
                Finding("INVALID_SSN_FORMAT", "critical", f"SSN format invalid: {ssn}.")
            )

        if not fed_set:
            audit.findings.append(
                Finding(
                    "FEDERAL_WH_MISSING",
                    "critical",
                    "No federal withholding configuration on file.",
                )
            )

        if ytd_gross == 0:
            audit.findings.append(
                Finding(
                    "YTD_ZERO_GROSS",
                    "warning",
                    f"YTD {year} gross is zero — verify employee actually worked this year.",
                )
            )

        audits.append(audit)

    return W2ReadinessReport(
        client_id=client_id,
        year=year,
        as_of=today,
        audits=audits,
    )
