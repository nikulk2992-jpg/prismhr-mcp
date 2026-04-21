"""Tests for PA EIT + OH municipal local tax calculators + MCP tools."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from prismhr_mcp.auth.prismhr_session import LOGIN_PATH  # noqa: E402
from prismhr_mcp.registry import create_server  # noqa: E402
from simploy.tax_engine.locals.oh_muni import (  # noqa: E402
    OHMuniInput, compute_oh_muni, validate_oh_muni_withholding,
)
from simploy.tax_engine.locals.pa_eit import (  # noqa: E402
    PAEITInput, compute_pa_eit, validate_pa_eit_withholding,
)


# ---------- PA EIT ----------


def test_pa_act32_applies_greater_of_home_resident_vs_work_nonresident() -> None:
    # Pittsburgh resident (3%) working in Bethlehem (1% NR)
    out = compute_pa_eit(PAEITInput(
        gross_wages_period=Decimal("2000"),
        home_psd="730402",  # Pittsburgh
        work_psd="480103",  # Bethlehem
    ))
    # max(3% resident, 1% nonresident) = 3%
    assert out.rate == Decimal("0.03")
    assert out.expected_withholding_period == Decimal("60.00")
    assert out.applied_rule == "act32_home_resident_rate"


def test_pa_act32_uses_work_nonresident_when_greater() -> None:
    # Bethlehem resident (1%) working in Pittsburgh (1% NR)
    # Equal rates → applied_rule is "act32_equal_rates"
    out = compute_pa_eit(PAEITInput(
        gross_wages_period=Decimal("2000"),
        home_psd="480103",  # Bethlehem 1%
        work_psd="730402",  # Pittsburgh NR 1%
    ))
    assert out.rate == Decimal("0.01")
    assert out.expected_withholding_period == Decimal("20.00")


def test_pa_philadelphia_nonresident_rate_applied() -> None:
    # Pittsburgh resident working in Philadelphia (outside Act 32)
    out = compute_pa_eit(PAEITInput(
        gross_wages_period=Decimal("2000"),
        home_psd="730402",
        work_psd="510101",  # Philadelphia
    ))
    # Philly NR 3.44%
    assert out.rate == Decimal("0.0344")
    assert out.applied_rule == "philly_nonresident_wage_tax"
    assert out.expected_withholding_period == Decimal("68.80")


def test_pa_philadelphia_resident_rate_for_phila_residents() -> None:
    out = compute_pa_eit(PAEITInput(
        gross_wages_period=Decimal("2000"),
        home_psd="510101",  # Phila resident
        work_psd="510101",  # Phila work
    ))
    assert out.rate == Decimal("0.0375")
    assert out.applied_rule == "philly_resident_wage_tax"


def test_pa_unknown_psd_uses_fallback_1pct() -> None:
    out = compute_pa_eit(PAEITInput(
        gross_wages_period=Decimal("1000"),
        home_psd="999999", work_psd="999998",
    ))
    assert out.rate == Decimal("0.01")


def test_pa_validator_reports_match_and_mismatch() -> None:
    m = validate_pa_eit_withholding(
        gross_wages_period=Decimal("2000"),
        home_psd="730402", work_psd="480103",
        actual_withholding_period=Decimal("60.00"),
    )
    assert m["status"] == "match"

    mm = validate_pa_eit_withholding(
        gross_wages_period=Decimal("2000"),
        home_psd="730402", work_psd="480103",
        actual_withholding_period=Decimal("20.00"),
    )
    assert mm["status"] == "mismatch"
    assert Decimal(mm["delta"]) < 0  # actual < expected


# ---------- OH municipal ----------


def test_oh_work_only_no_home_muni() -> None:
    out = compute_oh_muni(OHMuniInput(
        gross_wages_period=Decimal("1000"),
        home_muni="", work_muni="COLUMBUS",
    ))
    # Columbus 2.5% work rate
    assert out.work_city_tax == Decimal("25.00")
    assert out.resident_city_tax == Decimal("0")
    assert out.total_withholding_period == Decimal("25.00")


def test_oh_same_muni_home_and_work_no_credit_logic() -> None:
    out = compute_oh_muni(OHMuniInput(
        gross_wages_period=Decimal("1000"),
        home_muni="COLUMBUS", work_muni="COLUMBUS",
    ))
    # Both Columbus → just the 2.5% once
    assert out.total_withholding_period == Decimal("25.00")
    assert out.applied_rule == "same_muni"


def test_oh_cross_muni_resident_credit_full() -> None:
    # Cleveland resident working in Columbus
    # Columbus 2.5% work tax = $25; Cleveland 2.5% resident; credit_limit 2% → cap $20
    # So credit = min($25, $20) = $20; resident = max(0, 25 - 20) = $5
    # Total = 25 + 5 = $30
    out = compute_oh_muni(OHMuniInput(
        gross_wages_period=Decimal("1000"),
        home_muni="CLEVELAND", work_muni="COLUMBUS",
    ))
    assert out.work_city_tax == Decimal("25.00")
    assert out.credit_applied == Decimal("20.00")
    assert out.total_withholding_period == Decimal("30.00")


def test_oh_twenty_day_rule_suppresses_work_city_withholding() -> None:
    out = compute_oh_muni(OHMuniInput(
        gross_wages_period=Decimal("1000"),
        home_muni="COLUMBUS", work_muni="CINCINNATI",
        days_worked_in_work_muni=10,
        is_principal_place_of_work=False,
    ))
    # Under 20 days + not principal → no Cincinnati tax
    assert out.work_city_tax == Decimal("0")
    # Columbus resident still owes resident rate
    # Resident tax = 2.5%; no work-city tax so no credit; resident withhold = $25
    assert out.resident_city_tax == Decimal("25.00")
    assert out.total_withholding_period == Decimal("25.00")


def test_oh_unknown_muni_uses_fallback_2pct() -> None:
    out = compute_oh_muni(OHMuniInput(
        gross_wages_period=Decimal("1000"),
        home_muni="", work_muni="MADEUPVILLE",
    ))
    # Fallback 2%
    assert out.work_city_tax == Decimal("20.00")


def test_oh_validator_match_and_mismatch() -> None:
    m = validate_oh_muni_withholding(
        gross_wages_period=Decimal("1000"),
        home_muni="", work_muni="COLUMBUS",
        actual_total_withholding_period=Decimal("25.00"),
    )
    assert m["status"] == "match"
    mm = validate_oh_muni_withholding(
        gross_wages_period=Decimal("1000"),
        home_muni="", work_muni="COLUMBUS",
        actual_total_withholding_period=Decimal("10.00"),
    )
    assert mm["status"] == "mismatch"


# ---------- MCP tool wiring ----------


def _structured(result) -> dict:
    if isinstance(result, tuple) and len(result) == 2 and result[1] is not None:
        return result[1]
    blocks = result[0] if isinstance(result, tuple) else result
    if blocks:
        text = getattr(blocks[0], "text", None)
        if text:
            return json.loads(text)
    pytest.fail(f"no structured payload in {result!r}")
    return {}


def _build(runtime):
    from simploy.tools.tax_locals import register_tax_locals_tools
    server, registry = create_server()
    register_tax_locals_tools(server, registry, runtime.prismhr, runtime.permissions)
    return server


async def test_mcp_tool_pa_eit_returns_validation(runtime) -> None:
    server = _build(runtime)
    result = await server.call_tool(
        "commercial_tax_local_pa_eit_validate",
        {
            "gross_wages_period": "2000.00",
            "home_psd": "730402",
            "work_psd": "480103",
            "actual_withholding_period": "60.00",
        },
    )
    data = _structured(result)
    assert data["status"] == "match"


async def test_mcp_tool_oh_muni_returns_validation(runtime) -> None:
    server = _build(runtime)
    result = await server.call_tool(
        "commercial_tax_local_oh_muni_validate",
        {
            "gross_wages_period": "1000.00",
            "home_muni": "CLEVELAND",
            "work_muni": "COLUMBUS",
            "actual_total_withholding_period": "30.00",
        },
    )
    data = _structured(result)
    assert data["status"] == "match"
