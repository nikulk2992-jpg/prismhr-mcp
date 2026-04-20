"""California state income tax withholding — simplified diagnostic calc.

Source: Vertex Calculation Guide March 2026, California section (p160-185).

Key rules:
  * No formal reciprocity per Vertex, but CA allows credit for tax
    paid to other states EXCEPT AZ, OR, VA (where CA still withholds).
  * pJurIntTreatment = 2: "Credit the resident state by the amount of
    work tax withheld. Always accumulate wages."
  * Valid filing statuses: Single or Married with two or more incomes,
    Head of Household, Married with one income.
  * Allowance tax credit: $168.30 per regular withholding allowance.

2026 CA tax rate tables (simplified — top-bracket approximation).
Full implementation would require Method B tables from CA DE 44.
For diagnostic use: compare magnitudes, not per-penny values.

WARNING: this engine produces an approximation. For per-penny
validation, consume the Vertex DE 44 percentage-method tables
directly (14 brackets per filing status). Present scope: catch
gross under/over-withholding, not penny-level drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


# Simplified CA brackets (single filer, approximate 2026 values)
CA_BRACKETS_SIMPLE = [
    (Decimal("0"),        Decimal("0"),       Decimal("0.011")),
    (Decimal("10756"),    Decimal("118.32"),  Decimal("0.022")),
    (Decimal("25499"),    Decimal("442.65"),  Decimal("0.044")),
    (Decimal("40245"),    Decimal("1091.47"), Decimal("0.066")),
    (Decimal("55866"),    Decimal("2122.45"), Decimal("0.088")),
    (Decimal("70606"),    Decimal("3419.57"), Decimal("0.1023")),
    (Decimal("360659"),   Decimal("33094.99"), Decimal("0.1133")),
    (Decimal("432787"),   Decimal("41268.50"), Decimal("0.1243")),
    (Decimal("721314"),   Decimal("77129.08"), Decimal("0.1353")),
    (Decimal("1000000"),  Decimal("114853.11"), Decimal("0.1463")),
]

ALLOWANCE_CREDIT = Decimal("168.30")

CA_NO_CREDIT_STATES = frozenset({"AZ", "OR", "VA"})

SUPPLEMENTAL_FLAT_RATE = Decimal("0.0623")  # Bonuses
# Stock options / bonuses for 2026 tax year
SUPPLEMENTAL_STOCK_RATE = Decimal("0.1023")


@dataclass
class CACalcInput:
    gross_wages_period: Decimal
    pay_periods_per_year: int
    regular_allowances: int = 0
    is_ca_resident: bool = True
    work_state: str = "CA"
    work_state_withholding_period: Decimal = Decimal("0")


@dataclass
class CACalcResult:
    ca_withholding_period: Decimal
    annual_taxable_wages: Decimal
    applied_rule: str
    notes: list[str]
    confidence: str = "MEDIUM"  # diagnostic approximation, not per-penny


def _q(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ca_annual_tax(annual: Decimal) -> Decimal:
    for i, (lower, base, rate) in enumerate(CA_BRACKETS_SIMPLE):
        next_lower = CA_BRACKETS_SIMPLE[i + 1][0] if i + 1 < len(CA_BRACKETS_SIMPLE) else None
        if next_lower is None or annual < next_lower:
            return base + (annual - lower) * rate
    return Decimal("0")


def compute_ca(inp: CACalcInput) -> CACalcResult:
    notes = ["CA engine is a diagnostic approximation. Use Vertex DE 44 "
             "tables for per-penny accuracy."]
    periods = Decimal(inp.pay_periods_per_year)
    annual_gross = inp.gross_wages_period * periods
    annual_tax = _ca_annual_tax(annual_gross)

    # Subtract allowance credit (annual)
    allowance_credit = Decimal(inp.regular_allowances) * ALLOWANCE_CREDIT
    annual_tax = max(annual_tax - allowance_credit, Decimal("0"))
    period_tax = annual_tax / periods

    if inp.is_ca_resident and inp.work_state != "CA":
        if inp.work_state in CA_NO_CREDIT_STATES:
            applied = "resident_no_credit"
            notes.append(f"{inp.work_state} not in CA's credit-allowed list; "
                         f"full CA withholding required.")
        else:
            # CA pJurIntTreatment=2: reduce CA by work-state amount
            period_tax = max(period_tax - inp.work_state_withholding_period, Decimal("0"))
            applied = "resident_reduced"
            notes.append(f"CA reduced by work-state ${inp.work_state_withholding_period} "
                         f"(pJurIntTreatment=2).")
    elif inp.is_ca_resident:
        applied = "resident_only"
    else:
        applied = "nonresident"

    return CACalcResult(
        ca_withholding_period=_q(period_tax),
        annual_taxable_wages=_q(annual_gross),
        applied_rule=applied,
        notes=notes,
    )
