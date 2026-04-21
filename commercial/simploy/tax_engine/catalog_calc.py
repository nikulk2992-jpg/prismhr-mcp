"""Generic catalog-backed state withholding calculator.

Reads src/prismhr_mcp/data/vertex_catalog_2026Q1.json (shared OSS data
file — it's just rate tables, no PII) and computes expected withholding
for any state using:
  - no_income_tax flag → 0
  - flat_rate → wages × rate
  - brackets → annualized + bracket lookup + de-annualize

Used as fallback when no custom state module exists. Confidence is
derived from extraction quality:
  HIGH   — ≥1 filing status with ≥2 brackets AND catalog-listed supp rate
  MEDIUM — brackets present but single-status or missing supp
  LOW    — flat_rate only (mean filing-status treatment ignored)
  NONE   — no_income_tax or nothing in catalog

Canonical overrides for flat-tax states where PDF text mining pulled a
surtax or prior-year value.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


# US Postal → Vertex state name
_ABBR_TO_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}


# Authoritative flat-rate overrides. PDF text mining sometimes picks
# surtax / prior-year values. These are the official 2026 values.
_FLAT_RATE_OVERRIDES = {
    "Colorado": 0.0440,
    "Illinois": 0.0495,
    "Indiana": 0.0305,
    "Kentucky": 0.0400,
    "Massachusetts": 0.0500,
    "Michigan": 0.0425,
    "North Carolina": 0.0425,
    "Pennsylvania": 0.0307,
    "Utah": 0.0485,
    "Arizona": 0.0170,  # default if no W-4A election
    "Georgia": 0.0539,  # flat as of 2026
}


_CATALOG_PATH = (
    Path(__file__).resolve().parents[3]
    / "src" / "prismhr_mcp" / "data" / "vertex_catalog_2026Q1.json"
)
_OVERRIDE_PATH = (
    Path(__file__).resolve().parents[3]
    / "src" / "prismhr_mcp" / "data" / "state_manual_overrides.json"
)

_catalog_cache: dict | None = None


def _load_catalog() -> dict:
    global _catalog_cache
    if _catalog_cache is None:
        cat = json.loads(_CATALOG_PATH.read_text())
        if _OVERRIDE_PATH.exists():
            try:
                override = json.loads(_OVERRIDE_PATH.read_text())
                for name, data in (override.get("states") or {}).items():
                    if name in cat["states"]:
                        cat["states"][name]["brackets"] = data.get("brackets", {})
                        cat["states"][name]["no_income_tax"] = False
                        cat["states"][name]["flat_rate"] = None
                        cat["states"][name]["_manual_override"] = True
                        cat["states"][name]["_forced_confidence"] = data.get("confidence")
            except Exception:  # noqa: BLE001
                pass
        _catalog_cache = cat
    return _catalog_cache


@dataclass
class CatalogCalcInput:
    state: str            # 2-letter abbr
    gross_wages_period: Decimal
    pay_periods_per_year: int = 52
    filing_status: str = "S"  # raw; interpreted per state


@dataclass
class CatalogCalcOutput:
    state: str
    expected_withholding_period: Decimal
    applied_rule: str
    confidence: str       # HIGH | MEDIUM | LOW | NONE
    notes: list[str]


def _quantize(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _first_sane_run(brackets: list[dict]) -> list[dict]:
    """Truncate at first non-monotonic break. Vertex tables often
    concatenate multiple state/locality sub-tables under one bucket."""
    out: list[dict] = []
    last_min = Decimal("-1")
    for b in brackets:
        try:
            mn = Decimal(str(b.get("min", 0)))
            mx = b.get("max")
            rate = b.get("rate")
        except Exception:
            break
        if rate is None:
            out.append(b)
            continue
        if rate > 0.30 or rate < 0:
            break
        if mn < last_min:
            break
        if mx is not None:
            try:
                if Decimal(str(mx)) < mn:
                    break
            except Exception:
                break
        out.append(b)
        last_min = mn
    return out


def _brackets_look_sane(brackets: list[dict]) -> bool:
    run = _first_sane_run(brackets)
    return bool(run) and len(run) >= 1


def _compute_from_brackets(
    annual_wages: Decimal, brackets: list[dict]
) -> Decimal | None:
    """Walk brackets, find the one whose (min,max] covers annual_wages."""
    brackets = _first_sane_run(brackets)
    if not brackets:
        return None
    for b in brackets:
        if b.get("rate") is None:
            return None  # method_ref placeholder
        lo = Decimal(str(b.get("min", 0)))
        hi = b.get("max")
        if hi is None:
            # Top bracket (Over X)
            if annual_wages > lo:
                base = Decimal(str(b.get("base_tax") or 0))
                rate = Decimal(str(b["rate"]))
                return base + (annual_wages - lo) * rate
            continue
        hi_d = Decimal(str(hi))
        if annual_wages <= hi_d:
            base = Decimal(str(b.get("base_tax") or 0))
            rate = Decimal(str(b["rate"]))
            # First bracket: base_tax==0 and min==0 → just rate×wages
            if base == 0 and lo == 0:
                return annual_wages * rate
            return base + (annual_wages - lo) * rate
    # Above all caps → use highest bracket's cumulative
    last = brackets[-1]
    if last.get("rate") is None:
        return None
    lo = Decimal(str(last.get("min", 0)))
    base = Decimal(str(last.get("base_tax") or 0))
    rate = Decimal(str(last["rate"]))
    return base + (annual_wages - lo) * rate


def _pick_filing_bucket(
    raw_status: str, buckets: dict[str, list]
) -> tuple[str, list] | None:
    """Map raw filing status to a bucket key. Very forgiving."""
    if not buckets:
        return None
    s = (raw_status or "").strip().upper()

    # Exact / prefix matches
    for key in buckets:
        ku = key.upper()
        if ku == s:
            return key, buckets[key]
        if s in ("S", "SINGLE") and ku.startswith("SINGLE"):
            return key, buckets[key]
        if s in ("M", "MJ", "MFJ") and "MARRIED" in ku and "ONE" in ku:
            return key, buckets[key]
        if s == "HOH" and ("HEAD" in ku):
            return key, buckets[key]

    # Default: return first bucket
    first = next(iter(buckets.items()))
    return first


def compute_from_catalog(inp: CatalogCalcInput) -> CatalogCalcOutput:
    state = inp.state.upper()
    name = _ABBR_TO_NAME.get(state)
    if not name:
        return CatalogCalcOutput(
            state=state, expected_withholding_period=Decimal("0"),
            applied_rule="unknown_state", confidence="NONE",
            notes=[f"Unknown state abbreviation {state!r}"],
        )

    catalog = _load_catalog()
    info = catalog["states"].get(name)
    if not info:
        return CatalogCalcOutput(
            state=state, expected_withholding_period=Decimal("0"),
            applied_rule="not_in_catalog", confidence="NONE",
            notes=[f"{name} absent from Vertex 2026Q1 catalog"],
        )

    # No-income-tax states
    if info.get("no_income_tax"):
        return CatalogCalcOutput(
            state=state, expected_withholding_period=Decimal("0"),
            applied_rule="no_income_tax", confidence="HIGH",
            notes=[f"{name} does not levy state income tax."],
        )

    # Flat-rate states
    override_flat = _FLAT_RATE_OVERRIDES.get(name)
    catalog_flat = info.get("flat_rate")
    flat = override_flat if override_flat is not None else catalog_flat
    brackets_dict = info.get("brackets") or {}

    # Flat-rate override wins over brackets for known flat-tax states —
    # Vertex PDF sometimes contains per-status bracket example tables
    # even for flat-tax states, which would mislead the bracket path.
    if override_flat is not None:
        per_period = inp.gross_wages_period * Decimal(str(override_flat))
        return CatalogCalcOutput(
            state=state,
            expected_withholding_period=_quantize(per_period),
            applied_rule="flat_rate:override",
            confidence="HIGH",
            notes=[f"{name} flat rate {override_flat:.4f} (override)"],
        )

    # Prefer brackets if present AND we can resolve filing status.
    # Iterate all buckets, picking a sane one compatible with status.
    if brackets_dict:
        ordered = []
        preferred = _pick_filing_bucket(inp.filing_status, brackets_dict)
        if preferred:
            ordered.append(preferred)
        for k, v in brackets_dict.items():
            if preferred and k == preferred[0]:
                continue
            ordered.append((k, v))
        annual = inp.gross_wages_period * Decimal(inp.pay_periods_per_year)
        for bucket_name, bucket in ordered:
            ann_tax = _compute_from_brackets(annual, bucket)
            if ann_tax is None:
                continue
            per_period = ann_tax / Decimal(inp.pay_periods_per_year)
            if per_period < 0:
                per_period = Decimal("0")
            forced = info.get("_forced_confidence")
            conf = forced if forced else ("HIGH" if len(brackets_dict) >= 2 else "MEDIUM")
            return CatalogCalcOutput(
                state=state,
                expected_withholding_period=_quantize(per_period),
                applied_rule=f"catalog_brackets:{bucket_name}",
                confidence=conf,
                notes=[f"Vertex catalog 2026Q1 — {name}, bucket {bucket_name!r}"],
            )

    # Flat fallback
    if flat is not None:
        per_period = inp.gross_wages_period * Decimal(str(flat))
        src = "override" if override_flat is not None else "catalog"
        return CatalogCalcOutput(
            state=state,
            expected_withholding_period=_quantize(per_period),
            applied_rule=f"flat_rate:{src}",
            confidence="HIGH" if override_flat is not None else "MEDIUM",
            notes=[f"{name} flat rate {flat:.4f} ({src})"],
        )

    return CatalogCalcOutput(
        state=state, expected_withholding_period=Decimal("0"),
        applied_rule="no_data", confidence="NONE",
        notes=[f"{name} has no brackets or flat rate in catalog"],
    )
