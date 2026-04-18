"""Integration tests for Group 2 — payroll tools."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from prismhr_mcp.auth.prismhr_session import LOGIN_PATH
from prismhr_mcp.server import build
from prismhr_mcp.tools.payroll import (
    PATH_BATCH_LIST,
    PATH_BILLING_CODE_TOTALS,
    PATH_GET_EMPLOYEE,
    PATH_SCHEDULED_DEDUCTIONS,
    PATH_VOUCHERS_FOR_EMPLOYEE,
    PATH_YTD,
)


def _login_ok(mock: respx.Router) -> None:
    mock.post(LOGIN_PATH).mock(return_value=httpx.Response(200, json={"token": "t"}))


def _structured(result) -> dict:  # noqa: ANN001
    if isinstance(result, tuple) and len(result) == 2 and result[1] is not None:
        return result[1]
    blocks = result[0] if isinstance(result, tuple) else result
    if blocks:
        text = getattr(blocks[0], "text", None)
        if text:
            return json.loads(text)
    pytest.fail(f"no structured payload in {result!r}")
    return {}


# ---------- payroll_batch_status ----------


async def test_payroll_batch_status_returns_batches(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_BATCH_LIST).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"batchId": "B1", "payDate": "2026-03-15", "grossTotal": 10500, "batchStatus": "posted", "voucherCount": 12},
                    {"batchId": "B2", "payDate": "2026-03-29", "grossTotal": 11200, "batchStatus": "open", "voucherCount": 14},
                ],
            )
        )
        result = await built.server.call_tool(
            "payroll_batch_status",
            {"client_id": "ACME", "start_date": "2026-03-01", "end_date": "2026-03-31"},
        )
    data = _structured(result)
    assert data["count"] == 2
    assert {b["batch_id"] for b in data["batches"]} == {"B1", "B2"}


# ---------- payroll_pay_history ----------


async def test_payroll_pay_history_with_ytd(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_VOUCHERS_FOR_EMPLOYEE).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"voucherId": "V1", "payDate": "2026-01-15", "grossAmount": 2500},
                    {"voucherId": "V2", "payDate": "2026-01-29", "grossAmount": 2500},
                ],
            )
        )
        mock.get(PATH_YTD).mock(
            return_value=httpx.Response(200, json={"grossYTD": 5000, "netYTD": 3800})
        )
        result = await built.server.call_tool(
            "payroll_pay_history",
            {
                "client_id": "ACME",
                "employee_id": "E1",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
            },
        )
    data = _structured(result)
    assert data["count"] == 2
    assert data["ytd"]["gross_ytd"] == "5000"
    assert data["ytd"]["net_ytd"] == "3800"


async def test_payroll_pay_history_skips_ytd_when_disabled(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url, assert_all_called=False) as mock:
        _login_ok(mock)
        mock.get(PATH_VOUCHERS_FOR_EMPLOYEE).mock(return_value=httpx.Response(200, json=[]))
        ytd_route = mock.get(PATH_YTD)
        await built.server.call_tool(
            "payroll_pay_history",
            {
                "client_id": "ACME",
                "employee_id": "E1",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "include_ytd": False,
            },
        )
        assert ytd_route.call_count == 0


# ---------- payroll_pay_group_check ----------


async def test_pay_group_check_reports_assigned(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.post(PATH_GET_EMPLOYEE).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"employeeId": "E1", "payGroupId": "PG1", "payGroupName": "Weekly Hourly", "payFrequency": "weekly"}
                ],
            )
        )
        result = await built.server.call_tool(
            "payroll_pay_group_check",
            {"client_id": "ACME", "employee_id": "E1"},
        )
    data = _structured(result)
    assert data["assigned"] is True
    assert data["pay_group_id"] == "PG1"
    assert data["warning"] is None


async def test_pay_group_check_warns_when_unassigned(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.post(PATH_GET_EMPLOYEE).mock(
            return_value=httpx.Response(
                200, json=[{"employeeId": "E1"}]
            )
        )
        result = await built.server.call_tool(
            "payroll_pay_group_check",
            {"client_id": "ACME", "employee_id": "E1"},
        )
    data = _structured(result)
    assert data["assigned"] is False
    assert "no pay group assigned" in (data["warning"] or "").lower()


# ---------- payroll_deduction_conflicts ----------


async def test_deduction_conflicts_surfaces_priority_clash(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_SCHEDULED_DEDUCTIONS).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"status": "active", "code": "401K", "priority": 10},
                    {"status": "active", "code": "GARN", "priority": 10},
                ],
            )
        )
        result = await built.server.call_tool(
            "payroll_deduction_conflicts",
            {"client_id": "ACME", "employee_id": "E1"},
        )
    data = _structured(result)
    assert data["scanned_count"] == 2
    kinds = [c["kind"] for c in data["conflicts"]]
    assert "priority_clash" in kinds


# ---------- payroll_overtime_anomalies ----------


async def test_overtime_anomalies_flag_excessive(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_VOUCHERS_FOR_EMPLOYEE).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"voucherId": "V1", "payDate": "2026-04-01", "regularHours": 40, "overtimeHours": 45, "regularAmount": 800, "overtimeAmount": 1350},
                ],
            )
        )
        result = await built.server.call_tool(
            "payroll_overtime_anomalies",
            {
                "client_id": "ACME",
                "employee_id": "E1",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
            },
        )
    data = _structured(result)
    kinds = {a["kind"] for a in data["anomalies"]}
    assert "excessive_overtime" in kinds


# ---------- payroll_superbatch_status ----------


async def test_superbatch_status_aggregates(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_BATCH_LIST).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"batchId": "B1", "grossTotal": 1000, "voucherCount": 5, "batchStatus": "posted"},
                    {"batchId": "B2", "grossTotal": 2000, "voucherCount": 10, "batchStatus": "open"},
                    {"batchId": "B3", "grossTotal": 500, "voucherCount": 2, "batchStatus": "voided"},
                ],
            )
        )
        result = await built.server.call_tool(
            "payroll_superbatch_status",
            {"client_id": "ACME", "start_date": "2026-03-01", "end_date": "2026-03-31"},
        )
    data = _structured(result)
    assert data["batch_count"] == 3
    assert data["total_vouchers"] == 17
    assert data["posted_batch_count"] == 1
    assert data["open_batch_count"] == 1
    assert data["voided_batch_count"] == 1


# ---------- payroll_register_reconcile ----------


async def test_register_reconcile_matches_within_threshold(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_BILLING_CODE_TOTALS).mock(
            return_value=httpx.Response(200, json=[{"amount": 10000}])
        )
        mock.get(PATH_VOUCHERS_FOR_EMPLOYEE).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"voucherId": "V1", "grossAmount": 5000},
                    {"voucherId": "V2", "grossAmount": 5000},
                ],
            )
        )
        result = await built.server.call_tool(
            "payroll_register_reconcile",
            {"client_id": "ACME", "batch_id": "B1"},
        )
    data = _structured(result)
    assert data["reconciled"] is True
    assert data["delta"] == "0"


async def test_register_reconcile_flags_mismatch(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_BILLING_CODE_TOTALS).mock(
            return_value=httpx.Response(200, json=[{"amount": 10000}])
        )
        mock.get(PATH_VOUCHERS_FOR_EMPLOYEE).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"voucherId": "V1", "grossAmount": 4500},
                    {"voucherId": "V2", "grossAmount": 5000},
                ],
            )
        )
        result = await built.server.call_tool(
            "payroll_register_reconcile",
            {"client_id": "ACME", "batch_id": "B1"},
        )
    data = _structured(result)
    assert data["reconciled"] is False
    assert "MISMATCH" in data["message"]


# ---------- write stubs ----------


async def test_void_workflow_returns_not_implemented_when_scope_granted(runtime) -> None:  # noqa: ANN001
    from prismhr_mcp.permissions import Scope

    runtime.permissions.grant([Scope.PAYROLL_WRITE])  # cascade-includes PAYROLL_READ, CLIENT_READ
    built = build(runtime=runtime)
    result = await built.server.call_tool(
        "payroll_void_workflow",
        {"client_id": "ACME", "voucher_id": "V1", "reason": "duplicate payroll"},
    )
    data = _structured(result)
    assert data["code"] == "NOT_YET_IMPLEMENTED"
    assert "Phase 6" in data["planned_for"]


async def test_void_workflow_denied_without_scope(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    with pytest.raises(Exception) as exc_info:
        await built.server.call_tool(
            "payroll_void_workflow",
            {"client_id": "ACME", "voucher_id": "V1", "reason": "dup"},
        )
    assert "payroll:write" in str(exc_info.value) or "PERMISSION_NOT_GRANTED" in str(exc_info.value)
