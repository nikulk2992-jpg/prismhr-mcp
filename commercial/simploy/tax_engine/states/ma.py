"""Massachusetts state income tax withholding — flat 5% + 4% surtax on $1M+.

Source: Vertex Calculation Guide March 2026, Massachusetts section (p484-507).

Key rules:
  * Flat 5% on wages.
  * Millionaires' surtax: additional 4% on MA taxable income exceeding
    $1,083,150 (2026). This is annual; withholding uses the effective
    rate only above the threshold.
  * No formal reciprocity. MA residents working out-of-state can claim
    credit on MA tax return; employer still withholds MA.
  * Exemption amounts per M-4 form: $4,400 single; $8,800 married.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


MA_FLAT_RATE = Decimal("0.05")
MA_SURTAX_RATE = Decimal("0.04")
MA_SURTAX_THRESHOLD = Decimal("1083150")  # 2026

EXEMPTION_SINGLE = Decimal("4400")
EXEMPTION_MARRIED = Decimal("8800")

SUPPLEMENTAL_FLAT_RATE = Decimal("0.05")


@dataclass
class MACalcInput:
    gross_wages_period: Decimal
    pay_periods_per_year: int
    filing_status: str = "S"  # "S" or "MJ"
    blindness_exemptions: int = 0  # extra $2,200 each
    is_ma_resident: bool = True
    work_state: str = "MA"


@dataclass
class MACalcResult:
    ma_withholding_period: Decimal
    annual_taxable_wages: Decimal
    applied_rule: str
    notes: list[str]


def _q(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_ma(inp: MACalcInput) -> MACalcResult:
    notes: list[str] = []
    periods = Decimal(inp.pay_periods_per_year)
    annual_gross = inp.gross_wages_period * periods

    base_exemption = (
        EXEMPTION_MARRIED if inp.filing_status == "MJ" else EXEMPTION_SINGLE
    )
    blindness_extra = Decimal(inp.blindness_exemptions) * Decimal("2200")
    total_exemption = base_exemption + blindness_extra
    annual_taxable = max(annual_gross - total_exemption, Decimal("0"))

    annual_tax = annual_taxable * MA_FLAT_RATE

    # Millionaire surtax
    if annual_taxable > MA_SURTAX_THRESHOLD:
        surtax_base = annual_taxable - MA_SURTAX_THRESHOLD
        annual_tax += surtax_base * MA_SURTAX_RATE
        notes.append(f"Millionaire surtax applied: 4% on ${surtax_base} over "
                     f"${MA_SURTAX_THRESHOLD} threshold.")

    period_tax = annual_tax / periods

    applied = "resident_only" if inp.is_ma_resident else "nonresident"
    if inp.is_ma_resident and inp.work_state != "MA":
        applied = "resident_with_credit"
        notes.append("MA residents working out of state: MA still withholds; "
                     "employee claims credit for work-state tax at filing.")

    return MACalcResult(
        ma_withholding_period=_q(period_tax),
        annual_taxable_wages=_q(annual_taxable),
        applied_rule=applied,
        notes=notes,
    )
