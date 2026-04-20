"""Bonus gross-up audit — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.bonus_gross_up_audit import run_bonus_gross_up_audit  # noqa: E402


class FakeReader:
    def __init__(self, rows): self.rows = rows
    async def list_bonus_vouchers(self, cid, ps, pe): return self.rows


async def _run(reader):
    return await run_bonus_gross_up_audit(
        reader, client_id="T",
        period_start=date(2026, 1, 1), period_end=date(2026, 12, 31),
        as_of=date(2026, 4, 20),
    )


@pytest.mark.asyncio
async def test_flat_22_correct_rate_passes() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1",
        "supplementalMethod": "FLAT_22",
        "supplementalAmount": "5000",
        "federalWithheld": "1100",   # 22% of 5000
        "workState": "TX",
        "stateWithheld": "0",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.bonuses[0].findings}
    assert "WRONG_SUPPLEMENTAL_RATE" not in codes


@pytest.mark.asyncio
async def test_flat_22_wrong_rate_critical() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1",
        "supplementalMethod": "FLAT_22",
        "supplementalAmount": "5000",
        "federalWithheld": "800",    # WAY under 22%
        "workState": "TX",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.bonuses[0].findings}
    assert "WRONG_SUPPLEMENTAL_RATE" in codes


@pytest.mark.asyncio
async def test_over_1m_no_37pct_critical() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1",
        "supplementalMethod": "FLAT_22",
        "supplementalAmount": "100000",
        "ytdSupplementalWages": "1500000",  # already over $1M
        "federalWithheld": "22000",          # 22%, should be 37%
        "workState": "TX",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.bonuses[0].findings}
    assert "OVER_1M_NO_37PCT" in codes


@pytest.mark.asyncio
async def test_ny_state_supp_rate_wrong_warning() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1",
        "supplementalMethod": "FLAT_22",
        "supplementalAmount": "10000",
        "federalWithheld": "2200",
        "workState": "NY",
        "stateWithheld": "100",   # NY supp = 11.23%, expected $1,123
    }])
    r = await _run(reader)
    codes = {f.code for f in r.bonuses[0].findings}
    assert "STATE_SUPP_RATE_WRONG" in codes


@pytest.mark.asyncio
async def test_gross_up_mismatch_critical() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1",
        "supplementalMethod": "FLAT_22",
        "supplementalAmount": "10000",
        "federalWithheld": "2200",
        "workState": "TX",
        "isGrossUp": True,
        "targetNetRequested": "8000",
        "netPay": "7500",  # off by $500
    }])
    r = await _run(reader)
    codes = {f.code for f in r.bonuses[0].findings}
    assert "GROSS_UP_MISMATCH" in codes


@pytest.mark.asyncio
async def test_aggregate_without_context_warning() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1",
        "supplementalMethod": "AGGREGATE",
        "supplementalAmount": "3000",
        "workState": "TX",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.bonuses[0].findings}
    assert "AGGREGATE_NOT_ANNUALIZED" in codes


@pytest.mark.asyncio
async def test_unknown_method_critical() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1",
        "supplementalMethod": "CUSTOM",
        "supplementalAmount": "1000",
        "workState": "TX",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.bonuses[0].findings}
    assert "MIXED_METHODS" in codes
