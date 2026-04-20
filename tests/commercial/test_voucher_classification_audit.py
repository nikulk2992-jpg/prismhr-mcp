"""Voucher classification audit — unit tests.

Exercises the finding logic with an in-memory reader fake. No live
PrismHR calls; shape mirrors the verified
payroll.v1.getPayrollVoucherForBatch probe.
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.voucher_classification_audit import (  # noqa: E402
    run_voucher_classification_audit,
)


class FakeReader:
    def __init__(
        self,
        *,
        vouchers: list[dict],
        employees: dict[str, dict],
        pay_codes: dict[str, dict],
        unions: dict[str, list[str]] | None = None,
    ) -> None:
        self.vouchers = vouchers
        self.employees = employees
        self.pay_codes = pay_codes
        self.unions = unions or {}

    async def list_vouchers_for_period(self, client_id, ps, pe):
        return self.vouchers

    async def get_employee_tax_profile(self, client_id, eid):
        return self.employees.get(eid, {})

    async def get_pay_code_definition(self, client_id, code):
        return self.pay_codes.get(code, {})

    async def list_union_members(self, client_id, uid):
        return self.unions.get(uid, [])


def _fica_taxes(ss: str = "100", med: str = "25") -> list[dict]:
    return [
        {"empTaxDeductCode": "00-11", "empTaxAmount": med},
        {"empTaxDeductCode": "00-12", "empTaxAmount": ss},
        {"empTaxDeductCode": "00-10", "empTaxAmount": "150"},
    ]


async def _run(reader: FakeReader):
    return await run_voucher_classification_audit(
        reader,
        client_id="T",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 15),
        as_of=date(2026, 4, 20),
    )


# ---------- worker classification ----------


@pytest.mark.asyncio
async def test_contractor_on_w2_pay_code_is_critical() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V1", "employeeId": "E1", "totalEarnings": "1000",
            "type": "R", "payDate": "2026-04-15",
            "employeeTax": [],
            "earning": [{"payCode": "REG", "payAmount": "1000"}],
        }],
        employees={"E1": {"employeeType": "1099", "ficaExempt": True}},
        pay_codes={"REG": {"payCode": "REG", "isContractor": False, "ficaSubject": True}},
    )
    r = await _run(reader)
    codes = {f.code for line in r.vouchers[0].lines for f in line.findings}
    assert "CONTRACTOR_W2_PAY_CODE" in codes


@pytest.mark.asyncio
async def test_w2_employee_on_contractor_code_is_critical() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V2", "employeeId": "E2", "totalEarnings": "500",
            "type": "R",
            "employeeTax": _fica_taxes(),
            "earning": [{"payCode": "1099NE", "payAmount": "500"}],
        }],
        employees={"E2": {"employeeType": "W2"}},
        pay_codes={"1099NE": {"isContractor": True, "ficaSubject": False}},
    )
    r = await _run(reader)
    codes = {f.code for line in r.vouchers[0].lines for f in line.findings}
    assert "W2_CONTRACTOR_PAY_CODE" in codes


# ---------- FICA ----------


@pytest.mark.asyncio
async def test_fica_exempt_but_withheld_is_critical() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V3", "employeeId": "E3", "totalEarnings": "2000",
            "type": "R",
            "employeeTax": _fica_taxes(),
            "earning": [{"payCode": "REG", "payAmount": "2000"}],
        }],
        employees={"E3": {"employeeType": "W2", "ficaExempt": True}},
        pay_codes={"REG": {"ficaSubject": False}},
    )
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "FICA_EXEMPT_BUT_WITHHELD" in codes


@pytest.mark.asyncio
async def test_fica_nonexempt_not_withheld_is_critical() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V4", "employeeId": "E4", "totalEarnings": "2000",
            "type": "R",
            "employeeTax": [{"empTaxDeductCode": "00-10", "empTaxAmount": "150"}],
            "earning": [{"payCode": "REG", "payAmount": "2000"}],
        }],
        employees={"E4": {"employeeType": "W2", "ficaExempt": False}},
        pay_codes={"REG": {"ficaSubject": True}},
    )
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "FICA_NONEXEMPT_NOT_WITHHELD" in codes


@pytest.mark.asyncio
async def test_additional_medicare_missed_is_critical() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V5", "employeeId": "E5", "totalEarnings": "10000",
            "type": "R",
            "employeeTax": _fica_taxes(),
            "earning": [{"payCode": "REG", "payAmount": "10000"}],
        }],
        employees={"E5": {
            "employeeType": "W2", "ficaExempt": False, "medicareExempt": False,
            "ytdMedicareWages": "250000", "ytdAdditionalMedicareWithheld": "0",
        }},
        pay_codes={"REG": {"ficaSubject": True}},
    )
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "MEDICARE_ADDL_MISSED" in codes


# ---------- union ----------


@pytest.mark.asyncio
async def test_union_code_for_non_union_employee_is_critical() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V6", "employeeId": "E6", "totalEarnings": "1500",
            "type": "R",
            "employeeTax": _fica_taxes(),
            "earning": [{"payCode": "UN-REG", "payAmount": "1500"}],
        }],
        employees={"E6": {"employeeType": "W2", "ficaExempt": False}},
        pay_codes={"UN-REG": {"isUnion": True, "unionId": "LOCAL-123", "ficaSubject": True}},
        unions={"LOCAL-123": ["E99"]},
    )
    r = await _run(reader)
    codes = {f.code for line in r.vouchers[0].lines for f in line.findings}
    assert "UNION_CODE_NON_UNION_EMP" in codes


@pytest.mark.asyncio
async def test_union_dues_missing_is_warning() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V7", "employeeId": "E7", "totalEarnings": "1500",
            "type": "R",
            "employeeTax": _fica_taxes(),
            "earning": [{"payCode": "UN-REG", "payAmount": "1500"}],
            "deduction": [],
        }],
        employees={"E7": {"employeeType": "W2", "ficaExempt": False, "unionId": "LOCAL-42"}},
        pay_codes={"UN-REG": {"isUnion": True, "unionId": "LOCAL-42", "ficaSubject": True}},
        unions={"LOCAL-42": ["E7"]},
    )
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "UNION_DUES_MISSING" in codes


# ---------- state / sanity ----------


@pytest.mark.asyncio
async def test_state_suta_mismatch_is_warning() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V8", "employeeId": "E8", "totalEarnings": "1000",
            "type": "R",
            "wcState": "CA",
            "employeeTax": _fica_taxes(),
            "earning": [{"payCode": "REG", "payAmount": "1000"}],
        }],
        employees={"E8": {"employeeType": "W2", "ficaExempt": False, "workState": "TX"}},
        pay_codes={"REG": {"ficaSubject": True}},
    )
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "STATE_SUTA_MISMATCH" in codes


@pytest.mark.asyncio
async def test_negative_tax_positive_wages_is_critical() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V9", "employeeId": "E9", "totalEarnings": "500",
            "type": "R",
            "employeeTax": [
                {"empTaxDeductCode": "00-10", "empTaxAmount": "-50"},
                {"empTaxDeductCode": "00-11", "empTaxAmount": "7"},
                {"empTaxDeductCode": "00-12", "empTaxAmount": "31"},
            ],
            "earning": [{"payCode": "REG", "payAmount": "500"}],
        }],
        employees={"E9": {"employeeType": "W2", "ficaExempt": False}},
        pay_codes={"REG": {"ficaSubject": True}},
    )
    r = await _run(reader)
    codes = {f.code for line in r.vouchers[0].lines for f in line.findings}
    assert "NEGATIVE_TAX_POSITIVE_WAGES" in codes


@pytest.mark.asyncio
async def test_correction_voucher_does_not_flag_negative_tax() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V10", "employeeId": "E10", "totalEarnings": "500",
            "type": "C",  # correction
            "employeeTax": [
                {"empTaxDeductCode": "00-10", "empTaxAmount": "-50"},
                {"empTaxDeductCode": "00-11", "empTaxAmount": "7"},
                {"empTaxDeductCode": "00-12", "empTaxAmount": "31"},
            ],
            "earning": [{"payCode": "REG", "payAmount": "500"}],
        }],
        employees={"E10": {"employeeType": "W2", "ficaExempt": False}},
        pay_codes={"REG": {"ficaSubject": True}},
    )
    r = await _run(reader)
    codes = {f.code for line in r.vouchers[0].lines for f in line.findings}
    assert "NEGATIVE_TAX_POSITIVE_WAGES" not in codes


# ---------- SS wage-base cap (real UAT false positive: Phantom Neuro R11296) ----------


@pytest.mark.asyncio
async def test_over_ss_cap_not_flagged_as_fica_missing() -> None:
    """High earner whose YTD SS wages have exceeded the cap. 00-12 row
    present with $0 amount and empOverLimitAmount populated. System is
    working correctly — must NOT flag as FICA_NONEXEMPT_NOT_WITHHELD."""
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V-CAP", "employeeId": "HIGHEARNER", "totalEarnings": "11180.61",
            "type": "R",
            "employeeTax": [
                {"empTaxDeductCode": "00-10", "empTaxAmount": "1304.43"},
                # Medicare still withheld (no cap)
                {"empTaxDeductCode": "00-11", "empTaxAmount": "262.75",
                 "empTaxableAmount": "11180.61"},
                # OASDI: row present, amount $0, over-limit populated
                {"empTaxDeductCode": "00-12", "empTaxAmount": "0.00",
                 "empTaxableAmount": "11180.61",
                 "empOverLimitAmount": "11180.61"},
            ],
            "earning": [{"payCode": "REG", "payAmount": "11180.61"}],
        }],
        employees={"HIGHEARNER": {
            "employeeType": "W2", "ficaExempt": False, "status": "ACTIVE",
            "position": "Engineer",
        }},
        pay_codes={"REG": {"ficaSubject": True, "medicareSubject": True}},
    )
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "FICA_NONEXEMPT_NOT_WITHHELD" not in codes
    assert "FICA_EXEMPT_MISFLAG" not in codes


# ---------- FICA_EXEMPT_MISFLAG (real bug: client 001315 HARDIN BRYAN D) ----------


@pytest.mark.asyncio
async def test_fica_exempt_misflag_active_w2_with_wages_is_critical() -> None:
    """Reproduces the 941 balancing issue from Simploy employer 400 /
    client 001315. Active W-2 Laborer flagged FICA Exempt=Yes = data
    error. Voucher withheld $0, 941 doesn't balance."""
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V-HARDIN", "employeeId": "M12853", "totalEarnings": "2000",
            "type": "R",
            "employeeTax": [{"empTaxDeductCode": "00-10", "empTaxAmount": "150"}],
            "earning": [{"payCode": "REG", "payAmount": "2000"}],
        }],
        employees={"M12853": {
            "employeeType": "W2", "ficaExempt": True,
            "status": "ACTIVE", "position": "Laborer",
        }},
        pay_codes={"REG": {"ficaSubject": True}},
    )
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "FICA_EXEMPT_MISFLAG" in codes
    msg = next(f.message for f in r.vouchers[0].findings if f.code == "FICA_EXEMPT_MISFLAG")
    assert "M12853" in msg
    assert "Laborer" in msg


