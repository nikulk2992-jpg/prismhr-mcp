"""Prior-PEO YTD conversion recon tests."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.prior_peo_conversion import run_prior_peo_conversion_recon  # noqa: E402


class FakeReader:
    def __init__(self, prior=None, current=None, active=None):
        self.prior = prior or []
        self.current = current or []
        self.active = active or []
    async def list_prior_peo_statements(self, cid, dt): return self.prior
    async def list_current_ytd(self, cid, yr): return self.current
    async def list_active_employees_at(self, cid, dt): return self.active


async def _run(reader, year=2026):
    return await run_prior_peo_conversion_recon(
        reader, client_id="T",
        conversion_date=date(2026, 4, 1),
        tax_year=year,
        as_of=date(2026, 4, 5),
    )


@pytest.mark.asyncio
async def test_no_prior_statement_critical() -> None:
    reader = FakeReader(prior=[], current=[], active=["E1"])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "NO_PRIOR_STATEMENT" in codes


@pytest.mark.asyncio
async def test_ytd_not_loaded_critical() -> None:
    reader = FakeReader(
        prior=[{"employeeId": "E1", "priorYtdWages": "20000"}],
        current=[{"employeeId": "E1", "ytdGross": "0"}],
        active=["E1"],
    )
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "YTD_NOT_LOADED" in codes


@pytest.mark.asyncio
async def test_wage_mismatch_critical() -> None:
    reader = FakeReader(
        prior=[{"employeeId": "E1", "priorYtdWages": "20000"}],
        current=[{"employeeId": "E1", "ytdGross": "19000"}],
        active=["E1"],
    )
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "WAGE_MISMATCH" in codes


@pytest.mark.asyncio
async def test_401k_missing_critical() -> None:
    reader = FakeReader(
        prior=[{"employeeId": "E1", "priorYtdWages": "20000",
                "priorYtd401k": "5000"}],
        current=[{"employeeId": "E1", "ytdGross": "20000",
                  "ytd401kDeferrals": "0"}],
        active=["E1"],
    )
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "401K_YTD_MISSING" in codes


@pytest.mark.asyncio
async def test_ss_cap_exceeded_warning() -> None:
    reader = FakeReader(
        prior=[{"employeeId": "E1", "priorYtdWages": "180000",
                "priorYtdSSWages": "180000"}],
        current=[{"employeeId": "E1", "ytdGross": "180000",
                  "ytdSSWages": "180000"}],
        active=["E1"],
    )
    r = await _run(reader, year=2026)
    codes = {f.code for f in r.employees[0].findings}
    assert "SS_WAGE_CAP_EXCEEDED" in codes  # $180K > $176,100 2026 cap


@pytest.mark.asyncio
async def test_state_wage_mismatch_critical() -> None:
    reader = FakeReader(
        prior=[{"employeeId": "E1", "priorYtdWages": "20000",
                "priorStateYtd": {"MO": "20000"}}],
        current=[{"employeeId": "E1", "ytdGross": "20000",
                  "ytdStateWages": {"MO": "15000"}}],
        active=["E1"],
    )
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "STATE_WAGE_MISMATCH" in codes


@pytest.mark.asyncio
async def test_clean_conversion_passes() -> None:
    reader = FakeReader(
        prior=[{"employeeId": "E1", "priorYtdWages": "20000",
                "priorYtdFit": "2000", "priorYtdSSWages": "20000",
                "priorYtdMedicareWages": "20000", "priorYtd401k": "1000"}],
        current=[{"employeeId": "E1", "ytdGross": "20000",
                  "ytdFit": "2000", "ytdSSWages": "20000",
                  "ytdMedicareWages": "20000", "ytd401kDeferrals": "1000"}],
        active=["E1"],
    )
    r = await _run(reader)
    assert r.employees[0].findings == []
    assert r.clean == 1
