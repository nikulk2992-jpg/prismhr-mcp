"""Group 2 — Payroll Operations tools.

Read-path scope: `payroll:read`. Write-path scope: `payroll:write`.
Write tools are stubbed until Phase 6 (preview→confirm two-step).
"""

from __future__ import annotations

from datetime import date
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
        client_id: Annotated[str, Field(description="The client to look at.")],
        start_date: Annotated[str, Field(description="First day to include (YYYY-MM-DD).")],
        end_date: Annotated[str, Field(description="Last day to include (YYYY-MM-DD).")],
    ) -> BatchStatusResponse:
        """Find the payroll batches a client ran in a date window.

        Use when the user asks things like "what payrolls ran at Acme in March"
        or "show me this quarter's batches for client ABC". Returns batch IDs,
        pay dates, status, voucher counts, and gross totals.
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
        client_id: Annotated[str, Field(description="The client the employee belongs to.")],
        employee_id: Annotated[str, Field(description="Which employee.")],
        start_date: Annotated[str, Field(description="First day to include (YYYY-MM-DD).")],
        end_date: Annotated[str, Field(description="Last day to include (YYYY-MM-DD).")],
    ) -> PayHistoryResponse:
        """Get an employee's paychecks in a date window, plus year-to-date totals.

        Use when the user asks "what did Jane get paid this quarter" or
        "pull up John's checks for Q1". Returns each paycheck (gross, net,
        regular/overtime hours) plus YTD gross/net/taxes.
        """
        include_ytd = True  # always fetch YTD — hiding the knob; cheap extra call
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
        client_id: Annotated[str, Field(description="The client the employee belongs to.")],
        employee_id: Annotated[str, Field(description="Which employee.")],
    ) -> PayGroupAssignment:
        """Check whether an employee is set up to be paid (pay group assigned).

        Use when the user asks "why didn't Jane get paid" or "is this new hire
        ready for payroll". Returns whether a pay group is assigned and the
        pay frequency (weekly/biweekly/etc). Unassigned pay group is the #1
        reason an employee is skipped in a payroll run.
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
        client_id: Annotated[str, Field(description="The client the employee belongs to.")],
        employee_id: Annotated[str, Field(description="Which employee.")],
    ) -> DeductionConflictsResponse:
        """Find problems in an employee's scheduled deductions BEFORE payroll runs.

        Use when the user asks "check Jane's deductions" or "is this employee
        ready to run" or "why is so-and-so's garnishment doubled". Flags four
        issues: two deductions sharing the same priority, duplicate deductions
        with the same code, active deductions whose end date has already passed,
        and garnishment/loan deductions with no goal amount.
        """
        permissions.check(Scope.PAYROLL_READ)
        raw = await prismhr.get(
            PATH_SCHEDULED_DEDUCTIONS,
            params={"clientId": client_id, "employeeId": employee_id},
        )
        rows = _coerce_list(raw)
        today_str = date.today().isoformat()  # hide the knob; always compare against today
        conflicts = detect_deduction_conflicts(rows, today=today_str)
        return DeductionConflictsResponse(
            client_id=client_id,
            employee_id=employee_id,
            scanned_count=len(rows),
            conflicts=conflicts,
        )

    async def payroll_overtime_anomalies(
        client_id: Annotated[str, Field(description="The client the employee belongs to.")],
        employee_id: Annotated[str, Field(description="Which employee.")],
        start_date: Annotated[str, Field(description="First day to include (YYYY-MM-DD).")],
        end_date: Annotated[str, Field(description="Last day to include (YYYY-MM-DD).")],
        batch_id: Annotated[
            str | None,
            Field(description="Optional — narrow the scan to a single payroll batch."),
        ] = None,
    ) -> OvertimeAnomaliesResponse:
        """Find overtime problems in an employee's paychecks.

        Use when the user asks "does Jane's OT look right" or "flag weird
        overtime at Acme last month". Surfaces negative regular hours,
        overtime with no regular hours, excessive OT over 30/week, and
        overtime-rate/regular-rate mismatches that aren't ~1.5x.
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
        client_id: Annotated[str, Field(description="The client.")],
        start_date: Annotated[str, Field(description="First day to include (YYYY-MM-DD).")],
        end_date: Annotated[str, Field(description="Last day to include (YYYY-MM-DD).")],
    ) -> SuperBatchSummary:
        """Summarize a client's payroll cycle health across a date range.

        Use for morning-of-pay status checks: "how's Acme's payroll looking
        this week" or "show me everything that's open vs. posted for
        client XYZ this quarter". Counts batches by status (open / pending
        / posted / voided) and totals gross payroll across them.
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
        client_id: Annotated[str, Field(description="The client.")],
        batch_id: Annotated[str, Field(description="Which payroll batch.")],
    ) -> RegisterReconciliation:
        """Explain why a payroll batch's gross does not match billing.

        Use when the user says "something's off with this batch" or "why
        doesn't the register match the invoice for Acme's last pay run".
        Compares paycheck gross totals against billing-code totals; says
        reconciled=true if they agree within 5 cents per $100, otherwise
        returns the dollar delta and a plain-English finding.
        """
        threshold_pct = REGISTER_RECONCILE_THRESHOLD_PCT  # hidden constant
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
    # payroll_void_workflow + payroll_correction_workflow intentionally NOT
    # registered. They exist above as placeholders for Phase 6's preview→confirm
    # design but registering them now would create fake tools — permissioned,
    # visible to Claude, but nonfunctional — which pollutes consent and burns
    # user trust. Phase 6 will register them once they actually mutate data.
    _ = (payroll_void_workflow, payroll_correction_workflow)  # silence unused warnings


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
