"""Integration tests for Group 2 — OSS basic payroll tools."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from prismhr_mcp.auth.prismhr_session import LOGIN_PATH
from prismhr_mcp.server import build
from prismhr_mcp.tools.payroll import (
    PATH_BATCH_LIST,
    PATH_GET_EMPLOYEE,
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
                    {"batchId": "B2", "payDate": "2026-03-22", "grossTotal": 9800, "batchStatus": "open", "voucherCount": 11},
                ],
            )
        )
        result = await built.server.call_tool(
            "payroll_batch_status",
            {"client_id": "ACME", "start_date": "2026-03-01", "end_date": "2026-03-31"},
        )
    data = _structured(result)
    assert data["count"] == 2
    assert data["batches"][0]["batch_id"] == "B1"


# ---------- payroll_pay_history ----------


async def test_payroll_pay_history_with_ytd(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_VOUCHERS_FOR_EMPLOYEE).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"voucherId": "V1", "payDate": "2026-04-01", "grossAmount": 2000, "netAmount": 1600, "regularHours": 40},
                    {"voucherId": "V2", "payDate": "2026-04-15", "grossAmount": 2100, "netAmount": 1680, "regularHours": 42},
                ],
            )
        )
        mock.get(PATH_YTD).mock(
            return_value=httpx.Response(
                200,
                json={
                    "asOfDate": "2026-04-30",
                    "grossYTD": 8400,
                    "netYTD": 6720,
                    "federalTaxYTD": 1000,
                },
            )
        )
        result = await built.server.call_tool(
            "payroll_pay_history",
            {
                "client_id": "ACME",
                "employee_id": "E1",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
            },
        )
    data = _structured(result)
    assert data["count"] == 2
    assert data["ytd"]["gross_ytd"] == "8400"


async def test_payroll_pay_history_always_fetches_ytd(runtime) -> None:  # noqa: ANN001
    """YTD knob removed on purpose — always-on."""
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_VOUCHERS_FOR_EMPLOYEE).mock(return_value=httpx.Response(200, json=[]))
        ytd_route = mock.get(PATH_YTD).mock(
            return_value=httpx.Response(200, json={"asOfDate": "2026-04-30"})
        )
        await built.server.call_tool(
            "payroll_pay_history",
            {
                "client_id": "ACME",
                "employee_id": "E1",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
            },
        )
    assert ytd_route.called


# ---------- payroll_pay_group_check ----------


async def test_pay_group_check_reports_assigned(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.post(PATH_GET_EMPLOYEE).mock(
            return_value=httpx.Response(
                200,
                json=[{"payGroupId": "WEEKLY", "payGroupName": "Weekly", "payFrequency": "weekly"}],
            )
        )
        result = await built.server.call_tool(
            "payroll_pay_group_check",
            {"client_id": "ACME", "employee_id": "E1"},
        )
    data = _structured(result)
    assert data["assigned"] is True
    assert data["pay_group_id"] == "WEEKLY"


async def test_pay_group_check_warns_when_unassigned(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.post(PATH_GET_EMPLOYEE).mock(return_value=httpx.Response(200, json=[{}]))
        result = await built.server.call_tool(
            "payroll_pay_group_check",
            {"client_id": "ACME", "employee_id": "E1"},
        )
    data = _structured(result)
    assert data["assigned"] is False
    assert "no pay group assigned" in (data["warning"] or "").lower()


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
