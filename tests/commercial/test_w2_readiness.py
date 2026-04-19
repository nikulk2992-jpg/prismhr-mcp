"""W-2 Readiness — unit tests."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.w2_readiness import run_w2_readiness  # noqa: E402


class FakeReader:
    def __init__(self, ids, ssns, ytd, fed) -> None:
        self.ids = ids
        self.ssns = ssns
        self.ytd = ytd
        self.fed = fed
    async def list_active_employees(self, cid): return self.ids
    async def get_ssn(self, cid, eid): return self.ssns.get(eid, "")
    async def get_ytd_gross(self, cid, eid, yr): return self.ytd.get(eid, Decimal("0"))
    async def federal_wh_configured(self, cid, eid): return self.fed.get(eid, False)


@pytest.mark.asyncio
async def test_clean_employee_passes() -> None:
    r = FakeReader(
        ids=["E1"],
        ssns={"E1": "123-45-6789"},
        ytd={"E1": Decimal("50000")},
        fed={"E1": True},
    )
    rep = await run_w2_readiness(r, client_id="T", year=2025)
    assert rep.audits[0].findings == []


@pytest.mark.asyncio
async def test_missing_ssn_critical() -> None:
    r = FakeReader(ids=["E2"], ssns={"E2": ""}, ytd={"E2": Decimal("100")}, fed={"E2": True})
    rep = await run_w2_readiness(r, client_id="T", year=2025)
    assert any(f.code == "MISSING_SSN" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_masked_ssn_flagged() -> None:
    r = FakeReader(ids=["E3"], ssns={"E3": "***-**-****"}, ytd={"E3": Decimal("100")}, fed={"E3": True})
    rep = await run_w2_readiness(r, client_id="T", year=2025)
    assert any(f.code == "MISSING_SSN" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_invalid_ssn_format_critical() -> None:
    r = FakeReader(ids=["E4"], ssns={"E4": "12345"}, ytd={"E4": Decimal("100")}, fed={"E4": True})
    rep = await run_w2_readiness(r, client_id="T", year=2025)
    assert any(f.code == "INVALID_SSN_FORMAT" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_federal_wh_missing_critical() -> None:
    r = FakeReader(ids=["E5"], ssns={"E5": "123-45-6789"}, ytd={"E5": Decimal("50000")}, fed={"E5": False})
    rep = await run_w2_readiness(r, client_id="T", year=2025)
    assert any(f.code == "FEDERAL_WH_MISSING" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_zero_ytd_warning() -> None:
    r = FakeReader(ids=["E6"], ssns={"E6": "123-45-6789"}, ytd={"E6": Decimal("0")}, fed={"E6": True})
    rep = await run_w2_readiness(r, client_id="T", year=2025)
    assert any(f.code == "YTD_ZERO_GROSS" and f.severity == "warning" for f in rep.audits[0].findings)
