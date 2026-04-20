"""Commercial payroll-compliance tool tests.

Moved from tests/test_tools_payroll.py when the 5 tools migrated to
commercial tier (dev52).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from prismhr_mcp.auth.prismhr_session import LOGIN_PATH  # noqa: E402
from prismhr_mcp.permissions import Scope  # noqa: E402
from prismhr_mcp.registry import create_server  # noqa: E402


def _login_ok(mock: respx.Router) -> None:
    mock.post(LOGIN_PATH).mock(return_value=httpx.Response(200, json={"token": "t"}))


def _structured(result) -> dict:
    if isinstance(result, tuple) and len(result) == 2 and result[1] is not None:
        return result[1]
    blocks = result[0] if isinstance(result, tuple) else result
    if blocks:
        text = getattr(blocks[0], "text", None)
        if text:
            return json.loads(text)
    pytest.fail(f"no structured payload in {result!r}")
    return {}


def _build_commercial_server(runtime):
    """Build a server with the commercial payroll_compliance tools registered."""
    from simploy.tools.payroll_compliance import register_payroll_compliance_tools
    server, registry = create_server()
    register_payroll_compliance_tools(server, registry, runtime.prismhr, runtime.permissions)
    return server


# ---------- deduction_conflicts ----------


async def test_deduction_conflicts_surfaces_priority_clash(runtime) -> None:
    server = _build_commercial_server(runtime)
    path = "/employee/v1/getScheduledDeductions"
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(path).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"status": "active", "code": "401K", "priority": 10},
                    {"status": "active", "code": "GARN", "priority": 10},
                ],
            )
        )
        result = await server.call_tool(
            "commercial_payroll_deduction_conflicts",
            {"client_id": "ACME", "employee_id": "E1"},
        )
    data = _structured(result)
    assert data["scanned_count"] == 2
    assert "priority_clash" in [c["kind"] for c in data["conflicts"]]


# ---------- overtime_anomalies ----------


async def test_overtime_anomalies_flag_excessive(runtime) -> None:
    server = _build_commercial_server(runtime)
    path = "/payroll/v1/getPayrollVouchersForEmployee"
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(path).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"voucherId": "V1", "payDate": "2026-04-01",
                     "regularHours": 40, "overtimeHours": 45,
                     "regularAmount": 800, "overtimeAmount": 1350},
                ],
            )
        )
        result = await server.call_tool(
            "commercial_payroll_overtime_anomalies",
            {
                "client_id": "ACME", "employee_id": "E1",
                "start_date": "2026-04-01", "end_date": "2026-04-30",
            },
        )
    data = _structured(result)
    assert "excessive_overtime" in {a["kind"] for a in data["anomalies"]}


# ---------- register_reconcile ----------


async def test_register_reconcile_matches_within_threshold(runtime) -> None:
    server = _build_commercial_server(runtime)
    billing_path = "/payroll/v1/getBillingCodeTotalsForBatch"
    vouchers_path = "/payroll/v1/getPayrollVouchersForEmployee"
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(billing_path).mock(
            return_value=httpx.Response(200, json=[{"amount": 10000}])
        )
        mock.get(vouchers_path).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"voucherId": "V1", "grossAmount": 5000},
                    {"voucherId": "V2", "grossAmount": 5000},
                ],
            )
        )
        result = await server.call_tool(
            "commercial_payroll_register_reconcile",
            {"client_id": "ACME", "batch_id": "B1"},
        )
    data = _structured(result)
    assert data["reconciled"] is True
    assert data["delta"] == "0"


async def test_register_reconcile_flags_mismatch(runtime) -> None:
    server = _build_commercial_server(runtime)
    billing_path = "/payroll/v1/getBillingCodeTotalsForBatch"
    vouchers_path = "/payroll/v1/getPayrollVouchersForEmployee"
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(billing_path).mock(
            return_value=httpx.Response(200, json=[{"amount": 10000}])
        )
        mock.get(vouchers_path).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"voucherId": "V1", "grossAmount": 4500},
                    {"voucherId": "V2", "grossAmount": 5000},
                ],
            )
        )
        result = await server.call_tool(
            "commercial_payroll_register_reconcile",
            {"client_id": "ACME", "batch_id": "B1"},
        )
    data = _structured(result)
    assert data["reconciled"] is False
    assert "MISMATCH" in data["message"]


# ---------- void / correction workflow stubs ----------


async def test_void_workflow_returns_deferred(runtime) -> None:
    runtime.permissions.grant([Scope.PAYROLL_WRITE])
    server = _build_commercial_server(runtime)
    result = await server.call_tool(
        "commercial_payroll_void_workflow",
        {"client_id": "ACME", "voucher_id": "V1", "reason": "test"},
    )
    data = _structured(result)
    assert data["code"] == "NOT_YET_IMPLEMENTED"


async def test_correction_workflow_returns_deferred(runtime) -> None:
    runtime.permissions.grant([Scope.PAYROLL_WRITE])
    server = _build_commercial_server(runtime)
    result = await server.call_tool(
        "commercial_payroll_correction_workflow",
        {"client_id": "ACME", "voucher_id": "V1", "corrections": {}},
    )
    data = _structured(result)
    assert data["code"] == "NOT_YET_IMPLEMENTED"
