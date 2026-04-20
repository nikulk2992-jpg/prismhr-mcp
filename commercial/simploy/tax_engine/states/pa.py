"""Pennsylvania state income tax withholding — flat 3.07%.

Source: Vertex Calculation Guide March 2026, Pennsylvania section (p1000-1178).

Key rules:
  * Flat rate 3.07%
  * Reciprocity: IN, MD, NJ, OH, VA, WV (via Form REV-419)
  * pJurIntTreatment = 5: "Eliminate the resident tax if the work tax > 0.
    Accumulate wages only if tax is withheld."
  * No filing-status distinctions
  * No allowance/exemption handling
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


PA_FLAT_RATE = Decimal("0.0307")

PA_RECIPROCAL_STATES = frozenset({"IN", "MD", "NJ", "OH", "VA", "WV"})


@dataclass
class PACalcInput:
    gross_wages_period: Decimal
    pay_periods_per_year: int = 52  # not used; PA is per-period flat
    is_pa_resident: bool = True
    work_state: str = "PA"
    has_nr_cert: bool = False
    work_state_withholding_period: Decimal = Decimal("0")


@dataclass
class PACalcResult:
    pa_withholding_period: Decimal
    applied_rule: str
    notes: list[str]


def _q(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_pa(inp: PACalcInput) -> PACalcResult:
    notes: list[str] = []

    # Non-resident from reciprocal state with REV-419 cert = exempt
    if (
        not inp.is_pa_resident
        and inp.work_state == "PA"
        and inp.has_nr_cert
    ):
        return PACalcResult(
            pa_withholding_period=Decimal("0"),
            applied_rule="reciprocal_exempt",
            notes=["REV-419 on file; PA withholding = $0."],
        )

    # PA resident working out of state
    if inp.is_pa_resident and inp.work_state != "PA":
        if inp.has_nr_cert:
            return PACalcResult(
                pa_withholding_period=Decimal("0"),
                applied_rule="resident_suppressed",
                notes=["PA resident + NR cert out of state; withholding suppressed."],
            )
        # pJurIntTreatment=5 reduces by work-state
        gross_tax = _q(inp.gross_wages_period * PA_FLAT_RATE)
        reduced = max(gross_tax - inp.work_state_withholding_period, Decimal("0"))
        return PACalcResult(
            pa_withholding_period=_q(reduced),
            applied_rule="resident_reduced",
            notes=[f"PA reduced by work-state ${inp.work_state_withholding_period} "
                   f"(pJurIntTreatment=5)."],
        )

    # Default: resident in PA, or non-resident working in PA without cert
    tax = _q(inp.gross_wages_period * PA_FLAT_RATE)
    return PACalcResult(
        pa_withholding_period=tax,
        applied_rule=("resident_only" if inp.is_pa_resident else "nonresident"),
        notes=notes,
    )
