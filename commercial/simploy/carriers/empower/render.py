"""Empower (Empower Retirement / formerly Great-West) 401(k) PDI.

Pipe-delimited text. Each line represents one participant-record-
type. Contribution types are split into separate lines per source.

Line format:
  <plan_id>|<ssn>|<last>|<first>|<dob>|<hire>|<term>|<status>|
  <pay_date>|<source_code>|<amount>|<ytd_wages>|<hours>

Source codes (common):
  PT  = Pretax deferral
  RT  = Roth deferral
  CT  = Catch-up pretax
  CR  = Catch-up Roth
  LN  = Loan payment
  EM  = Employer match
  AT  = After-tax
"""

from __future__ import annotations

from decimal import Decimal

from ..retirement_common import ParticipantContribution, RetirementFeed


_SOURCES: list[tuple[str, str]] = [
    ("PT", "deferral_pretax"),
    ("RT", "deferral_roth"),
    ("CT", "catchup_pretax"),
    ("CR", "catchup_roth"),
    ("LN", "loan_repayment"),
    ("EM", "employer_match"),
    ("AT", "after_tax_contribution"),
]


def render_empower_pdi(feed: RetirementFeed) -> str:
    lines: list[str] = []
    # Header record — Empower uses HDR prefix
    lines.append(
        f"HDR|{feed.plan_id}|{feed.pay_date.strftime('%Y%m%d')}|{feed.client_id}"
    )
    for p in feed.participants:
        lines.extend(_participant_lines(p, feed))
    lines.append(f"TRL|{len(feed.participants)}")
    return "\n".join(lines) + "\n"


def _participant_lines(p: ParticipantContribution, feed: RetirementFeed) -> list[str]:
    out: list[str] = []
    base = [
        feed.plan_id,
        (p.ssn or "").replace("-", ""),
        p.last_name,
        p.first_name,
        p.dob.strftime("%Y%m%d") if p.dob else "",
        p.hire_date.strftime("%Y%m%d") if p.hire_date else "",
        p.termination_date.strftime("%Y%m%d") if p.termination_date else "",
        p.employment_status,
        feed.pay_date.strftime("%Y%m%d"),
    ]
    for code, attr in _SOURCES:
        amt = getattr(p, attr)
        if amt and amt != Decimal("0"):
            row = base + [code, _money(amt), _money(p.ytd_gross_wages), _money(p.period_hours)]
            out.append("|".join(row))
    return out


def _money(value) -> str:  # type: ignore[no-untyped-def]
    if value is None:
        return "0.00"
    return f"{Decimal(str(value)):.2f}"
