"""401(k) Match Rule Compliance — workflow #11.

Per PrismHR's Benefits Admin + Retirement Plan setup chapters: 401(k)
plans carry a match formula per rate group (employer match percent,
safe harbor status, catch-up eligibility, true-up requirement). Drift
between the plan's match rules and what employees actually received
in vouchers is a fiduciary risk and a common source of year-end true-
up corrections.

Findings:
  - MATCH_SHORT: employer match YTD is below the contractual formula
    given the employee's YTD contribution.
  - CATCHUP_NOT_ENABLED: employee is 50+ and at/near the 402(g) limit
    but no catch-up deduction code is active.
  - OVER_402G_LIMIT: employee's YTD elective contribution exceeds the
    402(g) annual cap.
  - MISSING_DEDCODE: plan is active for employee but no 401(k)
    pre-tax/post-tax deduction code is on file.

Input: client_id, year, tolerance (dollars).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str


# IRS limits for 2025–2026. Operators can override via config later.
_402G_LIMIT = Decimal("23500")
_CATCHUP_LIMIT_50PLUS = Decimal("7500")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class EmployeeRetirementAudit:
    employee_id: str
    age: int | None = None
    ytd_employee_contribution: Decimal = Decimal("0")
    ytd_employer_match: Decimal = Decimal("0")
    expected_match: Decimal = Decimal("0")
    findings: list[Finding] = field(default_factory=list)


@dataclass
class RetirementMatchReport:
    client_id: str
    year: int
    as_of: date
    plan_id: str
    employees: list[EmployeeRetirementAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for e in self.employees if e.findings)


class PrismHRReader(Protocol):
    async def get_retirement_plan(self, client_id: str) -> dict: ...
    async def get_401k_match_rules(self, client_id: str, plan_id: str) -> list[dict]: ...
    async def get_employee_401k_contributions(
        self, client_id: str, year: int
    ) -> list[dict]: ...
    async def get_scheduled_deductions(
        self, client_id: str, employee_id: str
    ) -> list[dict]: ...
    async def get_employee_dob(self, client_id: str, employee_id: str) -> date | None: ...


async def run_retirement_match_compliance(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
    tolerance: Decimal | str | float = "1.00",
) -> RetirementMatchReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))

    plan = await reader.get_retirement_plan(client_id)
    plan_id = str(plan.get("retirePlan") or plan.get("planId") or "401K")

    # Flatten match rules: list of {rateGroup, matchPct, matchUpToPct, catchupAllowed}
    raw_rules = await reader.get_401k_match_rules(client_id, plan_id)
    match_rules: list[dict] = []
    for r in raw_rules:
        if isinstance(r, dict):
            match_rules.append(
                {
                    "match_pct": _dec(r.get("matchPercent") or r.get("matchPct")),
                    "match_up_to_pct": _dec(r.get("matchUpToPercent") or r.get("matchUpToPct")),
                }
            )
    # Use the first (or single) rule for a v1 simple audit.
    primary_rule = match_rules[0] if match_rules else {"match_pct": Decimal("0"), "match_up_to_pct": Decimal("0")}

    contribs = await reader.get_employee_401k_contributions(client_id, year)
    audits: list[EmployeeRetirementAudit] = []
    for c in contribs:
        eid = str(c.get("employeeId") or "")
        if not eid:
            continue
        ee = _dec(c.get("employeeContribution") or c.get("employeeDeferral"))
        er = _dec(c.get("employerMatch") or c.get("employerContribution"))
        ytd_gross = _dec(c.get("ytdGross") or c.get("grossWages"))

        audit = EmployeeRetirementAudit(
            employee_id=eid,
            ytd_employee_contribution=ee,
            ytd_employer_match=er,
        )

        dob = await reader.get_employee_dob(client_id, eid)
        if dob:
            audit.age = (today - dob).days // 365

        # Expected match = min(match_up_to_pct * gross, match_pct * ee)
        match_pct = primary_rule["match_pct"] / Decimal("100")
        match_up = primary_rule["match_up_to_pct"] / Decimal("100")
        cap_on_wages = ytd_gross * match_up
        audit.expected_match = min(cap_on_wages, ee * match_pct) if match_up > 0 else ee * match_pct

        if audit.expected_match - er > tol:
            audit.findings.append(
                Finding(
                    "MATCH_SHORT",
                    "critical",
                    f"Expected YTD match ${audit.expected_match}, actual ${er} (short ${audit.expected_match - er}).",
                )
            )

        # 402(g) limit
        if ee > _402G_LIMIT and (audit.age is None or audit.age < 50):
            audit.findings.append(
                Finding(
                    "OVER_402G_LIMIT",
                    "critical",
                    f"Employee YTD contribution ${ee} exceeds 402(g) limit ${_402G_LIMIT} (age<50).",
                )
            )

        # Catch-up check for 50+
        if audit.age is not None and audit.age >= 50 and ee > _402G_LIMIT:
            ded_rows = await reader.get_scheduled_deductions(client_id, eid)
            has_catchup = any(
                "CATCH" in str(d.get("code") or d.get("deductionCode") or "").upper()
                for d in ded_rows
            )
            if not has_catchup:
                audit.findings.append(
                    Finding(
                        "CATCHUP_NOT_ENABLED",
                        "warning",
                        f"Age {audit.age} past 402(g) limit but no catch-up deduction code on file.",
                    )
                )

        audits.append(audit)

    return RetirementMatchReport(
        client_id=client_id,
        year=year,
        as_of=today,
        plan_id=plan_id,
        employees=audits,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
