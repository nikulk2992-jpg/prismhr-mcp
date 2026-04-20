"""Voya 401(k) PDI fixed-width feed.

Record layout (80-char records, blank-padded):

Header (record type H):
  Pos 1    : H
  Pos 2-11 : Plan ID (left-justified, blank-padded)
  Pos 12-19: Period end date YYYYMMDD
  Pos 20-27: Pay date YYYYMMDD
  Pos 28-37: Client ID (left-justified)
  Pos 38-80: reserved / blank

Detail (record type D) — one per participant:
  Pos 1    : D
  Pos 2-10 : SSN (9 digits, numeric, no dashes)
  Pos 11-35: Last name (left-justified)
  Pos 36-55: First name (left-justified)
  Pos 56-63: DOB YYYYMMDD (or 8 spaces)
  Pos 64-71: Hire date YYYYMMDD
  Pos 72   : Status code (A/T/L)
  Pos 73-82: Deferral pretax (8.2 fixed, signed, zero-padded)
  Pos 83-92: Deferral roth (8.2)
  Pos 93-102: Catchup pretax (8.2)
  Pos 103-112: Catchup roth (8.2)
  Pos 113-122: Loan repayment (8.2)
  Pos 123-132: Employer match (8.2)
  Pos 133-142: After-tax (8.2)
  Pos 143-152: YTD gross (9.2)
  Pos 153-162: Period gross (9.2)
  Pos 163-172: Period hours (6.2)

Trailer (record type T):
  Pos 1    : T
  Pos 2-8  : Detail record count (7 digits, zero-padded)
  Pos 9-23 : Total deferral (13.2 absolute, zero-padded)

The "exact" Voya PDI spec varies per plan setup; this is the
common-denominator shape Simploy has seen across Voya groups.
Operator-specific column tweaks live in the companion file (not
shipped here — kept per-plan in config).
"""

from __future__ import annotations

from decimal import Decimal

from ..retirement_common import ParticipantContribution, RetirementFeed


def render_voya_pdi(feed: RetirementFeed) -> str:
    lines: list[str] = []
    lines.append(_header(feed))
    total_def = Decimal("0")
    for p in feed.participants:
        lines.append(_detail(p))
        total_def += p.deferral_pretax + p.deferral_roth + p.catchup_pretax + p.catchup_roth
    lines.append(_trailer(len(feed.participants), total_def))
    return "\n".join(lines) + "\n"


def _header(feed: RetirementFeed) -> str:
    buf = ["H"]
    buf.append(feed.plan_id.ljust(10)[:10])
    buf.append(feed.period_end.strftime("%Y%m%d"))
    buf.append(feed.pay_date.strftime("%Y%m%d"))
    buf.append(feed.client_id.ljust(10)[:10])
    line = "".join(buf)
    return line.ljust(80)[:80]


def _detail(p: ParticipantContribution) -> str:
    buf = ["D"]
    buf.append((p.ssn or "000000000").replace("-", "").ljust(9)[:9])
    buf.append(p.last_name.ljust(25)[:25])
    buf.append(p.first_name.ljust(20)[:20])
    buf.append(p.dob.strftime("%Y%m%d") if p.dob else " " * 8)
    buf.append(p.hire_date.strftime("%Y%m%d") if p.hire_date else " " * 8)
    buf.append(p.employment_status[:1] or "A")
    for amt in (
        p.deferral_pretax, p.deferral_roth, p.catchup_pretax, p.catchup_roth,
        p.loan_repayment, p.employer_match, p.after_tax_contribution,
    ):
        buf.append(_fixed_money(amt, width=10, decimals=2))
    buf.append(_fixed_money(p.ytd_gross_wages, width=11, decimals=2))
    buf.append(_fixed_money(p.period_gross_wages, width=11, decimals=2))
    buf.append(_fixed_money(p.period_hours, width=8, decimals=2))
    line = "".join(buf)
    # Detail records are wider than 80. Pad all records to 172 chars
    # so a downstream SFTP partner can confidently parse as fixed-width.
    return line.ljust(172)[:172]


def _trailer(count: int, total_deferrals: Decimal) -> str:
    cnt = f"{count:07d}"
    tot = _fixed_money(total_deferrals, width=15, decimals=2)
    return f"T{cnt}{tot}".ljust(80)[:80]


def _fixed_money(value, width: int, decimals: int) -> str:  # type: ignore[no-untyped-def]
    """Zero-padded fixed-decimal number. Negative encoded with leading minus."""
    d = Decimal(str(value or "0")).quantize(Decimal(10) ** -decimals)
    sign = "-" if d < 0 else ""
    abs_str = f"{abs(d):.{decimals}f}".replace(".", "")
    padded = (sign + abs_str).rjust(width, "0")
    return padded[-width:]
