"""Client Go-Live Readiness — unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.client_golive_readiness import run_client_golive_readiness  # noqa: E402


class FakeReader:
    def __init__(self, **kwargs) -> None:
        self.data = kwargs
    async def get_client_master(self, cid): return self.data.get("master", {"clientId": cid})
    async def get_client_ownership(self, cid): return self.data.get("ownership", {})
    async def get_pay_groups(self, cid): return self.data.get("pay_groups", [])
    async def get_payroll_schedule(self, cid): return self.data.get("schedule", [])
    async def get_client_location_details(self, cid): return self.data.get("location", {})
    async def count_active_employees(self, cid): return self.data.get("emp_count", 0)
    async def get_benefit_plans(self, cid): return self.data.get("benefits", [])
    async def get_retirement_plan_list(self, cid): return self.data.get("retirement", [])


@pytest.mark.asyncio
async def test_fully_ready_client_passes() -> None:
    r = FakeReader(
        ownership={"fein": "12-3456789"},
        pay_groups=[{"groupId": "B"}],
        schedule=[{"scheduleId": "BW"}],
        location={"state": "NE", "sutaState": "NE"},
        emp_count=25,
        benefits=[{"planId": "MED"}],
        retirement=[{"retirePlan": "401K"}],
    )
    rep = await run_client_golive_readiness(r, client_id="T")
    assert rep.ready
    assert rep.score == 100.0


@pytest.mark.asyncio
async def test_missing_pay_group_critical() -> None:
    r = FakeReader(
        ownership={"fein": "12-3456789"},
        pay_groups=[],
        schedule=[{"scheduleId": "BW"}],
        location={"state": "NE"},
        emp_count=25,
    )
    rep = await run_client_golive_readiness(r, client_id="T")
    codes = {f.code for f in rep.findings}
    assert "NO_PAY_GROUP" in codes
    assert not rep.ready


@pytest.mark.asyncio
async def test_missing_fein_critical() -> None:
    r = FakeReader(
        ownership={},
        pay_groups=[{"groupId": "B"}],
        schedule=[{"scheduleId": "BW"}],
        location={"state": "NE"},
        emp_count=25,
    )
    rep = await run_client_golive_readiness(r, client_id="T")
    assert any(f.code == "NO_OWNERSHIP" for f in rep.findings)


@pytest.mark.asyncio
async def test_empty_client_scores_low() -> None:
    r = FakeReader()
    rep = await run_client_golive_readiness(r, client_id="T")
    assert rep.score < 50
    assert not rep.ready


@pytest.mark.asyncio
async def test_no_benefits_is_warning_not_critical() -> None:
    r = FakeReader(
        ownership={"fein": "12-3456789"},
        pay_groups=[{"groupId": "B"}],
        schedule=[{"scheduleId": "BW"}],
        location={"state": "NE"},
        emp_count=25,
        benefits=[],
        retirement=[],
    )
    rep = await run_client_golive_readiness(r, client_id="T")
    # All criticals should be resolved
    crit = [f for f in rep.findings if f.severity == "critical"]
    assert crit == []
