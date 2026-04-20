"""Illinois state income tax withholding reference calc.

Source: Vertex Calculation Guide March 2026, Illinois section (p330-344).

Key rules (verbatim from Vertex):
  * IL does NOT require withholding from IL residents working in other
    states that collect withholding tax.
  * IL withholding is required from nonresidents working in IL (except
    IA/KY/MI/WI residents with IL-W-5-NR).
  * Reciprocity: IA, KY, MI, WI only. MO is NOT reciprocal.
  * pJurIntTreatment = 7 (same as MO).

2026 IL rates (flat 4.95% with allowance deductions):
  * Basic allowance: $2,925 per Line 1
  * Additional allowance: $1,000 per Line 2

Calculation: annualized method (default).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


# IL has a FLAT rate — no brackets
IL_FLAT_RATE = Decimal("0.0495")

BASIC_ALLOWANCE = Decimal("2925")
ADDITIONAL_ALLOWANCE = Decimal("1000")

SUPPLEMENTAL_FLAT_RATE = Decimal("0.0495")

# Reciprocity — IL residents who should NOT have IL withholding when
# working in these states (or vice versa).
IL_RECIPROCAL_STATES = frozenset({"IA", "KY", "MI", "WI"})


@dataclass
class ILCalcInput:
    gross_wages_period: Decimal
    pay_periods_per_year: int
    basic_allowances: int = 0            # Line 1 on Form IL-W-4
    additional_allowances: int = 0       # Line 2 on Form IL-W-4
    additional_withholding: Decimal = Decimal("0")  # Line 3
    is_il_resident: bool = True
    work_state: str = "IL"
    # NR cert filed (IL-W-5-NR) = exempt from IL withholding for
    # reciprocal-state residents working in IL.
    has_nr_cert: bool = False
    # For IL residents working out of state (non-reciprocal), amount
    # withheld by work state. Reduces IL withholding when
    # has_nr_cert=False (pJurIntTreatment=7).
    work_state_withholding_period: Decimal = Decimal("0")


@dataclass
class ILCalcResult:
    il_withholding_period: Decimal
    annual_taxable_wages: Decimal
    notes: list[str]
    applied_rule: str


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_il(inp: ILCalcInput) -> ILCalcResult:
    notes: list[str] = []
    wages = inp.gross_wages_period
    periods = Decimal(inp.pay_periods_per_year)

    # Non-resident from reciprocal state with NR cert -> exempt
    if (
        not inp.is_il_resident
        and inp.work_state == "IL"
        and inp.has_nr_cert
    ):
        notes.append("IL-W-5-NR on file for reciprocal-state resident; "
                     "IL withholding = $0.")
        return ILCalcResult(
            il_withholding_period=Decimal("0"),
            annual_taxable_wages=Decimal("0"),
            applied_rule="reciprocal_exempt",
            notes=notes,
        )

    # IL resident working in another state that collects withholding
    if inp.is_il_resident and inp.work_state != "IL":
        if inp.has_nr_cert:
            notes.append("IL resident with NR cert working out of state — "
                         "IL withholding suppressed.")
            return ILCalcResult(
                il_withholding_period=Decimal("0"),
                annual_taxable_wages=Decimal("0"),
                applied_rule="resident_suppressed",
                notes=notes,
            )
        applied = "resident_reduced"
    elif inp.is_il_resident:
        applied = "resident_only"
    else:
        applied = "nonresident"

    # Annualized calc
    annual_gross = wages * periods
    total_allowances = (
        Decimal(inp.basic_allowances) * BASIC_ALLOWANCE
        + Decimal(inp.additional_allowances) * ADDITIONAL_ALLOWANCE
    )
    annual_taxable = max(annual_gross - total_allowances, Decimal("0"))
    annual_tax = annual_taxable * IL_FLAT_RATE
    period_tax = annual_tax / periods + inp.additional_withholding

    if applied == "resident_reduced":
        period_tax = max(
            period_tax - inp.work_state_withholding_period, Decimal("0")
        )
        notes.append(
            f"IL withholding reduced by work-state ${inp.work_state_withholding_period} "
            f"(pJurIntTreatment=7)."
        )

    return ILCalcResult(
        il_withholding_period=_q(period_tax),
        annual_taxable_wages=_q(annual_taxable),
        applied_rule=applied,
        notes=notes,
    )
