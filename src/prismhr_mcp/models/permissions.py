"""Response models for the permission-management meta tools."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScopeEntry(BaseModel):
    scope: str
    category: str
    label: str
    description: str
    risk: str
    recommended_default: bool
    endpoints: list[str]
    tools: list[str]
    requires: list[str]
    currently_granted: bool


class PermissionManifestResponse(BaseModel):
    """What the MCP can do + what the user has granted so far."""

    environment: str
    peo_id: str
    consent_file: str
    granted: list[str]
    total_scopes: int
    granted_count: int
    categories: dict[str, list[ScopeEntry]]
    recommended_defaults: list[str]
    user_message: str = Field(
        description=(
            "Guidance to show the end user when surfacing this manifest. "
            "Enumerates categories and invites them to call meta_grant_permissions."
        ),
    )


class PermissionGrantResponse(BaseModel):
    """Result of a grant/revoke/replace operation."""

    granted: list[str]
    granted_count: int
    added: list[str]
    removed: list[str]
    consent_file: str
    user_message: str


class PermissionCurrentResponse(BaseModel):
    environment: str
    peo_id: str
    granted: list[str]
    granted_count: int
    consent_file: str
