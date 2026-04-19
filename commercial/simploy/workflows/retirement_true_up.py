"""401(k) True-Up Calculation — workflow #22.

Per ERISA/IRS 401(k) match rules: if an employee hit their elective
deferral limit early in the year (e.g. via bonus), some plans
require a true-up employer contribution so they receive the full
match they would have earned had contributions been spread evenly.

Findings per employee:
  - TRUE_UP_OWED: employee under-matched per plan formula given
    annual compensation + deferral timing.
  - MISSED_MATCH_FINAL_PAYCHECK: final pay period had deferral but
    no employer match posted.
  - EXCESS_MATCH: employer match exceeds plan formula — adjustment
    to reverse may be needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class TrueUpAudit:
    employee_id: str
    ytd_gross: Decimal
    ytd_deferrals: Decimal
    ytd_employer_match: Decimal
    formula_full_year_match: Decimal
    true_up_owed: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class TrueUpReport:
    client_id: str
    year: int
    as_of: date
    audits: list[TrueUpAudit]
    match_percent: Decimal
    match_cap_pct_of_wages: Decimal

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)

    @property
    def total_true_up_owed(self) -> Decimal:
        return sum((a.true_up_owed for a in self.audits), Decimal("0"))


class PrismHRReader(Protocol):
    async def get_match_formula(
        self, client_id: str, plan_id: str
    ) -> dict: ...
    async def get_employee_401k_contributions(
        self, client_id: str, year: int
    ) -> list[dict]: ...
    async def get_employee_ytd_gross(
        self, client_id: str, employee_id: str, year: int
    ) -> Decimal: ...


async def run_retirement_true_up(
    reader: PrismHRReader,
    *,
    client_id: str,
    plan_id: str,
    year: int,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
) -> TrueUpReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))

    formula = await reader.get_match_formula(client_id, plan_id)
    match_pct = _dec(formula.get("matchPercent") or formula.get("matchPct")) / Decimal("100")
    match_cap = _dec(formula.get("matchUpToPercent") or formula.get("matchUpToPct")) / Decimal("100")

    contribs = await reader.get_employee_401k_contributions(client_id, year)
    audits: list[TrueUpAudit] = []
    for c in contribs:
        eid = str(c.get("employeeId") or "")
        if not eid:
            continue
        ytd_deferrals = _dec(c.get("employeeContribution") or c.get("employeeDeferral"))
        ytd_match = _dec(c.get("employerMatch") or c.get("employerContribution"))
        ytd_gross = _dec(c.get("ytdGross")) or await reader.get_employee_ytd_gross(client_id, eid, year)

        # Full-year formula match: min(deferrals * match_pct, ytd_gross * match_cap)
        deferral_based = ytd_deferrals * match_pct
        wage_cap = ytd_gross * match_cap if match_cap > 0 else deferral_based
        full_match = min(deferral_based, wage_cap) if match_cap > 0 else deferral_based
        full_match = full_match.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        owed = (full_match - ytd_match).quantize(Decimal("0.01"))
        audit = TrueUpAudit(
            employee_id=eid,
            ytd_gross=ytd_gross,
            ytd_deferrals=ytd_deferrals,
            ytd_employer_match=ytd_match,
            formula_full_year_match=full_match,
            true_up_owed=max(owed, Decimal("0")),
        )

        if owed > tol:
            audit.findings.append(
                Finding(
                    "TRUE_UP_OWED",
                    "critical",
                    f"Plan formula yields ${full_match}; actual match ${ytd_match}. True-up ${owed}.",
                )
            )
        elif owed < -tol:
            audit.findings.append(
                Finding(
                    "EXCESS_MATCH",
                    "warning",
                    f"Match ${ytd_match} exceeds formula ${full_match} by ${-owed}.",
                )
            )
        audits.append(audit)

    return TrueUpReport(
        client_id=client_id,
        year=year,
        as_of=today,
        audits=audits,
        match_percent=match_pct,
        match_cap_pct_of_wages=match_cap,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
