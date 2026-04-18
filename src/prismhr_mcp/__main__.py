"""Entry point: `uvx prismhr-mcp` → stdio MCP server."""

from __future__ import annotations

import asyncio

from .server import build


def main() -> None:
    built = build()
    try:
        built.server.run()
    finally:
        asyncio.run(built.runtime.aclose())


if __name__ == "__main__":
    main()
