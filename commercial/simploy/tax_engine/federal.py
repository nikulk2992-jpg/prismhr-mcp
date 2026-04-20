"""Federal income tax + FICA + FUTA + Additional Medicare reference calc.

Based on IRS Pub 15-T 2026 percentage method and Vertex Calculation Guide
(March 2026). Scope:

  * FIT via Pub 15-T percentage method — single / MFJ / HoH / MFS
  * FICA Social Security — 6.2% to wage-base cap, ee + er
  * FICA Medicare — 1.45% uncapped, ee + er
  * Additional Medicare — 0.9% over $200K YTD (employee only)
  * FUTA — 0.6% × $7K cap (credit-reduction overlay separate)

Intentionally simplified from full Vertex implementation:
  * 2026 brackets + standard deductions hardcoded
  * Annualized calculation method (Vertex default for Regular Only)
  * No W-4 Step 2 checkbox handling (multiple jobs) — flagged upstream
  * No cumulative or supplemental-only methods — those are the
    bonus_gross_up workflow's domain

Diagnostic purpose only: compare our output vs PrismHR-supplied-to-
Vertex result, flag meaningful deltas. Not a production engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal


FilingStatus = Literal["S", "MFJ", "HoH", "MFS"]


# 2026 Standard deductions (from Vertex Federal Withholding Tax Summary)
STANDARD_DEDUCTION_2026 = {
    "S": Decimal("16100"),   # Single or MFS
    "MFS": Decimal("16100"),
    "HoH": Decimal("23850"),
    "MFJ": Decimal("32200"),
}

# 2026 FICA Social Security
SS_RATE = Decimal("0.062")
SS_WAGE_BASE_2026 = Decimal("176100")
MEDICARE_RATE = Decimal("0.0145")
ADDITIONAL_MEDICARE_RATE = Decimal("0.009")
ADDITIONAL_MEDICARE_THRESHOLD = Decimal("200000")

# FUTA
FUTA_RATE = Decimal("0.006")
FUTA_WAGE_CAP = Decimal("7000")


# 2026 Federal Income Tax — Pub 15-T Annual Percentage Method
# Each row: (bracket_lower, base_tax, rate_above_lower)
# Filing status S applies to Single and MFS.
FIT_BRACKETS_2026 = {
    "S": [
        (Decimal("0"),      Decimal("0"),       Decimal("0.00")),
        (Decimal("6100"),   Decimal("0"),       Decimal("0.10")),
        (Decimal("17700"),  Decimal("1160"),    Decimal("0.12")),
        (Decimal("53550"),  Decimal("5462"),    Decimal("0.22")),
        (Decimal("106700"), Decimal("17155"),   Decimal("0.24")),
        (Decimal("198800"), Decimal("39259"),   Decimal("0.32")),
        (Decimal("250550"), Decimal("55819"),   Decimal("0.35")),
        (Decimal("626300"), Decimal("187331.25"), Decimal("0.37")),
    ],
    "MFJ": [
        (Decimal("0"),      Decimal("0"),       Decimal("0.00")),
        (Decimal("17400"),  Decimal("0"),       Decimal("0.10")),
        (Decimal("40600"),  Decimal("2320"),    Decimal("0.12")),
        (Decimal("112300"), Decimal("10924"),   Decimal("0.22")),
        (Decimal("218550"), Decimal("34299"),   Decimal("0.24")),
        (Decimal("402750"), Decimal("78507"),   Decimal("0.32")),
        (Decimal("506300"), Decimal("111643"),  Decimal("0.35")),
        (Decimal("759750"), Decimal("200345.50"), Decimal("0.37")),
    ],
    "HoH": [
        (Decimal("0"),      Decimal("0"),       Decimal("0.00")),
        (Decimal("13850"),  Decimal("0"),       Decimal("0.10")),
        (Decimal("30400"),  Decimal("1655"),    Decimal("0.12")),
        (Decimal("78750"),  Decimal("7457"),    Decimal("0.22")),
        (Decimal("122300"), Decimal("17038"),   Decimal("0.24")),
        (Decimal("214400"), Decimal("39142"),   Decimal("0.32")),
        (Decimal("266150"), Decimal("55702"),   Decimal("0.35")),
        (Decimal("641900"), Decimal("187214.50"), Decimal("0.37")),
    ],
}
FIT_BRACKETS_2026["MFS"] = FIT_BRACKETS_2026["S"]


@dataclass
class FederalCalcInput:
    gross_wages_period: Decimal
    pay_periods_per_year: int          # 52 weekly, 26 biweekly, 24 semi, 12 monthly
    filing_status: FilingStatus = "S"
    other_income_annual: Decimal = Decimal("0")    # W-4 4a
    other_deductions_annual: Decimal = Decimal("0")  # W-4 4b
    tax_credit_annual: Decimal = Decimal("0")        # W-4 3
    step_2_checkbox: bool = False                    # W-4 Step 2(c)
    ytd_medicare_wages: Decimal = Decimal("0")       # for additional Medicare
    ytd_ss_wages: Decimal = Decimal("0")             # for SS cap
    ytd_futa_wages: Decimal = Decimal("0")           # for FUTA cap


@dataclass
class FederalCalcResult:
    fit_period: Decimal
    ss_ee_period: Decimal
    ss_er_period: Decimal
    medicare_ee_period: Decimal
    medicare_er_period: Decimal
    additional_medicare_period: Decimal
    futa_period: Decimal
    annual_taxable_wages: Decimal   # after standard deduction adjustments
    notes: list[str]


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_fit(
    annual_taxable_wages: Decimal, filing_status: FilingStatus
) -> Decimal:
    """Apply the Pub 15-T percentage-method bracket table."""
    brackets = FIT_BRACKETS_2026.get(filing_status, FIT_BRACKETS_2026["S"])
    annual_tax = Decimal("0")
    for i, (lower, base, rate) in enumerate(brackets):
        next_lower = (
            brackets[i + 1][0] if i + 1 < len(brackets) else None
        )
        if next_lower is None or annual_taxable_wages < next_lower:
            annual_tax = base + (annual_taxable_wages - lower) * rate
            break
    if annual_tax < 0:
        annual_tax = Decimal("0")
    return _q(annual_tax)


def compute_federal(inp: FederalCalcInput) -> FederalCalcResult:
    notes: list[str] = []
    wages = inp.gross_wages_period
    periods = Decimal(inp.pay_periods_per_year)

    # ---- FIT via annualized percentage method ----
    annual_gross = wages * periods
    annual_plus_other = annual_gross + inp.other_income_annual
    annual_minus_other_deductions = annual_plus_other - inp.other_deductions_annual
    if inp.step_2_checkbox:
        standard_deduction = Decimal("0")
        notes.append("W-4 Step 2 checkbox set — standard deduction zeroed per Pub 15-T.")
    else:
        standard_deduction = STANDARD_DEDUCTION_2026.get(
            inp.filing_status, Decimal("0")
        )
    annual_taxable = annual_minus_other_deductions - standard_deduction
    if annual_taxable < 0:
        annual_taxable = Decimal("0")

    annual_fit = compute_fit(annual_taxable, inp.filing_status)
    # Subtract annual tax credit, then divide by periods
    annual_fit_after_credit = max(annual_fit - inp.tax_credit_annual, Decimal("0"))
    fit_period = _q(annual_fit_after_credit / periods)

    # ---- FICA SS (capped) ----
    ss_remaining_cap = max(SS_WAGE_BASE_2026 - inp.ytd_ss_wages, Decimal("0"))
    ss_taxable_this_period = min(wages, ss_remaining_cap)
    ss_ee = _q(ss_taxable_this_period * SS_RATE)
    ss_er = ss_ee  # employer match
    if ss_remaining_cap == 0:
        notes.append(
            f"SS wage base cap (${SS_WAGE_BASE_2026}) hit. $0 SS withheld."
        )

    # ---- Medicare (uncapped) ----
    medicare_ee = _q(wages * MEDICARE_RATE)
    medicare_er = medicare_ee

    # ---- Additional Medicare (0.9% over $200K YTD, employee only) ----
    addl_medicare = Decimal("0")
    ytd_med_after = inp.ytd_medicare_wages + wages
    if ytd_med_after > ADDITIONAL_MEDICARE_THRESHOLD:
        over = min(
            wages,
            ytd_med_after - ADDITIONAL_MEDICARE_THRESHOLD,
        )
        addl_medicare = _q(over * ADDITIONAL_MEDICARE_RATE)

    # ---- FUTA (employer only) ----
    futa_remaining = max(FUTA_WAGE_CAP - inp.ytd_futa_wages, Decimal("0"))
    futa_taxable = min(wages, futa_remaining)
    futa_period = _q(futa_taxable * FUTA_RATE)

    return FederalCalcResult(
        fit_period=fit_period,
        ss_ee_period=ss_ee,
        ss_er_period=ss_er,
        medicare_ee_period=medicare_ee,
        medicare_er_period=medicare_er,
        additional_medicare_period=addl_medicare,
        futa_period=futa_period,
        annual_taxable_wages=_q(annual_taxable),
        notes=notes,
    )
