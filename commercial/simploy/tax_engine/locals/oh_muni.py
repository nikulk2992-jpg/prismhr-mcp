"""Ohio municipal income tax calculator (HB 5 resident-credit model).

Calculation model (HB 5):
  1. Work-city tax = work_wages × work_city.work_rate
     (only if employee has worked >= 20 days in work_city OR it's
      their principal place of work)
  2. Resident-city tax liability = wages × resident_city.resident_rate
  3. Resident-city credit = min(work_city_tax,
                                wages × resident_city.credit_rate × credit_limit)
  4. Resident-city withholding = max(0, resident_liability - credit)

Total withholding = work_city_tax + resident_city_withholding.

This module loads a seed table of 11 major OH munis. Full refresh
via scripts/refresh_oh_muni.py. Override seed via
`.planning/locals-data/oh_muni_full.json`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


_SEED_PATH = (
    Path(__file__).resolve().parents[4]
    / "src" / "prismhr_mcp" / "data" / "locals" / "oh_muni_seed.json"
)
_OVERRIDE_PATH = Path(".planning/locals-data/oh_muni_full.json")

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        data = json.loads(_SEED_PATH.read_text())
        if _OVERRIDE_PATH.exists():
            try:
                override = json.loads(_OVERRIDE_PATH.read_text())
                data["muni_rates"].update(override.get("muni_rates") or {})
            except Exception:  # noqa: BLE001
                pass
        _cache = data
    return _cache


def _rates_for(muni: str) -> dict:
    if not muni:
        return _load()["fallback"]
    key = muni.strip().upper()
    data = _load()
    rate = data["muni_rates"].get(key)
    if rate:
        return {"name": key, **rate}
    return {"name": f"Unknown muni {key}", **data["fallback"]}


@dataclass
class OHMuniInput:
    gross_wages_period: Decimal
    home_muni: str
    work_muni: str
    days_worked_in_work_muni: int = 365  # assume full-time unless told otherwise
    is_principal_place_of_work: bool = True


@dataclass
class OHMuniOutput:
    total_withholding_period: Decimal
    work_city_tax: Decimal
    resident_city_tax: Decimal
    credit_applied: Decimal
    applied_rule: str
    home_rates: dict
    work_rates: dict
    notes: list[str] = field(default_factory=list)


def _q(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_oh_muni(inp: OHMuniInput) -> OHMuniOutput:
    data = _load()
    home = _rates_for(inp.home_muni)
    work = _rates_for(inp.work_muni)
    notes: list[str] = []

    threshold = int(data.get("twenty_day_rule", {}).get("threshold_days", 20))
    wages = inp.gross_wages_period

    # Work-city tax
    apply_work = (
        inp.is_principal_place_of_work
        or inp.days_worked_in_work_muni >= threshold
    )
    if apply_work and work.get("work_rate") is not None:
        work_tax = wages * Decimal(str(work["work_rate"]))
    else:
        work_tax = Decimal("0")
        if not apply_work:
            notes.append(
                f"20-day rule: only {inp.days_worked_in_work_muni} days in "
                f"{work.get('name')}; no work-city withholding required yet."
            )

    # Resident-city tax + credit for work-city tax paid
    resident_tax = Decimal("0")
    credit_applied = Decimal("0")
    resident_with = Decimal("0")
    same_muni = (
        (inp.home_muni or "").strip().upper()
        == (inp.work_muni or "").strip().upper()
        and inp.home_muni
    )
    if inp.home_muni and home.get("resident_rate") is not None and not same_muni:
        resident_tax = wages * Decimal(str(home["resident_rate"]))
        credit_rate = Decimal(str(home.get("credit_rate", 1.0)))
        credit_limit = Decimal(str(home.get("credit_limit", home["resident_rate"])))
        max_credit = min(
            work_tax,
            wages * credit_rate * credit_limit / Decimal(str(home["resident_rate"])),
        ) if home["resident_rate"] else Decimal("0")
        # Simpler: credit_limit is already a rate cap on creditable work tax
        max_credit = min(
            work_tax,
            wages * credit_rate * credit_limit,
        )
        credit_applied = max_credit
        resident_with = max(Decimal("0"), resident_tax - credit_applied)

    total = work_tax + resident_with
    applied_rule = (
        "same_muni"
        if same_muni
        else (
            "work_only_no_home"
            if not inp.home_muni
            else "work_and_resident_with_credit"
        )
    )

    return OHMuniOutput(
        total_withholding_period=_q(total),
        work_city_tax=_q(work_tax),
        resident_city_tax=_q(resident_tax),
        credit_applied=_q(credit_applied),
        applied_rule=applied_rule,
        home_rates=home, work_rates=work, notes=notes,
    )


def validate_oh_muni_withholding(
    *, gross_wages_period: Decimal, home_muni: str, work_muni: str,
    actual_total_withholding_period: Decimal,
    tolerance: Decimal = Decimal("0.50"),
    days_worked_in_work_muni: int = 365,
    is_principal_place_of_work: bool = True,
) -> dict:
    exp = compute_oh_muni(OHMuniInput(
        gross_wages_period=gross_wages_period,
        home_muni=home_muni, work_muni=work_muni,
        days_worked_in_work_muni=days_worked_in_work_muni,
        is_principal_place_of_work=is_principal_place_of_work,
    ))
    delta = actual_total_withholding_period - exp.total_withholding_period
    status = "match" if abs(delta) <= tolerance else "mismatch"
    return {
        "status": status,
        "expected_total": str(exp.total_withholding_period),
        "expected_work_city": str(exp.work_city_tax),
        "expected_resident_city": str(exp.resident_city_tax),
        "credit_applied": str(exp.credit_applied),
        "actual_total": str(actual_total_withholding_period),
        "delta": str(delta),
        "rule": exp.applied_rule,
        "home_muni_name": exp.home_rates.get("name"),
        "work_muni_name": exp.work_rates.get("name"),
        "notes": exp.notes,
    }
