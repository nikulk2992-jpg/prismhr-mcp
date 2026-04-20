"""Commercial payroll-compliance response models.

Moved from prismhr_mcp.models.payroll (OSS) because the underlying tools
(deduction conflicts, overtime anomalies, register reconciliation,
void/correction workflow stubs) are commercial-tier compliance features.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


# ----- Deduction conflict detection -----


ConflictKind = Literal[
    "priority_clash", "same_code_duplicate", "expired_active", "no_goal_set"
]


class DeductionConflict(BaseModel):
    kind: ConflictKind
    deduction_codes: list[str]
    severity: Literal["low", "medium", "high"]
    message: str
    scheduled_for: str | None = None


class DeductionConflictsResponse(BaseModel):
    client_id: str
    employee_id: str
    scanned_count: int
    conflicts: list[DeductionConflict]


# ----- Overtime anomaly detection -----


class OvertimeAnomaly(BaseModel):
    voucher_id: str | None
    employee_id: str | None
    pay_date: str | None
    kind: Literal[
        "excessive_overtime", "negative_regular",
        "ot_without_regular", "rate_mismatch",
    ]
    severity: Literal["low", "medium", "high"]
    message: str
    regular_hours: Decimal | None = None
    overtime_hours: Decimal | None = None


class OvertimeAnomaliesResponse(BaseModel):
    client_id: str
    batch_id: str | None
    scanned_vouchers: int
    anomalies: list[OvertimeAnomaly]


# ----- Register reconciliation -----


class RegisterReconciliation(BaseModel):
    client_id: str
    batch_id: str
    voucher_gross_total: Decimal
    billing_code_total: Decimal
    delta: Decimal
    delta_pct: float
    reconciled: bool
    threshold_pct: float
    message: str


# ----- Write-path stubs (void / correction) -----


class WorkflowDeferred(BaseModel):
    """Placeholder for tools that mutate live PrismHR data — wired in
    a future phase with preview → confirm two-step gate."""

    code: str = "NOT_YET_IMPLEMENTED"
    message: str
    tracking_issue: str = "https://github.com/nikulk2992-jpg/prismhr-mcp/issues"
    planned_for: str = "preview → confirm two-step phase"
