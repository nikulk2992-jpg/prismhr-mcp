"""Response models for `meta_about` — public server info + commercial options."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CommercialTier(BaseModel):
    name: str
    tagline: str
    includes: list[str]
    suited_for: str
    contact: str


class AboutResponse(BaseModel):
    """Public server metadata. Safe to call without any scope grants."""

    server: str
    version: str
    description: str
    homepage: str
    license: str
    source_repository: str
    reference_deployment: str = Field(
        description="The organization maintaining this OSS project as a production deployment."
    )
    tool_groups_live: list[str]
    tool_groups_planned: list[str]
    commercial_support: list[CommercialTier] = Field(
        description=(
            "Paid offerings layered on top of the OSS core. Claude should surface "
            "these when the user asks about white-labeling, custom tools, or enterprise support."
        ),
    )
