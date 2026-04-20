"""Final paycheck state compliance — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.final_paycheck_compliance import run_final_paycheck_compliance  # noqa: E402


class FakeReader:
    def __init__(self, rows): self.rows = rows
    async def list_recent_separations(self, cid, since): return self.rows


async def _run(reader, today=date(2026, 4, 20)):
    return await run_final_paycheck_compliance(
        reader, client_id="T",
        since=date(2026, 1, 1),
        as_of=today,
    )


@pytest.mark.asyncio
async def test_ca_involuntary_same_day_overdue() -> None:
    """CA involuntary term requires IMMEDIATE final check. 10 days late
    = critical overdue + waiting-time penalty risk."""
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "workState": "CA",
        "separationDate": "2026-04-10",
        "separationType": "INVOLUNTARY",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.separations[0].findings}
    assert "FINAL_CHECK_OVERDUE" in codes
    assert "WAITING_TIME_PENALTY_RISK" in codes
    assert r.waiting_time_exposure == 1


@pytest.mark.asyncio
async def test_ca_voluntary_quit_72h_grace() -> None:
    """CA voluntary quit = 72h deadline."""
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "workState": "CA",
        "separationDate": "2026-04-10",
        "separationType": "VOLUNTARY",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.separations[0].findings}
    # After 10 days, 72h deadline blown
    assert "FINAL_CHECK_OVERDUE" in codes


@pytest.mark.asyncio
async def test_pto_payout_owed_in_ca() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "workState": "CA",
        "separationDate": "2026-04-10",
        "separationType": "VOLUNTARY",
        "finalCheckIssuedDate": "2026-04-12",
        "finalCheckAmount": "2500",
        "unpaidPtoHours": "40",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.separations[0].findings}
    assert "PTO_PAYOUT_OWED" in codes


@pytest.mark.asyncio
async def test_ma_separation_notice_required() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "workState": "MA",
        "separationDate": "2026-04-19",
        "separationType": "INVOLUNTARY",
        "separationNoticeIssued": False,
    }])
    r = await _run(reader)
    codes = {f.code for f in r.separations[0].findings}
    assert "SEPARATION_NOTICE_MISSING" in codes


@pytest.mark.asyncio
async def test_unpaid_commission_critical() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "workState": "TX",
        "separationDate": "2026-04-10",
        "separationType": "INVOLUNTARY",
        "unpaidCommission": "5000",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.separations[0].findings}
    assert "COMMISSION_UNPAID" in codes


@pytest.mark.asyncio
async def test_tx_6_day_deadline() -> None:
    """TX involuntary = 6 days. Term on the 10th, today's the 20th = overdue."""
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "workState": "TX",
        "separationDate": "2026-04-10",
        "separationType": "INVOLUNTARY",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.separations[0].findings}
    assert "FINAL_CHECK_OVERDUE" in codes
    # TX does NOT have daily penalty wages
    assert "WAITING_TIME_PENALTY_RISK" not in codes


@pytest.mark.asyncio
async def test_timely_final_check_no_findings() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "workState": "CA",
        "separationDate": "2026-04-19",
        "separationType": "VOLUNTARY",
        "finalCheckIssuedDate": "2026-04-20",
        "finalCheckAmount": "2500",
    }])
    r = await _run(reader, today=date(2026, 4, 20))
    codes = {f.code for f in r.separations[0].findings}
    assert "FINAL_CHECK_OVERDUE" not in codes
    assert "WAITING_TIME_PENALTY_RISK" not in codes
