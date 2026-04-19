"""401(k) Match Compliance workflow — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.retirement_match_compliance import (  # noqa: E402
    run_retirement_match_compliance,
)


class FakeReader:
    def __init__(self, plan, rules, contribs, deductions, dobs) -> None:
        self.plan = plan
        self.rules = rules
        self.contribs = contribs
        self.deductions = deductions
        self.dobs = dobs

    async def get_retirement_plan(self, cid): return self.plan
    async def get_401k_match_rules(self, cid, pid): return self.rules
    async def get_employee_401k_contributions(self, cid, yr): return self.contribs
    async def get_scheduled_deductions(self, cid, eid): return self.deductions.get(eid, [])
    async def get_employee_dob(self, cid, eid): return self.dobs.get(eid)


@pytest.mark.asyncio
async def test_clean_match_no_findings() -> None:
    # Plan: 100% match up to 3% of gross
    r = FakeReader(
        plan={"retirePlan": "401K"},
        rules=[{"matchPercent": 100, "matchUpToPercent": 3}],
        contribs=[{"employeeId": "E1", "employeeContribution": "1500", "employerMatch": "1500", "ytdGross": "50000"}],
        deductions={},
        dobs={"E1": date(1985, 1, 1)},
    )
    rep = await run_retirement_match_compliance(r, client_id="T", year=2026, as_of=date(2026, 6, 30))
    assert rep.employees[0].findings == []


@pytest.mark.asyncio
async def test_match_short_critical() -> None:
    r = FakeReader(
        plan={"retirePlan": "401K"},
        rules=[{"matchPercent": 100, "matchUpToPercent": 3}],
        contribs=[{"employeeId": "E2", "employeeContribution": "1500", "employerMatch": "500", "ytdGross": "50000"}],
        deductions={},
        dobs={},
    )
    rep = await run_retirement_match_compliance(r, client_id="T", year=2026)
    codes = {f.code for f in rep.employees[0].findings}
    assert "MATCH_SHORT" in codes


@pytest.mark.asyncio
async def test_over_402g_limit_critical_under_50() -> None:
    r = FakeReader(
        plan={"retirePlan": "401K"},
        rules=[{"matchPercent": 100, "matchUpToPercent": 3}],
        contribs=[{"employeeId": "E3", "employeeContribution": "25000", "employerMatch": "1500", "ytdGross": "80000"}],
        deductions={},
        dobs={"E3": date(1990, 1, 1)},
    )
    rep = await run_retirement_match_compliance(r, client_id="T", year=2026, as_of=date(2026, 12, 31))
    codes = {f.code for f in rep.employees[0].findings}
    assert "OVER_402G_LIMIT" in codes


@pytest.mark.asyncio
async def test_catchup_not_enabled_for_50plus() -> None:
    r = FakeReader(
        plan={"retirePlan": "401K"},
        rules=[{"matchPercent": 100, "matchUpToPercent": 3}],
        contribs=[{"employeeId": "E4", "employeeContribution": "25000", "employerMatch": "2400", "ytdGross": "80000"}],
        deductions={"E4": [{"code": "401K"}]},  # no catchup code
        dobs={"E4": date(1970, 1, 1)},
    )
    rep = await run_retirement_match_compliance(r, client_id="T", year=2026, as_of=date(2026, 12, 31))
    codes = {f.code for f in rep.employees[0].findings}
    assert "CATCHUP_NOT_ENABLED" in codes


@pytest.mark.asyncio
async def test_catchup_present_for_50plus_not_flagged() -> None:
    r = FakeReader(
        plan={"retirePlan": "401K"},
        rules=[{"matchPercent": 100, "matchUpToPercent": 3}],
        contribs=[{"employeeId": "E5", "employeeContribution": "25000", "employerMatch": "2400", "ytdGross": "80000"}],
        deductions={"E5": [{"code": "401K"}, {"code": "CATCHUP401K"}]},
        dobs={"E5": date(1970, 1, 1)},
    )
    rep = await run_retirement_match_compliance(r, client_id="T", year=2026, as_of=date(2026, 12, 31))
    codes = {f.code for f in rep.employees[0].findings}
    assert "CATCHUP_NOT_ENABLED" not in codes
