"""Group 1 tool tests — client_list / client_employees / client_employee / search."""

from __future__ import annotations

import httpx
import pytest
import respx

from prismhr_mcp.auth.prismhr_session import LOGIN_PATH
from prismhr_mcp.server import build
from prismhr_mcp.tools.client import (
    PATH_CLIENT_LIST,
    PATH_EMPLOYEE,
    PATH_EMPLOYEE_LIST,
)


def _login_ok(mock: respx.Router) -> None:
    mock.post(LOGIN_PATH).mock(return_value=httpx.Response(200, json={"token": "t"}))


async def test_client_list_returns_typed_response(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    fn = built.registry._seen  # sanity: registered
    assert "client_list" in fn

    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_CLIENT_LIST).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"clientId": "ACME", "clientName": "Acme Corp", "statusType": "active"},
                    {"clientId": "BETA", "clientName": "Beta LLC", "statusType": "active"},
                ],
            )
        )
        result = await built.server.call_tool("client_list", {})
    # FastMCP returns tuple (content_blocks, structured). Grab structured.
    structured = _structured(result)
    assert structured["count"] == 2
    assert {c["client_id"] for c in structured["clients"]} == {"ACME", "BETA"}


async def test_client_employees_filters_status(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        route = mock.get(PATH_EMPLOYEE_LIST).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"employeeId": "E1", "firstName": "Ada", "lastName": "Lovelace", "statusType": "active"},
                    {"employeeId": "E2", "firstName": "Alan", "lastName": "Turing", "statusType": "active"},
                ],
            )
        )
        result = await built.server.call_tool(
            "client_employees", {"client_id": "ACME", "status": "active"}
        )
    structured = _structured(result)
    assert structured["client_id"] == "ACME"
    assert structured["count"] == 2
    request = route.calls.last.request
    assert "statusType=active" in str(request.url)
    assert "clientId=ACME" in str(request.url)


async def test_client_employee_batches_into_20s(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    ids = [f"E{i}" for i in range(45)]

    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)

        def handler(request: httpx.Request) -> httpx.Response:
            payload = request.read().decode()
            import json

            body = json.loads(payload)
            emp_ids = body["employeeIds"]
            return httpx.Response(
                200,
                json=[
                    {"employeeId": eid, "clientId": "ACME", "firstName": "X", "lastName": "Y"}
                    for eid in emp_ids
                ],
            )

        route = mock.post(PATH_EMPLOYEE).mock(side_effect=handler)
        result = await built.server.call_tool(
            "client_employee", {"client_id": "ACME", "employee_ids": ids}
        )

    structured = _structured(result)
    assert len(structured["employees"]) == 45
    assert structured["missing_ids"] == []
    assert route.call_count == 3  # 20 + 20 + 5


async def test_client_employee_reports_missing_ids(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.post(PATH_EMPLOYEE).mock(
            return_value=httpx.Response(
                200,
                json=[{"employeeId": "E1", "clientId": "ACME"}],
            )
        )
        result = await built.server.call_tool(
            "client_employee", {"client_id": "ACME", "employee_ids": ["E1", "E2"]}
        )
    structured = _structured(result)
    assert [e["employee_id"] for e in structured["employees"]] == ["E1"]
    assert structured["missing_ids"] == ["E2"]


async def test_client_employee_search_scopes_by_query(runtime) -> None:  # noqa: ANN001
    built = build(runtime=runtime)
    with respx.mock(base_url=runtime.settings.prismhr_base_url) as mock:
        _login_ok(mock)
        mock.get(PATH_CLIENT_LIST).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"clientId": "ACME", "clientName": "Acme"},
                    {"clientId": "BETA", "clientName": "Beta"},
                ],
            )
        )

        def emp_handler(request: httpx.Request) -> httpx.Response:
            cid = request.url.params["clientId"]
            if cid == "ACME":
                return httpx.Response(
                    200,
                    json=[
                        {"employeeId": "E1", "firstName": "Ada", "lastName": "Lovelace"},
                        {"employeeId": "E2", "firstName": "Bob", "lastName": "Smith"},
                    ],
                )
            return httpx.Response(
                200,
                json=[{"employeeId": "E9", "firstName": "Ada", "lastName": "Byron"}],
            )

        mock.get(PATH_EMPLOYEE_LIST).mock(side_effect=emp_handler)

        result = await built.server.call_tool(
            "client_employee_search", {"query": "ada"}
        )

    structured = _structured(result)
    assert structured["searched_clients"] == 2
    assert structured["count"] == 2
    ids = {m["employee_id"] for m in structured["matches"]}
    assert ids == {"E1", "E9"}


# ---------- helpers ----------


def _structured(call_tool_result) -> dict:  # noqa: ANN001
    """Tolerant helper — FastMCP's `call_tool` return shape varies by version."""
    # Newer mcp versions return (content_blocks, structured_content).
    if isinstance(call_tool_result, tuple) and len(call_tool_result) == 2:
        _, structured = call_tool_result
        if structured is not None:
            return structured
    # Older versions return just content blocks; structured lives in the first
    # block's text (JSON) when the tool returns a Pydantic model.
    blocks = call_tool_result[0] if isinstance(call_tool_result, tuple) else call_tool_result
    if blocks:
        block = blocks[0]
        text = getattr(block, "text", None)
        if text:
            import json

            return json.loads(text)
    pytest.fail(f"Could not extract structured payload from {call_tool_result!r}")
    return {}
