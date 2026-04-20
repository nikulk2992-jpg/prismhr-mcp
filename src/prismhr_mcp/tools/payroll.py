"""Group 2 — Payroll Operations tools (OSS basic reads).

Read-path scope: `payroll:read`.

Compliance / reconciliation / write-path workflows (deduction conflicts,
overtime anomalies, register reconcile, void/correction) live in the
commercial tier at `simploy.tools.payroll_compliance`, not here.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..clients.prismhr import PrismHRClient
from ..models.payroll import (
    BatchEntry,
    BatchStatusResponse,
    PayGroupAssignment,
    PayHistoryResponse,
    PayVoucher,
    SuperBatchSummary,
    YTDValues,
)
from ..permissions import PermissionManager, Scope
from ..registry import ToolRegistry


# PrismHR endpoints — exposed for respx test targeting.
PATH_BATCH_LIST = "/payroll/v1/getBatchListByDate"
PATH_VOUCHERS_FOR_EMPLOYEE = "/payroll/v1/getPayrollVouchersForEmployee"
PATH_YTD = "/payroll/v1/getYearToDateValues"
PATH_GET_EMPLOYEE = "/employee/v1/getEmployee"


def register(
    server: FastMCP,
    registry: ToolRegistry,
    prismhr: PrismHRClient,
    permissions: PermissionManager,
) -> None:

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
        include_ytd = True
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
        pay_group_id = _first(record, "payGroupId", "pay_group_id", "payrollGroupId")
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

    registry.register(server, "payroll_batch_status", payroll_batch_status)
    registry.register(server, "payroll_pay_history", payroll_pay_history)
    registry.register(server, "payroll_pay_group_check", payroll_pay_group_check)
    registry.register(server, "payroll_superbatch_status", payroll_superbatch_status)


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
