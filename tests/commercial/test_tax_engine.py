"""Reference tax engine — unit tests.

Spot-checks math for federal + MO + IL against worked examples.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.tax_engine.federal import (  # noqa: E402
    FederalCalcInput,
    compute_federal,
    compute_fit,
)
from simploy.tax_engine.states.mo import MOCalcInput, compute_mo  # noqa: E402
from simploy.tax_engine.states.il import ILCalcInput, compute_il  # noqa: E402
from simploy.tax_engine.multi_state import (  # noqa: E402
    analyze_voucher,
    is_reciprocal,
)


# ---------- Federal ----------


def test_fica_ss_under_cap() -> None:
    inp = FederalCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        ytd_ss_wages=Decimal("0"),
    )
    result = compute_federal(inp)
    # 6.2% × 1000 = 62.00
    assert result.ss_ee_period == Decimal("62.00")
    assert result.ss_er_period == Decimal("62.00")


def test_fica_ss_over_cap_zero_withholding() -> None:
    inp = FederalCalcInput(
        gross_wages_period=Decimal("5000"),
        pay_periods_per_year=52,
        ytd_ss_wages=Decimal("200000"),  # well over 176,100 cap
    )
    result = compute_federal(inp)
    assert result.ss_ee_period == Decimal("0.00")
    assert "cap" in result.notes[0].lower()


def test_medicare_uncapped() -> None:
    inp = FederalCalcInput(
        gross_wages_period=Decimal("2000"),
        pay_periods_per_year=52,
    )
    result = compute_federal(inp)
    # 1.45% × 2000 = 29.00
    assert result.medicare_ee_period == Decimal("29.00")


def test_additional_medicare_over_200k_ytd() -> None:
    inp = FederalCalcInput(
        gross_wages_period=Decimal("5000"),
        pay_periods_per_year=52,
        ytd_medicare_wages=Decimal("199000"),  # just under threshold
    )
    result = compute_federal(inp)
    # YTD after = 204000. Excess over 200K = 4000. 4000 * 0.9% = 36.00
    assert result.additional_medicare_period == Decimal("36.00")


def test_futa_capped_at_7k() -> None:
    inp = FederalCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        ytd_futa_wages=Decimal("6500"),
    )
    result = compute_federal(inp)
    # Only 500 of this check is futa-taxable: 500 * 0.006 = 3.00
    assert result.futa_period == Decimal("3.00")


def test_fit_single_low_wage() -> None:
    # $500/week single = $26,000 annual, standard deduction $16,100
    # taxable = $9,900, bracket: 10% from $6,100
    # annual tax = 0 + (9900 - 6100) × 0.10 = $380
    # per period = 380 / 52 = 7.30769
    inp = FederalCalcInput(
        gross_wages_period=Decimal("500"),
        pay_periods_per_year=52,
        filing_status="S",
    )
    result = compute_federal(inp)
    assert result.annual_taxable_wages == Decimal("9900.00")
    assert result.fit_period == Decimal("7.31")


def test_fit_mfj_higher_bracket() -> None:
    # $2000/week MFJ = $104,000 annual, std ded $32,200
    # taxable = $71,800, brackets: 10%/12% over $40,600
    # $40,600×0 + ($40,600-$17,400)×0.10 + ($71,800-$40,600)×0.12 =
    # $2,320 + $3,744 = $6,064
    inp = FederalCalcInput(
        gross_wages_period=Decimal("2000"),
        pay_periods_per_year=52,
        filing_status="MFJ",
    )
    result = compute_federal(inp)
    assert result.annual_taxable_wages == Decimal("71800.00")
    # 6064 / 52 = 116.6154 → rounds to 116.62
    assert result.fit_period == Decimal("116.62")


# ---------- Missouri ----------


def test_mo_resident_working_in_mo() -> None:
    inp = MOCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        filing_status="SM",
        is_mo_resident=True,
        work_state="MO",
    )
    result = compute_mo(inp)
    assert result.applied_rule == "resident_only"
    assert result.mo_withholding_period > 0


def test_mo_resident_working_out_of_state_with_nr_cert() -> None:
    inp = MOCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        is_mo_resident=True,
        work_state="IL",
        has_nr_cert=True,
    )
    result = compute_mo(inp)
    assert result.applied_rule == "suppressed"
    assert result.mo_withholding_period == Decimal("0.00")


def test_mo_resident_working_out_of_state_no_nr_cert_reduces() -> None:
    # pJurIntTreatment=7: MO reduced by work-state amount
    inp = MOCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        is_mo_resident=True,
        work_state="IL",
        has_nr_cert=False,
        work_state_withholding_period=Decimal("25"),
    )
    result = compute_mo(inp)
    assert result.applied_rule == "resident_reduced"
    # MO computed tax then reduced by 25


def test_mo_nonresident_working_in_mo_withholds() -> None:
    inp = MOCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        is_mo_resident=False,
        work_state="MO",
    )
    result = compute_mo(inp)
    assert result.applied_rule == "nonresident"
    assert result.mo_withholding_period > 0


# ---------- Illinois ----------


def test_il_resident_working_in_il() -> None:
    inp = ILCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        basic_allowances=1,
        is_il_resident=True,
        work_state="IL",
    )
    result = compute_il(inp)
    # Annual gross 52000 - 2925 allowance = 49075; × 4.95% = 2429.21
    # / 52 = 46.72 (approx)
    assert result.applied_rule == "resident_only"
    assert Decimal("40") < result.il_withholding_period < Decimal("55")


def test_il_reciprocal_state_resident_with_cert_exempt() -> None:
    # IA resident works IL, has IL-W-5-NR
    inp = ILCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        is_il_resident=False,
        work_state="IL",
        has_nr_cert=True,
    )
    result = compute_il(inp)
    assert result.applied_rule == "reciprocal_exempt"
    assert result.il_withholding_period == Decimal("0")


def test_il_resident_working_mo_no_cert_reduces() -> None:
    # IL resident works MO (non-reciprocal); pJurIntTreatment=7 kicks in
    inp = ILCalcInput(
        gross_wages_period=Decimal("1000"),
        pay_periods_per_year=52,
        basic_allowances=1,
        is_il_resident=True,
        work_state="MO",
        has_nr_cert=False,
        work_state_withholding_period=Decimal("30"),
    )
    result = compute_il(inp)
    assert result.applied_rule == "resident_reduced"


# ---------- Multi-state voucher validator ----------


def test_reciprocity_table() -> None:
    # IL reciprocal with IA/KY/MI/WI, not MO
    assert is_reciprocal("IL", "IA")
    assert is_reciprocal("IL", "WI")
    assert is_reciprocal("WI", "IL")
    assert not is_reciprocal("IL", "MO")
    assert not is_reciprocal("MO", "IL")


def test_voucher_wrong_state_withheld_non_reciprocal() -> None:
    """MO resident, IL work, MO withheld instead of IL. Real Simploy bug."""
    voucher = {
        "voucherId": "V1", "employeeId": "E1",
        "wcState": "IL",
        "employeeTax": [
            {"empTaxDeductCode": "29-20",  # MO (PrismHR's MO code)
             "empTaxDeductCodeDesc": "MO INCOME TAX",
             "empTaxAmount": "45.00"},
        ],
    }
    audit = analyze_voucher(voucher, home_state="MO")
    codes = {f.code for f in audit.findings}
    assert "WRONG_STATE_WITHHELD" in codes


def test_voucher_double_withheld_mo_il_is_critical() -> None:
    """Both MO and IL withheld for an MO/IL commuter (non-reciprocal)."""
    voucher = {
        "voucherId": "V1", "employeeId": "E1",
        "wcState": "IL",
        "employeeTax": [
            {"empTaxDeductCode": "29-20",
             "empTaxDeductCodeDesc": "MO INCOME TAX",
             "empTaxAmount": "45.00"},
            {"empTaxDeductCode": "17-20",
             "empTaxDeductCodeDesc": "IL INCOME TAX",
             "empTaxAmount": "49.50"},
        ],
    }
    audit = analyze_voucher(voucher, home_state="MO")
    codes = {f.code for f in audit.findings}
    assert "DOUBLE_WITHHELD_NON_RECIPROCAL" in codes


def test_voucher_reciprocal_pair_work_withheld_no_cert() -> None:
    """IA resident working IL without IL-W-5-NR on file — IL shouldn't withhold."""
    voucher = {
        "voucherId": "V1", "employeeId": "E1",
        "wcState": "IL",
        "employeeTax": [
            {"empTaxDeductCode": "17-20",
             "empTaxDeductCodeDesc": "IL INCOME TAX",
             "empTaxAmount": "49.50"},
        ],
    }
    audit = analyze_voucher(voucher, home_state="IA", has_nr_cert=False)
    codes = {f.code for f in audit.findings}
    assert "RECIPROCAL_WORK_WITHHELD_NO_CERT" in codes


def test_voucher_clean_nonreciprocal_single_state() -> None:
    """MO resident, IL work, ONLY IL withheld — correct under pJurIntTreatment=7."""
    voucher = {
        "voucherId": "V1", "employeeId": "E1",
        "wcState": "IL",
        "employeeTax": [
            {"empTaxDeductCode": "17-20",
             "empTaxDeductCodeDesc": "IL INCOME TAX",
             "empTaxAmount": "49.50"},
        ],
    }
    audit = analyze_voucher(voucher, home_state="MO")
    crit_codes = {f.code for f in audit.findings if f.severity == "critical"}
    assert "WRONG_STATE_WITHHELD" not in crit_codes
    assert "DOUBLE_WITHHELD_NON_RECIPROCAL" not in crit_codes
