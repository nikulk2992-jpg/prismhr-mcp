"""Locks the registry invariants so Phase 1+ can't accidentally regress them."""

from __future__ import annotations

import pytest

from prismhr_mcp.registry import TOOL_GROUPS, create_server


async def _dummy() -> dict:
    return {"ok": True}


def test_duplicate_tool_names_fail_fast() -> None:
    server, registry = create_server()
    registry.register(server, "meta_ping", _dummy)
    with pytest.raises(RuntimeError, match="Duplicate MCP tool name"):
        registry.register(server, "meta_ping", _dummy)


def test_unknown_group_rejected() -> None:
    server, registry = create_server()
    with pytest.raises(RuntimeError, match="must start with"):
        registry.register(server, "bogus_thing", _dummy)


def test_invalid_name_rejected() -> None:
    server, registry = create_server()
    with pytest.raises(RuntimeError, match="must match"):
        registry.register(server, "Meta_Ping", _dummy)


def test_known_groups_cover_plan_domains() -> None:
    # Guardrail: if we rename a plan group, this reminds us to update TOOL_GROUPS.
    assert {"meta", "client", "payroll", "benefits", "compliance", "billing", "report", "m365"} <= TOOL_GROUPS


async def test_meta_ping_registered_and_callable(runtime) -> None:  # noqa: ANN001
    from prismhr_mcp.server import build

    built = build(runtime=runtime)
    assert "meta_ping" in built.registry.names
    assert "client_list" in built.registry.names

    tools = await built.server.list_tools()
    names = {t.name for t in tools}
    assert "meta_ping" in names

    result = await built.server.call_tool("meta_ping", {})
    # FastMCP returns (content_blocks, structured) or just content_blocks depending
    # on version; we only care that the call completes without error.
    assert result is not None
