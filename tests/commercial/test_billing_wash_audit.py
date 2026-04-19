"""Billing-vs-Payroll Wash Audit — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.billing_wash_audit import run_billing_wash_audit  # noqa: E402


class FakeReader:
    def __init__(self, billing, confirmations, deductions, plan_map) -> None:
        self.billing = billing
        self.confirmations = confirmations
        self.deductions = deductions
        self.plan_map = plan_map

    async def get_billing_vouchers_by_month(self, cid, yr, mo):
        return self.billing

    async def get_benefit_confirmations(self, cid):
        return self.confirmations

    async def get_scheduled_deductions(self, cid, eid):
        return self.deductions.get(eid, [])

    async def get_group_benefit_plan(self, pid):
        return self.plan_map.get(pid, {})


@pytest.mark.asyncio
async def test_matching_billed_deducted_has_no_findings() -> None:
    r = FakeReader(
        billing=[{"employeeId": "E1", "planId": "MED", "premiumBilled": "125.00"}],
        confirmations=[{"employeeId": "E1", "plans": [{"planId": "MED"}]}],
        deductions={"E1": [{"code": "MEDEE", "amount": "125.00"}]},
        plan_map={"MED": {"prDednCode": "MEDEE"}},
    )
    rep = await run_billing_wash_audit(r, client_id="T", year=2026, month=4)
    assert rep.rows[0].findings == []


@pytest.mark.asyncio
async def test_billed_no_deduction_critical() -> None:
    r = FakeReader(
        billing=[{"employeeId": "E2", "planId": "MED", "premiumBilled": "125.00"}],
        confirmations=[{"employeeId": "E2", "plans": [{"planId": "MED"}]}],
        deductions={"E2": []},
        plan_map={"MED": {"prDednCode": "MEDEE"}},
    )
    rep = await run_billing_wash_audit(r, client_id="T", year=2026, month=4)
    codes = {f.code for f in rep.rows[0].findings}
    assert "BILLED_NO_DEDUCTION" in codes


@pytest.mark.asyncio
async def test_deducted_no_bill_critical() -> None:
    r = FakeReader(
        billing=[],
        confirmations=[{"employeeId": "E3", "plans": [{"planId": "MED"}]}],
        deductions={"E3": [{"code": "MEDEE", "amount": "100.00"}]},
        plan_map={"MED": {"prDednCode": "MEDEE"}},
    )
    rep = await run_billing_wash_audit(r, client_id="T", year=2026, month=4)
    codes = {f.code for f in rep.rows[0].findings}
    assert "DEDUCTED_NO_BILL" in codes


@pytest.mark.asyncio
async def test_tolerance_absorbs_penny_drift() -> None:
    r = FakeReader(
        billing=[{"employeeId": "E4", "planId": "MED", "premiumBilled": "125.01"}],
        confirmations=[{"employeeId": "E4", "plans": [{"planId": "MED"}]}],
        deductions={"E4": [{"code": "MEDEE", "amount": "125.00"}]},
        plan_map={"MED": {"prDednCode": "MEDEE"}},
    )
    rep = await run_billing_wash_audit(r, client_id="T", year=2026, month=4, tolerance=Decimal("0.50"))
    assert rep.rows[0].findings == []
