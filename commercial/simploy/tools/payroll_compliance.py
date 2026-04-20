"""Commercial payroll-compliance MCP tools.

Moved from the OSS `prismhr_mcp.tools.payroll` module because these 5
tools are compliance workflows, not basic PrismHR reads:

  commercial_payroll_deduction_conflicts
  commercial_payroll_overtime_anomalies
  commercial_payroll_register_reconcile
  commercial_payroll_void_workflow         (stub until write-phase)
  commercial_payroll_correction_workflow   (stub until write-phase)

Basic reads stay in OSS (payroll_batch_status, payroll_pay_history,
payroll_pay_group_check, payroll_superbatch_status).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.models.payroll import PayVoucher  # shared OSS contract
from prismhr_mcp.permissions import PermissionManager, Scope
from prismhr_mcp.registry import ToolRegistry

from simploy.models.payroll_compliance import (
    DeductionConflictsResponse,
    OvertimeAnomaliesResponse,
    RegisterReconciliation,
    WorkflowDeferred,
)
from simploy.normalizers.payroll_compliance import (
    detect_deduction_conflicts,
    detect_overtime_anomalies,
)


_PATH_BATCH_LIST = "/payroll/v1/getBatchListByDate"
_PATH_BILLING_CODE_TOTALS = "/payroll/v1/getBillingCodeTotalsForBatch"
_PATH_VOUCHERS_FOR_EMPLOYEE = "/payroll/v1/getPayrollVouchersForEmployee"
_PATH_SCHEDULED_DEDUCTIONS = "/employee/v1/getScheduledDeductions"

_REGISTER_RECONCILE_THRESHOLD_PCT = 0.05


def _coerce_list(raw: object) -> list[dict]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw  # type: ignore[return-value]
    if isinstance(raw, dict):
        for value in raw.values():
            if isinstance(value, list):
                return value  # type: ignore[return-value]
        return [raw]
    return []


def _sum_amount(rows: list[dict], keys: tuple[str, ...]) -> Decimal:
    total = Decimal("0")
    for row in rows:
        for k in keys:
            v = row.get(k)
            if v in (None, ""):
                continue
            try:
                total += Decimal(str(v))
                break
            except Exception:  # noqa: BLE001
                continue
    return total


def register_payroll_compliance_tools(
    server: FastMCP,
    registry: ToolRegistry,
    prismhr: PrismHRClient,
    permissions: PermissionManager,
) -> None:
    """Register the 5 commercial payroll-compliance tools."""

    async def commercial_payroll_deduction_conflicts(
        client_id: Annotated[str, Field(description="The client the employee belongs to.")],
        employee_id: Annotated[str, Field(description="Which employee.")],
    ) -> DeductionConflictsResponse:
        """Find problems in an employee's scheduled deductions BEFORE payroll runs.

        Flags: priority clashes, duplicate deduction codes, expired-but-active
        deductions, and goal-based deductions (garnishment/loan/catchup) with
        no goal amount set.
        """
        permissions.check(Scope.PAYROLL_READ)
        raw = await prismhr.get(
            _PATH_SCHEDULED_DEDUCTIONS,
            params={"clientId": client_id, "employeeId": employee_id},
        )
        rows = _coerce_list(raw)
        today_str = date.today().isoformat()
        conflicts = detect_deduction_conflicts(rows, today=today_str)
        return DeductionConflictsResponse(
            client_id=client_id,
            employee_id=employee_id,
            scanned_count=len(rows),
            conflicts=conflicts,
        )

    registry.register(server, "commercial_payroll_deduction_conflicts",
                      commercial_payroll_deduction_conflicts)

    async def commercial_payroll_overtime_anomalies(
        client_id: Annotated[str, Field(description="The client the employee belongs to.")],
        employee_id: Annotated[str, Field(description="Which employee.")],
        start_date: Annotated[str, Field(description="First day to include (YYYY-MM-DD).")],
        end_date: Annotated[str, Field(description="Last day to include (YYYY-MM-DD).")],
        batch_id: Annotated[
            str | None,
            Field(description="Optional — narrow the scan to a single payroll batch."),
        ] = None,
    ) -> OvertimeAnomaliesResponse:
        """DOL FLSA overtime anomaly detector. Surfaces negative regular
        hours, OT without regular hours, excessive OT (>30/week), and
        rate mismatches that aren't ~1.5x."""
        permissions.check(Scope.PAYROLL_READ)
        raw = await prismhr.get(
            _PATH_VOUCHERS_FOR_EMPLOYEE,
            params={
                "clientId": client_id,
                "employeeId": employee_id,
                "payDateStart": start_date,
                "payDateEnd": end_date,
            },
        )
        vouchers = [PayVoucher.model_validate(row) for row in _coerce_list(raw)]
        if batch_id:
            vouchers = [v for v in vouchers if v.batch_id == batch_id]
        anomalies = detect_overtime_anomalies(vouchers)
        for a in anomalies:
            a.employee_id = employee_id
        return OvertimeAnomaliesResponse(
            client_id=client_id,
            batch_id=batch_id,
            scanned_vouchers=len(vouchers),
            anomalies=anomalies,
        )

    registry.register(server, "commercial_payroll_overtime_anomalies",
                      commercial_payroll_overtime_anomalies)

    async def commercial_payroll_register_reconcile(
        client_id: Annotated[str, Field(description="The client.")],
        batch_id: Annotated[str, Field(description="Which payroll batch.")],
    ) -> RegisterReconciliation:
        """Explain why a payroll batch's gross does not match billing."""
        threshold_pct = _REGISTER_RECONCILE_THRESHOLD_PCT
        permissions.check(Scope.PAYROLL_READ)

        billing_raw = await prismhr.get(
            _PATH_BILLING_CODE_TOTALS,
            params={"clientId": client_id, "batchId": batch_id},
        )
        billing_total = _sum_amount(
            _coerce_list(billing_raw),
            ("amount", "totalAmount", "billingAmount", "total"),
        )

        voucher_raw = await prismhr.get(
            _PATH_VOUCHERS_FOR_EMPLOYEE,
            params={"clientId": client_id, "batchId": batch_id},
        )
        voucher_rows = _coerce_list(voucher_raw)
        voucher_total = _sum_amount(
            voucher_rows,
            ("grossAmount", "gross", "grossPay", "gross_amount"),
        )

        delta = voucher_total - billing_total
        if voucher_total == 0:
            delta_pct = 0.0 if billing_total == 0 else 100.0
        else:
            delta_pct = float(abs(delta) / voucher_total * 100)
        reconciled = delta_pct <= threshold_pct

        message = (
            f"Reconciled: voucher gross {voucher_total} matches billing "
            f"total {billing_total} within {threshold_pct}%."
            if reconciled
            else (
                f"MISMATCH: voucher gross {voucher_total} vs billing "
                f"{billing_total} (delta {delta}, {delta_pct:.3f}%). "
                "Check pay codes vs billing codes."
            )
        )

        return RegisterReconciliation(
            client_id=client_id,
            batch_id=batch_id,
            voucher_gross_total=voucher_total,
            billing_code_total=billing_total,
            delta=delta,
            delta_pct=delta_pct,
            reconciled=reconciled,
            threshold_pct=threshold_pct,
            message=message,
        )

    registry.register(server, "commercial_payroll_register_reconcile",
                      commercial_payroll_register_reconcile)

    # ------------- write-path stubs -------------

    async def commercial_payroll_void_workflow(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        voucher_id: Annotated[str, Field(description="Voucher / check number to void.")],
        reason: Annotated[str, Field(description="Why this void is being issued (audit trail).")],
    ) -> WorkflowDeferred:
        """Initiate a payroll void (deferred — preview→confirm two-step TBD)."""
        permissions.check(Scope.PAYROLL_WRITE)
        return WorkflowDeferred(
            message=(
                f"commercial_payroll_void_workflow(client_id={client_id!r}, "
                f"voucher_id={voucher_id!r}) is scheduled for a future write-phase. "
                f"No mutation performed."
            )
        )

    registry.register(server, "commercial_payroll_void_workflow",
                      commercial_payroll_void_workflow)

    async def commercial_payroll_correction_workflow(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        voucher_id: Annotated[str, Field(description="Voucher to correct.")],
        corrections: Annotated[
            dict[str, Any],
            Field(description="Proposed field changes."),
        ],
    ) -> WorkflowDeferred:
        """Initiate a payroll correction (deferred — preview→confirm TBD)."""
        permissions.check(Scope.PAYROLL_WRITE)
        return WorkflowDeferred(
            message=(
                f"commercial_payroll_correction_workflow(client_id={client_id!r}, "
                f"voucher_id={voucher_id!r}) is scheduled for a future write-phase. "
                f"No mutation performed."
            )
        )

    registry.register(server, "commercial_payroll_correction_workflow",
                      commercial_payroll_correction_workflow)
