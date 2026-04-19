"""Benefits-Deduction Discrepancy Audit — workflow #3.

Cross-references benefit enrollments against scheduled deductions at a
client. Catches the silent leak where an employee is enrolled in a
plan but no deduction was ever set up — the PEO bills the carrier for
the coverage while the employee never pays their premium.

Findings:
  - ENROLLED_NO_DEDUCTION: employee is enrolled but has no deduction
    code on file for that plan.
  - ZERO_AMOUNT_DEDUCTION: deduction exists but the amount is zero.
  - ORPHAN_DEDUCTION: benefit-related deduction on file with no matching
    active enrollment.

Input: client_id.
Output: per-employee list of discrepancies with severity.

Data sources (all verified reads):
  - benefits.v1.getBenefitConfirmationList
  - benefits.v1.getActiveBenefitPlans
  - employee.v1.getScheduledDeductions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


Severity = str  # "critical" | "warning" | "info"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class EmployeeBenefitAudit:
    employee_id: str
    first_name: str
    last_name: str
    enrolled_plans: list[str] = field(default_factory=list)
    deduction_codes: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)


@dataclass
class BenefitsDeductionAuditReport:
    client_id: str
    as_of: date
    employees: list[EmployeeBenefitAudit]

    @property
    def total(self) -> int:
        return len(self.employees)

    @property
    def passed(self) -> int:
        return sum(1 for e in self.employees if e.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed


class PrismHRReader(Protocol):
    """Minimal read surface for this workflow."""

    async def get_active_benefit_plans(self, client_id: str) -> list[dict]: ...
    async def get_benefit_confirmations(self, client_id: str) -> list[dict]: ...
    async def get_scheduled_deductions(
        self, client_id: str, employee_id: str
    ) -> list[dict]: ...


async def run_benefits_deduction_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
) -> BenefitsDeductionAuditReport:
    """Sweep enrollments vs deductions for a client."""
    today = as_of or date.today()

    # Step 1: build the plan-code -> expected-deduction-codes map.
    plans = await reader.get_active_benefit_plans(client_id)
    plan_deduction_map: dict[str, set[str]] = {}
    all_benefit_deduction_codes: set[str] = set()
    for p in plans:
        code = p.get("planId") or p.get("planCode") or ""
        if not code:
            continue
        expected = p.get("expectedDeductionCodes") or []
        if isinstance(expected, str):
            expected = [expected]
        codes = {str(x) for x in expected if x}
        plan_deduction_map[code] = codes
        all_benefit_deduction_codes.update(codes)

    # Step 2: iterate employee enrollments.
    confirmations = await reader.get_benefit_confirmations(client_id)
    audits: list[EmployeeBenefitAudit] = []
    for conf in confirmations:
        eid = str(conf.get("employeeId") or "")
        if not eid:
            continue
        enrolled = [
            str(p.get("planId") or p.get("planCode") or "")
            for p in (conf.get("plans") or [])
            if p.get("planId") or p.get("planCode")
        ]
        enrolled = [p for p in enrolled if p]

        ded_rows = await reader.get_scheduled_deductions(client_id, eid)
        ded_by_code: dict[str, dict] = {}
        for d in ded_rows:
            code = str(d.get("code") or d.get("deductionCode") or "")
            if code:
                ded_by_code[code] = d

        audit = EmployeeBenefitAudit(
            employee_id=eid,
            first_name=conf.get("firstName", ""),
            last_name=conf.get("lastName", ""),
            enrolled_plans=enrolled,
            deduction_codes=list(ded_by_code.keys()),
        )

        # Finding: ENROLLED_NO_DEDUCTION
        for plan in enrolled:
            expected_codes = plan_deduction_map.get(plan, set())
            if not expected_codes:
                # Plan has no known deduction mapping — cannot evaluate.
                continue
            if not any(c in ded_by_code for c in expected_codes):
                audit.findings.append(
                    Finding(
                        "ENROLLED_NO_DEDUCTION",
                        "critical",
                        f"Enrolled in {plan} (expects {sorted(expected_codes)}) but no matching deduction on file.",
                    )
                )
            else:
                # Finding: ZERO_AMOUNT_DEDUCTION
                for c in expected_codes:
                    row = ded_by_code.get(c)
                    if row is None:
                        continue
                    amt = row.get("amount") or row.get("deductionAmount")
                    try:
                        if amt is not None and float(amt) == 0:
                            audit.findings.append(
                                Finding(
                                    "ZERO_AMOUNT_DEDUCTION",
                                    "critical",
                                    f"Deduction {c} for plan {plan} exists but amount is 0.",
                                )
                            )
                    except (TypeError, ValueError):
                        continue

        # Finding: ORPHAN_DEDUCTION — benefit-looking deduction with no
        # matching enrollment.
        enrolled_expected: set[str] = set()
        for plan in enrolled:
            enrolled_expected.update(plan_deduction_map.get(plan, set()))
        for code in ded_by_code:
            if code in all_benefit_deduction_codes and code not in enrolled_expected:
                audit.findings.append(
                    Finding(
                        "ORPHAN_DEDUCTION",
                        "warning",
                        f"Deduction {code} on file but no matching enrollment for it.",
                    )
                )

        audits.append(audit)

    return BenefitsDeductionAuditReport(
        client_id=client_id,
        as_of=today,
        employees=audits,
    )
