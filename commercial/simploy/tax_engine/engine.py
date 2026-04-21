"""Central dispatcher for state tax engine.

Given a work state + wages + profile, routes to the appropriate state
module and returns the expected withholding. Used by tax_engine_diff.

Confidence scale:
  HIGH   — MO, IL, PA, MA (exact or flat-rate verifiable)
  MEDIUM — OH, NJ (bracket table approximated to Vertex)
  LOW    — CA, NY (multi-bracket approximation; use Vertex for per-penny)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from simploy.tax_engine.catalog_calc import (
    CatalogCalcInput,
    compute_from_catalog,
)
from simploy.tax_engine.states import il as il_mod
from simploy.tax_engine.states import ma as ma_mod
from simploy.tax_engine.states import mo as mo_mod
from simploy.tax_engine.states import nj as nj_mod
from simploy.tax_engine.states import oh as oh_mod
from simploy.tax_engine.states import pa as pa_mod


@dataclass
class StateCalcInput:
    work_state: str
    home_state: str
    gross_wages_period: Decimal
    pay_periods_per_year: int = 52
    filing_status: str = "S"
    allowances: int = 0
    has_nr_cert: bool = False
    work_state_withholding_period: Decimal = Decimal("0")


@dataclass
class StateCalcOutput:
    state: str
    expected_withholding_period: Decimal
    applied_rule: str
    confidence: str   # HIGH | MEDIUM | LOW
    notes: list[str]


CONFIDENCE = {
    "MO": "HIGH",
    "IL": "HIGH",
    "PA": "HIGH",
    "MA": "HIGH",
    "OH": "MEDIUM",
    "NJ": "MEDIUM",
    # CA / NY route through catalog (Vertex March 2026 brackets) — HIGH.
    "CA": "HIGH",
    "NY": "HIGH",
}


def compute_state(inp: StateCalcInput) -> StateCalcOutput:
    state = inp.work_state.upper()
    home = inp.home_state.upper()
    is_resident = (state == home) if state and home else True

    if state == "MO":
        r = mo_mod.compute_mo(mo_mod.MOCalcInput(
            gross_wages_period=inp.gross_wages_period,
            pay_periods_per_year=inp.pay_periods_per_year,
            filing_status=inp.filing_status if inp.filing_status in {"SM", "MFJ_SNW", "MFJ_SW", "HoH", "MFS"} else "SM",
            is_mo_resident=(home == "MO"),
            work_state=state,
            has_nr_cert=inp.has_nr_cert,
            work_state_withholding_period=inp.work_state_withholding_period,
        ))
        return StateCalcOutput(state, r.mo_withholding_period, r.applied_rule,
                               CONFIDENCE["MO"], r.notes)
    if state == "IL":
        r = il_mod.compute_il(il_mod.ILCalcInput(
            gross_wages_period=inp.gross_wages_period,
            pay_periods_per_year=inp.pay_periods_per_year,
            basic_allowances=inp.allowances,
            is_il_resident=(home == "IL"),
            work_state=state,
            has_nr_cert=inp.has_nr_cert,
            work_state_withholding_period=inp.work_state_withholding_period,
        ))
        return StateCalcOutput(state, r.il_withholding_period, r.applied_rule,
                               CONFIDENCE["IL"], r.notes)
    if state == "PA":
        r = pa_mod.compute_pa(pa_mod.PACalcInput(
            gross_wages_period=inp.gross_wages_period,
            is_pa_resident=(home == "PA"),
            work_state=state,
            has_nr_cert=inp.has_nr_cert,
            work_state_withholding_period=inp.work_state_withholding_period,
        ))
        return StateCalcOutput(state, r.pa_withholding_period, r.applied_rule,
                               CONFIDENCE["PA"], r.notes)
    if state == "OH":
        r = oh_mod.compute_oh(oh_mod.OHCalcInput(
            gross_wages_period=inp.gross_wages_period,
            pay_periods_per_year=inp.pay_periods_per_year,
            exemptions=inp.allowances,
            is_oh_resident=(home == "OH"),
            work_state=state,
            has_nr_cert=inp.has_nr_cert,
            work_state_withholding_period=inp.work_state_withholding_period,
        ))
        return StateCalcOutput(state, r.oh_withholding_period, r.applied_rule,
                               CONFIDENCE["OH"], r.notes)
    if state == "MA":
        r = ma_mod.compute_ma(ma_mod.MACalcInput(
            gross_wages_period=inp.gross_wages_period,
            pay_periods_per_year=inp.pay_periods_per_year,
            filing_status="MJ" if inp.filing_status in {"MFJ", "MJ"} else "S",
            is_ma_resident=(home == "MA"),
            work_state=state,
        ))
        return StateCalcOutput(state, r.ma_withholding_period, r.applied_rule,
                               CONFIDENCE["MA"], r.notes)
    if state == "NJ":
        r = nj_mod.compute_nj(nj_mod.NJCalcInput(
            gross_wages_period=inp.gross_wages_period,
            pay_periods_per_year=inp.pay_periods_per_year,
            exemptions=inp.allowances,
            is_nj_resident=(home == "NJ"),
            work_state=state,
            has_nr_cert=inp.has_nr_cert,
        ))
        return StateCalcOutput(state, r.nj_withholding_period, r.applied_rule,
                               CONFIDENCE["NJ"], r.notes)
    # CA / NY — route through Vertex catalog for HIGH confidence.
    # Custom modules (ca_mod, ny_mod) remain importable for reference
    # but the dispatcher uses catalog brackets from the March 2026 guide.

    # Fallback: Vertex catalog-backed generic calculator. Covers the
    # ~40 states without custom modules using bracket / flat / no-tax
    # classification from the 2026Q1 Vertex extraction.
    c = compute_from_catalog(CatalogCalcInput(
        state=state,
        gross_wages_period=inp.gross_wages_period,
        pay_periods_per_year=inp.pay_periods_per_year,
        filing_status=inp.filing_status,
    ))
    return StateCalcOutput(
        state=c.state,
        expected_withholding_period=c.expected_withholding_period,
        applied_rule=f"catalog:{c.applied_rule}",
        confidence=c.confidence,
        notes=c.notes,
    )
