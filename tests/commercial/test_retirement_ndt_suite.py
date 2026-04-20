"""401k NDT + §125 + FSA 55 tests."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.retirement_ndt_suite import run_retirement_ndt  # noqa: E402


class FakeReader:
    def __init__(self, k401=None, s125=None, dcfsa=None):
        self.k401 = k401 or []
        self.s125 = s125 or []
        self.dcfsa = dcfsa or []
    async def list_401k_participants(self, cid, yr): return self.k401
    async def list_section_125_participants(self, cid, yr): return self.s125
    async def list_dependent_care_fsa(self, cid, yr): return self.dcfsa


async def _run(reader):
    return await run_retirement_ndt(
        reader, client_id="T", plan_year=2025, as_of=date(2026, 1, 15),
    )


@pytest.mark.asyncio
async def test_adp_passes_on_balanced_plan() -> None:
    # NHCE avg 4%, HCE avg 6% -> allowed is 4+2=6%, passes exactly
    reader = FakeReader(k401=[
        {"employeeId": "E1", "ytdGross": "100000", "ytdDeferral": "4000",
         "ytdEmployerMatch": "0", "ytdAfterTax": "0", "isHCE": False},
        {"employeeId": "E2", "ytdGross": "100000", "ytdDeferral": "4000",
         "ytdEmployerMatch": "0", "ytdAfterTax": "0", "isHCE": False},
        {"employeeId": "E3", "ytdGross": "200000", "ytdDeferral": "12000",
         "ytdEmployerMatch": "0", "ytdAfterTax": "0", "isHCE": True},
    ])
    r = await _run(reader)
    assert r.adp.passed


@pytest.mark.asyncio
async def test_adp_fails_when_hce_too_high() -> None:
    # NHCE 2%, HCE 10% -> allowed 4%, fails
    reader = FakeReader(k401=[
        {"employeeId": "E1", "ytdGross": "100000", "ytdDeferral": "2000",
         "ytdEmployerMatch": "0", "ytdAfterTax": "0", "isHCE": False},
        {"employeeId": "E2", "ytdGross": "200000", "ytdDeferral": "20000",
         "ytdEmployerMatch": "0", "ytdAfterTax": "0", "isHCE": True},
    ])
    r = await _run(reader)
    codes = {f.code for f in r.adp.findings}
    assert "ADP_TEST_FAILED" in codes
    assert not r.adp.passed


@pytest.mark.asyncio
async def test_acp_includes_after_tax() -> None:
    reader = FakeReader(k401=[
        {"employeeId": "E1", "ytdGross": "100000",
         "ytdDeferral": "0", "ytdEmployerMatch": "1000", "ytdAfterTax": "0", "isHCE": False},
        {"employeeId": "E2", "ytdGross": "200000",
         "ytdDeferral": "0", "ytdEmployerMatch": "15000", "ytdAfterTax": "5000", "isHCE": True},
    ])
    r = await _run(reader)
    codes = {f.code for f in r.acp.findings}
    assert "ACP_TEST_FAILED" in codes


@pytest.mark.asyncio
async def test_hce_missing_warning_uses_comp_threshold() -> None:
    reader = FakeReader(k401=[
        {"employeeId": "E1", "ytdGross": "50000", "ytdDeferral": "2000",
         "ytdEmployerMatch": "0", "ytdAfterTax": "0"},  # HCE flag missing
        {"employeeId": "E2", "ytdGross": "200000", "ytdDeferral": "8000",
         "ytdEmployerMatch": "0", "ytdAfterTax": "0"},
    ])
    r = await _run(reader)
    codes = {f.code for f in r.adp.findings}
    assert "HCE_DETERMINATION_NEEDED" in codes


@pytest.mark.asyncio
async def test_section_125_concentration_fails() -> None:
    # Key employees 40% concentration > 25%
    reader = FakeReader(s125=[
        {"employeeId": "K1", "ytdPretaxBenefits": "20000", "isKeyEmployee": True},
        {"employeeId": "R1", "ytdPretaxBenefits": "30000", "isKeyEmployee": False},
    ])
    r = await _run(reader)
    codes = {f.code for f in r.section_125.findings}
    assert "SECTION_125_CONCENTRATION" in codes
    assert not r.section_125.passed


@pytest.mark.asyncio
async def test_section_125_concentration_passes() -> None:
    reader = FakeReader(s125=[
        {"employeeId": "K1", "ytdPretaxBenefits": "5000", "isKeyEmployee": True},
        {"employeeId": "R1", "ytdPretaxBenefits": "30000", "isKeyEmployee": False},
    ])
    r = await _run(reader)
    assert r.section_125.passed


@pytest.mark.asyncio
async def test_fsa_55_fails_when_nhce_low() -> None:
    # HCE avg $5K, NHCE avg $2K -> 40% < 55% floor
    reader = FakeReader(dcfsa=[
        {"employeeId": "H1", "fsaBenefit": "5000", "isHCE": True},
        {"employeeId": "N1", "fsaBenefit": "2000", "isHCE": False},
    ])
    r = await _run(reader)
    codes = {f.code for f in r.fsa_55.findings}
    assert "FSA_55_PERCENT_FAILED" in codes
    assert not r.fsa_55.passed


@pytest.mark.asyncio
async def test_fsa_55_passes_when_nhce_high() -> None:
    reader = FakeReader(dcfsa=[
        {"employeeId": "H1", "fsaBenefit": "5000", "isHCE": True},
        {"employeeId": "N1", "fsaBenefit": "4000", "isHCE": False},
    ])
    r = await _run(reader)
    assert r.fsa_55.passed


@pytest.mark.asyncio
async def test_all_passed_aggregate_property() -> None:
    reader = FakeReader()  # empty inputs => passes (insufficient data)
    r = await _run(reader)
    assert r.all_passed
