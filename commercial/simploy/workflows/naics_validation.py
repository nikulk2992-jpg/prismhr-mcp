"""NAICS / Industry Validation — workflow #41.

NAICS code determines WC class defaults, BLS reporting buckets, SUTA
industry rate, and some state-specific payroll tax rules. A missing
or invalid NAICS is a quiet bug — it shows up at year-end when the
BLS 202 report fails validation or the SUTA new-employer rate
applies instead of an industry-specific rate.

Findings:
  - NO_NAICS: client has no NAICS on file.
  - INVALID_NAICS: NAICS not in the current IRS/BLS list.
  - MISMATCH_WITH_WC_CLASS: NAICS industry doesn't align with the
    dominant WC class on payroll.
  - DEPRECATED_NAICS: NAICS from an older cycle (e.g. 2012 code in
    a post-2022 tenant).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


Severity = str

# Minimal NAICS industry-group prefix map for mismatch checks.
# 2-digit sector → human-readable sector name.
_NAICS_SECTORS: dict[str, str] = {
    "11": "Agriculture",
    "21": "Mining",
    "22": "Utilities",
    "23": "Construction",
    "31": "Manufacturing",
    "32": "Manufacturing",
    "33": "Manufacturing",
    "42": "Wholesale Trade",
    "44": "Retail Trade",
    "45": "Retail Trade",
    "48": "Transportation",
    "49": "Transportation",
    "51": "Information",
    "52": "Finance & Insurance",
    "53": "Real Estate",
    "54": "Professional Services",
    "55": "Management",
    "56": "Administrative",
    "61": "Education",
    "62": "Health Care",
    "71": "Arts & Entertainment",
    "72": "Accommodation & Food",
    "81": "Other Services",
    "92": "Public Administration",
}

# WC class code to NAICS sector rough mapping for obvious mismatch flagging.
_WC_TO_SECTOR_HINT: dict[str, str] = {
    "8810": "54",  # clerical — professional services
    "8742": "54",  # outside sales — professional services
    "5606": "23",  # construction contract executive supervisor
    "9079": "72",  # restaurants — accommodation & food
    "7229": "62",  # home health care — health care
    "8829": "62",  # convalescent / nursing homes
    "7380": "48",  # drivers / chauffeurs — transportation
}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class NAICSAudit:
    client_id: str
    naics: str
    sector_name: str
    dominant_wc_class: str
    findings: list[Finding] = field(default_factory=list)


class PrismHRReader(Protocol):
    async def get_client_naics(self, client_id: str) -> str: ...
    async def is_naics_valid(self, naics: str) -> bool: ...
    async def is_naics_deprecated(self, naics: str) -> bool: ...
    async def dominant_wc_class(self, client_id: str) -> str: ...


async def run_naics_validation(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
) -> NAICSAudit:
    naics = (await reader.get_client_naics(client_id) or "").strip()
    audit = NAICSAudit(
        client_id=client_id,
        naics=naics,
        sector_name="",
        dominant_wc_class="",
    )

    if not naics:
        audit.findings.append(
            Finding("NO_NAICS", "critical", "Client has no NAICS code assigned.")
        )
        return audit

    sector = _NAICS_SECTORS.get(naics[:2], "")
    audit.sector_name = sector

    if not await reader.is_naics_valid(naics):
        audit.findings.append(
            Finding("INVALID_NAICS", "critical", f"NAICS {naics} not in the current code list.")
        )
    elif await reader.is_naics_deprecated(naics):
        audit.findings.append(
            Finding("DEPRECATED_NAICS", "warning", f"NAICS {naics} is from an older cycle.")
        )

    wc = (await reader.dominant_wc_class(client_id) or "").strip()
    audit.dominant_wc_class = wc
    if wc and wc in _WC_TO_SECTOR_HINT and naics[:2]:
        expected = _WC_TO_SECTOR_HINT[wc]
        if naics[:2] != expected:
            audit.findings.append(
                Finding(
                    "MISMATCH_WITH_WC_CLASS",
                    "warning",
                    f"Dominant WC class {wc} suggests sector {expected} but NAICS is {naics[:2]} ({sector}).",
                )
            )
    return audit
