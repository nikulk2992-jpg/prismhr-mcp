"""FSA/HSA Contribution Limit Tracker — workflow #17.

Per PrismHR's Section 125 Plans chapter + IRS rules, FSA and HSA
plans have strict annual contribution limits. Employees near or over
the limit trigger payroll-deduction stoppage + potential IRS penalty.

2026 IRS limits (operators override via config):
  FSA (healthcare):       $3,300
  FSA dependent care:     $5,000 (married filing jointly)
  HSA individual:         $4,400
  HSA family:             $8,850
  HSA catch-up (55+):     $1,000

Findings per enrolled employee + plan:
  - OVER_LIMIT: YTD deductions > IRS limit.
  - APPROACHING_LIMIT: YTD deductions > 90% of limit.
  - PROJECTED_OVERAGE: annualized pace > limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str


# 2026 IRS limits, overridable per call
IRS_LIMITS_2026 = {
    "FSA_HEALTHCARE": Decimal("3300"),
    "FSA_DEPENDENT_CARE": Decimal("5000"),
    "HSA_INDIVIDUAL": Decimal("4400"),
    "HSA_FAMILY": Decimal("8850"),
    "HSA_CATCHUP_55PLUS": Decimal("1000"),
}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class EmployeeLimitAudit:
    employee_id: str
    plan_type: str
    plan_id: str
    ytd_contribution: Decimal
    applicable_limit: Decimal
    projected_annual: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class FSAHSATrackerReport:
    client_id: str
    year: int
    as_of: date
    audits: list[EmployeeLimitAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def get_section125_plans(
        self, client_id: str, plan_type: str
    ) -> list[dict]: ...
    async def get_flex_enrollees(
        self, client_id: str, plan_id: str
    ) -> list[dict]: ...
    async def get_ytd_deduction(
        self, client_id: str, employee_id: str, deduction_code: str, year: int
    ) -> Decimal: ...


async def run_fsa_hsa_limit_tracker(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    as_of: date | None = None,
    limits: dict[str, Decimal] | None = None,
) -> FSAHSATrackerReport:
    today = as_of or date.today()
    lim = limits or IRS_LIMITS_2026

    audits: list[EmployeeLimitAudit] = []

    # Section 125 plans by type. 'H' = HSA, 'F' = FSA, 'S' = Premium Only.
    # Skip POP — no contribution limit.
    for plan_type_code, plan_type_name in (("H", "HSA"), ("F", "FSA")):
        plans = await reader.get_section125_plans(client_id, plan_type_code)
        for plan in plans:
            plan_id = str(plan.get("planId") or "")
            ded_code = str(plan.get("deductionCode") or plan.get("prDednCode") or "")
            if not plan_id or not ded_code:
                continue

            enrollees = await reader.get_flex_enrollees(client_id, plan_id)
            for e in enrollees:
                eid = str(e.get("employeeId") or "")
                if not eid:
                    continue
                ytd = await reader.get_ytd_deduction(client_id, eid, ded_code, year)

                # Pick the right limit
                coverage_tier = str(e.get("coverageTier") or "").upper()
                if plan_type_name == "HSA":
                    limit = lim.get("HSA_FAMILY" if coverage_tier in {"FAM", "FAMILY", "ESP", "ECH"} else "HSA_INDIVIDUAL", Decimal("4400"))
                else:
                    limit = lim.get("FSA_HEALTHCARE", Decimal("3300"))

                # Annualize projection based on year-to-date fraction
                day_of_year = (today - date(year, 1, 1)).days + 1
                fraction = Decimal(day_of_year) / Decimal("365")
                projected = ytd / fraction if fraction > 0 else ytd

                audit = EmployeeLimitAudit(
                    employee_id=eid,
                    plan_type=plan_type_name,
                    plan_id=plan_id,
                    ytd_contribution=ytd,
                    applicable_limit=limit,
                    projected_annual=projected.quantize(Decimal("0.01")),
                )

                if ytd > limit:
                    audit.findings.append(
                        Finding(
                            "OVER_LIMIT",
                            "critical",
                            f"YTD ${ytd} exceeds {plan_type_name} limit ${limit}.",
                        )
                    )
                elif ytd > limit * Decimal("0.9"):
                    audit.findings.append(
                        Finding(
                            "APPROACHING_LIMIT",
                            "warning",
                            f"YTD ${ytd} is {(ytd/limit*100).quantize(Decimal('0.1'))}% of limit.",
                        )
                    )
                elif projected > limit:
                    audit.findings.append(
                        Finding(
                            "PROJECTED_OVERAGE",
                            "warning",
                            f"Annualized pace ${audit.projected_annual} would exceed limit ${limit}.",
                        )
                    )
                audits.append(audit)

    return FSAHSATrackerReport(
        client_id=client_id, year=year, as_of=today, audits=audits
    )
