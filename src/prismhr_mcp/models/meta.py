"""Shared output models for the `meta` tool group."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PingResponse(BaseModel):
    """Output of `meta_ping` — server liveness probe."""

    server: str = Field(description="Server identifier (constant).")
    version: str = Field(description="Installed package version.")
    utc: datetime = Field(description="Current server UTC time.")
    status: str = Field(description='"ok" when the server is serving requests.')
