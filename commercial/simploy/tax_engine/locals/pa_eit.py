"""Pennsylvania Earned Income Tax (Act 32) calculator.

Act 32 rule (for PSDs *inside* Act 32, i.e. not Philadelphia):
  Employer withholds max(resident_rate_of_home_PSD, nonresident_rate_of_work_PSD)
  Remits to the work-location TCD.

Philadelphia is OUTSIDE Act 32 — uses Philadelphia Wage Tax rates
(resident + nonresident separately). PA residents working in Philly
get a credit against their home-PSD EIT for the Philly tax paid,
capped at their home-PSD rate.

This module loads a seed table of ~9 major PSDs. For the other
~2900 PSDs, a fallback rate applies. Override seed via a full file
at `.planning/locals-data/pa_eit_full.json` if present.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


_SEED_PATH = (
    Path(__file__).resolve().parents[4]
    / "src" / "prismhr_mcp" / "data" / "locals" / "pa_eit_seed.json"
)
_OVERRIDE_PATH = Path(".planning/locals-data/pa_eit_full.json")

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        data = json.loads(_SEED_PATH.read_text())
        if _OVERRIDE_PATH.exists():
            try:
                override = json.loads(_OVERRIDE_PATH.read_text())
                data["psd_rates"].update(override.get("psd_rates") or {})
            except Exception:  # noqa: BLE001
                pass
        _cache = data
    return _cache


def _rates_for_psd(psd: str) -> dict:
    data = _load()
    rate = data["psd_rates"].get(psd)
    if rate is not None:
        return rate
    fb = data["fallback"]
    return {
        "name": f"Unknown PSD {psd}",
        "resident": fb["resident"],
        "nonresident": fb["nonresident"],
        "lst_annual": 0,
        "outside_act_32": False,
    }


@dataclass
class PAEITInput:
    gross_wages_period: Decimal
    home_psd: str
    work_psd: str


@dataclass
class PAEITOutput:
    expected_withholding_period: Decimal
    applied_rule: str
    rate: Decimal
    home_rates: dict
    work_rates: dict
    notes: list[str] = field(default_factory=list)


def _q(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_pa_eit(inp: PAEITInput) -> PAEITOutput:
    """Compute per-period PA EIT withholding per Act 32 rules."""
    home = _rates_for_psd(inp.home_psd)
    work = _rates_for_psd(inp.work_psd)
    notes: list[str] = []

    # Philadelphia special case (work location outside Act 32)
    if work.get("outside_act_32"):
        if home.get("outside_act_32"):
            rate = Decimal(str(work["resident"]))
            rule = "philly_resident_wage_tax"
        else:
            rate = Decimal(str(work["nonresident"]))
            rule = "philly_nonresident_wage_tax"
            notes.append("Resident may claim credit against home-PSD EIT.")
        return PAEITOutput(
            expected_withholding_period=_q(inp.gross_wages_period * rate),
            applied_rule=rule, rate=rate,
            home_rates=home, work_rates=work, notes=notes,
        )

    # Act 32: max of resident-of-home and nonresident-of-work
    resident_rate = Decimal(str(home["resident"]))
    nonresident_rate = Decimal(str(work["nonresident"]))
    rate = max(resident_rate, nonresident_rate)
    applied_rule = (
        "act32_home_resident_rate"
        if rate == resident_rate
        else "act32_work_nonresident_rate"
    )
    if resident_rate == nonresident_rate:
        applied_rule = "act32_equal_rates"

    withholding = inp.gross_wages_period * rate
    return PAEITOutput(
        expected_withholding_period=_q(withholding),
        applied_rule=applied_rule, rate=rate,
        home_rates=home, work_rates=work, notes=notes,
    )


def validate_pa_eit_withholding(
    *, gross_wages_period: Decimal, home_psd: str, work_psd: str,
    actual_withholding_period: Decimal, tolerance: Decimal = Decimal("0.50"),
) -> dict:
    """Compare actual withholding against computed. Return structured finding."""
    expected = compute_pa_eit(PAEITInput(
        gross_wages_period=gross_wages_period,
        home_psd=home_psd, work_psd=work_psd,
    ))
    delta = actual_withholding_period - expected.expected_withholding_period
    status = "match" if abs(delta) <= tolerance else "mismatch"
    return {
        "status": status,
        "expected": str(expected.expected_withholding_period),
        "actual": str(actual_withholding_period),
        "delta": str(delta),
        "rate_applied": str(expected.rate),
        "rule": expected.applied_rule,
        "home_psd_name": expected.home_rates.get("name"),
        "work_psd_name": expected.work_rates.get("name"),
        "notes": expected.notes,
    }
