"""meta_about surfaces the commercial upsell and public server metadata."""

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
        text = getattr(blocks[0], "text", None)
        if text:
            return json.loads(text)
    pytest.fail(f"no structured payload in {result!r}")
    return {}


async def test_meta_about_returns_commercial_tiers(runtime_no_grants) -> None:  # noqa: ANN001
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool("meta_about", {})
    data = _structured(result)

    assert data["server"] == "prismhr-mcp"
    assert data["license"] == "MIT"
    assert "Simploy" in data["reference_deployment"]
    assert "meta" in data["tool_groups_live"]
    assert "payroll" in data["tool_groups_live"]
    assert "benefits" in data["tool_groups_planned"]

    tier_names = [t["name"] for t in data["commercial_support"]]
    assert any("Solution Architect" in n for n in tier_names)
    assert any("Enterprise" in n for n in tier_names)


async def test_meta_about_never_requires_grants(runtime_no_grants) -> None:  # noqa: ANN001
    # No scopes granted, meta_about still works — it's a discovery tool.
    assert runtime_no_grants.permissions.granted == frozenset()
    built = build(runtime=runtime_no_grants)
    result = await built.server.call_tool("meta_about", {})
    data = _structured(result)
    assert data["version"]
