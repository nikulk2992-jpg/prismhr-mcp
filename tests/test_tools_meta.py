"""Meta tool tests — ping, permission request/grant/list flow."""

from __future__ import annotations

import json

import pytest

from prismhr_mcp.server import build


def _structured(result) -> dict:  # noqa: ANN001
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        if structured is not None:
            return structured
    blocks = result[0] if isinstance(result, tuple) else result
    if blocks:
        block = blocks[0]
        text = getattr(block, "text", None)
        if text:
            return json.loads(text)
    pytest.fail(f"no structured payload in {result!r}")
    return {}


async def test_meta_ping_has_no_scope_requirement(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool("meta_ping", {})
    data = _structured(result)
    assert data["server"] == "prismhr-mcp"
    assert data["status"] == "ok"


async def test_request_permissions_returns_full_manifest(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool("meta_request_permissions", {})
    data = _structured(result)
    assert data["granted_count"] == 0
    assert data["total_scopes"] > 0
    # Should include at least one recommended-default scope.
    assert "client:read" in data["recommended_defaults"]
    # Each category is a list of scope entries.
    assert "PrismHR — Read" in data["categories"]
    entries = data["categories"]["PrismHR — Read"]
    assert any(e["scope"] == "client:read" for e in entries)


async def test_grant_permissions_adds_and_persists(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool(
        "meta_grant_permissions",
        {"granted": ["client:read"]},
    )
    data = _structured(result)
    assert "client:read" in data["granted"]
    assert data["added"] == ["client:read"]
    assert runtime_no_grants.permissions.is_granted(
        runtime_no_grants.permissions.state.granted.__iter__().__next__()
    )


async def test_grant_accept_recommended_defaults(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool(
        "meta_grant_permissions",
        {"accept_recommended_defaults": True},
    )
    data = _structured(result)
    assert "client:read" in data["granted"]
    # Writes should NOT be granted by recommended defaults.
    assert "payroll:write" not in data["granted"]
    assert "m365:email:send" not in data["granted"]


async def test_grant_auto_includes_prerequisites(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool(
        "meta_grant_permissions",
        {"granted": ["employee:read"]},
    )
    data = _structured(result)
    # employee:read requires client:read — must be auto-added.
    assert "client:read" in data["granted"]
    assert "employee:read" in data["granted"]


async def test_revoke_removes_and_cascades(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    await built.server.call_tool(
        "meta_grant_permissions",
        {"granted": ["employee:read"]},  # also grants client:read
    )
    result = await built.server.call_tool(
        "meta_grant_permissions",
        {"revoked": ["client:read"]},
    )
    data = _structured(result)
    # client:read gone, employee:read cascade-removed.
    assert "client:read" not in data["granted"]
    assert "employee:read" not in data["granted"]


async def test_replace_starts_from_scratch(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    await built.server.call_tool(
        "meta_grant_permissions",
        {"granted": ["employee:read", "payroll:read"]},
    )
    result = await built.server.call_tool(
        "meta_grant_permissions",
        {"granted": ["billing:read"], "replace": True},
    )
    data = _structured(result)
    assert set(data["granted"]) == {"billing:read"}


async def test_list_permissions_reports_current_state(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    await built.server.call_tool(
        "meta_grant_permissions",
        {"granted": ["client:read"]},
    )
    result = await built.server.call_tool("meta_list_permissions", {})
    data = _structured(result)
    assert data["granted"] == ["client:read"]
    assert data["granted_count"] == 1


async def test_client_list_denied_when_no_grant(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    with pytest.raises(Exception) as exc_info:
        await built.server.call_tool("client_list", {})
    # FastMCP wraps tool errors; the string should surface the remediation.
    assert "PERMISSION_NOT_GRANTED" in str(exc_info.value) or "client:read" in str(exc_info.value)


async def test_client_list_works_after_granting(runtime_no_grants) -> None:  # noqa: ANN001
    import httpx
    import respx

    from prismhr_mcp.auth.prismhr_session import LOGIN_PATH
    from prismhr_mcp.tools.client import PATH_CLIENT_LIST

    built = build(runtime=runtime_no_grants)
    # Grant first.
    await built.server.call_tool(
        "meta_grant_permissions", {"granted": ["client:read"]}
    )

    with respx.mock(base_url=runtime_no_grants.settings.prismhr_base_url) as mock:
        mock.post(LOGIN_PATH).mock(return_value=httpx.Response(200, json={"token": "t"}))
        mock.get(PATH_CLIENT_LIST).mock(
            return_value=httpx.Response(
                200, json=[{"clientId": "ACME", "clientName": "Acme"}]
            )
        )
        result = await built.server.call_tool("client_list", {})
    data = _structured(result)
    assert data["count"] == 1
    assert data["clients"][0]["client_id"] == "ACME"
