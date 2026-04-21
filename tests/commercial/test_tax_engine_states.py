"""Tests for OH / CA / NY / MA / NJ / PA state engines + dispatcher."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.tax_engine.engine import StateCalcInput, compute_state  # noqa: E402
from simploy.tax_engine.states.ca import CACalcInput, compute_ca  # noqa: E402
from simploy.tax_engine.states.ma import MACalcInput, compute_ma  # noqa: E402
from simploy.tax_engine.states.nj import NJCalcInput, compute_nj  # noqa: E402
from simploy.tax_engine.states.ny import NYCalcInput, compute_ny  # noqa: E402
from simploy.tax_engine.states.oh import OHCalcInput, compute_oh  # noqa: E402
from simploy.tax_engine.states.pa import PACalcInput, compute_pa  # noqa: E402


# ---------- PA ----------


def test_pa_flat_rate() -> None:
    # $1,000 × 3.07% = 30.70
    r = compute_pa(PACalcInput(
        gross_wages_period=Decimal("1000"),
        is_pa_resident=True, work_state="PA",
    ))
    assert r.pa_withholding_period == Decimal("30.70")


def test_pa_resident_with_nr_cert_out_of_state() -> None:
    r = compute_pa(PACalcInput(
        gross_wages_period=Decimal("1000"),
        is_pa_resident=True, work_state="NJ",
        has_nr_cert=True,
    ))
    assert r.pa_withholding_period == Decimal("0")
    assert r.applied_rule == "resident_suppressed"


def test_pa_resident_reduced_by_work_state() -> None:
    # PA resident works in NJ without cert; PA reduced by NJ withholding
    r = compute_pa(PACalcInput(
        gross_wages_period=Decimal("1000"),
        is_pa_resident=True, work_state="NJ",
        has_nr_cert=False,
        work_state_withholding_period=Decimal("20"),
    ))
    # 30.70 - 20 = 10.70
    assert r.pa_withholding_period == Decimal("10.70")
    assert r.applied_rule == "resident_reduced"


# ---------- OH ----------


def test_oh_low_bracket() -> None:
    # Annual 52000, exemption 0, bracket: Line 2 at $26,050 + 2.99% × excess
    # Tax = 462.39 + 2.99% × (52000 - 26050) = 462.39 + 776.09 = 1238.48
    # Per pay = 1238.48 / 52 = 23.82
    r = compute_oh(OHCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        exemptions=0,
        is_oh_resident=True,
        work_state="OH",
    ))
    assert Decimal("23") <= r.oh_withholding_period <= Decimal("25")


def test_oh_reciprocal_state_with_nr_cert() -> None:
    # KY resident works in OH with IT-4 NR
    r = compute_oh(OHCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        is_oh_resident=False,
        work_state="OH",
        has_nr_cert=True,
    ))
    assert r.oh_withholding_period == Decimal("0")
    assert r.applied_rule == "reciprocal_exempt"


# ---------- MA ----------


def test_ma_flat_5_percent() -> None:
    # $1000/week × 52 = 52000 annual - 4400 exemption = 47600 taxable
    # × 5% = 2380 annual / 52 = 45.77
    r = compute_ma(MACalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        filing_status="S",
    ))
    assert Decimal("44") <= r.ma_withholding_period <= Decimal("48")


def test_ma_millionaire_surtax_applies_over_threshold() -> None:
    # Per-period wages = 25,000 × 52 = 1,300,000 annual - 4400 = 1,295,600
    # Surtax: 4% on (1,295,600 - 1,083,150) = 4% × 212,450 = 8,498
    # Regular: 5% × 1,295,600 = 64,780
    # Total: 73,278 / 52 = 1,409.19
    r = compute_ma(MACalcInput(
        gross_wages_period=Decimal("25000"),
        pay_periods_per_year=52,
        filing_status="S",
    ))
    assert any("surtax" in n.lower() for n in r.notes)


# ---------- NJ ----------


def test_nj_low_bracket_resident() -> None:
    r = compute_nj(NJCalcInput(
        gross_wages_period=Decimal("500"),
        pay_periods_per_year=52,
        exemptions=1,
        is_nj_resident=True,
    ))
    # Annual 26000 - 1000 = 25000 taxable. Bracket 2: 280 + 1.75%*5000 = 367.50 / 52 = 7.07
    assert Decimal("6") <= r.nj_withholding_period <= Decimal("8")


def test_nj_pa_reciprocal_exempt_with_cert() -> None:
    # PA resident works in NJ with NJ-165
    r = compute_nj(NJCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        is_nj_resident=False,
        work_state="NJ",
        has_nr_cert=True,
    ))
    assert r.nj_withholding_period == Decimal("0")
    assert r.applied_rule == "reciprocal_exempt"


# ---------- CA ----------


def test_ca_basic_calc() -> None:
    r = compute_ca(CACalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        is_ca_resident=True,
    ))
    assert r.ca_withholding_period >= Decimal("0")
    assert any("approximation" in n.lower() for n in r.notes)


# ---------- NY ----------


def test_ny_basic_calc() -> None:
    r = compute_ny(NYCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        is_ny_resident=True,
    ))
    assert r.ny_withholding_period >= Decimal("0")


def test_ny_resident_out_of_state_still_withholds() -> None:
    r = compute_ny(NYCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        is_ny_resident=True,
        work_state="NJ",
    ))
    assert r.ny_withholding_period > Decimal("0")
    assert r.applied_rule == "resident_with_credit"


# ---------- Dispatcher ----------


def test_dispatcher_routes_mo() -> None:
    out = compute_state(StateCalcInput(
        work_state="MO", home_state="MO",
        gross_wages_period=Decimal("1000"),
        filing_status="SM",
    ))
    assert out.state == "MO"
    assert out.confidence == "HIGH"


def test_dispatcher_routes_pa() -> None:
    out = compute_state(StateCalcInput(
        work_state="PA", home_state="PA",
        gross_wages_period=Decimal("1000"),
    ))
    assert out.state == "PA"
    assert out.expected_withholding_period == Decimal("30.70")


def test_dispatcher_unsupported_state_returns_zero() -> None:
    # TX has no state income tax — catalog fallback classifies as HIGH $0.
    out = compute_state(StateCalcInput(
        work_state="TX", home_state="TX",
        gross_wages_period=Decimal("1000"),
    ))
    assert out.expected_withholding_period == Decimal("0")
    assert out.confidence == "HIGH"
    assert "no_income_tax" in out.applied_rule


def test_dispatcher_ca_marked_low_confidence() -> None:
    out = compute_state(StateCalcInput(
        work_state="CA", home_state="CA",
        gross_wages_period=Decimal("1000"),
    ))
    assert out.confidence == "LOW"
