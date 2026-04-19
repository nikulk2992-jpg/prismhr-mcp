"""Batch 3 — workflows #2, #17, #21, #28, #33, #45.

Compact tests: each workflow gets a happy path + at least one
critical finding path with an in-memory FakeReader.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.doc_expiration_sweep import run_doc_expiration_sweep  # noqa: E402
from simploy.workflows.fsa_hsa_limit_tracker import run_fsa_hsa_limit_tracker  # noqa: E402
from simploy.workflows.invoice_aging import run_invoice_aging  # noqa: E402
from simploy.workflows.pto_reconciliation import run_pto_reconciliation  # noqa: E402
from simploy.workflows.retirement_loan_status import run_retirement_loan_status  # noqa: E402
from simploy.workflows.workers_comp_exposure import run_workers_comp_exposure  # noqa: E402


# ---- #2 Doc expiration ----


class DocFake:
    def __init__(self, rows): self.rows = rows
    async def get_doc_expirations(self, cid, types, days): return self.rows


@pytest.mark.asyncio
async def test_expired_doc_critical() -> None:
    today = date(2026, 4, 19)
    r = DocFake([{"employeeId": "E1", "docType": "I9", "expirationDate": (today - timedelta(days=10)).isoformat()}])
    rep = await run_doc_expiration_sweep(r, client_id="T", as_of=today)
    assert any(f.code == "EXPIRED" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_expiring_urgent_critical() -> None:
    today = date(2026, 4, 19)
    r = DocFake([{"employeeId": "E2", "docType": "I9", "expirationDate": (today + timedelta(days=15)).isoformat()}])
    rep = await run_doc_expiration_sweep(r, client_id="T", as_of=today)
    assert any(f.code == "EXPIRING_URGENT" for f in rep.audits[0].findings)


# ---- #17 FSA/HSA ----


class FSAFake:
    def __init__(self, plans, enrollees, ded): self.plans=plans; self.enrollees=enrollees; self.ded=ded
    async def get_section125_plans(self, cid, pt):
        return self.plans.get(pt, [])
    async def get_flex_enrollees(self, cid, pid):
        return self.enrollees.get(pid, [])
    async def get_ytd_deduction(self, cid, eid, code, year):
        return self.ded.get(eid, Decimal("0"))


@pytest.mark.asyncio
async def test_fsa_over_limit_critical() -> None:
    r = FSAFake(
        plans={"F": [{"planId": "FSA-HC", "deductionCode": "FSAHC"}], "H": []},
        enrollees={"FSA-HC": [{"employeeId": "E1", "coverageTier": "EMP"}]},
        ded={"E1": Decimal("3500")},
    )
    rep = await run_fsa_hsa_limit_tracker(r, client_id="T", year=2026, as_of=date(2026, 6, 30))
    assert any(f.code == "OVER_LIMIT" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_fsa_within_limit_passes() -> None:
    r = FSAFake(
        plans={"F": [{"planId": "FSA", "deductionCode": "FSA"}], "H": []},
        enrollees={"FSA": [{"employeeId": "E1", "coverageTier": "EMP"}]},
        ded={"E1": Decimal("1000")},
    )
    rep = await run_fsa_hsa_limit_tracker(r, client_id="T", year=2026, as_of=date(2026, 6, 30))
    assert rep.audits[0].findings == []


# ---- #21 Retirement loan status ----


class LoanFake:
    def __init__(self, loans): self.loans = loans
    async def get_retirement_loans(self, cid): return self.loans


@pytest.mark.asyncio
async def test_defaulted_loan_critical() -> None:
    today = date(2026, 4, 19)
    r = LoanFake([{
        "employeeId": "E1", "loanId": "L1", "outstandingBalance": "5000",
        "lastPaymentDate": (today - timedelta(days=120)).isoformat(),
    }])
    rep = await run_retirement_loan_status(r, client_id="T", as_of=today)
    assert any(f.code == "LOAN_DEFAULTED" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_loan_past_term_critical() -> None:
    today = date(2026, 4, 19)
    r = LoanFake([{
        "employeeId": "E2", "loanId": "L2", "outstandingBalance": "500",
        "lastPaymentDate": (today - timedelta(days=10)).isoformat(),
        "scheduledEndDate": (today - timedelta(days=30)).isoformat(),
    }])
    rep = await run_retirement_loan_status(r, client_id="T", as_of=today)
    codes = {f.code for f in rep.audits[0].findings}
    assert "LOAN_PAST_TERM" in codes


# ---- #28 Workers Comp Exposure ----


class WCFake:
    def __init__(self, mods, emps): self.mods=mods; self.emps=emps
    async def get_wc_accrual_modifiers(self, cid): return self.mods
    async def get_wc_billing_modifiers(self, cid, state): return []
    async def list_employees_with_wc(self, cid): return self.emps


@pytest.mark.asyncio
async def test_missing_wc_code_critical() -> None:
    r = WCFake(
        mods=[{"wcCode": "8810", "state": "NE", "ratePer100": "0.25", "experienceModifier": "1.0"}],
        emps=[{"employeeId": "E1", "wcCode": "", "state": "", "ytdWages": "50000"}],
    )
    rep = await run_workers_comp_exposure(r, client_id="T", year=2025)
    assert any(f.code == "MISSING_WC_CODE" for f in rep.findings)


@pytest.mark.asyncio
async def test_wc_premium_calculation() -> None:
    r = WCFake(
        mods=[{"wcCode": "8810", "state": "NE", "ratePer100": "0.25", "experienceModifier": "1.0"}],
        emps=[{"employeeId": "E1", "wcCode": "8810", "wcState": "NE", "ytdWages": "100000"}],
    )
    rep = await run_workers_comp_exposure(r, client_id="T", year=2025)
    # 100000 / 100 * 0.25 * 1.0 = 250
    assert rep.exposures[0].estimated_premium == Decimal("250.00")


# ---- #33 Invoice aging ----


class InvoiceFake:
    def __init__(self, invs): self.invs = invs
    async def get_bulk_outstanding_invoices(self): return self.invs


@pytest.mark.asyncio
async def test_invoice_90_plus_critical() -> None:
    today = date(2026, 4, 19)
    r = InvoiceFake([{
        "clientId": "C1", "invoiceDate": (today - timedelta(days=120)).isoformat(),
        "outstandingAmount": "5000", "invoiceNumber": "INV001",
    }])
    rep = await run_invoice_aging(r, as_of=today)
    assert any(f.code == "INVOICE_90_PLUS" for f in rep.clients[0].findings)


@pytest.mark.asyncio
async def test_client_at_risk_critical() -> None:
    today = date(2026, 4, 19)
    r = InvoiceFake([
        {"clientId": "C2", "invoiceDate": (today - timedelta(days=75)).isoformat(), "outstandingAmount": "15000"},
    ])
    rep = await run_invoice_aging(r, as_of=today, at_risk_threshold="10000")
    codes = {f.code for f in rep.clients[0].findings}
    assert "CLIENT_AT_RISK" in codes


# ---- #45 PTO reconciliation ----


class PTOFake:
    def __init__(self, classes, plans, rows): self.c=classes; self.p=plans; self.r=rows
    async def get_pto_classes(self, cid): return self.c
    async def get_pto_plans(self, cid): return self.p
    async def get_employee_pto_rows(self, cid): return self.r


@pytest.mark.asyncio
async def test_no_pto_class_critical() -> None:
    r = PTOFake(classes=[], plans=[], rows=[{"employeeId": "E1", "ptoClass": "", "balanceHours": "40"}])
    rep = await run_pto_reconciliation(r, client_id="T")
    assert any(f.code == "NO_PTO_CLASS_ASSIGNED" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_negative_balance_critical() -> None:
    r = PTOFake(classes=[], plans=[], rows=[{"employeeId": "E2", "ptoClass": "FT", "balanceHours": "-10"}])
    rep = await run_pto_reconciliation(r, client_id="T")
    assert any(f.code == "NEGATIVE_BALANCE" for f in rep.audits[0].findings)


@pytest.mark.asyncio
async def test_pto_over_cap_warning() -> None:
    r = PTOFake(
        classes=[{"classCode": "FT", "planId": "PL1"}],
        plans=[{"id": "PL1", "maxHours": "120"}],
        rows=[{"employeeId": "E3", "ptoClass": "FT", "balanceHours": "150"}],
    )
    rep = await run_pto_reconciliation(r, client_id="T")
    assert any(f.code == "OVER_CAP" for f in rep.audits[0].findings)
