"""Imputed income calculation audit.

Imputed income = value of non-cash benefits that must be added to
taxable wages. Common sources:

  1. Group term life (GTL) coverage over $50,000
     IRS Table I: age-based rate per $1,000 over $50K, per month
  2. Domestic partner (DP) benefits
     Employer-paid premium for non-spouse/non-tax-dependent partner
  3. Personal use of company auto / fleet vehicle
     IRS cents-per-mile or lease-value tables
  4. Moving expense reimbursements (post-TCJA: all taxable for most)
  5. Employee discounts over safe-harbor threshold

Output: per-employee imputed income recap + findings on missed or
miscalculated items.

Finding codes:
  GTL_OVER_50K_NOT_IMPUTED        employee has > $50K GTL, $0 imputed
  GTL_RATE_WRONG                  Table I rate doesn't match age bracket
  DP_BENEFIT_NOT_IMPUTED          DP enrolled, employer premium not imputed
  AUTO_FRINGE_MISSING             company auto on file, no imputed income
  MOVING_EXPENSE_NOT_TAXED        moving reimb paid as non-taxable (post-TCJA rule)
  IMPUTED_INCOME_NO_FICA          imputed income added but not subject to FICA
  NEGATIVE_IMPUTED                imputed income < 0 (data error)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

_GTL_BASIC_EXCLUSION = Decimal("50000")


# IRS Table I: monthly cost per $1,000 of coverage over $50K, by age.
_TABLE_I: list[tuple[int, Decimal]] = [
    (24, Decimal("0.05")),
    (29, Decimal("0.06")),
    (34, Decimal("0.08")),
    (39, Decimal("0.09")),
    (44, Decimal("0.10")),
    (49, Decimal("0.15")),
    (54, Decimal("0.23")),
    (59, Decimal("0.43")),
    (64, Decimal("0.66")),
    (69, Decimal("1.27")),
    (999, Decimal("2.06")),
]


def _table_i_rate(age: int) -> Decimal:
    for bracket_max, rate in _TABLE_I:
        if age <= bracket_max:
            return rate
    return _TABLE_I[-1][1]


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class ImputedAudit:
    employee_id: str
    gtl_coverage: Decimal
    gtl_imputed: Decimal
    dp_enrolled: bool
    dp_employer_premium: Decimal
    dp_imputed: Decimal
    auto_fringe_declared: bool
    auto_imputed: Decimal
    moving_reimb: Decimal
    moving_taxed: Decimal
    imputed_fica_taxable: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ImputedIncomeReport:
    client_id: str
    tax_year: int
    as_of: date
    employees: list[ImputedAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for e in self.employees if e.findings)


class PrismHRReader(Protocol):
    async def list_employees_with_fringe_benefits(
        self, client_id: str, tax_year: int
    ) -> list[dict]:
        """Rows: {employeeId, age, gtlCoverageAmount, gtlImputedYtd,
        dpEnrolled, dpEmployerPremium, dpImputedYtd,
        hasCompanyAuto, autoImputedYtd,
        movingReimbYtd, movingReimbTaxedYtd,
        imputedFicaTaxableYtd}"""
        ...


async def run_imputed_income_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    tax_year: int,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
) -> ImputedIncomeReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))
    rows = await reader.list_employees_with_fringe_benefits(client_id, tax_year)

    audits: list[ImputedAudit] = []
    for row in rows:
        eid = str(row.get("employeeId") or "")
        age = int(row.get("age") or 0)
        gtl_cov = _dec(row.get("gtlCoverageAmount"))
        gtl_imp = _dec(row.get("gtlImputedYtd"))
        dp = bool(row.get("dpEnrolled"))
        dp_prem = _dec(row.get("dpEmployerPremium"))
        dp_imp = _dec(row.get("dpImputedYtd"))
        has_auto = bool(row.get("hasCompanyAuto"))
        auto_imp = _dec(row.get("autoImputedYtd"))
        moving = _dec(row.get("movingReimbYtd"))
        moving_taxed = _dec(row.get("movingReimbTaxedYtd"))
        imp_fica = _dec(row.get("imputedFicaTaxableYtd"))

        audit = ImputedAudit(
            employee_id=eid,
            gtl_coverage=gtl_cov,
            gtl_imputed=gtl_imp,
            dp_enrolled=dp,
            dp_employer_premium=dp_prem,
            dp_imputed=dp_imp,
            auto_fringe_declared=has_auto,
            auto_imputed=auto_imp,
            moving_reimb=moving,
            moving_taxed=moving_taxed,
            imputed_fica_taxable=imp_fica,
        )

        # GTL over $50K
        if gtl_cov > _GTL_BASIC_EXCLUSION:
            over = gtl_cov - _GTL_BASIC_EXCLUSION
            if gtl_imp <= tol:
                audit.findings.append(
                    Finding(
                        "GTL_OVER_50K_NOT_IMPUTED",
                        "critical",
                        f"Employee {eid} has ${gtl_cov} GTL coverage "
                        f"(${over} over $50K) but ${gtl_imp} imputed YTD.",
                    )
                )
            elif age > 0:
                rate = _table_i_rate(age)
                # Rough annual expected: (over/1000) × rate × 12
                expected_annual = (
                    (over / Decimal("1000")) * rate * Decimal("12")
                ).quantize(Decimal("0.01"))
                if (gtl_imp - expected_annual).copy_abs() > expected_annual * Decimal("0.15"):
                    audit.findings.append(
                        Finding(
                            "GTL_RATE_WRONG",
                            "warning",
                            f"Age {age}: Table I annual expected ≈ "
                            f"${expected_annual}, imputed ${gtl_imp}.",
                        )
                    )

        # Domestic partner
        if dp and dp_prem > 0 and dp_imp <= tol:
            audit.findings.append(
                Finding(
                    "DP_BENEFIT_NOT_IMPUTED",
                    "critical",
                    f"DP enrolled with employer premium ${dp_prem} but "
                    f"${dp_imp} imputed.",
                )
            )

        # Auto fringe
        if has_auto and auto_imp <= tol:
            audit.findings.append(
                Finding(
                    "AUTO_FRINGE_MISSING",
                    "warning",
                    f"Company auto on file for {eid} but no imputed income "
                    f"(cents-per-mile or lease-value calc).",
                )
            )

        # Moving expense (post-TCJA: fully taxable except military)
        if moving > 0 and moving_taxed < moving - tol:
            audit.findings.append(
                Finding(
                    "MOVING_EXPENSE_NOT_TAXED",
                    "critical",
                    f"Moving reimb ${moving} but only ${moving_taxed} taxed. "
                    f"Post-TCJA all moving is taxable (except active military).",
                )
            )

        # FICA on imputed income
        total_imputed = gtl_imp + dp_imp + auto_imp + moving_taxed
        if total_imputed > 0 and imp_fica + tol < total_imputed:
            audit.findings.append(
                Finding(
                    "IMPUTED_INCOME_NO_FICA",
                    "warning",
                    f"Total imputed ${total_imputed} but only ${imp_fica} "
                    f"subject to FICA. Most imputed income is FICA-subject.",
                )
            )

        if gtl_imp < 0 or dp_imp < 0 or auto_imp < 0:
            audit.findings.append(
                Finding(
                    "NEGATIVE_IMPUTED",
                    "critical",
                    "Negative imputed-income value on record; data error.",
                )
            )

        audits.append(audit)

    return ImputedIncomeReport(
        client_id=client_id,
        tax_year=tax_year,
        as_of=today,
        employees=audits,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
