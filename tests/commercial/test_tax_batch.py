"""Tax automation batch — workflows #56, #57, #58, #59."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.form_940_reconciliation import run_form_940_reconciliation  # noqa: E402
from simploy.workflows.state_filings_orchestrator import run_state_filings_orchestrator  # noqa: E402
from simploy.workflows.state_withholding_recon import run_state_withholding_recon  # noqa: E402
from simploy.workflows.tax_remittance_tracking import run_tax_remittance_tracking  # noqa: E402


# ---- #56 state withholding recon ----


class StateFake:
    def __init__(self, wages, filings): self.wages = wages; self.filings = filings
    async def list_wages_by_state(self, cid, yr, q): return self.wages
    async def get_state_filings(self, cid, yr, q): return self.filings


@pytest.mark.asyncio
async def test_state_withholding_mismatch_critical() -> None:
    r = StateFake(
        wages=[{"state": "CA", "totalWages": "100000", "stateWithholding": "8000", "sutaWages": "100000", "employeeCount": 10}],
        filings=[{"state": "CA", "totalWages": "100000", "withholding": "7500", "sutaWages": "100000", "employeeCount": 10}],
    )
    rep = await run_state_withholding_recon(r, client_id="T", year=2025, quarter=1)
    codes = {f.code for f in rep.states[0].findings}
    assert "WITHHOLDING_MISMATCH" in codes


@pytest.mark.asyncio
async def test_state_no_filing_critical() -> None:
    r = StateFake(
        wages=[{"state": "TX", "totalWages": "50000", "stateWithholding": "0", "sutaWages": "50000", "employeeCount": 5}],
        filings=[],
    )
    rep = await run_state_withholding_recon(r, client_id="T", year=2025, quarter=1)
    codes = {f.code for f in rep.states[0].findings}
    assert "NO_FILING" in codes


# ---- #57 FUTA 940 recon ----


class F940Fake:
    def __init__(self, rows, form, cr_states, employer_states):
        self.rows = rows
        self.form = form
        self.cr_states = cr_states
        self.employer_states = employer_states
    async def list_employee_annual_wages(self, cid, yr): return self.rows
    async def get_form940(self, cid, yr): return self.form
    async def list_credit_reduction_states(self, yr): return self.cr_states
    async def list_employer_states(self, cid, yr): return self.employer_states


@pytest.mark.asyncio
async def test_940_futa_tax_mismatch_critical() -> None:
    # Two employees, each earning $50K. Capped FUTA = $14K. Tax = $84.
    r = F940Fake(
        rows=[{"employeeId": "E1", "totalWages": "50000"}, {"employeeId": "E2", "totalWages": "50000"}],
        form={"totalTaxableFutaWages": "14000", "futaTaxBeforeAdjustments": "50"},
        cr_states=[],
        employer_states=["NE"],
    )
    rep = await run_form_940_reconciliation(r, client_id="T", year=2025)
    codes = {f.code for f in rep.recon.findings}
    assert "FUTA_TAX_MISMATCH" in codes


@pytest.mark.asyncio
async def test_940_credit_reduction_missing_critical() -> None:
    r = F940Fake(
        rows=[{"employeeId": "E1", "totalWages": "10000"}],
        form={"totalTaxableFutaWages": "7000", "futaTaxBeforeAdjustments": "42", "part3CreditReductionStates": []},
        cr_states=["CA"],
        employer_states=["CA"],
    )
    rep = await run_form_940_reconciliation(r, client_id="T", year=2025)
    codes = {f.code for f in rep.recon.findings}
    assert "CREDIT_REDUCTION_STATE_MISSING" in codes


# ---- #58 Tax remittance tracking ----


class RemitFake:
    def __init__(self, liab, dep): self.liab = liab; self.dep = dep
    async def list_tax_liabilities(self, cid, juris, code, yr): return self.liab
    async def list_tax_deposits(self, cid, juris, code, yr): return self.dep


@pytest.mark.asyncio
async def test_deposit_missing_critical() -> None:
    r = RemitFake(
        liab=[{"id": "L1", "liabilityDate": "2025-03-15", "dueDate": "2025-04-15", "amount": "5000"}],
        dep=[],
    )
    rep = await run_tax_remittance_tracking(r, client_id="T", jurisdiction="federal", tax_code="FIT", year=2025)
    codes = {f.code for f in rep.deposits[0].findings}
    assert "DEPOSIT_MISSING" in codes


@pytest.mark.asyncio
async def test_deposit_late_critical() -> None:
    r = RemitFake(
        liab=[{"id": "L2", "liabilityDate": "2025-03-15", "dueDate": "2025-04-15", "amount": "5000"}],
        dep=[{"liabilityId": "L2", "depositDate": "2025-04-20", "amount": "5000"}],
    )
    rep = await run_tax_remittance_tracking(r, client_id="T", jurisdiction="federal", tax_code="FIT", year=2025)
    codes = {f.code for f in rep.deposits[0].findings}
    assert "DEPOSIT_LATE" in codes


@pytest.mark.asyncio
async def test_deposit_under_critical() -> None:
    r = RemitFake(
        liab=[{"id": "L3", "liabilityDate": "2025-03-15", "dueDate": "2025-04-15", "amount": "5000"}],
        dep=[{"liabilityId": "L3", "depositDate": "2025-04-10", "amount": "4500"}],
    )
    rep = await run_tax_remittance_tracking(r, client_id="T", jurisdiction="federal", tax_code="FIT", year=2025)
    codes = {f.code for f in rep.deposits[0].findings}
    assert "DEPOSIT_UNDER" in codes


# ---- #59 State filings orchestrator ----


class FilingsFake:
    def __init__(self, employer_states, filings, recon_issues):
        self.employer_states = employer_states
        self.filings = filings
        self.recon_issues = recon_issues
    async def list_employer_states(self, cid, yr, q): return self.employer_states
    async def get_filing_status(self, cid, state, yr, q): return self.filings.get(state, {})
    async def get_state_recon_findings(self, cid, state, yr, q): return self.recon_issues.get(state, 0)


@pytest.mark.asyncio
async def test_state_filing_overdue_critical() -> None:
    today = date(2026, 6, 15)  # past Q1 2026 due of Apr 30
    r = FilingsFake(
        employer_states=[{"state": "CA", "hasWages": True}],
        filings={},
        recon_issues={},
    )
    rep = await run_state_filings_orchestrator(r, client_id="T", year=2026, quarter=1, as_of=today)
    codes = {f.code for f in rep.states[0].findings}
    assert "FILING_OVERDUE" in codes


@pytest.mark.asyncio
async def test_state_filing_already_filed_info() -> None:
    today = date(2026, 4, 10)
    r = FilingsFake(
        employer_states=[{"state": "CA", "hasWages": True}],
        filings={"CA": {"filed": True, "submissionConfirmation": "CA-Q1-2026-123"}},
        recon_issues={},
    )
    rep = await run_state_filings_orchestrator(r, client_id="T", year=2026, quarter=1, as_of=today)
    codes = {f.code for f in rep.states[0].findings}
    assert "ALREADY_FILED" in codes


@pytest.mark.asyncio
async def test_state_recon_blocks_filing() -> None:
    today = date(2026, 4, 10)
    r = FilingsFake(
        employer_states=[{"state": "NY", "hasWages": True}],
        filings={},
        recon_issues={"NY": 3},
    )
    rep = await run_state_filings_orchestrator(r, client_id="T", year=2026, quarter=1, as_of=today)
    codes = {f.code for f in rep.states[0].findings}
    assert "RECONCILIATION_BLOCKED" in codes
