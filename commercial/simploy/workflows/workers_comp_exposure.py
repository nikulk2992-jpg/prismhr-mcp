"""Workers Comp Exposure — workflow #28.

Per PrismHR's Workers Comp setup chapter: every employee carries a WC
class code + state; premium = wages * (rate per $100) * experience
modifier. Under-classification or misrouted state codes = audit
exposure. WC carriers audit annually; a $5K classification error at
1,000-employee scale is a $5M audit finding.

Findings per client + state:
  - EXPOSURE_BY_CODE: summary of YTD wages × rate per class code.
  - MISSING_WC_CODE: employee missing a class code assignment.
  - UNUSED_CLASS_CODE: class code on file but no wages against it.
  - HIGH_RISK_CODE_CONCENTRATION: more than 20% of wages in the
    top-risk code — audit-trigger flag.

Input: client_id, year.
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
class WCCodeExposure:
    wc_code: str
    state: str
    ytd_wages: Decimal
    rate_per_100: Decimal
    modifier: Decimal
    estimated_premium: Decimal


@dataclass
class WCExposureReport:
    client_id: str
    year: int
    as_of: date
    exposures: list[WCCodeExposure]
    findings: list[Finding]
    missing_code_employees: list[str]

    @property
    def total_premium(self) -> Decimal:
        return sum((e.estimated_premium for e in self.exposures), Decimal("0"))


class PrismHRReader(Protocol):
    async def get_wc_accrual_modifiers(self, client_id: str) -> list[dict]: ...
    async def get_wc_billing_modifiers(self, client_id: str, state: str) -> list[dict]: ...
    async def list_employees_with_wc(self, client_id: str) -> list[dict]: ...


async def run_workers_comp_exposure(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
) -> WCExposureReport:
    today = as_of or date.today()

    modifiers = await reader.get_wc_accrual_modifiers(client_id)
    # Key modifiers by (wc_code, state) for quick lookup.
    mod_map: dict[tuple[str, str], dict] = {}
    for m in modifiers:
        wc = str(m.get("wcCode") or m.get("classCode") or "")
        state = str(m.get("state") or m.get("stateCode") or "")
        if wc and state:
            mod_map[(wc, state)] = m

    employees = await reader.list_employees_with_wc(client_id)

    # Aggregate YTD wages per (wc_code, state).
    agg: dict[tuple[str, str], Decimal] = {}
    missing: list[str] = []
    for e in employees:
        eid = str(e.get("employeeId") or "")
        wc = str(e.get("wcCode") or e.get("classCode") or "")
        state = str(e.get("wcState") or e.get("state") or "")
        ytd = _dec(e.get("ytdWages") or e.get("grossWages"))
        if not wc or not state:
            missing.append(eid)
            continue
        agg[(wc, state)] = agg.get((wc, state), Decimal("0")) + ytd

    exposures: list[WCCodeExposure] = []
    for (wc, state), wages in agg.items():
        mod = mod_map.get((wc, state), {})
        rate = _dec(mod.get("ratePer100") or mod.get("rate"))
        modifier = _dec(mod.get("experienceModifier") or mod.get("modifier")) or Decimal("1")
        premium = (wages / Decimal("100")) * rate * modifier
        exposures.append(
            WCCodeExposure(
                wc_code=wc,
                state=state,
                ytd_wages=wages,
                rate_per_100=rate,
                modifier=modifier,
                estimated_premium=premium.quantize(Decimal("0.01")),
            )
        )

    findings: list[Finding] = []
    if missing:
        findings.append(
            Finding(
                "MISSING_WC_CODE",
                "critical",
                f"{len(missing)} employees have no WC class code / state assignment.",
            )
        )

    total_wages = sum((e.ytd_wages for e in exposures), Decimal("0"))
    if total_wages > 0:
        for e in sorted(exposures, key=lambda x: x.ytd_wages, reverse=True)[:1]:
            pct = (e.ytd_wages / total_wages * 100).quantize(Decimal("0.1"))
            if pct > Decimal("20"):
                findings.append(
                    Finding(
                        "HIGH_RISK_CODE_CONCENTRATION",
                        "warning",
                        f"WC code {e.wc_code} ({e.state}) accounts for {pct}% of wages.",
                    )
                )

    return WCExposureReport(
        client_id=client_id,
        year=year,
        as_of=today,
        exposures=exposures,
        findings=findings,
        missing_code_employees=missing,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
