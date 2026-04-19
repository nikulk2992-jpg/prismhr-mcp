"""1095-C Value Consistency Audit — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.form_1095c_consistency import run_1095c_consistency_audit  # noqa: E402


class FakeReader:
    def __init__(self, roster, monthly, enrolled, events, type_changes=None) -> None:
        self.roster = roster
        self.monthly = monthly
        self.enrolled = enrolled
        self.events = events
        self.type_changes = type_changes or {}

    async def list_employees_with_1095c(self, cid, year):
        return self.roster
    async def get_1095c_monthly(self, cid, eid, year):
        return self.monthly.get(eid, {})
    async def get_benefit_enrollment_months(self, cid, eid, year):
        return self.enrolled.get(eid, {})
    async def get_employment_events(self, cid, eid, year):
        return self.events.get(eid, [])
    async def get_status_type_changes(self, cid, eid, year):
        return self.type_changes.get(eid, [])


@pytest.mark.asyncio
async def test_1h_with_coverage_critical() -> None:
    r = FakeReader(
        roster=[{"employeeId": "E1"}],
        monthly={"E1": {"line14": {str(m): "1H" for m in range(1, 13)}}},
        enrolled={"E1": {m: True for m in range(1, 13)}},
        events={},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2025)
    codes = {f.code for f in rep.employees[0].findings}
    assert "CODE_1H_WITH_COVERAGE" in codes


@pytest.mark.asyncio
async def test_safe_harbor_conflict_1h_2c() -> None:
    r = FakeReader(
        roster=[{"employeeId": "E2"}],
        monthly={"E2": {"line14": {"3": "1H"}, "line16": {"3": "2C"}}},
        enrolled={"E2": {}},
        events={},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2025)
    codes = {f.code for f in rep.employees[0].findings}
    assert "SAFE_HARBOR_CONFLICT" in codes


@pytest.mark.asyncio
async def test_line15_populated_on_1h_critical() -> None:
    r = FakeReader(
        roster=[{"employeeId": "E3"}],
        monthly={"E3": {"line14": {"5": "1H"}, "line15": {"5": "125.00"}}},
        enrolled={"E3": {}},
        events={},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2025)
    codes = {f.code for f in rep.employees[0].findings}
    assert "LINE15_POPULATED_ON_NONSHARE_CODE" in codes


@pytest.mark.asyncio
async def test_safe_harbor_missing_on_1a_is_warning() -> None:
    # Blank Line 16 on an offer is legal-but-unprotected, not a
    # submission-blocking error. Should be warning severity.
    r = FakeReader(
        roster=[{"employeeId": "E4"}],
        monthly={"E4": {"line14": {"1": "1A"}}},
        enrolled={"E4": {}},
        events={},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2025)
    matching = [f for f in rep.employees[0].findings if f.code == "LINE16_BLANK_ON_OFFER"]
    assert matching, "should still surface finding"
    assert all(f.severity == "warning" for f in matching)


@pytest.mark.asyncio
async def test_ichra_code_invalid_pre_2020() -> None:
    r = FakeReader(
        roster=[{"employeeId": "E5"}],
        monthly={"E5": {"line14": {"1": "1L"}}},
        enrolled={"E5": {}},
        events={},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2019)
    codes = {f.code for f in rep.employees[0].findings}
    assert "ICHRA_CODE_INVALID_YEAR" in codes


@pytest.mark.asyncio
async def test_code_change_without_event_warning() -> None:
    # 1E all year except month 6 which flips to 1H, no employment event
    r = FakeReader(
        roster=[{"employeeId": "E6"}],
        monthly={"E6": {
            "line14": {**{str(m): "1E" for m in range(1, 13)}, "6": "1H"},
            "line16": {str(m): "2C" for m in range(1, 13)},
        }},
        enrolled={"E6": {m: True for m in range(1, 13)}},
        events={"E6": []},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2025)
    codes = [f.code for f in rep.employees[0].findings]
    assert "CODE_CHANGE_WITHOUT_EVENT" in codes


@pytest.mark.asyncio
async def test_ft_to_pt_lag_warning() -> None:
    # Employee went FT->PT in month 6 but Line 14 still 1E in months 7-12.
    l14 = {str(m): "1E" for m in range(1, 13)}
    r = FakeReader(
        roster=[{"employeeId": "E8"}],
        monthly={"E8": {"line14": l14, "line16": {str(m): "2C" for m in range(1, 13)}}},
        enrolled={"E8": {m: True for m in range(1, 13)}},
        events={},
        type_changes={"E8": [{"date": "2025-06-15", "from_type": "FT", "to_type": "PT"}]},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2025)
    codes = {f.code for f in rep.employees[0].findings}
    assert "FT_TO_PT_COVERAGE_LAG" in codes


@pytest.mark.asyncio
async def test_waiting_period_miscoded_critical() -> None:
    # PT->FT in month 3; months 3-5 = 1H but Line 16 = blank (should be 2D).
    l14 = {str(m): "1H" for m in range(3, 6)}
    l16 = {}  # blank across waiting period
    r = FakeReader(
        roster=[{"employeeId": "E9"}],
        monthly={"E9": {"line14": l14, "line16": l16}},
        enrolled={"E9": {}},
        events={},
        type_changes={"E9": [{"date": "2025-03-10", "from_type": "PT", "to_type": "FT"}]},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2025)
    codes = {f.code for f in rep.employees[0].findings}
    assert "WAITING_PERIOD_MISCODED" in codes


@pytest.mark.asyncio
async def test_status_type_change_mismatch() -> None:
    # employmentType change in month 4 but Line 14 unchanged around it.
    l14 = {str(m): "1E" for m in range(1, 13)}
    r = FakeReader(
        roster=[{"employeeId": "E10"}],
        monthly={"E10": {"line14": l14, "line16": {str(m): "2C" for m in range(1, 13)}}},
        enrolled={"E10": {m: True for m in range(1, 13)}},
        events={},
        type_changes={"E10": [{"date": "2025-04-01", "from_type": "SALARIED", "to_type": "HOURLY"}]},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2025)
    codes = {f.code for f in rep.employees[0].findings}
    assert "STATUS_TYPE_CHANGE_MISMATCH" in codes


@pytest.mark.asyncio
async def test_clean_employee_passes() -> None:
    r = FakeReader(
        roster=[{"employeeId": "E7"}],
        monthly={"E7": {
            "line14": {str(m): "1E" for m in range(1, 13)},
            "line15": {str(m): "125.00" for m in range(1, 13)},
            "line16": {str(m): "2C" for m in range(1, 13)},
        }},
        enrolled={"E7": {m: True for m in range(1, 13)}},
        events={},
    )
    rep = await run_1095c_consistency_audit(r, client_id="T", year=2025)
    assert rep.employees[0].findings == []
