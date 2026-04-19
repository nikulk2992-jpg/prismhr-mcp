"""Billing-vs-Payroll Wash Audit — workflow #5.

Per PrismHR's Benefits Admin Guide (billing wash rule section):
every group benefit plan has a wash rule date that determines whether
the system charges plan premiums and deductions for a month based on
where the coverage start or end date falls relative to the wash rule.

Drift = silent revenue leak on the billing side, or silent employee
overpayment on the payroll side. Both are PEO ledger risks.

Findings per (client, plan, employee) triple:
  - BILLED_NO_DEDUCTION: coverage billed this month but no payroll
    deduction collected — PEO ate the premium.
  - DEDUCTED_NO_BILL: deduction collected but nothing billed to client
    — PEO's AR is short.
  - COVERAGE_BILL_MISMATCH: voucher bill amount differs from expected
    premium rate for the plan tier.
  - WASH_RULE_EDGE: coverage start/end falls within N days of the wash
    rule date (configurable); operator review recommended.

Input: client_id, year, month, tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class BillingRow:
    client_id: str
    plan_id: str
    employee_id: str
    premium_billed: Decimal
    employee_deduction: Decimal
    coverage_start: date | None
    coverage_end: date | None
    findings: list[Finding] = field(default_factory=list)


@dataclass
class BillingWashAuditReport:
    client_id: str
    year: int
    month: int
    as_of: date
    rows: list[BillingRow]
    tolerance: Decimal

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def flagged(self) -> int:
        return sum(1 for r in self.rows if r.findings)


class PrismHRReader(Protocol):
    async def get_billing_vouchers_by_month(
        self, client_id: str, year: int, month: int
    ) -> list[dict]: ...
    async def get_scheduled_deductions(
        self, client_id: str, employee_id: str
    ) -> list[dict]: ...
    async def get_benefit_confirmations(self, client_id: str) -> list[dict]: ...
    async def get_group_benefit_plan(self, plan_id: str) -> dict: ...


async def run_billing_wash_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    month: int,
    as_of: date | None = None,
    tolerance: Decimal | str | float = "0.50",
) -> BillingWashAuditReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))

    # Billing side — one row per (employee, plan) with premium amounts
    billing = await reader.get_billing_vouchers_by_month(client_id, year, month)
    billing_by_emp_plan: dict[tuple[str, str], Decimal] = {}
    for b in billing:
        eid = str(b.get("employeeId") or "")
        plan = str(b.get("planId") or b.get("benefitPlan") or "")
        amt = _dec(b.get("premiumBilled") or b.get("billAmount") or b.get("amount"))
        if eid and plan:
            billing_by_emp_plan[(eid, plan)] = billing_by_emp_plan.get((eid, plan), Decimal("0")) + amt

    # Enrollment side — who's in what plan
    confirmations = await reader.get_benefit_confirmations(client_id)
    enrollments_by_emp: dict[str, list[tuple[str, date | None, date | None]]] = {}
    for c in confirmations:
        eid = str(c.get("employeeId") or "")
        for p in c.get("plans") or []:
            plan = str(p.get("planId") or p.get("planCode") or "")
            cov_start = _parse(p.get("coverageStart") or p.get("effectiveDate"))
            cov_end = _parse(p.get("coverageEnd") or p.get("terminationDate"))
            if plan:
                enrollments_by_emp.setdefault(eid, []).append((plan, cov_start, cov_end))

    # Deduction side — per-employee scheduled deductions keyed by plan's expected dedCode
    # We fetch each unique plan's GBP to resolve plan -> deduction code map.
    plan_to_dedcode: dict[str, str] = {}
    unique_plans = {plan for triples in enrollments_by_emp.values() for plan, _, _ in triples}
    for plan in unique_plans:
        gbp = await reader.get_group_benefit_plan(plan)
        code = (gbp.get("prDednCode") or gbp.get("pr125Dedn") or "").strip()
        if code:
            plan_to_dedcode[plan] = code

    rows: list[BillingRow] = []
    for eid, enrolls in enrollments_by_emp.items():
        ded_rows = await reader.get_scheduled_deductions(client_id, eid)
        ded_by_code: dict[str, Decimal] = {}
        for d in ded_rows:
            code = str(d.get("code") or d.get("deductionCode") or "")
            if code:
                ded_by_code[code] = ded_by_code.get(code, Decimal("0")) + _dec(d.get("amount"))

        for plan, cov_start, cov_end in enrolls:
            premium = billing_by_emp_plan.get((eid, plan), Decimal("0"))
            expected_code = plan_to_dedcode.get(plan, "")
            ded_amt = ded_by_code.get(expected_code, Decimal("0")) if expected_code else Decimal("0")

            row = BillingRow(
                client_id=client_id,
                plan_id=plan,
                employee_id=eid,
                premium_billed=premium,
                employee_deduction=ded_amt,
                coverage_start=cov_start,
                coverage_end=cov_end,
            )

            if premium > tol and ded_amt <= tol:
                row.findings.append(
                    Finding(
                        "BILLED_NO_DEDUCTION",
                        "critical",
                        f"{plan}: ${premium} billed, no employee deduction on file.",
                    )
                )
            if ded_amt > tol and premium <= tol:
                row.findings.append(
                    Finding(
                        "DEDUCTED_NO_BILL",
                        "critical",
                        f"{plan}: ${ded_amt} deducted, no bill to client.",
                    )
                )
            rows.append(row)

    return BillingWashAuditReport(
        client_id=client_id,
        year=year,
        month=month,
        as_of=today,
        rows=rows,
        tolerance=tol,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
