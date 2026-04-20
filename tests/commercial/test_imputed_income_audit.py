"""Imputed income audit — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.imputed_income_audit import run_imputed_income_audit  # noqa: E402


class FakeReader:
    def __init__(self, rows): self.rows = rows
    async def list_employees_with_fringe_benefits(self, cid, yr):
        return self.rows


async def _run(reader):
    return await run_imputed_income_audit(
        reader, client_id="T", tax_year=2025, as_of=date(2026, 1, 15),
    )


@pytest.mark.asyncio
async def test_gtl_over_50k_not_imputed_critical() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "age": 40,
        "gtlCoverageAmount": "100000",
        "gtlImputedYtd": "0",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "GTL_OVER_50K_NOT_IMPUTED" in codes


@pytest.mark.asyncio
async def test_gtl_under_50k_no_flag() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "age": 40,
        "gtlCoverageAmount": "40000",
        "gtlImputedYtd": "0",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "GTL_OVER_50K_NOT_IMPUTED" not in codes


@pytest.mark.asyncio
async def test_dp_not_imputed_critical() -> None:
    reader = FakeReader([{
        "employeeId": "E1",
        "dpEnrolled": True, "dpEmployerPremium": "6000",
        "dpImputedYtd": "0",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "DP_BENEFIT_NOT_IMPUTED" in codes


@pytest.mark.asyncio
async def test_auto_fringe_missing_warning() -> None:
    reader = FakeReader([{
        "employeeId": "E1",
        "hasCompanyAuto": True, "autoImputedYtd": "0",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "AUTO_FRINGE_MISSING" in codes


@pytest.mark.asyncio
async def test_moving_expense_not_taxed_critical() -> None:
    reader = FakeReader([{
        "employeeId": "E1",
        "movingReimbYtd": "5000", "movingReimbTaxedYtd": "0",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "MOVING_EXPENSE_NOT_TAXED" in codes


@pytest.mark.asyncio
async def test_negative_imputed_critical() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "age": 40,
        "gtlCoverageAmount": "100000",
        "gtlImputedYtd": "-500",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "NEGATIVE_IMPUTED" in codes


@pytest.mark.asyncio
async def test_clean_record_no_flags() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "age": 40,
        "gtlCoverageAmount": "40000",
        "gtlImputedYtd": "0",
    }])
    r = await _run(reader)
    assert r.employees[0].findings == []
