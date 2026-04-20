"""Payroll-to-GL reconciliation — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.payroll_gl_recon import run_payroll_gl_recon  # noqa: E402


class FakePrismHR:
    def __init__(self, lines): self.lines = lines
    async def list_journal_lines(self, client_id, *, period_start, period_end):
        return self.lines


class FakeIntacct:
    def __init__(self, lines): self.lines = lines
    async def list_payroll_gl_lines(self, client_id, *, period_start, period_end):
        return self.lines


def _row(**over):
    base = {
        "glAccount": "6000",
        "amount": "1000",
        "debitCredit": "D",
        "clientDim": "CLT1",
        "departmentDim": "",
        "locationDim": "",
        "sourceVoucherId": "V1",
    }
    base.update(over)
    return base


_P = {"period_start": date(2026, 4, 1), "period_end": date(2026, 4, 15)}


@pytest.mark.asyncio
async def test_clean_match_no_findings() -> None:
    p = FakePrismHR([
        _row(glAccount="6000", amount="1000", debitCredit="D"),
        _row(glAccount="2100", amount="1000", debitCredit="C"),
    ])
    i = FakeIntacct([
        _row(glAccount="6000", amount="1000", debitCredit="D", docRef="JE-1"),
        _row(glAccount="2100", amount="1000", debitCredit="C", docRef="JE-1"),
    ])
    r = await run_payroll_gl_recon(prismhr=p, intacct=i, client_id="T", **_P)
    assert r.flagged == 0
    assert r.batch_delta == Decimal("0.00")


@pytest.mark.asyncio
async def test_line_missing_in_intacct_critical() -> None:
    p = FakePrismHR([
        _row(glAccount="6000", amount="1000", debitCredit="D", sourceVoucherId="V42"),
        _row(glAccount="2100", amount="1000", debitCredit="C"),
    ])
    i = FakeIntacct([
        _row(glAccount="2100", amount="1000", debitCredit="C", docRef="JE-1"),
    ])
    r = await run_payroll_gl_recon(prismhr=p, intacct=i, client_id="T", **_P)
    codes = {f.code for k in r.keys for f in k.findings}
    assert "LINE_MISSING_IN_INTACCT" in codes


@pytest.mark.asyncio
async def test_line_extra_in_intacct_critical() -> None:
    p = FakePrismHR([
        _row(glAccount="6000", amount="1000", debitCredit="D"),
        _row(glAccount="2100", amount="1000", debitCredit="C"),
    ])
    i = FakeIntacct([
        _row(glAccount="6000", amount="1000", debitCredit="D", docRef="JE-1"),
        _row(glAccount="2100", amount="1000", debitCredit="C", docRef="JE-1"),
        _row(glAccount="7500", amount="250", debitCredit="D", docRef="JE-MANUAL-99"),
        _row(glAccount="2100", amount="250", debitCredit="C", docRef="JE-MANUAL-99"),
    ])
    r = await run_payroll_gl_recon(prismhr=p, intacct=i, client_id="T", **_P)
    codes = {f.code for k in r.keys for f in k.findings}
    assert "LINE_EXTRA_IN_INTACCT" in codes


@pytest.mark.asyncio
async def test_amount_drift_critical() -> None:
    p = FakePrismHR([
        _row(glAccount="6000", amount="1000", debitCredit="D"),
        _row(glAccount="2100", amount="1000", debitCredit="C"),
    ])
    i = FakeIntacct([
        _row(glAccount="6000", amount="950", debitCredit="D", docRef="JE-1"),
        _row(glAccount="2100", amount="950", debitCredit="C", docRef="JE-1"),
    ])
    r = await run_payroll_gl_recon(prismhr=p, intacct=i, client_id="T", **_P)
    codes = {f.code for k in r.keys for f in k.findings}
    assert "AMOUNT_DRIFT" in codes


@pytest.mark.asyncio
async def test_tolerance_suppresses_small_drift() -> None:
    p = FakePrismHR([
        _row(glAccount="6000", amount="1000.00", debitCredit="D"),
        _row(glAccount="2100", amount="1000.00", debitCredit="C"),
    ])
    i = FakeIntacct([
        _row(glAccount="6000", amount="999.50", debitCredit="D", docRef="JE-1"),
        _row(glAccount="2100", amount="999.50", debitCredit="C", docRef="JE-1"),
    ])
    r = await run_payroll_gl_recon(
        prismhr=p, intacct=i, client_id="T", tolerance="1.00", **_P
    )
    codes = {f.code for k in r.keys for f in k.findings}
    assert "AMOUNT_DRIFT" not in codes


@pytest.mark.asyncio
async def test_per_account_tolerance_override() -> None:
    p = FakePrismHR([
        _row(glAccount="6000", amount="100.00", debitCredit="D"),
        _row(glAccount="2100", amount="100.00", debitCredit="C"),
    ])
    i = FakeIntacct([
        _row(glAccount="6000", amount="97.00", debitCredit="D", docRef="JE-1"),
        _row(glAccount="2100", amount="97.00", debitCredit="C", docRef="JE-1"),
    ])
    # Default tol $1 would flag; per-acct $5 for account 6000 suppresses.
    r = await run_payroll_gl_recon(
        prismhr=p, intacct=i, client_id="T",
        tolerance="1.00",
        per_account_tolerance={"6000": Decimal("5.00")},
        **_P,
    )
    codes_6000 = {
        f.code for k in r.keys if k.gl_account == "6000" for f in k.findings
    }
    assert "AMOUNT_DRIFT" not in codes_6000


@pytest.mark.asyncio
async def test_batch_totals_drift_flag() -> None:
    p = FakePrismHR([
        _row(glAccount="6000", amount="1000", debitCredit="D"),
        _row(glAccount="2100", amount="1000", debitCredit="C"),
    ])
    i = FakeIntacct([
        _row(glAccount="6000", amount="500", debitCredit="D", docRef="JE-1"),
        _row(glAccount="2100", amount="500", debitCredit="C", docRef="JE-1"),
    ])
    r = await run_payroll_gl_recon(prismhr=p, intacct=i, client_id="T", **_P)
    codes = {f.code for f in r.batch_findings}
    assert "BATCH_TOTALS_DRIFT" in codes


@pytest.mark.asyncio
async def test_dimension_level_matching() -> None:
    """Same account + client, different departments = different keys."""
    p = FakePrismHR([
        _row(glAccount="6000", amount="600", debitCredit="D", departmentDim="SALES"),
        _row(glAccount="6000", amount="400", debitCredit="D", departmentDim="ENG"),
        _row(glAccount="2100", amount="1000", debitCredit="C"),
    ])
    i = FakeIntacct([
        # Intacct has same total but wrong split
        _row(glAccount="6000", amount="500", debitCredit="D", departmentDim="SALES", docRef="JE-1"),
        _row(glAccount="6000", amount="500", debitCredit="D", departmentDim="ENG", docRef="JE-1"),
        _row(glAccount="2100", amount="1000", debitCredit="C", docRef="JE-1"),
    ])
    r = await run_payroll_gl_recon(prismhr=p, intacct=i, client_id="T", **_P)
    # Two separate keys should flag drift.
    drift_count = sum(
        1 for k in r.keys if any(f.code == "AMOUNT_DRIFT" for f in k.findings)
    )
    assert drift_count == 2


@pytest.mark.asyncio
async def test_source_voucher_ids_surface_in_finding() -> None:
    p = FakePrismHR([
        _row(glAccount="6000", amount="1000", debitCredit="D", sourceVoucherId="V123"),
        _row(glAccount="2100", amount="1000", debitCredit="C"),
    ])
    i = FakeIntacct([
        _row(glAccount="2100", amount="1000", debitCredit="C", docRef="JE-1"),
    ])
    r = await run_payroll_gl_recon(prismhr=p, intacct=i, client_id="T", **_P)
    missing = next(k for k in r.keys if k.gl_account == "6000")
    assert "V123" in missing.source_voucher_ids
    assert any("V123" in f.message for f in missing.findings)
