"""Batch 7 — workflows #35, #39, #41, #43, #44."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.labor_allocation_drift import run_labor_allocation_drift  # noqa: E402
from simploy.workflows.location_setup import run_location_setup  # noqa: E402
from simploy.workflows.naics_validation import run_naics_validation  # noqa: E402
from simploy.workflows.prepay_liability_sweep import run_prepay_liability_sweep  # noqa: E402
from simploy.workflows.unbundled_billing_audit import run_unbundled_billing_audit  # noqa: E402


# ---- #43 location setup ----


class LocFake:
    def __init__(self, rows): self.rows = rows
    async def list_client_locations(self, cid): return self.rows


@pytest.mark.asyncio
async def test_location_missing_address_critical_with_active_emp() -> None:
    r = LocFake([{"locationId": "L1", "addressLine1": "", "city": "", "state": "", "activeEmployees": 12}])
    rep = await run_location_setup(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "NO_ADDRESS" in codes
    assert "EMPLOYEE_AT_INCOMPLETE_LOCATION" in codes


@pytest.mark.asyncio
async def test_location_missing_suta_state_critical() -> None:
    # Empty state + empty sutaState = no SUTA attribution at all.
    r = LocFake([{"locationId": "L2", "addressLine1": "1 Main", "city": "Omaha", "state": "", "zipCode": "68102", "sutaState": "", "activeEmployees": 5}])
    rep = await run_location_setup(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "NO_SUTA_STATE" in codes


# ---- #41 NAICS validation ----


class NaicsFake:
    def __init__(self, naics, valid, deprecated, wc):
        self.naics = naics
        self.valid = valid
        self.deprecated = deprecated
        self.wc = wc
    async def get_client_naics(self, cid): return self.naics
    async def is_naics_valid(self, n): return self.valid
    async def is_naics_deprecated(self, n): return self.deprecated
    async def dominant_wc_class(self, cid): return self.wc


@pytest.mark.asyncio
async def test_naics_missing_critical() -> None:
    r = NaicsFake(naics="", valid=False, deprecated=False, wc="")
    a = await run_naics_validation(r, client_id="T")
    assert any(f.code == "NO_NAICS" for f in a.findings)


@pytest.mark.asyncio
async def test_naics_wc_mismatch_warning() -> None:
    # Clerical WC (8810) suggests sector 54, but NAICS 31 (manufacturing)
    r = NaicsFake(naics="311000", valid=True, deprecated=False, wc="8810")
    a = await run_naics_validation(r, client_id="T")
    codes = {f.code for f in a.findings}
    assert "MISMATCH_WITH_WC_CLASS" in codes


# ---- #35 Prepay-vs-liability sweep ----


class SweepFake:
    def __init__(self, balances, sweeps): self.b = balances; self.s = sweeps
    async def get_prepay_balances_by_month(self, cid, yr): return self.b
    async def get_sweeps_by_month(self, cid, yr): return self.s


@pytest.mark.asyncio
async def test_sweep_under_critical() -> None:
    r = SweepFake(
        balances={1: Decimal("5000")},
        sweeps={1: {"amount": "4500", "completedOn": "2025-02-01"}},
    )
    rep = await run_prepay_liability_sweep(r, client_id="T", year=2025, as_of=date(2026, 1, 1))
    m1 = [m for m in rep.months if m.month == 1][0]
    assert any(f.code == "SWEEP_UNDER" for f in m1.findings)


@pytest.mark.asyncio
async def test_sweep_not_performed_critical() -> None:
    r = SweepFake(
        balances={6: Decimal("3000")},
        sweeps={},
    )
    rep = await run_prepay_liability_sweep(r, client_id="T", year=2025, as_of=date(2026, 1, 1))
    m6 = [m for m in rep.months if m.month == 6][0]
    assert any(f.code == "SWEEP_NOT_PERFORMED" for f in m6.findings)


# ---- #39 Unbundled billing audit ----


class BillingFake:
    def __init__(self, rules, active, activity):
        self.rules = rules
        self.active = active
        self.activity = activity
    async def list_unbundled_billing_rules(self, cid): return self.rules
    async def list_active_components(self, cid): return self.active
    async def rule_recent_activity(self, cid, rid, ld): return self.activity.get(rid, True)


@pytest.mark.asyncio
async def test_unbundled_rate_out_of_range() -> None:
    r = BillingFake(
        rules=[{"ruleId": "R1", "component": "HC", "rate": "150"}],
        active=["HC"],
        activity={"R1": True},
    )
    rep = await run_unbundled_billing_audit(r, client_id="T")
    codes = {f.code for rule in rep.rules for f in rule.findings}
    assert "RATE_OUT_OF_RANGE" in codes


@pytest.mark.asyncio
async def test_unbundled_orphan_component() -> None:
    r = BillingFake(
        rules=[{"ruleId": "R1", "component": "HC", "rate": "5"}],
        active=["HC", "WC", "401K"],
        activity={"R1": True},
    )
    rep = await run_unbundled_billing_audit(r, client_id="T")
    assert "WC" in rep.orphan_components
    assert "401K" in rep.orphan_components


# ---- #44 Labor allocation drift ----


class LADFake:
    def __init__(self, allocs, inactive): self.a = allocs; self.i = inactive
    async def list_labor_allocations(self, cid): return self.a
    async def list_inactive_codes(self, cid): return self.i


@pytest.mark.asyncio
async def test_labor_not_100_pct_critical() -> None:
    r = LADFake(
        allocs=[
            {"employeeId": "E1", "codeType": "DEPT", "code": "100", "percent": "60"},
            {"employeeId": "E1", "codeType": "DEPT", "code": "200", "percent": "30"},
        ],
        inactive=set(),
    )
    rep = await run_labor_allocation_drift(r, client_id="T")
    assert any(f.code == "ALLOCATION_NOT_100_PCT" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_labor_inactive_code_critical() -> None:
    r = LADFake(
        allocs=[{"employeeId": "E2", "codeType": "DEPT", "code": "999", "percent": "100"}],
        inactive={"999"},
    )
    rep = await run_labor_allocation_drift(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "ALLOCATION_TO_INACTIVE_CODE" in codes


@pytest.mark.asyncio
async def test_labor_over_allocated_critical() -> None:
    r = LADFake(
        allocs=[
            {"employeeId": "E3", "codeType": "PROJ", "code": "A", "percent": "70"},
            {"employeeId": "E3", "codeType": "PROJ", "code": "B", "percent": "60"},
        ],
        inactive=set(),
    )
    rep = await run_labor_allocation_drift(r, client_id="T")
    assert any(f.code == "OVER_ALLOCATED" for f in rep.audits[0].findings)
