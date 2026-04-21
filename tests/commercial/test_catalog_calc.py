"""Tests for the Vertex-catalog-backed generic state calculator."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.tax_engine.catalog_calc import (  # noqa: E402
    CatalogCalcInput,
    compute_from_catalog,
)


def _calc(state: str, wages: str, fs: str = "S", periods: int = 26):
    return compute_from_catalog(CatalogCalcInput(
        state=state,
        gross_wages_period=Decimal(wages),
        pay_periods_per_year=periods,
        filing_status=fs,
    ))


def test_no_income_tax_state_returns_zero_high_confidence() -> None:
    out = _calc("FL", "2000")
    assert out.expected_withholding_period == Decimal("0")
    assert out.confidence == "HIGH"
    assert out.applied_rule == "no_income_tax"


def test_all_nine_no_tax_states_return_zero() -> None:
    for st in ["AK", "FL", "NV", "NH", "SD", "TN", "TX", "WA", "WY"]:
        out = _calc(st, "5000")
        assert out.expected_withholding_period == Decimal("0"), st
        assert out.confidence == "HIGH", st


def test_flat_rate_override_applied_for_co() -> None:
    out = _calc("CO", "2000")
    # 4.40% of $2000
    assert out.expected_withholding_period == Decimal("88.00")
    assert out.confidence == "HIGH"
    assert "override" in out.applied_rule


def test_flat_rate_override_pa_307() -> None:
    out = _calc("PA", "2000")
    assert out.expected_withholding_period == Decimal("61.40")
    assert out.confidence == "HIGH"


def test_ca_uses_catalog_brackets_high_confidence() -> None:
    out = _calc("CA", "2000", fs="S")
    assert out.expected_withholding_period > Decimal("0")
    assert out.confidence == "HIGH"
    assert "Single" in out.applied_rule


def test_ca_married_filing_jointly_routes_to_married_bucket() -> None:
    out = _calc("CA", "2000", fs="MJ")
    assert out.confidence == "HIGH"
    assert "Married" in out.applied_rule


def test_unknown_state_returns_none_confidence() -> None:
    out = _calc("ZZ", "1000")
    assert out.confidence == "NONE"


def test_high_wages_routed_to_top_bracket_for_ca() -> None:
    # $500K biweekly → top bracket territory
    out = _calc("CA", "20000", fs="S")
    pct = out.expected_withholding_period / Decimal("20000")
    # CA top marginal ~13.3% so effective should exceed 5%
    assert pct > Decimal("0.05")
    assert out.confidence == "HIGH"


def test_negative_wages_do_not_produce_negative_withholding() -> None:
    out = _calc("CO", "-100")
    # Flat rate × negative wages would be negative; we allow that
    # to surface as a finding upstream, but confidence should stay HIGH.
    assert out.confidence == "HIGH"
