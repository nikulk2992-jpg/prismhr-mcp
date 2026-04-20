"""Fidelity 401(k) tape-spec fixed-width record.

Fidelity's tape spec is 150-char records, all-caps, with money in
implied-decimal format (value × 100, no decimal point).

Record layout:
  Pos 1-10  : Participant SSN (zero-padded)
  Pos 11-40 : Last name (padded, all-caps)
  Pos 41-60 : First name (padded, all-caps)
  Pos 61-68 : DOB YYYYMMDD
  Pos 69-76 : Hire YYYYMMDD
  Pos 77    : Status A/T/L/R
  Pos 78-79 : Source code
  Pos 80-92 : Contribution amount (13 digits, implied 2 decimals)
  Pos 93-105: Gross wages (YTD, 13 digits, implied 2 decimals)
  Pos 106-113: Pay date YYYYMMDD
  Pos 114-125: Plan ID
  Pos 126-150: reserved / blank
"""

from __future__ import annotations

from decimal import Decimal

from ..retirement_common import ParticipantContribution, RetirementFeed


_SOURCES: list[tuple[str, str]] = [
    ("01", "deferral_pretax"),
    ("02", "deferral_roth"),
    ("03", "catchup_pretax"),
    ("04", "catchup_roth"),
    ("05", "loan_repayment"),
    ("06", "employer_match"),
    ("07", "after_tax_contribution"),
]


def render_fidelity_tape(feed: RetirementFeed) -> str:
    lines: list[str] = []
    for p in feed.participants:
        for code, attr in _SOURCES:
            amt = getattr(p, attr)
            if amt and amt != Decimal("0"):
                lines.append(_record(p, feed, code, amt))
    return "\n".join(lines) + "\n"


def _record(p: ParticipantContribution, feed: RetirementFeed, source: str, amount: Decimal) -> str:
    ssn = (p.ssn or "").replace("-", "").rjust(10, "0")[:10]
    last = p.last_name.upper().ljust(30)[:30]
    first = p.first_name.upper().ljust(20)[:20]
    dob = p.dob.strftime("%Y%m%d") if p.dob else " " * 8
    hire = p.hire_date.strftime("%Y%m%d") if p.hire_date else " " * 8
    status = (p.employment_status or "A")[:1]
    amt_impl = _implied_decimal(amount, width=13)
    ytd_impl = _implied_decimal(p.ytd_gross_wages, width=13)
    paydt = feed.pay_date.strftime("%Y%m%d")
    plan = feed.plan_id.ljust(12)[:12]
    record = f"{ssn}{last}{first}{dob}{hire}{status}{source}{amt_impl}{ytd_impl}{paydt}{plan}"
    return record.ljust(150)[:150]


def _implied_decimal(value, width: int) -> str:  # type: ignore[no-untyped-def]
    d = Decimal(str(value or "0")).quantize(Decimal("0.01"))
    cents = int(d * 100)
    # Sign encoded by prefix "-"; Fidelity generally expects positive.
    if cents < 0:
        return ("-" + str(abs(cents))).rjust(width, "0")[-width:]
    return str(cents).rjust(width, "0")[-width:]
