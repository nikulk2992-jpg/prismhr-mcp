"""Batch 6 — workflows #15, #27, #36, #37, #46."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.absence_journal_audit import run_absence_journal_audit  # noqa: E402
from simploy.workflows.benefit_adjustment_trail import run_benefit_adjustment_trail  # noqa: E402
from simploy.workflows.gl_template_integrity import run_gl_template_integrity  # noqa: E402
from simploy.workflows.state_tax_setup import run_state_tax_setup_validator  # noqa: E402
from simploy.workflows.suta_rate_drift import run_suta_rate_drift  # noqa: E402


# ---- #27 state tax setup ----


class StateSetupFake:
    def __init__(self, rows): self.rows = rows
    async def list_state_setups(self, cid): return self.rows


@pytest.mark.asyncio
async def test_state_setup_no_suta_critical() -> None:
    r = StateSetupFake([{"state": "CA", "hasWagesCurrentPeriod": True, "sutaAccountId": ""}])
    rep = await run_state_tax_setup_validator(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "NO_SUTA_ACCOUNT" in codes


@pytest.mark.asyncio
async def test_state_setup_no_wh_account_for_taxable_state() -> None:
    r = StateSetupFake([{
        "state": "CA", "hasWagesCurrentPeriod": True,
        "sutaAccountId": "12345", "sutaRate": "0.034",
        "withholdingAccountId": "",
    }])
    rep = await run_state_tax_setup_validator(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "NO_WH_ACCOUNT" in codes


@pytest.mark.asyncio
async def test_state_setup_no_income_tax_state_skips_wh_check() -> None:
    r = StateSetupFake([{
        "state": "TX", "hasWagesCurrentPeriod": True,
        "sutaAccountId": "99999", "sutaRate": "0.027",
        "withholdingAccountId": "",
    }])
    rep = await run_state_tax_setup_validator(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "NO_WH_ACCOUNT" not in codes


# ---- #36 GL template integrity ----


class GLFake:
    def __init__(self, template, pay, ded, plans, mappings):
        self.template = template
        self.pay = pay
        self.ded = ded
        self.plans = plans
        self.mappings = mappings
    async def get_client_gl_template(self, cid): return self.template
    async def list_active_pay_codes(self, cid): return self.pay
    async def list_active_deduction_codes(self, cid): return self.ded
    async def list_active_benefit_plans(self, cid): return self.plans
    async def get_gl_mappings(self, cid, tid): return self.mappings


@pytest.mark.asyncio
async def test_gl_no_template_critical() -> None:
    r = GLFake(template={}, pay=[], ded=[], plans=[], mappings={})
    rep = await run_gl_template_integrity(r, client_id="T")
    assert any(f.code == "NO_GL_TEMPLATE" for f in rep.findings)


@pytest.mark.asyncio
async def test_gl_unmapped_pay_code_critical() -> None:
    r = GLFake(
        template={"templateId": "TPL1"},
        pay=["REG", "OT"],
        ded=[],
        plans=[],
        mappings={"payCodes": {"REG": "5000"}, "deductions": {}, "benefitPlans": {}},
    )
    rep = await run_gl_template_integrity(r, client_id="T")
    codes = {f.code for f in rep.findings}
    assert "UNMAPPED_PAY_CODE" in codes
    assert "OT" in rep.pay_codes_unmapped


# ---- #37 SUTA rate drift ----


class SUTAFake:
    def __init__(self, accrual, billing): self.a = accrual; self.b = billing
    async def get_suta_accrual_rates(self, cid): return self.a
    async def get_suta_billing_rates(self, cid): return self.b


@pytest.mark.asyncio
async def test_suta_rate_misalignment_critical() -> None:
    r = SUTAFake(
        accrual=[{"state": "CA", "rate": "0.05", "effectiveDate": "2025-01-01"}],
        billing=[{"state": "CA", "rate": "0.04", "effectiveDate": "2025-01-01"}],
    )
    rep = await run_suta_rate_drift(r, client_id="T", as_of=date(2026, 1, 1))
    codes = {f.code for a in rep.audits for f in a.findings}
    assert "RATE_MISALIGNMENT" in codes


@pytest.mark.asyncio
async def test_suta_large_yoy_warning() -> None:
    r = SUTAFake(
        accrual=[
            {"state": "NE", "rate": "0.02", "effectiveDate": "2024-01-01"},
            {"state": "NE", "rate": "0.04", "effectiveDate": "2025-01-01"},
        ],
        billing=[],
    )
    rep = await run_suta_rate_drift(r, client_id="T", as_of=date(2026, 1, 1), yoy_change_pct="0.5")
    codes = {f.code for a in rep.audits for f in a.findings}
    assert "LARGE_YOY_CHANGE" in codes


# ---- #15 Benefit adjustment trail ----


class AdjFake:
    def __init__(self, adjustments, term_dates):
        self.adjustments = adjustments
        self.term_dates = term_dates
    async def list_benefit_adjustments(self, cid, s, e): return self.adjustments
    async def get_termination_date(self, cid, eid): return self.term_dates.get(eid)


@pytest.mark.asyncio
async def test_adj_large_warning() -> None:
    r = AdjFake(
        adjustments=[{"adjustmentId": "A1", "employeeId": "E1", "dateApplied": "2025-03-15", "amount": "2500", "reasonCode": "RETRO", "approver": "X"}],
        term_dates={},
    )
    rep = await run_benefit_adjustment_trail(
        r, client_id="T", window_start=date(2025, 1, 1), window_end=date(2025, 12, 31), large_threshold="1000"
    )
    codes = {f.code for f in rep.audits[0].findings}
    assert "LARGE_ADJUSTMENT" in codes


@pytest.mark.asyncio
async def test_adj_after_term_warning() -> None:
    r = AdjFake(
        adjustments=[{"adjustmentId": "A2", "employeeId": "E2", "dateApplied": "2025-05-15", "amount": "500", "reasonCode": "R", "approver": "X"}],
        term_dates={"E2": date(2025, 4, 1)},
    )
    rep = await run_benefit_adjustment_trail(r, client_id="T", window_start=date(2025, 1, 1), window_end=date(2025, 12, 31))
    codes = {f.code for f in rep.audits[0].findings}
    assert "ADJUSTMENT_AFTER_TERM" in codes


@pytest.mark.asyncio
async def test_adj_negative_without_approver_critical() -> None:
    r = AdjFake(
        adjustments=[{"adjustmentId": "A3", "employeeId": "E3", "dateApplied": "2025-03-15", "amount": "-250", "reasonCode": "R"}],
        term_dates={},
    )
    rep = await run_benefit_adjustment_trail(r, client_id="T", window_start=date(2025, 1, 1), window_end=date(2025, 12, 31))
    codes = {f.code for f in rep.audits[0].findings}
    assert "NEGATIVE_WITHOUT_JUSTIFICATION" in codes


# ---- #46 Absence journal audit ----


class AbsFake:
    def __init__(self, rows): self.rows = rows
    async def list_absence_journal(self, cid, s, e): return self.rows


@pytest.mark.asyncio
async def test_absence_orphan_entry_critical() -> None:
    r = AbsFake([{"journalId": "J1", "employeeId": "E1", "entryDate": "2025-04-10", "hours": "8", "absenceCode": "PTO", "voucherHoursPaid": "0", "balanceDelta": "0"}])
    rep = await run_absence_journal_audit(r, client_id="T", window_start=date(2025,4,1), window_end=date(2025,4,30))
    codes = {f.code for f in rep.audits[0].findings}
    assert "ORPHAN_ENTRY" in codes


@pytest.mark.asyncio
async def test_absence_concurrent_overlapping_warning() -> None:
    r = AbsFake([
        {"journalId": "J2", "employeeId": "E1", "entryDate": "2025-04-10", "hours": "8", "absenceCode": "PTO", "voucherHoursPaid": "8", "balanceDelta": "-8"},
        {"journalId": "J3", "employeeId": "E1", "entryDate": "2025-04-10", "hours": "4", "absenceCode": "SICK", "voucherHoursPaid": "4", "balanceDelta": "-4"},
    ])
    rep = await run_absence_journal_audit(r, client_id="T", window_start=date(2025,4,1), window_end=date(2025,4,30))
    codes = [f.code for a in rep.audits for f in a.findings]
    assert "CONCURRENT_OVERLAPPING" in codes
