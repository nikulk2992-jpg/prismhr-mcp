"""Billing-vs-Payroll Reconciliation — unit tests."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.billing_payroll_recon import run_billing_payroll_recon  # noqa: E402


class FakeReader:
    def __init__(self, billing, payroll) -> None:
        self.billing = billing
        self.payroll = payroll
    async def billing_totals_by_month(self, cid, yr): return self.billing
    async def payroll_totals_by_month(self, cid, yr): return self.payroll


@pytest.mark.asyncio
async def test_matching_totals_pass() -> None:
    r = FakeReader(
        billing={m: Decimal("10000") for m in range(1, 13)},
        payroll={m: Decimal("10000") for m in range(1, 13)},
    )
    rep = await run_billing_payroll_recon(r, client_id="T", year=2025, tolerance=Decimal("50"))
    assert rep.flagged == 0


@pytest.mark.asyncio
async def test_zero_billing_with_payroll_critical() -> None:
    r = FakeReader(
        billing={1: Decimal("0")},
        payroll={1: Decimal("5000")},
    )
    rep = await run_billing_payroll_recon(r, client_id="T", year=2025)
    m1 = [m for m in rep.months if m.month == 1][0]
    assert any(f.code == "ZERO_BILL_WITH_PAYROLL" for f in m1.findings)


@pytest.mark.asyncio
async def test_underbilled_critical() -> None:
    r = FakeReader(
        billing={1: Decimal("5000")},
        payroll={1: Decimal("6000")},
    )
    rep = await run_billing_payroll_recon(r, client_id="T", year=2025, tolerance=Decimal("50"))
    m1 = [m for m in rep.months if m.month == 1][0]
    assert any(f.code == "UNDERBILLED" for f in m1.findings)


@pytest.mark.asyncio
async def test_overbilled_warning() -> None:
    r = FakeReader(
        billing={1: Decimal("6500")},
        payroll={1: Decimal("5000")},
    )
    rep = await run_billing_payroll_recon(r, client_id="T", year=2025, tolerance=Decimal("50"))
    m1 = [m for m in rep.months if m.month == 1][0]
    assert any(f.code == "OVERBILLED" for f in m1.findings)


@pytest.mark.asyncio
async def test_tolerance_absorbs_small_drift() -> None:
    r = FakeReader(
        billing={1: Decimal("5010")},
        payroll={1: Decimal("5000")},
    )
    rep = await run_billing_payroll_recon(r, client_id="T", year=2025, tolerance=Decimal("50"))
    m1 = [m for m in rep.months if m.month == 1][0]
    assert m1.findings == []