@pytest.mark.asyncio
async def test_fica_exempt_allowlist_by_id_suppresses_finding() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V1", "employeeId": "CLERGY1", "totalEarnings": "2000",
            "type": "R",
            "employeeTax": [{"empTaxDeductCode": "00-10", "empTaxAmount": "150"}],
            "earning": [{"payCode": "REG", "payAmount": "2000"}],
        }],
        employees={"CLERGY1": {
            "employeeType": "W2", "ficaExempt": True,
            "status": "ACTIVE", "position": "Minister",
        }},
        pay_codes={"REG": {"ficaSubject": True}},
    )
    r = await run_voucher_classification_audit(
        reader,
        client_id="T",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 15),
        as_of=date(2026, 4, 20),
        fica_exempt_allowlist_ids=frozenset({"CLERGY1"}),
    )
    codes = {f.code for f in r.vouchers[0].findings}
    assert "FICA_EXEMPT_MISFLAG" not in codes


@pytest.mark.asyncio
async def test_fica_exempt_allowlist_by_position_suppresses_finding() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V1", "employeeId": "E1", "totalEarnings": "2000",
            "type": "R",
            "employeeTax": [{"empTaxDeductCode": "00-10", "empTaxAmount": "150"}],
            "earning": [{"payCode": "REG", "payAmount": "2000"}],
        }],
        employees={"E1": {
            "employeeType": "W2", "ficaExempt": True,
            "status": "ACTIVE", "position": "Minister",
        }},
        pay_codes={"REG": {"ficaSubject": True}},
    )
    r = await run_voucher_classification_audit(
        reader,
        client_id="T",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 15),
        as_of=date(2026, 4, 20),
        fica_exempt_allowlist_positions=frozenset({"MINISTER"}),
    )
    codes = {f.code for f in r.vouchers[0].findings}
    assert "FICA_EXEMPT_MISFLAG" not in codes


