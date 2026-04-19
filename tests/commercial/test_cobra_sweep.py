"""COBRA Eligibility Sweep — unit tests."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.cobra_eligibility_sweep import run_cobra_sweep  # noqa: E402


class FakeReader:
    def __init__(self, terms, cobra) -> None:
        self.terms = terms
        self.cobra = cobra
    async def get_terminations(self, cid, lookback_days): return self.terms
    async def get_cobra_enrollees(self, cid): return self.cobra


@pytest.mark.asyncio
async def test_termination_no_cobra_record_critical_after_window() -> None:
    today = date(2026, 4, 19)
    r = FakeReader(
        terms=[{"employeeId": "E1", "statusDate": (today - timedelta(days=50)).isoformat(), "termReasonCode": "Q"}],
        cobra=[],
    )
    rep = await run_cobra_sweep(r, client_id="T", as_of=today)
    codes = {f.code: f.severity for f in rep.audits[0].findings}
    assert codes.get("NOTICE_WINDOW_CLOSED") == "critical"


@pytest.mark.asyncio
async def test_recent_termination_is_warning() -> None:
    today = date(2026, 4, 19)
    r = FakeReader(
        terms=[{"employeeId": "E2", "statusDate": (today - timedelta(days=5)).isoformat()}],
        cobra=[],
    )
    rep = await run_cobra_sweep(r, client_id="T", as_of=today)
    assert any(f.code == "NOTICE_WINDOW_CLOSING" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_cobra_enrollee_with_near_election_deadline() -> None:
    today = date(2026, 4, 19)
    r = FakeReader(
        terms=[{"employeeId": "E3", "statusDate": (today - timedelta(days=30)).isoformat()}],
        cobra=[{"employeeId": "E3", "cobraStatus": "PENDING", "electionDeadline": (today + timedelta(days=3)).isoformat()}],
    )
    rep = await run_cobra_sweep(r, client_id="T", as_of=today)
    assert any(f.code == "ELECTION_WINDOW_CLOSING" for f in rep.audits[0].findings)
