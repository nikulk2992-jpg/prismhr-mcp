"""Missouri state income tax withholding reference calc.

Source: Vertex Calculation Guide March 2026, Missouri section (p564-587).

Key rules (from Vertex):
  * No formal reciprocity. MO does NOT require withholding from MO
    residents working in other states that collect withholding tax.
  * MO withholding is required from non-residents working in MO.
  * pJurIntTreatment = 7: "Eliminate the resident tax if the work tax
    imposes a withholding tax on nonresidents. Accumulate wages only
    if tax is withheld."
  * pNRCertif flag controls whether MO withholding is reduced by
    work-state withholding for MO residents working out of state.

2026 Standard Deductions (Vertex):
  * Single or MFS / MFJ spouse works: $16,100
  * Head of Household: $24,150
  * Married spouse does not work: $32,200

Calculation: annualized method (default).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal


MOFilingStatus = Literal["SM", "MFJ_SNW", "MFJ_SW", "HoH", "MFS"]


# 2026 MO standard deductions (from Vertex)
STANDARD_DEDUCTION = {
    "SM": Decimal("16100"),       # Single
    "MFS": Decimal("16100"),      # Married Filing Separately
    "MFJ_SW": Decimal("16100"),   # MFJ spouse works (same as single)
    "HoH": Decimal("24150"),
    "MFJ_SNW": Decimal("32200"),  # MFJ spouse does NOT work
}

# 2026 MO withholding tax brackets (annualized)
# Source: MO Form 4282 (public DOR publication), per Vertex alignment
MO_BRACKETS_2026 = [
    (Decimal("0"),    Decimal("0"),   Decimal("0.00")),
    (Decimal("1300"), Decimal("0"),   Decimal("0.02")),
    (Decimal("2600"), Decimal("26"),  Decimal("0.025")),
    (Decimal("3900"), Decimal("58.50"), Decimal("0.03")),
    (Decimal("5200"), Decimal("97.50"), Decimal("0.035")),
    (Decimal("6500"), Decimal("143"),   Decimal("0.04")),
    (Decimal("7800"), Decimal("195"),   Decimal("0.045")),
    (Decimal("9100"), Decimal("253.50"), Decimal("0.0475")),
]

SUPPLEMENTAL_FLAT_RATE = Decimal("0.0475")


@dataclass
class MOCalcInput:
    gross_wages_period: Decimal
    pay_periods_per_year: int
    filing_status: MOFilingStatus = "SM"
    is_mo_resident: bool = True
    work_state: str = "MO"
    # pNRCertif on file for MO resident working out of state.
    # When False, MO residents working in a state that collects
    # withholding = MO withholding reduced by work-state withholding.
    # When True, no MO withholding (work state handles it).
    has_nr_cert: bool = False
    # For MO residents working out of state, the amount withheld by
    # the work state. Used to reduce MO withholding when
    # has_nr_cert=False (i.e., pJurIntTreatment=7 logic).
    work_state_withholding_period: Decimal = Decimal("0")


@dataclass
class MOCalcResult:
    mo_withholding_period: Decimal
    annual_taxable_wages: Decimal
    notes: list[str]
    applied_rule: str   # 'resident_only' / 'nonresident' / 'resident_reduced' / 'suppressed'


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _mo_annual_tax(annual_taxable: Decimal) -> Decimal:
    tax = Decimal("0")
    for i, (lower, base, rate) in enumerate(MO_BRACKETS_2026):
        next_lower = (
            MO_BRACKETS_2026[i + 1][0] if i + 1 < len(MO_BRACKETS_2026) else None
        )
        if next_lower is None or annual_taxable < next_lower:
            tax = base + (annual_taxable - lower) * rate
            break
    return max(tax, Decimal("0"))


def compute_mo(inp: MOCalcInput) -> MOCalcResult:
    notes: list[str] = []
    wages = inp.gross_wages_period
    periods = Decimal(inp.pay_periods_per_year)

    # Determine the applicable rule
    if inp.is_mo_resident:
        if inp.work_state == "MO":
            applied = "resident_only"
        elif inp.has_nr_cert:
            # NR cert filed -> MO does NOT withhold (Vertex rule)
            applied = "suppressed"
            notes.append("NR cert on file; MO withholding suppressed. "
                         "Work state handles it.")
            return MOCalcResult(
                mo_withholding_period=Decimal("0"),
                annual_taxable_wages=Decimal("0"),
                applied_rule=applied,
                notes=notes,
            )
        else:
            # pJurIntTreatment=7: MO reduced by work-state withholding
            applied = "resident_reduced"
    else:
        # Non-resident working in MO -> MO withholds
        applied = "nonresident"

    # Annualized calc
    annual_gross = wages * periods
    std_ded = STANDARD_DEDUCTION.get(inp.filing_status, Decimal("16100"))
    annual_taxable = max(annual_gross - std_ded, Decimal("0"))
    annual_tax = _mo_annual_tax(annual_taxable)
    period_tax = annual_tax / periods

    if applied == "resident_reduced":
        # Reduce by work-state withholding, floor at 0
        period_tax = max(
            period_tax - inp.work_state_withholding_period, Decimal("0")
        )
        notes.append(
            f"MO withholding reduced by work-state ${inp.work_state_withholding_period} "
            f"(pJurIntTreatment=7)."
        )

    return MOCalcResult(
        mo_withholding_period=_q(period_tax),
        annual_taxable_wages=_q(annual_taxable),
        applied_rule=applied,
        notes=notes,
    )
