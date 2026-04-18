"""Group 2 — Payroll Operations tools.

Read-path scope: `payroll:read`. Write-path scope: `payroll:write`.
Write tools are stubbed until Phase 6 (preview→confirm two-step).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..clients.prismhr import PrismHRClient
from ..errors import MCPError
from ..models.payroll import (
    BatchEntry,
    BatchStatusResponse,
    DeductionConflictsResponse,
    OvertimeAnomaliesResponse,
    PayGroupAssignment,
    PayHistoryResponse,
    PayVoucher,
    RegisterReconciliation,
    SuperBatchSummary,
    WorkflowDeferred,
    YTDValues,
)
from ..normalizers.payroll import (
    detect_deduction_conflicts,
    detect_overtime_anomalies,
)
from ..permissions import PermissionManager, Scope
from ..registry import ToolRegistry

# PrismHR endpoints — exposed for respx test targeting.
PATH_BATCH_LIST = "/payroll/v1/getBatchListByDate"
PATH_BILLING_CODE_TOTALS = "/payroll/v1/getBillingCodeTotalsForBatch"
PATH_VOUCHERS_FOR_EMPLOYEE = "/payroll/v1/getPayrollVouchersForEmployee"
PATH_YTD = "/payroll/v1/getYearToDateValues"
PATH_SCHEDULED_DEDUCTIONS = "/employee/v1/getScheduledDeductions"
PATH_GET_EMPLOYEE = "/employee/v1/getEmployee"

REGISTER_RECONCILE_THRESHOLD_PCT = 0.05  # 0.05% gross-vs-billing delta is acceptable


def register(
    server: FastMCP,
    registry: ToolRegistry,
    prismhr: PrismHRClient,
    permissions: PermissionManager,
) -> None:

    # ------------- read tools -------------

    async def payroll_batch_status(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        start_date: Annotated[
            str, Field(description="Inclusive start date (YYYY-MM-DD). Matches PrismHR's batch list filter.")
        ],
        end_date: Annotated[str, Field(description="Inclusive end date (YYYY-MM-DD).")],
    ) -> BatchStatusResponse:
        """List payroll batches for a client between two dates.

        Returns batch IDs, pay dates, status, voucher counts, and gross totals.
        Downstream: feeds `payroll_register_reconcile`, `payroll_overtime_anomalies`,
        `payroll_superbatch_status`, and branded payroll summary reports.
        """
        permissions.check(Scope.PAYROLL_READ)
        raw = await prismhr.get(
            PATH_BATCH_LIST,
            params={"clientId": client_id, "startDate": start_date, "endDate": end_date},
        )
        rows = _coerce_list(raw)
        for row in rows:
            row.setdefault("clientId", client_id)
        batches = [BatchEntry.model_validate(row) for row in rows]
        return BatchStatusResponse(
            client_id=client_id,
            start_date=start_date,
            end_date=end_date,
            batches=batches,
            count=len(batches),
        )

    async def payroll_pay_history(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        employee_id: Annotated[str, Field(description="Employee ID within the client.")],
        start_date: Annotated[str, Field(description="Inclusive start date (YYYY-MM-DD).")],
        end_date: Annotated[str, Field(description="Inclusive end date (YYYY-MM-DD).")],
        include_ytd: Annotated[
            bool,
            Field(description="If true, also fetches year-to-date totals as of end_date."),
        ] = True,
    ) -> PayHistoryResponse:
        """Fetch pay vouchers for an employee across a date range, optionally with YTD totals.

        Returns a list of `PayVoucher` records (gross, net, regular/overtime hours,
        pay dates, voided flag) plus optional `YTDValues`.
        """
        permissions.check(Scope.PAYROLL_READ)
        voucher_raw = await prismhr.get(
            PATH_VOUCHERS_FOR_EMPLOYEE,
            params={
                "clientId": client_id,
                "employeeId": employee_id,
                "payDateStart": start_date,
                "payDateEnd": end_date,
            },
        )
        vouchers = [PayVoucher.model_validate(row) for row in _coerce_list(voucher_raw)]

        ytd: YTDValues | None = None
        if include_ytd:
            ytd_raw = await prismhr.get(
                PATH_YTD,
                params={
                    "clientId": client_id,
                    "employeeId": employee_id,
                    "asOfDate": end_date,
                },
            )
            if isinstance(ytd_raw, dict) and ytd_raw:
                ytd = YTDValues.model_validate(ytd_raw)
            elif isinstance(ytd_raw, list) and ytd_raw and isinstance(ytd_raw[0], dict):
                ytd = YTDValues.model_validate(ytd_raw[0])

        return PayHistoryResponse(
            client_id=client_id,
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            vouchers=vouchers,
            ytd=ytd,
            count=len(vouchers),
        )

    async def payroll_pay_group_check(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        employee_id: Annotated[str, Field(description="Employee ID within the client.")],
    ) -> PayGroupAssignment:
        """Verify that an employee is assigned to a pay group, and surface frequency.

        Unassigned or mis-assigned pay groups are the most common cause of
        missed payroll. This tool returns a clear `assigned` boolean plus a
        warning message when something looks off.
        """
        permissions.check(Scope.PAYROLL_READ)
        raw = await prismhr.post(
            PATH_GET_EMPLOYEE,
            json={"clientId": client_id, "employeeIds": [employee_id]},
        )
        rows = _coerce_list(raw)
        record = rows[0] if rows else {}
        pay_group_id = _first(
            record,
            "payGroupId",
            "pay_group_id",
            "payrollGroupId",
        )
        pay_group_name = _first(record, "payGroupName", "pay_group_name")
        pay_frequency = _first(record, "payFrequency", "pay_frequency")

        warning = None
        if not pay_group_id:
            warning = (
                "Employee has no pay group assigned — payroll will skip this employee. "
                "Assign via PrismHR's HR module."
            )

        return PayGroupAssignment(
            client_id=client_id,
            employee_id=employee_id,
            pay_group_id=pay_group_id,
            pay_group_name=pay_group_name,
            pay_frequency=pay_frequency,
            assigned=bool(pay_group_id),
            warning=warning,
        )

    async def payroll_deduction_conflicts(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        employee_id: Annotated[str, Field(description="Employee ID within the client.")],
        today: Annotated[
            str | None,
            Field(
                description="YYYY-MM-DD; used to flag `expired_active` deductions. Defaults to empty (no date check).",
            ),
        ] = None,
    ) -> DeductionConflictsResponse:
        """Scan an employee's scheduled deductions for conflicts (priority clashes, duplicates, expired-but-active, goal missing).

        Wraps `normalizers.payroll.detect_deduction_conflicts`. Use this
        before running payroll to avoid surprise underwithholdings or
        duplicate deduction amounts.
        """
        permissions.check(Scope.PAYROLL_READ)
        raw = await prismhr.get(
            PATH_SCHEDULED_DEDUCTIONS,
            params={"clientId": client_id, "employeeId": employee_id},
        )
        rows = _coerce_list(raw)
        conflicts = detect_deduction_conflicts(rows, today=today)
        return DeductionConflictsResponse(
            client_id=client_id,
            employee_id=employee_id,
            scanned_count=len(rows),
            conflicts=conflicts,
        )

    async def payroll_overtime_anomalies(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        employee_id: Annotated[str, Field(description="Employee ID within the client.")],
        start_date: Annotated[str, Field(description="Inclusive start date (YYYY-MM-DD).")],
        end_date: Annotated[str, Field(description="Inclusive end date (YYYY-MM-DD).")],
        batch_id: Annotated[
            str | None,
            Field(description="Optional — filter anomalies to vouchers in this batch only."),
        ] = None,
    ) -> OvertimeAnomaliesResponse:
        """Analyze an employee's vouchers for overtime anomalies.

        Detects negative regular hours, OT without regular hours, excessive
        OT, and OT/regular rate mismatches. Wraps
        `normalizers.payroll.detect_overtime_anomalies`.
        """
        permissions.check(Scope.PAYROLL_READ)
        raw = await prismhr.get(
            PATH_VOUCHERS_FOR_EMPLOYEE,
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

    async def payroll_superbatch_status(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        start_date: Annotated[str, Field(description="Inclusive start date (YYYY-MM-DD).")],
        end_date: Annotated[str, Field(description="Inclusive end date (YYYY-MM-DD).")],
    ) -> SuperBatchSummary:
        """Aggregate payroll-batch status across a date range, mirroring PrismHR's SuperBatch UI.

        Counts open/pending/posted/voided batches and totals gross across
        all of them. Useful for morning-of-pay status checks.
        """
        permissions.check(Scope.PAYROLL_READ)
        raw = await prismhr.get(
            PATH_BATCH_LIST,
            params={"clientId": client_id, "startDate": start_date, "endDate": end_date},
        )
        rows = _coerce_list(raw)
        for row in rows:
            row.setdefault("clientId", client_id)
        batches = [BatchEntry.model_validate(row) for row in rows]

        total_gross = sum((b.gross_total or Decimal("0")) for b in batches)
        total_vouchers = sum((b.voucher_count or 0) for b in batches)
        open_ct = _count_status(batches, "open")
        pending_ct = _count_status(batches, "pending", "review", "calc")
        posted_ct = _count_status(batches, "posted", "closed", "finalized")
        voided_ct = _count_status(batches, "void", "voided")

        return SuperBatchSummary(
            client_id=client_id,
            start_date=start_date,
            end_date=end_date,
            batch_count=len(batches),
            total_vouchers=total_vouchers,
            total_gross=Decimal(total_gross),
            open_batch_count=open_ct,
            pending_batch_count=pending_ct,
            posted_batch_count=posted_ct,
            voided_batch_count=voided_ct,
            batches=batches,
        )

    async def payroll_register_reconcile(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        batch_id: Annotated[str, Field(description="Batch to reconcile.")],
        threshold_pct: Annotated[
            float,
            Field(description="Tolerance in percent. Default 0.05 (5 cents per $100)."),
        ] = REGISTER_RECONCILE_THRESHOLD_PCT,
    ) -> RegisterReconciliation:
        """Compare voucher gross totals to billing-code totals for a batch.

        If the two agree within `threshold_pct` of gross, the batch is
        considered reconciled. Otherwise surfaces the delta in both dollars
        and percentage so ops can find the discrepancy.
        """
        permissions.check(Scope.PAYROLL_READ)

        billing_raw = await prismhr.get(
            PATH_BILLING_CODE_TOTALS,
            params={"clientId": client_id, "batchId": batch_id},
        )
        billing_total = _sum_amount(
            _coerce_list(billing_raw),
            ("amount", "totalAmount", "billingAmount", "total"),
        )

        voucher_raw = await prismhr.get(
            PATH_VOUCHERS_FOR_EMPLOYEE,
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

    # ------------- write-path stubs (Phase 6) -------------

    async def payroll_void_workflow(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        voucher_id: Annotated[str, Field(description="Voucher / check number to void.")],
        reason: Annotated[str, Field(description="Why this void is being issued (audit trail).")],
    ) -> WorkflowDeferred:
        """Initiate a payroll void (Phase 6 — deferred).

        Currently a stub that validates the permission scope + inputs,
        then returns a `NOT_YET_IMPLEMENTED` marker pointing at the
        roadmap issue. Phase 6 will add a two-step preview → confirm flow.
        """
        permissions.check(Scope.PAYROLL_WRITE)
        return WorkflowDeferred(
            message=(
                f"payroll_void_workflow(client_id={client_id!r}, voucher_id={voucher_id!r}) "
                "is scheduled for Phase 6. No mutation performed."
            )
        )

    async def payroll_correction_workflow(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        voucher_id: Annotated[str, Field(description="Voucher to correct.")],
        corrections: Annotated[
            dict[str, Any],
            Field(description="Proposed field changes. Shape locked down in Phase 6."),
        ],
    ) -> WorkflowDeferred:
        """Initiate a payroll correction (Phase 6 — deferred).

        Same posture as `payroll_void_workflow` — scope is enforced now so
        users discover the permission model early, but the actual mutation
        is behind Phase 6's preview → confirm gate.
        """
        permissions.check(Scope.PAYROLL_WRITE)
        return WorkflowDeferred(
            message=(
                f"payroll_correction_workflow(client_id={client_id!r}, voucher_id={voucher_id!r}) "
                "is scheduled for Phase 6. No mutation performed."
            )
        )

    registry.register(server, "payroll_batch_status", payroll_batch_status)
    registry.register(server, "payroll_pay_history", payroll_pay_history)
    registry.register(server, "payroll_pay_group_check", payroll_pay_group_check)
    registry.register(server, "payroll_deduction_conflicts", payroll_deduction_conflicts)
    registry.register(server, "payroll_overtime_anomalies", payroll_overtime_anomalies)
    registry.register(server, "payroll_superbatch_status", payroll_superbatch_status)
    registry.register(server, "payroll_register_reconcile", payroll_register_reconcile)
    registry.register(server, "payroll_void_workflow", payroll_void_workflow)
    registry.register(server, "payroll_correction_workflow", payroll_correction_workflow)


# ---------- helpers ----------


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


def _first(record: dict, *keys: str) -> Any | None:
    for k in keys:
        if record.get(k) not in (None, ""):
            return record[k]
    return None


def _count_status(batches: list[BatchEntry], *markers: str) -> int:
    count = 0
    for b in batches:
        status = (b.status or "").lower()
        if any(marker in status for marker in markers):
            count += 1
    return count


def _sum_amount(rows: list[dict], keys: tuple[str, ...]) -> Decimal:
    total = Decimal("0")
    for row in rows:
        for key in keys:
            val = row.get(key)
            if val is None:
                continue
            try:
                total += Decimal(str(val))
                break
            except (ValueError, ArithmeticError):
                continue
    return total
