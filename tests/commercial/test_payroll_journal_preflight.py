"""Payroll journal preflight — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.payroll_journal_preflight import (  # noqa: E402
    PreflightConfig,
    run_payroll_journal_preflight,
)


class FakeReader:
    def __init__(self, lines: list[dict]) -> None:
        self.lines = lines

    async def list_journal_lines(self, client_id, *, batch_id, period_start, period_end):
        return self.lines


_PERIOD = {"period_start": date(2026, 4, 1), "period_end": date(2026, 4, 15)}


def _line(**over):
    base = {
        "lineId": "L1",
        "glAccount": "6000",
        "amount": "1000.00",
        "debitCredit": "D",
        "clientDim": "CLT1",
        "departmentDim": "DEPT1",
        "locationDim": "LOC1",
        "postDate": "2026-04-10",
        "sourceVoucherId": "V1",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_balanced_clean_batch_passes() -> None:
    reader = FakeReader([
        _line(lineId="L1", glAccount="6000", amount="1000", debitCredit="D", sourceVoucherId="V1"),
        _line(lineId="L2", glAccount="2100", amount="1000", debitCredit="C", sourceVoucherId="V1"),
    ])
    r = await run_payroll_journal_preflight(reader, client_id="T", **_PERIOD)
    assert r.balanced
    assert r.passed
    assert r.flagged_lines == 0


@pytest.mark.asyncio
async def test_net_not_zero_is_critical() -> None:
    reader = FakeReader([
        _line(lineId="L1", amount="1000", debitCredit="D"),
        _line(lineId="L2", glAccount="2100", amount="500", debitCredit="C", sourceVoucherId="V1"),
    ])
    r = await run_payroll_journal_preflight(reader, client_id="T", **_PERIOD)
    codes = {f.code for f in r.batch_findings}
    assert "NET_NOT_ZERO" in codes
    assert not r.balanced
    assert r.net == Decimal("500.00")


@pytest.mark.asyncio
async def test_suspense_hit_flags_line() -> None:
    reader = FakeReader([
        _line(lineId="L1", glAccount="9999", amount="1000", debitCredit="D"),
        _line(lineId="L2", glAccount="2100", amount="1000", debitCredit="C", sourceVoucherId="V1"),
    ])
    cfg = PreflightConfig(suspense_accounts=frozenset({"9999"}))
    r = await run_payroll_journal_preflight(
        reader, client_id="T", config=cfg, **_PERIOD
    )
    codes = {f.code for l in r.lines for f in l.findings}
    assert "SUSPENSE_HIT" in codes


@pytest.mark.asyncio
async def test_unmapped_gl_account_is_critical() -> None:
    reader = FakeReader([
        _line(lineId="L1", glAccount="", amount="1000", debitCredit="D"),
        _line(lineId="L2", glAccount="2100", amount="1000", debitCredit="C", sourceVoucherId="V1"),
    ])
    r = await run_payroll_journal_preflight(reader, client_id="T", **_PERIOD)
    codes = {f.code for l in r.lines for f in l.findings}
    assert "UNMAPPED_GL_ACCOUNT" in codes


@pytest.mark.asyncio
async def test_missing_dimension_flag() -> None:
    reader = FakeReader([
        _line(lineId="L1", clientDim="", amount="1000", debitCredit="D"),
        _line(lineId="L2", glAccount="2100", amount="1000", debitCredit="C", sourceVoucherId="V1"),
    ])
    cfg = PreflightConfig(required_dims=("client",))
    r = await run_payroll_journal_preflight(
        reader, client_id="T", config=cfg, **_PERIOD
    )
    codes = {f.code for l in r.lines for f in l.findings}
    assert "MISSING_DIMENSION" in codes


@pytest.mark.asyncio
async def test_unknown_client_dim_critical() -> None:
    reader = FakeReader([
        _line(lineId="L1", clientDim="CLT_MYSTERY", amount="1000", debitCredit="D"),
        _line(lineId="L2", glAccount="2100", amount="1000", debitCredit="C",
              clientDim="CLT_MYSTERY", sourceVoucherId="V1"),
    ])
    cfg = PreflightConfig(known_clients=frozenset({"CLT1", "CLT2"}))
    r = await run_payroll_journal_preflight(
        reader, client_id="T", config=cfg, **_PERIOD
    )
    codes = {f.code for l in r.lines for f in l.findings}
    assert "UNKNOWN_DIMENSION" in codes


@pytest.mark.asyncio
async def test_duplicate_line_key_is_critical() -> None:
    dup = _line(lineId="L1", amount="1000", debitCredit="D", sourceVoucherId="V1")
    dup2 = _line(lineId="L2", amount="1000", debitCredit="D", sourceVoucherId="V1")
    reader = FakeReader([
        dup, dup2,
        _line(lineId="L3", glAccount="2100", amount="2000", debitCredit="C", sourceVoucherId="V1"),
    ])
    r = await run_payroll_journal_preflight(reader, client_id="T", **_PERIOD)
    batch_codes = {f.code for f in r.batch_findings}
    line_codes = {f.code for l in r.lines for f in l.findings}
    assert "DUPLICATE_LINE_KEY" in batch_codes
    assert "DUPLICATE_LINE_KEY" in line_codes


@pytest.mark.asyncio
async def test_out_of_period_warning() -> None:
    reader = FakeReader([
        _line(lineId="L1", postDate="2026-05-01", amount="1000", debitCredit="D"),
        _line(lineId="L2", glAccount="2100", amount="1000", debitCredit="C", sourceVoucherId="V1"),
    ])
    r = await run_payroll_journal_preflight(reader, client_id="T", **_PERIOD)
    codes = {f.code for l in r.lines for f in l.findings}
    assert "OUT_OF_PERIOD" in codes


@pytest.mark.asyncio
async def test_zero_amount_line_warning() -> None:
    reader = FakeReader([
        _line(lineId="L1", amount="0", debitCredit="D"),
        _line(lineId="L2", glAccount="2100", amount="0", debitCredit="C", sourceVoucherId="V1"),
    ])
    r = await run_payroll_journal_preflight(reader, client_id="T", **_PERIOD)
    codes = {f.code for l in r.lines for f in l.findings}
    assert "ZERO_AMOUNT_LINE" in codes


@pytest.mark.asyncio
async def test_negative_line_no_void_flag() -> None:
    reader = FakeReader([
        _line(lineId="L1", amount="-100", debitCredit="D"),
        _line(lineId="L2", glAccount="2100", amount="-100", debitCredit="C", sourceVoucherId="V1"),
    ])
    r = await run_payroll_journal_preflight(reader, client_id="T", **_PERIOD)
    codes = {f.code for l in r.lines for f in l.findings}
    assert "NEGATIVE_WAGE_NO_VOID" in codes


@pytest.mark.asyncio
async def test_negative_line_with_void_is_fine() -> None:
    reader = FakeReader([
        _line(lineId="L1", amount="-100", debitCredit="D",
              voidVoucherId="V99"),
        _line(lineId="L2", glAccount="2100", amount="-100", debitCredit="C",
              sourceVoucherId="V1", voidVoucherId="V99"),
    ])
    r = await run_payroll_journal_preflight(reader, client_id="T", **_PERIOD)
    codes = {f.code for l in r.lines for f in l.findings}
    assert "NEGATIVE_WAGE_NO_VOID" not in codes
