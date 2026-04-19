"""Payroll Batch Health workflow — unit tests with in-memory reader fake."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.payroll_batch_health import (  # noqa: E402
    run_payroll_batch_health,
)


class FakeReader:
    def __init__(self, data: dict) -> None:
        self.data = data

    async def list_open_batches(self, client_id):
        return self.data["open"]

    async def get_batch_status(self, client_id, batch_id):
        return self.data["status"].get(batch_id, {})

    async def get_batch_info(self, client_id, batch_id):
        return self.data["info"].get(batch_id, {})

    async def get_batch_vouchers(self, client_id, batch_id):
        return self.data["vouchers"].get(batch_id, [])

    async def get_approval_summary(self, client_id, batch_id):
        return self.data["summary"].get(batch_id, {})


@pytest.mark.asyncio
async def test_fully_clean_batch_passes() -> None:
    reader = FakeReader({
        "open": [{"batchId": "B1"}],
        "status": {"B1": {"status": "TS.READY", "statusDescription": "Ready for time entry"}},
        "info": {"B1": {"payDate": "2026-04-25", "periodEnd": "2026-04-18"}},
        "vouchers": {"B1": [{"employeeId": "E1", "netPay": "1234.56"}]},
        "summary": {},
    })
    report = await run_payroll_batch_health(
        reader, client_id="TEST", as_of=date(2026, 4, 19),
    )
    assert report.total == 1
    assert report.clean == 1
    assert report.batches[0].findings == []


@pytest.mark.asyncio
async def test_stuck_approval_is_critical() -> None:
    reader = FakeReader({
        "open": [{"batchId": "B2"}],
        "status": {"B2": {"status": "AP.PEND", "statusDescription": "Awaiting approval"}},
        "info": {"B2": {"payDate": "2026-04-30", "periodEnd": "2026-04-10"}},
        "vouchers": {"B2": [{"netPay": "100"}]},
        "summary": {},
    })
    report = await run_payroll_batch_health(
        reader, client_id="TEST", as_of=date(2026, 4, 19),
    )
    codes = {f.code: f.severity for f in report.batches[0].findings}
    assert codes["STUCK_APPROVAL"] == "critical"


@pytest.mark.asyncio
async def test_paydate_past_with_no_post_is_critical() -> None:
    reader = FakeReader({
        "open": [{"batchId": "B3"}],
        "status": {"B3": {"status": "AP.READY"}},
        "info": {"B3": {"payDate": "2026-04-10", "periodEnd": "2026-04-03"}},
        "vouchers": {"B3": [{"netPay": "50"}]},
        "summary": {},
    })
    report = await run_payroll_batch_health(
        reader, client_id="TEST", as_of=date(2026, 4, 19),
    )
    codes = {f.code for f in report.batches[0].findings}
    assert "PAYDATE_PAST" in codes


@pytest.mark.asyncio
async def test_zero_voucher_post_init_is_critical() -> None:
    reader = FakeReader({
        "open": [{"batchId": "B4"}],
        "status": {"B4": {"status": "AP.PEND"}},
        "info": {"B4": {"payDate": "2026-05-01", "periodEnd": "2026-04-17"}},
        "vouchers": {"B4": []},
        "summary": {},
    })
    report = await run_payroll_batch_health(
        reader, client_id="TEST", as_of=date(2026, 4, 19),
    )
    codes = {f.code for f in report.batches[0].findings}
    assert "ZERO_VOUCHERS" in codes


@pytest.mark.asyncio
async def test_init_batch_with_zero_vouchers_not_flagged() -> None:
    reader = FakeReader({
        "open": [{"batchId": "B5"}],
        "status": {"B5": {"status": "INITIAL"}},
        "info": {"B5": {"payDate": "2026-05-01", "periodEnd": "2026-04-17"}},
        "vouchers": {"B5": []},
        "summary": {},
    })
    report = await run_payroll_batch_health(
        reader, client_id="TEST", as_of=date(2026, 4, 19),
    )
    codes = {f.code for f in report.batches[0].findings}
    assert "ZERO_VOUCHERS" not in codes


@pytest.mark.asyncio
async def test_negative_net_is_critical() -> None:
    reader = FakeReader({
        "open": [{"batchId": "B6"}],
        "status": {"B6": {"status": "AP.PEND"}},
        "info": {"B6": {"payDate": "2026-04-25", "periodEnd": "2026-04-18"}},
        "vouchers": {"B6": [
            {"employeeId": "OK1", "netPay": "500"},
            {"employeeId": "BAD", "netPay": "-42.10"},
        ]},
        "summary": {},
    })
    report = await run_payroll_batch_health(
        reader, client_id="TEST", as_of=date(2026, 4, 19),
    )
    codes = [f.code for f in report.batches[0].findings]
    assert "NEGATIVE_NET" in codes


@pytest.mark.asyncio
async def test_approval_summary_available_is_info() -> None:
    reader = FakeReader({
        "open": [{"batchId": "B7"}],
        "status": {"B7": {"status": "INITOK"}},
        "info": {"B7": {"payDate": "2026-05-01", "periodEnd": "2026-04-18"}},
        "vouchers": {"B7": [{"netPay": "100"}]},
        "summary": {"B7": {"approvalStatus": "PENDING", "total": "100"}},
    })
    report = await run_payroll_batch_health(
        reader, client_id="TEST", as_of=date(2026, 4, 19),
    )
    codes = {f.code: f.severity for f in report.batches[0].findings}
    assert codes.get("APPROVAL_SUMMARY_READY") == "info"


@pytest.mark.asyncio
async def test_empty_open_list_produces_empty_report() -> None:
    reader = FakeReader({
        "open": [],
        "status": {},
        "info": {},
        "vouchers": {},
        "summary": {},
    })
    report = await run_payroll_batch_health(
        reader, client_id="TEST", as_of=date(2026, 4, 19),
    )
    assert report.total == 0
    assert report.flagged == 0
