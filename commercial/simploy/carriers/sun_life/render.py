"""Sun Life EDX renderer — pipe-delimited flat-file.

Format (simplified reference — exact field list varies per Sun Life
product line; operator maps the relevant fields via configuration):

  HDR|Simploy EDX Feed|<run_date>|<record_count>
  EMP|<sun_life_group_id>|<employee_id>|<ssn>|<first>|<last>|<dob>|<gender>|<hire_date>|<status>|<plan_code>|<coverage_effective>|<coverage_amount>|<weekly_salary>
  EMP|...
  TRL|<record_count>|<checksum>

Caller's Enrollment is never mutated.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..render import Enrollment


@dataclass(frozen=True)
class SunLifeCompanionGuide:
    group_id: str = "SIMPLOY-SL-TEST"
    feed_name: str = "Simploy EDX Feed"
    delimiter: str = "|"
    include_hdhp_flag: bool = False
    production: bool = False


DEFAULT_GUIDE = SunLifeCompanionGuide()


def render_sun_life_edx(
    enrollment: Enrollment,
    *,
    guide: SunLifeCompanionGuide | None = None,
) -> str:
    guide = guide or DEFAULT_GUIDE
    working = copy.deepcopy(enrollment)
    d = guide.delimiter

    lines: list[str] = []
    run_date = working.transaction_date.strftime("%Y%m%d")
    emp_lines: list[str] = []

    for enrollee in working.enrollees:
        # One record per (employee, coverage)
        for cov in enrollee.coverages:
            weekly = (
                (cov.employer_contribution or Decimal("0"))
                + (cov.employee_contribution or Decimal("0"))
            )
            line = d.join([
                "EMP",
                guide.group_id,
                enrollee.member_id,
                enrollee.ssn or "",
                enrollee.first_name,
                enrollee.last_name,
                enrollee.dob.strftime("%Y%m%d") if enrollee.dob else "",
                enrollee.gender,
                enrollee.hire_date.strftime("%Y%m%d") if enrollee.hire_date else "",
                enrollee.employment_status,
                cov.plan_code,
                cov.effective_date.strftime("%Y%m%d"),
                str(cov.employer_contribution or "0"),
                str(weekly),
            ])
            emp_lines.append(line)

    header = d.join([
        "HDR",
        guide.feed_name,
        run_date,
        str(len(emp_lines)),
        "P" if guide.production else "T",
    ])
    trailer = d.join([
        "TRL",
        str(len(emp_lines)),
        _checksum(emp_lines),
    ])
    lines.append(header)
    lines.extend(emp_lines)
    lines.append(trailer)
    return "\n".join(lines) + "\n"


def _checksum(lines: list[str]) -> str:
    """Simple checksum: sum of character codes mod 999999, zero-padded."""
    total = sum(ord(c) for line in lines for c in line) % 999999
    return f"{total:06d}"
