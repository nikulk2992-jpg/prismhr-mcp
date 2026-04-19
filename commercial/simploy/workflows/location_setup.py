"""Location Setup Completeness — workflow #43.

Each client location needs state, county, city, and ZIP+4 configured
for accurate tax localization. Missing = workers get mis-taxed,
local jurisdictions get underfunded, year-end reports need manual
correction.

Findings per location:
  - NO_ADDRESS: location has no street / city / state.
  - NO_ZIP: ZIP code missing.
  - NO_SUTA_STATE: location's SUTA state is blank.
  - EMPLOYEE_AT_INCOMPLETE_LOCATION: employees actively assigned to
    a location missing fields (critical — active payroll risk).
  - GEOCODE_MISSING: no geocode/tax district stored — local tax
    accuracy at risk in jurisdictions like OH/PA with payroll taxes.
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
class LocationAudit:
    location_id: str
    location_name: str
    state: str
    active_employees: int
    findings: list[Finding] = field(default_factory=list)


@dataclass
class LocationSetupReport:
    client_id: str
    as_of: date
    audits: list[LocationAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_client_locations(self, client_id: str) -> list[dict]: ...


async def run_location_setup(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
) -> LocationSetupReport:
    today = as_of or date.today()
    rows = await reader.list_client_locations(client_id)

    audits: list[LocationAudit] = []
    for r in rows:
        loc_id = str(r.get("locationId") or r.get("id") or "")
        name = str(r.get("locationName") or r.get("name") or "")
        state = str(r.get("state") or "").upper()
        line1 = str(r.get("addressLine1") or "").strip()
        city = str(r.get("city") or "").strip()
        zip_code = str(r.get("zipCode") or r.get("postalCode") or "").strip()
        geocode = str(r.get("geocode") or r.get("taxDistrict") or "").strip()
        suta_state = str(r.get("sutaState") or state).strip()
        active = int(r.get("activeEmployees") or 0)

        audit = LocationAudit(
            location_id=loc_id,
            location_name=name,
            state=state,
            active_employees=active,
        )

        missing_address = not (line1 and city and state)
        if missing_address:
            audit.findings.append(
                Finding("NO_ADDRESS", "critical" if active > 0 else "warning", "Location missing street/city/state.")
            )
        if not zip_code:
            audit.findings.append(
                Finding("NO_ZIP", "critical" if active > 0 else "warning", "Location missing ZIP.")
            )
        if not suta_state:
            audit.findings.append(
                Finding("NO_SUTA_STATE", "critical", "Location has no SUTA state — wages won't post correctly.")
            )
        if not geocode and active > 0:
            audit.findings.append(
                Finding(
                    "GEOCODE_MISSING",
                    "warning",
                    "No geocode stored — local tax accuracy at risk in jurisdictions that require one.",
                )
            )
        if active > 0 and (missing_address or not zip_code or not suta_state):
            audit.findings.append(
                Finding(
                    "EMPLOYEE_AT_INCOMPLETE_LOCATION",
                    "critical",
                    f"{active} active employees assigned — fix before next payroll.",
                )
            )
        audits.append(audit)

    return LocationSetupReport(client_id=client_id, as_of=today, audits=audits)
