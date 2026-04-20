"""New Jersey state income tax withholding — simplified diagnostic calc.

Source: Vertex Calculation Guide March 2026, New Jersey section (p639-662).

Key rules:
  * Reciprocity with PA (only). NJ residents working PA + PA residents
    working NJ exempt with NJ-165 / REV-419 cert.
  * Valid filing statuses: Single, Married/CU Partner Joint, Married/CU
    Partner Separate, Head of Household, Qualifying Widow(er).
  * Graduated rates: 1.4% to 10.75% (brackets below).
  * Personal exemption: $1,000 per Line B on NJ-W4.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


# 2026 NJ single-filer brackets (simplified; Rate Table A)
NJ_BRACKETS_SINGLE = [
    (Decimal("0"),       Decimal("0"),       Decimal("0.014")),
    (Decimal("20000"),   Decimal("280"),     Decimal("0.0175")),
    (Decimal("35000"),   Decimal("542.50"),  Decimal("0.035")),
    (Decimal("40000"),   Decimal("717.50"),  Decimal("0.05525")),
    (Decimal("75000"),   Decimal("2651.25"), Decimal("0.0637")),
    (Decimal("500000"),  Decimal("29722.50"), Decimal("0.0897")),
    (Decimal("1000000"), Decimal("74572.50"), Decimal("0.1075")),
]

PERSONAL_EXEMPTION = Decimal("1000")  # per Line B

NJ_RECIPROCAL_STATES = frozenset({"PA"})

SUPPLEMENTAL_FLAT_RATE = Decimal("0.0637")


@dataclass
class NJCalcInput:
    gross_wages_period: Decimal
    pay_periods_per_year: int
    exemptions: int = 0
    is_nj_resident: bool = True
    work_state: str = "NJ"
    has_nr_cert: bool = False


@dataclass
class NJCalcResult:
    nj_withholding_period: Decimal
    annual_taxable_wages: Decimal
    applied_rule: str
    notes: list[str]


def _q(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _nj_annual_tax(annual: Decimal) -> Decimal:
    for i, (lower, base, rate) in enumerate(NJ_BRACKETS_SINGLE):
        next_lower = NJ_BRACKETS_SINGLE[i + 1][0] if i + 1 < len(NJ_BRACKETS_SINGLE) else None
        if next_lower is None or annual < next_lower:
            return base + (annual - lower) * rate
    return Decimal("0")


def compute_nj(inp: NJCalcInput) -> NJCalcResult:
    notes: list[str] = []

    # PA resident working NJ with NJ-165 = exempt
    if (
        not inp.is_nj_resident
        and inp.work_state == "NJ"
        and inp.has_nr_cert
    ):
        return NJCalcResult(
            nj_withholding_period=Decimal("0"),
            annual_taxable_wages=Decimal("0"),
            applied_rule="reciprocal_exempt",
            notes=["NJ-165 on file for PA resident; NJ withholding = $0."],
        )

    # NJ resident working PA with NJ-165 = exempt from NJ withholding
    # (PA handles withholding for PA/NJ commuter via REV-419)
    if (
        inp.is_nj_resident
        and inp.work_state == "PA"
        and inp.has_nr_cert
    ):
        return NJCalcResult(
            nj_withholding_period=Decimal("0"),
            annual_taxable_wages=Decimal("0"),
            applied_rule="reciprocal_exempt",
            notes=["NJ resident with NR cert working PA; NJ withholding suppressed."],
        )

    periods = Decimal(inp.pay_periods_per_year)
    annual_gross = inp.gross_wages_period * periods
    total_exemption = Decimal(inp.exemptions) * PERSONAL_EXEMPTION
    annual_taxable = max(annual_gross - total_exemption, Decimal("0"))
    annual_tax = _nj_annual_tax(annual_taxable)
    period_tax = annual_tax / periods

    applied = "resident_only" if inp.is_nj_resident else "nonresident"

    return NJCalcResult(
        nj_withholding_period=_q(period_tax),
        annual_taxable_wages=_q(annual_taxable),
        applied_rule=applied,
        notes=notes,
    )
