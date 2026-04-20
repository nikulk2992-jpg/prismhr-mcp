"""IRS AIR Submission Pre-Flight — workflow #32.

Before submitting the 1094-C/1095-C bundle to the IRS AIR system,
the file must pass a handful of validity checks that the IRS
routinely rejects for. Bible lists these as the top AIR-rejection
reasons; this workflow enforces them locally.

Findings:
  - NON_STANDARD_CHARACTER: file contains characters outside the
    ASCII printable range.
  - LEADING_OR_TRAILING_SPACE: name/address fields with leading or
    trailing whitespace.
  - INVALID_SSN_CHECKSUM: any 1095-C SSN fails 9-digit-all-digit +
    not-obviously-invalid check (000, 666, 9xx area).
  - INVALID_EIN: employer EIN fails 9-digit or uses 00- prefix.
  - EMPTY_ALL_12_MONTHS_WITH_PER_MONTH: "all 12 months" field has
    a value but individual month fields also have values
    (mutually exclusive per IRS instruction).
  - COVERED_INDIVIDUAL_NOT_MARKED: covered individual appears on
    Part III but no month flag is set.
  - INVALID_MANIFEST_CHECKSUM: file's manifest checksum doesn't
    match the computed checksum over the Form file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


Severity = str

_SSN_RE = re.compile(r"^\d{9}$")
_EIN_RE = re.compile(r"^\d{9}$")
_NON_ASCII_RE = re.compile(r"[^\x20-\x7E]")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class Submission1094Audit:
    ein: str
    employee_count: int
    findings: list[Finding] = field(default_factory=list)


@dataclass
class AIRPreflightReport:
    client_id: str
    year: int
    as_of: date
    submission: Submission1094Audit

    @property
    def ready_to_submit(self) -> bool:
        return not any(f.severity == "critical" for f in self.submission.findings)


class PrismHRReader(Protocol):
    async def get_submission_bundle(
        self, client_id: str, year: int
    ) -> dict: ...


async def run_irs_air_preflight(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
) -> AIRPreflightReport:
    today = as_of or date.today()
    bundle = await reader.get_submission_bundle(client_id, year)

    ein = str(bundle.get("ein") or bundle.get("employerEin") or "").replace("-", "")
    form_text = str(bundle.get("formXml") or bundle.get("rawText") or "")
    manifest_checksum = str(bundle.get("manifestChecksum") or "").lower()
    computed_checksum = str(bundle.get("computedChecksum") or "").lower()
    employee_rows = bundle.get("employees") or []

    audit = Submission1094Audit(ein=ein, employee_count=len(employee_rows))

    if not _EIN_RE.match(ein) or ein.startswith("00"):
        audit.findings.append(
            Finding("INVALID_EIN", "critical", f"EIN {ein} is not a valid 9-digit IRS EIN.")
        )

    if _NON_ASCII_RE.search(form_text):
        audit.findings.append(
            Finding("NON_STANDARD_CHARACTER", "critical", "Form file contains non-ASCII characters.")
        )

    if manifest_checksum and computed_checksum and manifest_checksum != computed_checksum:
        audit.findings.append(
            Finding(
                "INVALID_MANIFEST_CHECKSUM",
                "critical",
                f"Manifest checksum {manifest_checksum[:8]}… != computed {computed_checksum[:8]}….",
            )
        )

    for emp in employee_rows:
        eid = str(emp.get("employeeId") or "")
        ssn = str(emp.get("ssn") or "").replace("-", "")
        first = str(emp.get("firstName") or "")
        last = str(emp.get("lastName") or "")

        if first != first.strip() or last != last.strip():
            audit.findings.append(
                Finding(
                    "LEADING_OR_TRAILING_SPACE",
                    "warning",
                    f"Employee {eid}: name has leading/trailing whitespace.",
                )
            )

        if not _SSN_RE.match(ssn) or ssn.startswith("000") or ssn.startswith("666") or ssn[:1] == "9":
            audit.findings.append(
                Finding(
                    "INVALID_SSN_CHECKSUM",
                    "critical",
                    f"Employee {eid}: SSN {ssn or 'blank'} fails validity check.",
                )
            )

        # "All 12 months" vs individual month mutual exclusivity
        all12 = emp.get("allMonths") or {}
        per_month = emp.get("byMonth") or {}
        for field_name in ("line14", "line15", "line16"):
            if all12.get(field_name) and any(per_month.get(field_name, {}).values()):
                audit.findings.append(
                    Finding(
                        "EMPTY_ALL_12_MONTHS_WITH_PER_MONTH",
                        "critical",
                        f"Employee {eid}: {field_name} has both all-12 and per-month values.",
                    )
                )

        # Covered individuals in Part III must have at least one month flag
        for ci in emp.get("coveredIndividuals") or []:
            months = ci.get("monthsCovered") or {}
            if not any(months.values()):
                audit.findings.append(
                    Finding(
                        "COVERED_INDIVIDUAL_NOT_MARKED",
                        "critical",
                        f"Employee {eid}: covered individual {ci.get('name', '?')} has no month flags.",
                    )
                )

    return AIRPreflightReport(
        client_id=client_id, year=year, as_of=today, submission=audit
    )
