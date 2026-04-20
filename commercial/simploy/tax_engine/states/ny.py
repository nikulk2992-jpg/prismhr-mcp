"""New York state income tax withholding — simplified diagnostic calc.

Source: Vertex Calculation Guide March 2026, New York section (p681-725).

Key rules:
  * No formal reciprocity (NY is not reciprocal with any state).
  * NY residents working out-of-state still owe NY tax with credit
    for work-state tax paid.
  * Valid filing statuses: Single or Married (single rate table applied
    uniformly with different allowance amounts).
  * NYC resident tax + Yonkers resident tax are separate locals not
    handled here; check city-tax fields separately.

2026 NY tax rate table (simplified top-bracket approximation for
Single / MFJ). Full implementation: NYS-50-T-NYS percentage-method
tables. Present scope: diagnostic only.

WARNING: approximation. Use Vertex-provided NYS-50-T tables for
exact per-penny validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


# 2026 NY single-filer brackets (approximate)
NY_BRACKETS_SINGLE = [
    (Decimal("0"),       Decimal("0"),       Decimal("0.04")),
    (Decimal("8500"),    Decimal("340"),     Decimal("0.045")),
    (Decimal("11700"),   Decimal("484"),     Decimal("0.0525")),
    (Decimal("13900"),   Decimal("600"),     Decimal("0.055")),
    (Decimal("80650"),   Decimal("4271.25"), Decimal("0.06")),
    (Decimal("215400"),  Decimal("12356.25"), Decimal("0.0685")),
    (Decimal("1077550"), Decimal("71413.88"), Decimal("0.0965")),
    (Decimal("5000000"), Decimal("449929.38"), Decimal("0.103")),
    (Decimal("25000000"), Decimal("2509929.38"), Decimal("0.109")),
]

ALLOWANCE_AMOUNT = Decimal("1000")  # per allowance, annual

SUPPLEMENTAL_FLAT_RATE = Decimal("0.1123")


@dataclass
class NYCalcInput:
    gross_wages_period: Decimal
    pay_periods_per_year: int
    allowances: int = 0
    is_ny_resident: bool = True
    work_state: str = "NY"


@dataclass
class NYCalcResult:
    ny_withholding_period: Decimal
    annual_taxable_wages: Decimal
    applied_rule: str
    notes: list[str]


def _q(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ny_annual_tax(annual: Decimal) -> Decimal:
    for i, (lower, base, rate) in enumerate(NY_BRACKETS_SINGLE):
        next_lower = NY_BRACKETS_SINGLE[i + 1][0] if i + 1 < len(NY_BRACKETS_SINGLE) else None
        if next_lower is None or annual < next_lower:
            return base + (annual - lower) * rate
    return Decimal("0")


def compute_ny(inp: NYCalcInput) -> NYCalcResult:
    notes = ["NY engine is a diagnostic approximation. Use Vertex NYS-50-T "
             "tables for per-penny accuracy."]
    periods = Decimal(inp.pay_periods_per_year)
    annual_gross = inp.gross_wages_period * periods
    allowance_total = Decimal(inp.allowances) * ALLOWANCE_AMOUNT
    annual_taxable = max(annual_gross - allowance_total, Decimal("0"))
    annual_tax = _ny_annual_tax(annual_taxable)
    period_tax = annual_tax / periods

    applied = "resident_only" if inp.is_ny_resident else "nonresident"
    if inp.is_ny_resident and inp.work_state != "NY":
        applied = "resident_with_credit"
        notes.append("NY residents working out of state: NY still requires "
                     "withholding, with credit for out-of-state tax at filing. "
                     "This engine does NOT reduce NY withholding.")

    return NYCalcResult(
        ny_withholding_period=_q(period_tax),
        annual_taxable_wages=_q(annual_taxable),
        applied_rule=applied,
        notes=notes,
    )
