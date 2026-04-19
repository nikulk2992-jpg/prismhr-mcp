"""Batch 4 — workflows #4, #7, #18, #22, #25.

Compact: each workflow gets a happy path + critical-finding path.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.dependent_age_out import run_dependent_age_out  # noqa: E402
from simploy.workflows.form_941_reconciliation import run_form_941_reconciliation  # noqa: E402
from simploy.workflows.manual_check_audit import run_manual_check_audit  # noqa: E402
from simploy.workflows.retirement_true_up import run_retirement_true_up  # noqa: E402
from simploy.workflows.terminated_cleanup import run_terminated_cleanup  # noqa: E402


# ---- #4 Terminated cleanup ----


class TermFake:
    def __init__(self, termed, final_check, deds, benefits, cobra, pto, ach):
        self.termed = termed
        self.final_check = final_check
        self.deds = deds
        self.benefits = benefits
        self.cobra = cobra
        self.pto = pto
        self.ach = ach
    async def list_terminated_employees(self, cid, ld): return self.termed
    async def has_final_voucher(self, cid, eid, td): return self.final_check.get(eid, False)
    async def get_scheduled_deductions(self, cid, eid): return self.deds.get(eid, [])
    async def active_benefits(self, cid, eid, aod): return self.benefits.get(eid, [])
    async def has_cobra_record(self, cid, eid): return self.cobra.get(eid, False)
    async def get_pto_balance(self, cid, eid): return self.pto.get(eid, Decimal("0"))
    async def has_active_ach(self, cid, eid): return self.ach.get(eid, False)


@pytest.mark.asyncio
async def test_term_no_final_check_critical() -> None:
    today = date(2026, 4, 19)
    r = TermFake(
        termed=[{"employeeId": "E1", "statusDate": (today - timedelta(days=30)).isoformat()}],
        final_check={"E1": False}, deds={}, benefits={}, cobra={}, pto={}, ach={},
    )
    rep = await run_terminated_cleanup(r, client_id="T", as_of=today)
    assert any(f.code == "NO_FINAL_CHECK" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_term_active_deductions_critical() -> None:
    today = date(2026, 4, 19)
    r = TermFake(
        termed=[{"employeeId": "E2", "statusDate": (today - timedelta(days=20)).isoformat()}],
        final_check={"E2": True},
        deds={"E2": [{"deductionCode": "MED", "active": True}]},
        benefits={}, cobra={}, pto={}, ach={},
    )
    rep = await run_terminated_cleanup(r, client_id="T", as_of=today)
    assert any(f.code == "DEDUCTIONS_STILL_ACTIVE" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_term_benefits_without_cobra() -> None:
    today = date(2026, 4, 19)
    r = TermFake(
        termed=[{"employeeId": "E3", "statusDate": (today - timedelta(days=20)).isoformat()}],
        final_check={"E3": True}, deds={},
        benefits={"E3": ["MED-HMO"]},
        cobra={"E3": False}, pto={}, ach={},
    )
    rep = await run_terminated_cleanup(r, client_id="T", as_of=today)
    codes = {f.code for f in rep.audits[0].findings}
    assert "BENEFITS_STILL_ACTIVE" in codes
    assert "NO_COBRA_RECORD" in codes


# ---- #7 Manual check audit ----


class MCFake:
    def __init__(self, checks): self.checks = checks
    async def list_manual_checks(self, cid, s, e): return self.checks


@pytest.mark.asyncio
async def test_manual_check_excessive_amount() -> None:
    r = MCFake([{"checkId": "M1", "employeeId": "E1", "checkDate": "2026-01-15", "amount": "15000", "reasonCode": "BONUS", "approver": "CFO"}])
    rep = await run_manual_check_audit(r, client_id="T", window_start=date(2026,1,1), window_end=date(2026,3,31), excessive_threshold="10000")
    assert any(f.code == "EXCESSIVE_AMOUNT" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_manual_check_no_approver() -> None:
    r = MCFake([{"checkId": "M2", "employeeId": "E1", "checkDate": "2026-01-15", "amount": "500", "reasonCode": "CORRECTION", "approver": ""}])
    rep = await run_manual_check_audit(r, client_id="T", window_start=date(2026,1,1), window_end=date(2026,3,31))
    assert any(f.code == "OFF_CYCLE_NO_APPROVAL" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_manual_check_duplicate_window() -> None:
    r = MCFake([
        {"checkId": "M3", "employeeId": "E1", "checkDate": "2026-01-05", "amount": "500", "reasonCode": "A", "approver": "X"},
        {"checkId": "M4", "employeeId": "E1", "checkDate": "2026-01-10", "amount": "500", "reasonCode": "B", "approver": "X"},
    ])
    rep = await run_manual_check_audit(r, client_id="T", window_start=date(2026,1,1), window_end=date(2026,3,31))
    codes = [f.code for a in rep.audits for f in a.findings]
    assert codes.count("DUPLICATE_WITHIN_WINDOW") >= 1


# ---- #18 Dependent age-out ----


class DepFake:
    def __init__(self, deps): self.deps = deps
    async def list_covered_dependents(self, cid): return self.deps


@pytest.mark.asyncio
async def test_dep_aged_out_critical() -> None:
    today = date(2026, 4, 19)
    r = DepFake([{"dependentId": "D1", "employeeId": "E1", "name": "Kid", "dob": "1998-01-01"}])
    rep = await run_dependent_age_out(r, client_id="T", as_of=today)
    assert any(f.code == "AGED_OUT" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_dep_aging_out_urgent() -> None:
    today = date(2026, 4, 19)
    bday_soon = today + timedelta(days=20)
    dob = date(bday_soon.year - 26, bday_soon.month, bday_soon.day)
    r = DepFake([{"dependentId": "D2", "employeeId": "E2", "dob": dob.isoformat()}])
    rep = await run_dependent_age_out(r, client_id="T", as_of=today)
    assert any(f.code == "AGING_OUT_30D" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_dep_no_dob_warning() -> None:
    r = DepFake([{"dependentId": "D3", "employeeId": "E3"}])
    rep = await run_dependent_age_out(r, client_id="T")
    assert any(f.code == "NO_DOB_ON_FILE" for f in rep.audits[0].findings)


# ---- #22 401(k) True-up ----


class TrueUpFake:
    def __init__(self, formula, contribs, gross):
        self.formula = formula
        self.contribs = contribs
        self.gross = gross
    async def get_match_formula(self, cid, pid): return self.formula
    async def get_employee_401k_contributions(self, cid, yr): return self.contribs
    async def get_employee_ytd_gross(self, cid, eid, yr): return self.gross.get(eid, Decimal("0"))


@pytest.mark.asyncio
async def test_true_up_owed_critical() -> None:
    r = TrueUpFake(
        formula={"matchPercent": 100, "matchUpToPercent": 3},
        contribs=[{"employeeId": "E1", "employeeContribution": "6000", "employerMatch": "3000", "ytdGross": "200000"}],
        gross={"E1": Decimal("200000")},
    )
    rep = await run_retirement_true_up(r, client_id="T", plan_id="401K", year=2025)
    assert any(f.code == "TRUE_UP_OWED" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_true_up_no_findings_when_matched() -> None:
    r = TrueUpFake(
        formula={"matchPercent": 100, "matchUpToPercent": 3},
        contribs=[{"employeeId": "E2", "employeeContribution": "3000", "employerMatch": "3000", "ytdGross": "100000"}],
        gross={"E2": Decimal("100000")},
    )
    rep = await run_retirement_true_up(r, client_id="T", plan_id="401K", year=2025)
    assert rep.audits[0].findings == []


# ---- #25 941 Recon ----


class F941Fake:
    def __init__(self, voucher, form941):
        self.voucher = voucher
        self.form941 = form941
    async def sum_vouchers_for_quarter(self, cid, yr, q): return self.voucher
    async def get_form941(self, cid, yr, q): return self.form941


@pytest.mark.asyncio
async def test_941_wages_mismatch_critical() -> None:
    r = F941Fake(
        voucher={"totalWages": "100000", "federalIncomeTax": "15000", "socialSecurityWages": "100000", "medicareWages": "100000"},
        form941={"line2_totalWages": "95000", "line3_fit": "15000", "line5a_socialSecurityTax": "12400", "line5c_medicareTax": "2900"},
    )
    rep = await run_form_941_reconciliation(r, client_id="T", year=2025, quarter=1)
    codes = {f.code for f in rep.recon.findings}
    assert "WAGES_MISMATCH" in codes


@pytest.mark.asyncio
async def test_941_clean_passes() -> None:
    r = F941Fake(
        voucher={"totalWages": "100000", "federalIncomeTax": "15000", "socialSecurityWages": "100000", "medicareWages": "100000"},
        form941={"line2_totalWages": "100000", "line3_fit": "15000", "line5a_socialSecurityTax": "12400", "line5c_medicareTax": "2900"},
    )
    rep = await run_form_941_reconciliation(r, client_id="T", year=2025, quarter=1, tolerance=Decimal("0.50"))
    assert rep.recon.findings == []
