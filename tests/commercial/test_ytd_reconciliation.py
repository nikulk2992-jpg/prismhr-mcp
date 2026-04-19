"""YTD Payroll Reconciliation — unit tests with in-memory reader fake."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.ytd_reconciliation import (  # noqa: E402
    run_ytd_reconciliation,
)


class FakeReader:
    def __init__(self, ytd, vouchers) -> None:
        self.ytd = ytd
        self.vouchers = vouchers

    async def get_bulk_ytd(self, client_id, year):
        return self.ytd

    async def get_vouchers(self, client_id, year):
        return self.vouchers


@pytest.mark.asyncio
async def test_matching_ytd_and_vouchers_pass() -> None:
    reader = FakeReader(
        ytd=[{"employeeId": "E1", "YTD": {"grossWages": "50000.00", "netPay": "38000.00", "taxWithholding": "9000.00"}}],
        vouchers=[
            {"employeeId": "E1", "totalEarnings": "25000.00", "netPay": "19000.00", "employeeTax": "4500.00"},
            {"employeeId": "E1", "totalEarnings": "25000.00", "netPay": "19000.00", "employeeTax": "4500.00"},
        ],
    )
    report = await run_ytd_reconciliation(
        reader, client_id="TEST", year=2026, as_of=date(2026, 6, 30)
    )
    assert report.total == 1
    assert report.passed == 1


@pytest.mark.asyncio
async def test_gross_mismatch_is_critical() -> None:
    reader = FakeReader(
        ytd=[{"employeeId": "E2", "YTD": {"grossWages": "50000.00", "netPay": "38000.00", "taxWithholding": "9000.00"}}],
        vouchers=[
            {"employeeId": "E2", "totalEarnings": "24000.00", "netPay": "19000.00", "employeeTax": "4500.00"},
            {"employeeId": "E2", "totalEarnings": "25000.00", "netPay": "19000.00", "employeeTax": "4500.00"},
        ],
    )
    report = await run_ytd_reconciliation(reader, client_id="TEST", year=2026)
    codes = {f.code for f in report.employees[0].findings}
    assert "YTD_MISMATCH_GROSS" in codes


@pytest.mark.asyncio
async def test_ytd_missing_when_vouchers_exist() -> None:
    reader = FakeReader(
        ytd=[],
        vouchers=[
            {"employeeId": "E3", "totalEarnings": "100", "netPay": "80", "employeeTax": "15"},
        ],
    )
    report = await run_ytd_reconciliation(reader, client_id="TEST", year=2026)
    codes = {f.code for f in report.employees[0].findings}
    assert "YTD_MISSING" in codes


@pytest.mark.asyncio
async def test_vouchers_missing_when_ytd_exists() -> None:
    reader = FakeReader(
        ytd=[{"employeeId": "E4", "YTD": {"grossWages": "10000", "netPay": "8000", "taxWithholding": "1500"}}],
        vouchers=[],
    )
    report = await run_ytd_reconciliation(reader, client_id="TEST", year=2026)
    codes = {f.code for f in report.employees[0].findings}
    assert "VOUCHERS_MISSING" in codes


@pytest.mark.asyncio
async def test_tolerance_suppresses_penny_drift() -> None:
    reader = FakeReader(
        ytd=[{"employeeId": "E5", "YTD": {"grossWages": "50000.01", "netPay": "38000", "taxWithholding": "9000"}}],
        vouchers=[
            {"employeeId": "E5", "totalEarnings": "50000.00", "netPay": "38000", "employeeTax": "9000"},
        ],
    )
    report = await run_ytd_reconciliation(
        reader, client_id="TEST", year=2026, tolerance="0.02"
    )
    assert report.employees[0].findings == []


@pytest.mark.asyncio
async def test_three_mismatches_all_flagged() -> None:
    reader = FakeReader(
        ytd=[{"employeeId": "E6", "YTD": {"grossWages": "1000", "netPay": "800", "taxWithholding": "150"}}],
        vouchers=[
            {"employeeId": "E6", "totalEarnings": "900", "netPay": "720", "employeeTax": "135"},
        ],
    )
    report = await run_ytd_reconciliation(reader, client_id="TEST", year=2026)
    codes = {f.code for f in report.employees[0].findings}
    assert {"YTD_MISMATCH_GROSS", "YTD_MISMATCH_NET", "YTD_MISMATCH_TAX"} <= codes


@pytest.mark.asyncio
async def test_empty_inputs_produce_empty_report() -> None:
    reader = FakeReader(ytd=[], vouchers=[])
    report = await run_ytd_reconciliation(reader, client_id="TEST", year=2026)
    assert report.total == 0
