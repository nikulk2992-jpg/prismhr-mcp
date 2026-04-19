"""Garnishment Payment History — unit tests."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.garnishment_history import run_garnishment_history_audit  # noqa: E402


class FakeReader:
    def __init__(self, holders, details, payments) -> None:
        self.holders = holders
        self.details = details
        self.payments = payments
    async def list_garnishment_holders(self, cid): return self.holders
    async def get_garnishment_details(self, cid, eid): return self.details.get(eid, [])
    async def get_garnishment_payments(self, cid, eid): return self.payments.get(eid, [])


@pytest.mark.asyncio
async def test_active_garnishment_no_payments_is_critical() -> None:
    r = FakeReader(
        holders=[{"employeeId": "E1"}],
        details={"E1": [{"garnishmentId": "G1", "active": True, "balance": "1000"}]},
        payments={"E1": []},
    )
    rep = await run_garnishment_history_audit(r, client_id="T")
    assert any(f.code == "NO_PAYMENTS_AT_ALL" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_overdue_payment_critical() -> None:
    today = date(2026, 4, 19)
    r = FakeReader(
        holders=[{"employeeId": "E2"}],
        details={"E2": [{"garnishmentId": "G2", "active": True, "balance": "500"}]},
        payments={"E2": [{"garnishmentId": "G2", "paymentDate": (today - timedelta(days=60)).isoformat(), "amount": "100"}]},
    )
    rep = await run_garnishment_history_audit(r, client_id="T", as_of=today, overdue_days=45)
    assert any(f.code == "PAYMENT_OVERDUE" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_recent_payment_passes() -> None:
    today = date(2026, 4, 19)
    r = FakeReader(
        holders=[{"employeeId": "E3"}],
        details={"E3": [{"garnishmentId": "G3", "active": True, "balance": "500"}]},
        payments={"E3": [{"garnishmentId": "G3", "paymentDate": (today - timedelta(days=7)).isoformat(), "amount": "100"}]},
    )
    rep = await run_garnishment_history_audit(r, client_id="T", as_of=today)
    assert rep.audits[0].findings == []


@pytest.mark.asyncio
async def test_multiple_active_garnishments_warning() -> None:
    today = date(2026, 4, 19)
    r = FakeReader(
        holders=[{"employeeId": "E4"}],
        details={"E4": [
            {"garnishmentId": "G4a", "active": True, "balance": "200"},
            {"garnishmentId": "G4b", "active": True, "balance": "300"},
        ]},
        payments={"E4": [
            {"garnishmentId": "G4a", "paymentDate": (today - timedelta(days=5)).isoformat(), "amount": "50"},
            {"garnishmentId": "G4b", "paymentDate": (today - timedelta(days=5)).isoformat(), "amount": "80"},
        ]},
    )
    rep = await run_garnishment_history_audit(r, client_id="T", as_of=today)
    all_codes = [f.code for a in rep.audits for f in a.findings]
    assert "MULTIPLE_GARNISHMENTS" in all_codes
