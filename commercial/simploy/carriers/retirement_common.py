"""Shared dataclasses for 401(k) / retirement carrier feeds.

Voya, Empower, Fidelity all consume essentially the same data per
participant: deferral pre-tax, deferral Roth, catch-up, loan
repayment, gross wages, hours. They differ on exact field widths +
delimiter + ordering.

Keeping the payload format carrier-agnostic lets operators build
the data once upstream from PrismHR and fan out to multiple
recordkeepers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class ParticipantContribution:
    employee_id: str
    ssn: str
    first_name: str
    last_name: str
    dob: date | None
    hire_date: date | None
    termination_date: date | None = None
    employment_status: str = "A"
    division: str = ""
    ytd_gross_wages: Decimal = Decimal("0")
    period_gross_wages: Decimal = Decimal("0")
    period_hours: Decimal = Decimal("0")
    deferral_pretax: Decimal = Decimal("0")
    deferral_roth: Decimal = Decimal("0")
    catchup_pretax: Decimal = Decimal("0")
    catchup_roth: Decimal = Decimal("0")
    loan_repayment: Decimal = Decimal("0")
    employer_match: Decimal = Decimal("0")
    after_tax_contribution: Decimal = Decimal("0")


@dataclass
class RetirementFeed:
    plan_id: str
    client_id: str
    period_start: date
    period_end: date
    pay_date: date
    participants: list[ParticipantContribution] = field(default_factory=list)
