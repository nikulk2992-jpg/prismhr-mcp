"""Ohio state income tax withholding reference calc.

Source: Vertex Calculation Guide March 2026, Ohio section (p781-941).

Key rules:
  * Reciprocity: IN, KY, MI, PA, WV (via Form IT-4 NR)
  * pJurIntTreatment = 6: "Eliminate the resident tax if the work tax
    imposes a withholding tax on nonresidents. Always accumulate wages."
  * OH does NOT require withholding from OH residents working in other
    states that collect withholding.
  * OH withholding required from non-residents working in OH (except
    reciprocal-state residents with IT-4 NR).

2026 rate table (3 brackets, annualized; per Vertex p791):
  * Not over $26,050           -> 1.775% × wages
  * $26,050 to $100,000        -> $462.39 + 2.99% × (wages - 26,050)
  * Over $100,000              -> $2,673.50 + 3.64% × (wages - 100,000)

Personal exemption: $650 per exemption (annual, subtracted before rate lookup)
Supplemental flat rate: 2.75%

Local tax NOT handled here — Ohio has 600+ municipal taxes administered
via RITA / CCA / direct-city portals. Separate workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


OH_BRACKETS_2026 = [
    # (lower, base_tax_at_lower, rate_above_lower, upper)
    (Decimal("0"),       Decimal("0"),        Decimal("0.01775"),  Decimal("26050")),
    (Decimal("26050"),   Decimal("462.39"),   Decimal("0.0299"),   Decimal("100000")),
    (Decimal("100000"),  Decimal("2673.50"),  Decimal("0.0364"),   None),
]

PERSONAL_EXEMPTION_ANNUAL = Decimal("650")

OH_RECIPROCAL_STATES = frozenset({"IN", "KY", "MI", "PA", "WV"})

SUPPLEMENTAL_FLAT_RATE = Decimal("0.0275")


@dataclass
class OHCalcInput:
    gross_wages_period: Decimal
    pay_periods_per_year: int
    exemptions: int = 0   # number of personal exemptions
    is_oh_resident: bool = True
    work_state: str = "OH"
    has_nr_cert: bool = False
    work_state_withholding_period: Decimal = Decimal("0")


@dataclass
class OHCalcResult:
    oh_withholding_period: Decimal
    annual_taxable_wages: Decimal
    applied_rule: str
    notes: list[str]


def _q(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _oh_annual_tax(annual_taxable: Decimal) -> Decimal:
    for lower, base, rate, upper in OH_BRACKETS_2026:
        if upper is None or annual_taxable <= upper:
            return base + (annual_taxable - lower) * rate
    return Decimal("0")


def compute_oh(inp: OHCalcInput) -> OHCalcResult:
    notes: list[str] = []

    # Non-resident from reciprocal state with IT-4 NR = exempt
    if (
        not inp.is_oh_resident
        and inp.work_state == "OH"
        and inp.has_nr_cert
    ):
        return OHCalcResult(
            oh_withholding_period=Decimal("0"),
            annual_taxable_wages=Decimal("0"),
            applied_rule="reciprocal_exempt",
            notes=["IT-4 NR on file; OH withholding = $0."],
        )

    # OH resident working out of state with withholding
    if inp.is_oh_resident and inp.work_state != "OH":
        if inp.has_nr_cert:
            return OHCalcResult(
                oh_withholding_period=Decimal("0"),
                annual_taxable_wages=Decimal("0"),
                applied_rule="resident_suppressed",
                notes=["OH resident + NR cert out of state; withholding suppressed."],
            )
        applied = "resident_reduced"
    elif inp.is_oh_resident:
        applied = "resident_only"
    else:
        applied = "nonresident"

    # Annualized calc
    periods = Decimal(inp.pay_periods_per_year)
    annual_gross = inp.gross_wages_period * periods
    exemption_amount = Decimal(inp.exemptions) * PERSONAL_EXEMPTION_ANNUAL
    annual_taxable = max(annual_gross - exemption_amount, Decimal("0"))
    annual_tax = max(_oh_annual_tax(annual_taxable), Decimal("0"))
    period_tax = annual_tax / periods

    if applied == "resident_reduced":
        period_tax = max(period_tax - inp.work_state_withholding_period, Decimal("0"))
        notes.append(f"OH reduced by work-state ${inp.work_state_withholding_period} "
                     f"(pJurIntTreatment=6).")

    return OHCalcResult(
        oh_withholding_period=_q(period_tax),
        annual_taxable_wages=_q(annual_taxable),
        applied_rule=applied,
        notes=notes,
    )
