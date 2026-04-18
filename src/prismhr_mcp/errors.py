"""Structured, PEO-meaningful errors surfaced via MCP tool responses.

Never let a raw HTTP status bubble to Claude. Every exception has a code,
a human-friendly message, and optional context for debugging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPError(Exception):
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    retriable: bool = False

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code}: {self.message}"


class PrismHRRequestError(MCPError):
    """PrismHR returned an HTTP error we couldn't recover from."""


class PrismHRAuthError(MCPError):
    """Session refresh kept failing — credentials likely wrong or account locked."""


class RateLimitedError(MCPError):
    """PrismHR or Graph throttled us. `context['retry_after']` if available."""
