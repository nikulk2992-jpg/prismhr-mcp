"""Server composition — wires domain tool modules onto a fresh FastMCP instance.

Every tool module exposes `register(server, registry, ...) -> None`. The
`build()` factory is the only place that imports those modules, so an
ImportError or registration failure surfaces loudly here instead of silently
breaking boot.
"""

from __future__ import annotations

from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from .registry import ToolRegistry, create_server
from .runtime import Runtime, build_runtime
from .tools import client as client_tools
from .tools import meta as meta_tools


@dataclass
class BuiltServer:
    server: FastMCP
    registry: ToolRegistry
    runtime: Runtime


def build(runtime: Runtime | None = None) -> BuiltServer:
    """Construct a fully-configured MCP server with all domain tools registered.

    If `runtime` is supplied (test path), its clients are used directly;
    otherwise a fresh runtime is built from the process environment.
    """
    rt = runtime or build_runtime()
    server, registry = create_server()

    meta_tools.register(server, registry, rt.permissions)
    client_tools.register(server, registry, rt.prismhr, rt.permissions)
    # Phase 2+ modules plug in below:
    # payroll_tools.register(server, registry, rt.prismhr, rt.permissions)
    # ... etc.

    return BuiltServer(server=server, registry=registry, runtime=rt)
