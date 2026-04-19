"""G/L Template Integrity — workflow #36.

Per PrismHR's Accounting chapter: every pay code, deduction code,
and benefit plan needs a GL account mapping in the client's GL
template. A missing mapping sends the transaction to a wash or
suspense account, silently corrupting the client's books.

Findings:
  - UNMAPPED_PAY_CODE: pay code in use with no GL account.
  - UNMAPPED_DEDUCTION_CODE: same for deduction.
  - UNMAPPED_BENEFIT_PLAN: benefit plan missing accrual + expense
    accounts.
  - DUPLICATE_MAPPING: two codes point to the same GL account with
    different intent (warning — check the template).
  - NO_GL_TEMPLATE: client has no template assigned.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class GLIntegrityReport:
    client_id: str
    as_of: date
    template_id: str
    pay_codes_unmapped: list[str]
    deduction_codes_unmapped: list[str]
    benefit_plans_unmapped: list[str]
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)


class PrismHRReader(Protocol):
    async def get_client_gl_template(self, client_id: str) -> dict: ...
    async def list_active_pay_codes(self, client_id: str) -> list[str]: ...
    async def list_active_deduction_codes(self, client_id: str) -> list[str]: ...
    async def list_active_benefit_plans(self, client_id: str) -> list[str]: ...
    async def get_gl_mappings(
        self, client_id: str, template_id: str
    ) -> dict[str, dict[str, str]]: ...


async def run_gl_template_integrity(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
) -> GLIntegrityReport:
    today = as_of or date.today()
    template = await reader.get_client_gl_template(client_id)
    template_id = str(template.get("templateId") or template.get("id") or "")

    report = GLIntegrityReport(
        client_id=client_id,
        as_of=today,
        template_id=template_id,
        pay_codes_unmapped=[],
        deduction_codes_unmapped=[],
        benefit_plans_unmapped=[],
    )

    if not template_id:
        report.findings.append(
            Finding("NO_GL_TEMPLATE", "critical", "Client has no GL template assigned.")
        )
        return report

    mappings = await reader.get_gl_mappings(client_id, template_id)
    # mappings shape: {"payCodes": {code: gl_account}, "deductions": {...}, "benefitPlans": {...}}

    pay_codes = await reader.list_active_pay_codes(client_id)
    ded_codes = await reader.list_active_deduction_codes(client_id)
    plans = await reader.list_active_benefit_plans(client_id)

    pay_map = mappings.get("payCodes") or {}
    ded_map = mappings.get("deductions") or {}
    plan_map = mappings.get("benefitPlans") or {}

    for code in pay_codes:
        if code not in pay_map or not pay_map[code]:
            report.pay_codes_unmapped.append(code)
    for code in ded_codes:
        if code not in ded_map or not ded_map[code]:
            report.deduction_codes_unmapped.append(code)
    for plan in plans:
        if plan not in plan_map or not plan_map[plan]:
            report.benefit_plans_unmapped.append(plan)

    if report.pay_codes_unmapped:
        report.findings.append(
            Finding(
                "UNMAPPED_PAY_CODE",
                "critical",
                f"{len(report.pay_codes_unmapped)} active pay codes have no GL account: {report.pay_codes_unmapped[:5]}.",
            )
        )
    if report.deduction_codes_unmapped:
        report.findings.append(
            Finding(
                "UNMAPPED_DEDUCTION_CODE",
                "critical",
                f"{len(report.deduction_codes_unmapped)} active deduction codes have no GL account: {report.deduction_codes_unmapped[:5]}.",
            )
        )
    if report.benefit_plans_unmapped:
        report.findings.append(
            Finding(
                "UNMAPPED_BENEFIT_PLAN",
                "critical",
                f"{len(report.benefit_plans_unmapped)} active benefit plans have no GL account: {report.benefit_plans_unmapped[:5]}.",
            )
        )

    # Duplicate mapping detection
    reverse: dict[str, list[str]] = defaultdict(list)
    for code, acct in pay_map.items():
        if acct:
            reverse[str(acct)].append(f"pay:{code}")
    for code, acct in ded_map.items():
        if acct:
            reverse[str(acct)].append(f"ded:{code}")
    for plan, acct in plan_map.items():
        if acct:
            reverse[str(acct)].append(f"plan:{plan}")
    for acct, codes in reverse.items():
        if len(codes) > 1:
            report.findings.append(
                Finding(
                    "DUPLICATE_MAPPING",
                    "warning",
                    f"GL account {acct} mapped from multiple codes: {codes}.",
                )
            )

    return report
