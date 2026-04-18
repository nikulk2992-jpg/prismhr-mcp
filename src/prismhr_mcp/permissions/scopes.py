"""Scope catalog — the single source of truth for what the MCP can request.

Every tool maps to at least one `Scope`. Scopes group into `ScopeCategory`
buckets that are shown to the user at consent time ("PrismHR Reads",
"Microsoft 365 Writes", etc.). Each spec also declares the concrete PrismHR
endpoints or Graph resources the scope permits — so the user knows exactly
what they're approving, not just a friendly label.

Adding a new tool? Update the `tools` field of the relevant ScopeSpec.
Adding a new scope? Update the `Scope` enum, add a `ScopeSpec`, and add to
the category order if it's a new bucket.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Scope(str, Enum):
    # ---- PrismHR read ----
    CLIENT_READ = "client:read"
    EMPLOYEE_READ = "employee:read"
    PAYROLL_READ = "payroll:read"
    BENEFITS_READ = "benefits:read"
    COMPLIANCE_READ = "compliance:read"
    BILLING_READ = "billing:read"

    # ---- PrismHR write (live data mutations) ----
    PAYROLL_WRITE = "payroll:write"

    # ---- Reporting ----
    REPORTS_GENERATE = "reports:generate"

    # ---- Microsoft 365 ----
    M365_EMAIL_SEND = "m365:email:send"
    M365_SHAREPOINT_READ = "m365:sharepoint:read"
    M365_SHAREPOINT_WRITE = "m365:sharepoint:write"
    M365_TEAMS_POST = "m365:teams:post"
    M365_OUTLOOK_CALENDAR = "m365:outlook:calendar"
    M365_OUTLOOK_TASKS = "m365:outlook:tasks"


class ScopeCategory(str, Enum):
    PRISMHR_READ = "PrismHR — Read"
    PRISMHR_WRITE = "PrismHR — Write (mutates live data)"
    REPORTING = "Branded Reporting"
    M365_READ = "Microsoft 365 — Read"
    M365_WRITE = "Microsoft 365 — Write"


CATEGORY_ORDER: list[ScopeCategory] = [
    ScopeCategory.PRISMHR_READ,
    ScopeCategory.REPORTING,
    ScopeCategory.M365_READ,
    ScopeCategory.M365_WRITE,
    ScopeCategory.PRISMHR_WRITE,
]


@dataclass(frozen=True)
class ScopeSpec:
    scope: Scope
    category: ScopeCategory
    label: str
    description: str
    risk: str  # "low" | "medium" | "high"
    recommended_default: bool
    endpoints: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    requires: tuple[Scope, ...] = field(default_factory=tuple)


# The canonical manifest. Order matters for UI display.
MANIFEST: tuple[ScopeSpec, ...] = (
    ScopeSpec(
        scope=Scope.CLIENT_READ,
        category=ScopeCategory.PRISMHR_READ,
        label="Read client directory",
        description="List PrismHR clients and read client master records.",
        risk="low",
        recommended_default=True,
        endpoints=(
            "/clientMaster/v1/getClientList",
            "/clientMaster/v1/getClientMaster",
        ),
        tools=("client_list",),
    ),
    ScopeSpec(
        scope=Scope.EMPLOYEE_READ,
        category=ScopeCategory.PRISMHR_READ,
        label="Read employee records",
        description="Read employee rosters, detail records, and employment status.",
        risk="low",
        recommended_default=True,
        endpoints=(
            "/employee/v1/getEmployeeList",
            "/employee/v1/getEmployee",
            "/employee/v1/getScheduledDeductions",
        ),
        tools=("client_employees", "client_employee", "client_employee_search"),
        requires=(Scope.CLIENT_READ,),  # search needs to enumerate clients first
    ),
    ScopeSpec(
        scope=Scope.PAYROLL_READ,
        category=ScopeCategory.PRISMHR_READ,
        label="Read payroll data",
        description="Pay vouchers, pay history, batch status, YTD values, billing totals.",
        risk="low",
        recommended_default=True,
        endpoints=(
            "/payroll/v1/getPayrollVouchersForEmployee",
            "/payroll/v1/getYearToDateValues",
            "/payroll/v1/getBatchListByDate",
            "/payroll/v1/getBillingCodeTotalsForBatch",
            "/payroll/v1/getBillingVouchersByBatch",
            "/employee/v1/getScheduledDeductions",
        ),
        tools=(
            "payroll_batch_status",
            "payroll_pay_history",
            "payroll_pay_group_check",
            "payroll_deduction_conflicts",
            "payroll_overtime_anomalies",
            "payroll_superbatch_status",
            "payroll_register_reconcile",
        ),
    ),
    ScopeSpec(
        scope=Scope.BENEFITS_READ,
        category=ScopeCategory.PRISMHR_READ,
        label="Read benefits & deductions",
        description="Benefit elections, deduction schedules, PTO, dependents, ACA.",
        risk="low",
        recommended_default=True,
        endpoints=(
            "/benefits/v1/getBenefitElectionDetails",
            "/benefits/v1/getClientBenefitPlans",
            "/benefits/v1/getPaidTimeOff",
            "/benefits/v1/getMonthlyACAInfo",
        ),
        tools=(),  # Phase 3 populates
    ),
    ScopeSpec(
        scope=Scope.COMPLIANCE_READ,
        category=ScopeCategory.PRISMHR_READ,
        label="Read compliance data",
        description="W2 status, garnishments, state tax setup, 941 reconciliation, I-9 audit.",
        risk="low",
        recommended_default=True,
        tools=(),
    ),
    ScopeSpec(
        scope=Scope.BILLING_READ,
        category=ScopeCategory.PRISMHR_READ,
        label="Read client billing & financials",
        description="Billing rates, invoice summaries, AR status, employer tax liability.",
        risk="low",
        recommended_default=True,
        tools=(),
    ),
    ScopeSpec(
        scope=Scope.REPORTS_GENERATE,
        category=ScopeCategory.REPORTING,
        label="Generate branded reports",
        description="Render Simploy-branded PDF/XLSX/HTML/DOCX from PrismHR data.",
        risk="low",
        recommended_default=True,
        tools=(),
    ),
    ScopeSpec(
        scope=Scope.M365_SHAREPOINT_READ,
        category=ScopeCategory.M365_READ,
        label="Read SharePoint files",
        description="List files in client SharePoint document libraries.",
        risk="low",
        recommended_default=True,
        tools=(),
    ),
    ScopeSpec(
        scope=Scope.M365_SHAREPOINT_WRITE,
        category=ScopeCategory.M365_WRITE,
        label="Upload files to SharePoint",
        description="Upload generated reports to client SharePoint libraries.",
        risk="medium",
        recommended_default=False,
        tools=(),
        requires=(Scope.M365_SHAREPOINT_READ,),
    ),
    ScopeSpec(
        scope=Scope.M365_EMAIL_SEND,
        category=ScopeCategory.M365_WRITE,
        label="Send email via Graph API",
        description="Send outbound email on behalf of the service account.",
        risk="medium",
        recommended_default=False,
        tools=(),
    ),
    ScopeSpec(
        scope=Scope.M365_TEAMS_POST,
        category=ScopeCategory.M365_WRITE,
        label="Post to Teams channels",
        description="Post summaries / cards to Microsoft Teams channels.",
        risk="medium",
        recommended_default=False,
        tools=(),
    ),
    ScopeSpec(
        scope=Scope.M365_OUTLOOK_CALENDAR,
        category=ScopeCategory.M365_WRITE,
        label="Create Outlook events",
        description="Schedule calendar events (follow-ups, client calls).",
        risk="medium",
        recommended_default=False,
        tools=(),
    ),
    ScopeSpec(
        scope=Scope.M365_OUTLOOK_TASKS,
        category=ScopeCategory.M365_WRITE,
        label="Create Outlook tasks",
        description="Add To-Do items for PEO reps.",
        risk="low",
        recommended_default=False,
        tools=(),
    ),
    ScopeSpec(
        scope=Scope.PAYROLL_WRITE,
        category=ScopeCategory.PRISMHR_WRITE,
        label="Initiate payroll voids & corrections",
        description="Kick off void/correction workflows in PrismHR. Always gated behind preview → confirm.",
        risk="high",
        recommended_default=False,
        tools=("payroll_void_workflow", "payroll_correction_workflow"),
        requires=(Scope.PAYROLL_READ,),
    ),
)


def lookup(scope: Scope) -> ScopeSpec:
    for spec in MANIFEST:
        if spec.scope == scope:
            return spec
    raise KeyError(f"Unknown scope: {scope!r}")


def manifest_by_category() -> dict[ScopeCategory, list[ScopeSpec]]:
    buckets: dict[ScopeCategory, list[ScopeSpec]] = {cat: [] for cat in CATEGORY_ORDER}
    for spec in MANIFEST:
        buckets[spec.category].append(spec)
    return buckets
