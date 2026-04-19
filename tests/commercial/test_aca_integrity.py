"""ACA Integrity workflow — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.aca_integrity import run_aca_integrity  # noqa: E402


class FakeReader:
    def __init__(self, form1094, offered, monthly) -> None:
        self.form1094 = form1094
        self.offered = offered
        self.monthly = monthly

    async def get_1094_data(self, cid, yr): return self.form1094
    async def get_aca_offered_employees(self, cid, yr): return self.offered
    async def get_monthly_aca_info(self, cid, yr): return self.monthly
    async def get_1095c_years(self, cid, eid): return {}


@pytest.mark.asyncio
async def test_mec_no_flagged_critical() -> None:
    r = FakeReader(
        form1094={"mecIndicator": [{"month": 3, "indicator": "No"}]},
        offered=[],
        monthly=[],
    )
    rep = await run_aca_integrity(r, client_id="T", year=2026)
    m3 = [m for m in rep.months if m.month == 3][0]
    assert any(f.code == "MEC_INDICATOR_NO" and f.severity == "critical" for f in m3.findings)


@pytest.mark.asyncio
async def test_mec_below_95pct_flagged() -> None:
    r = FakeReader(
        form1094={"mecIndicator": []},
        offered=[],
        monthly=[{"month": 1, "fullTimeCount": 100, "mecCount": 80}],
    )
    rep = await run_aca_integrity(r, client_id="T", year=2026)
    m1 = [m for m in rep.months if m.month == 1][0]
    assert any(f.code == "MEC_BELOW_95_PCT" for f in m1.findings)


@pytest.mark.asyncio
async def test_safe_harbor_missing_with_offer_code() -> None:
    r = FakeReader(
        form1094={},
        offered=[{
            "employeeId": "E1",
            "offerCodes": {"1": "1A", "2": "1A"},
            "safeHarborCodes": {"1": "2A"},  # month 2 missing
        }],
        monthly=[],
    )
    rep = await run_aca_integrity(r, client_id="T", year=2026)
    codes = [f.code for e in rep.employees for f in e.findings]
    assert codes.count("SAFE_HARBOR_MISSING") == 1


@pytest.mark.asyncio
async def test_1g_with_line16_is_warning() -> None:
    r = FakeReader(
        form1094={},
        offered=[{
            "employeeId": "E2",
            "offerCodes": {"5": "1G"},
            "safeHarborCodes": {"5": "2C"},
        }],
        monthly=[],
    )
    rep = await run_aca_integrity(r, client_id="T", year=2026)
    codes = {f.code for e in rep.employees for f in e.findings}
    assert "OFFER_CODE_1G_LINE16_POPULATED" in codes


@pytest.mark.asyncio
async def test_clean_report_has_no_findings() -> None:
    r = FakeReader(
        form1094={"mecIndicator": [{"month": m, "indicator": "Yes"} for m in range(1, 13)]},
        offered=[],
        monthly=[{"month": m, "fullTimeCount": 100, "mecCount": 100} for m in range(1, 13)],
    )
    rep = await run_aca_integrity(r, client_id="T", year=2026)
    assert rep.critical_count == 0
