"""Server factory + strict tool registration.

Centralizes FastMCP instance creation so tool modules receive an explicit
server handle instead of importing a module-level singleton. Prevents the
failure mode where one bad tool-module import kills the whole server boot.

Also enforces unique tool names and a naming convention (`<group>_<verb>`),
because FastMCP's built-in duplicate handling only warns (mcp 1.27).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

# Tool groups — keep in sync with the plan. Every tool name MUST start with
# one of these prefixes so Claude and humans can locate it by domain.
TOOL_GROUPS: frozenset[str] = frozenset(
    {
        "meta",        # ping, list_report_templates, etc.
        "client",      # Group 1 (clients & employees)
        "payroll",     # Group 2
        "benefits",    # Group 3
        "compliance",  # Group 4
        "billing",     # Group 5
        "report",      # Group 6 (branded reporting)
        "m365",        # Group 7 (Microsoft 365 connectors)
        "commercial",  # Paid tier (simploy.* modules) — separate namespace
    }
)

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class ToolRegistry:
    """Tracks registered tool names to catch collisions at boot."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def register(self, server: FastMCP, name: str, fn: Callable[..., Any], **kwargs: Any) -> None:
        """Register `fn` as an MCP tool under `name`. Fails fast on duplicates or bad names."""
        self._validate(name)
        server.tool(name=name, **kwargs)(fn)
        self._seen.add(name)

    def _validate(self, name: str) -> None:
        if name in self._seen:
            raise RuntimeError(f"Duplicate MCP tool name: {name!r}")
        if not _NAME_RE.match(name):
            raise RuntimeError(
                f"Invalid tool name {name!r}: must match {_NAME_RE.pattern}"
            )
        group = name.split("_", 1)[0]
        if group not in TOOL_GROUPS:
            raise RuntimeError(
                f"Tool {name!r} must start with one of {sorted(TOOL_GROUPS)} (got {group!r})"
            )

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self._seen)


def create_server() -> tuple[FastMCP, ToolRegistry]:
    """Build a fresh FastMCP server and empty registry.

    Tool modules should expose `def register(server, registry) -> None` and
    be wired from `server.py`, not via module-level decorators. This keeps
    import order explicit and means a broken tool module fails loudly at
    registration time, not silently at import time.
    """
    server = FastMCP("prismhr-mcp")
    registry = ToolRegistry()
    return server, registry
