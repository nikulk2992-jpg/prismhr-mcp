"""Off-cycle payroll audit — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.off_cycle_payroll_audit import run_off_cycle_payroll_audit  # noqa: E402


class FakeReader:
    def __init__(self, rows, avgs=None):
        self.rows = rows
        self.avgs = avgs or {}
    async def list_off_cycle_vouchers(self, cid, ps, pe):
        return self.rows
    async def get_employee_avg_regular_check(self, cid, eid):
        return self.avgs.get(eid, "0")


async def _run(reader):
    return await run_off_cycle_payroll_audit(
        reader, client_id="T",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        as_of=date(2026, 4, 20),
    )


@pytest.mark.asyncio
async def test_no_approver_critical() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1", "type": "B",
        "payDate": "2026-04-10", "totalEarnings": "5000",
        "supplementalTaxMethod": "FLAT_22",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "NO_APPROVER" in codes


@pytest.mark.asyncio
async def test_unusual_amount_warning() -> None:
    reader = FakeReader(
        rows=[{
            "voucherId": "V1", "employeeId": "E1", "type": "B",
            "payDate": "2026-04-10", "totalEarnings": "10000",
            "approver": "mgr", "supplementalTaxMethod": "FLAT_22",
        }],
        avgs={"E1": "1500"},
    )
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "UNUSUAL_AMOUNT" in codes


@pytest.mark.asyncio
async def test_bonus_without_tax_method_critical() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1", "type": "B",
        "payDate": "2026-04-10", "totalEarnings": "5000", "approver": "mgr",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "TAX_METHOD_MISSING" in codes


@pytest.mark.asyncio
async def test_manual_no_reason_warning() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1", "type": "M",
        "payDate": "2026-04-10", "totalEarnings": "500", "approver": "mgr",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "MANUAL_NO_REASON" in codes


@pytest.mark.asyncio
async def test_termination_no_final_critical() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1", "type": "M",
        "payDate": "2026-04-10", "totalEarnings": "500", "approver": "mgr",
        "reason": "stipend", "terminationDate": "2026-04-15",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "TERMINATION_NO_FINAL" in codes


@pytest.mark.asyncio
async def test_bonus_loop_warning() -> None:
    rows = [
        {"voucherId": f"V{i}", "employeeId": "E1", "type": "B",
         "payDate": f"2026-04-{1 + i:02d}", "totalEarnings": "1000",
         "approver": "mgr", "supplementalTaxMethod": "FLAT_22"}
        for i in range(4)
    ]
    reader = FakeReader(rows)
    r = await _run(reader)
    codes_any = {f.code for v in r.vouchers for f in v.findings}
    assert "MULTIPLE_BONUS_RUNS" in codes_any


@pytest.mark.asyncio
async def test_pre_dated_voucher_warning() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1", "type": "M",
        "payDate": "2026-03-01",  # way in the past
        "totalEarnings": "500", "approver": "mgr", "reason": "X",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "PRE_DATED_VOUCHER" in codes


@pytest.mark.asyncio
async def test_post_dated_future_warning() -> None:
    reader = FakeReader([{
        "voucherId": "V1", "employeeId": "E1", "type": "B",
        "payDate": "2026-06-01",  # way in future
        "totalEarnings": "5000", "approver": "mgr",
        "supplementalTaxMethod": "FLAT_22",
    }])
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "POST_DATED_FUTURE" in codes