@pytest.mark.asyncio
async def test_fica_exempt_1099_does_not_misflag() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V1", "employeeId": "E1", "totalEarnings": "2000",
            "type": "R",
            "employeeTax": [],
            "earning": [{"payCode": "1099NE", "payAmount": "2000"}],
        }],
        employees={"E1": {
            "employeeType": "1099", "ficaExempt": True,
            "status": "ACTIVE", "position": "Consultant",
        }},
        pay_codes={"1099NE": {"isContractor": True, "ficaSubject": False}},
    )
    r = await _run(reader)
    codes = {f.code for f in r.vouchers[0].findings}
    assert "FICA_EXEMPT_MISFLAG" not in codes


# ---------- clean path ----------


@pytest.mark.asyncio
async def test_fully_clean_w2_voucher_has_no_findings() -> None:
    reader = FakeReader(
        vouchers=[{
            "voucherId": "V11", "employeeId": "E11", "totalEarnings": "2000",
            "type": "R",
            "wcState": "MO",
            "employeeTax": _fica_taxes(ss="124", med="29"),
            "earning": [{"payCode": "REG", "payAmount": "2000"}],
        }],
        employees={"E11": {
            "employeeType": "W2", "ficaExempt": False,
            "medicareExempt": False, "workState": "MO",
        }},
        pay_codes={"REG": {"ficaSubject": True, "medicareSubject": True}},
    )
    r = await _run(reader)
    assert r.clean == 1
    assert r.flagged == 0
    assert r.vouchers[0].findings == []
    for line in r.vouchers[0].lines:
        assert line.findings == []


@pytest.mark.asyncio
async def test_report_totals_roll_up_flagged_count() -> None:
    reader = FakeReader(
        vouchers=[
            {
                "voucherId": "V12", "employeeId": "E12", "totalEarnings": "1000",
                "type": "R",
                "employeeTax": _fica_taxes(),
                "earning": [{"payCode": "REG", "payAmount": "1000"}],
            },
            {
                "voucherId": "V13", "employeeId": "E13", "totalEarnings": "1000",
                "type": "R",
                "employeeTax": _fica_taxes(),
                "earning": [{"payCode": "REG", "payAmount": "1000"}],
            },
        ],
        employees={
            "E12": {"employeeType": "1099"},
            "E13": {"employeeType": "W2", "ficaExempt": False},
        },
        pay_codes={"REG": {"ficaSubject": True, "isContractor": False}},
    )
    r = await _run(reader)
    assert r.total == 2
    # E12 is 1099 on W-2 pay code = critical flag. E13 is clean W-2.
    assert r.flagged == 1
    assert r.clean == 1
