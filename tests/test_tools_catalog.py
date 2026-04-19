"""Catalog tool tests — meta_capabilities, meta_describe, meta_find, meta_call."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from prismhr_mcp.auth.prismhr_session import LOGIN_PATH
from prismhr_mcp.permissions import Scope
from prismhr_mcp.server import build


def _structured(result) -> dict | list:  # noqa: ANN001
    if isinstance(result, tuple) and len(result) == 2 and result[1] is not None:
        return result[1]
    blocks = result[0] if isinstance(result, tuple) else result
    if blocks:
        text = getattr(blocks[0], "text", None)
        if text:
            return json.loads(text)
    pytest.fail(f"no structured payload in {result!r}")
    return {}


# ---- meta_capabilities ----


async def test_meta_capabilities_always_callable(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool("meta_capabilities", {})
    data = _structured(result)
    assert data["catalog_size"] > 0
    assert data["verified_count"] >= 0
    assert isinstance(data["services"], list)
    assert isinstance(data["sample_verified"], list)


async def test_meta_capabilities_service_filter(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool(
        "meta_capabilities", {"service": "payroll"}
    )
    data = _structured(result)
    assert "payroll" in data["services"]
    # All sampled should be payroll
    for entry in data["sample_verified"]:
        assert entry["service"] == "payroll"


# ---- meta_describe ----


async def test_meta_describe_returns_contract(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool(
        "meta_describe", {"method_id": "payroll.v1.getBatchListByDate.GET"}
    )
    data = _structured(result)
    assert data["path"] == "/payroll/v1/getBatchListByDate"
    assert data["http_method"] == "GET"
    params = {p["name"] for p in data["parameters"]}
    assert "clientId" in params
    assert "startDate" in params


async def test_meta_describe_flags_admin_services(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool(
        "meta_describe", {"method_id": "login.v1.createPeoSession.POST"}
    )
    data = _structured(result)
    assert data["is_admin"] is True
    assert data["remediation_if_admin"] is not None


async def test_meta_describe_unknown_method_errors(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    with pytest.raises(Exception) as exc_info:
        await built.server.call_tool(
            "meta_describe", {"method_id": "fake.v1.notAMethod.GET"}
        )
    assert "UNKNOWN_METHOD_ID" in str(exc_info.value)


# ---- meta_find ----


async def test_meta_find_returns_matches(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool(
        "meta_find", {"query": "payroll batch"}
    )
    data = _structured(result)
    # FastMCP wraps list returns in {"result": [...]}.
    matches = data["result"] if isinstance(data, dict) and "result" in data else data
    assert isinstance(matches, list)
    assert matches, "should find at least one match"
    assert any("batch" in m["method_id"].lower() for m in matches)


# ---- meta_call ----


async def test_meta_call_requires_scope(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    with pytest.raises(Exception) as exc_info:
        await built.server.call_tool(
            "meta_call",
            {"method_id": "payroll.v1.getPayrollScheduleCodes.GET", "args": {}},
        )
    assert "catalog:call" in str(exc_info.value) or "PERMISSION_NOT_GRANTED" in str(
        exc_info.value
    )


async def test_meta_call_admin_blocked(runtime) -> None:  # noqa: ANN001
    runtime.permissions.grant([Scope.CATALOG_CALL])
    built = build(runtime=runtime)
    result = await built.server.call_tool(
        "meta_call",
        {"method_id": "login.v1.createPeoSession.POST", "args": {"body": {"username": "x"}}},
    )
    data = _structured(result)
    assert data["status"] == "admin_blocked"


async def test_meta_call_validation_error(runtime) -> None:  # noqa: ANN001
    runtime.permissions.grant([Scope.CATALOG_CALL])
    built = build(runtime=runtime)
    # getBatchListByDate needs clientId, startDate, endDate, dateType
    result = await built.server.call_tool(
        "meta_call",
        {"method_id": "payroll.v1.getBatchListByDate.GET", "args": {}},
    )
    data = _structured(result)
    assert data["status"] == "validation_error"
    assert "clientId" in data["note"]


async def test_meta_call_ok_passes_through(runtime) -> None:  # noqa: ANN001
    runtime.permissions.grant([Scope.CATALOG_CALL])
    built = build(runtime=runtime)

    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        mock.post(LOGIN_PATH).mock(
            return_value=httpx.Response(200, json={"sessionId": "t"})
        )
        mock.get("/payroll/v1/getPayrollScheduleCodes").mock(
            return_value=httpx.Response(
                200,
                json={
                    "payrollScheduleCodes": [
                        {"scheduleCode": "W1", "description": "Weekly"}
                    ],
                    "errorCode": "0",
                    "errorMessage": "",
                },
            )
        )
        result = await built.server.call_tool(
            "meta_call",
            {
                "method_id": "payroll.v1.getPayrollScheduleCodes.GET",
                "args": {},
            },
        )
    data = _structured(result)
    # Either ok (if verified) or unverified_warning; body should be present either way.
    assert data["status"] in {"ok", "unverified_warning"}
    assert data["body"] is not None
