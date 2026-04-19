"""Meta tools — liveness + permission consent flow.

Permission flow:
  1. User connects the MCP. No consent file exists → nothing is granted.
  2. User asks Claude: "what can this server do?" → Claude calls
     `meta_request_permissions` and shows the manifest with recommended
     defaults. User reviews.
  3. User accepts or tweaks → Claude calls `meta_grant_permissions`.
  4. Tools are now callable per the granted set. Ungranted tools return
     a structured `PERMISSION_NOT_GRANTED` error with remediation.

These meta tools never require scope — they're what you use to ESTABLISH
scope, so gating them would be a chicken-and-egg problem.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import __version__
from ..clients.prismhr import PrismHRClient
from ..models.about import AboutResponse, CommercialTier
from ..models.meta import PingResponse
from pydantic import BaseModel
from ..models.permissions import (
    PermissionCurrentResponse,
    PermissionGrantResponse,
    PermissionManifestResponse,
    ScopeEntry,
)
from ..permissions import (
    MANIFEST,
    PermissionManager,
    Scope,
    manifest_by_category,
)
from ..permissions import scopes as _scopes  # noqa: F401 — keeps module importable for lookup
from ..registry import ToolRegistry


class UpstreamPermissionsResponse(BaseModel):
    """What PrismHR authorizes the current API account to call.

    Distinct from `meta_list_permissions` — that's which tools the MCP
    user has opted into locally; this is what the PrismHR admin granted
    upstream. Tools that map to unauthorized services will 403 even if
    the MCP scope is granted.
    """

    authorized_method_count: int
    services_by_prefix: dict[str, int]
    methods: list[str]
    error: str | None = None


def register(
    server: FastMCP,
    registry: ToolRegistry,
    permissions: PermissionManager,
    prismhr: PrismHRClient,
) -> None:
    async def meta_ping() -> PingResponse:
        """Health check. Returns server name, version, and UTC time.

        Always callable — no scope required. Use this to confirm the server
        is reachable before worrying about credentials or permissions.
        """
        return PingResponse(
            server="prismhr-mcp",
            version=__version__,
            utc=datetime.now(timezone.utc),
            status="ok",
        )

    async def meta_request_permissions() -> PermissionManifestResponse:
        """List every scope the server can request, grouped by category.

        Returns: the full manifest, which scopes are currently granted,
        the server's recommended defaults (reads = yes, writes = no),
        and a human-readable message to show the user. Call
        `meta_grant_permissions` next with the scopes the user approves.
        """
        granted = permissions.granted
        by_cat = manifest_by_category()
        categories: dict[str, list[ScopeEntry]] = {}
        for category, specs in by_cat.items():
            if not specs:
                continue
            categories[category.value] = [
                ScopeEntry(
                    scope=spec.scope.value,
                    category=category.value,
                    label=spec.label,
                    description=spec.description,
                    risk=spec.risk,
                    recommended_default=spec.recommended_default,
                    endpoints=list(spec.endpoints),
                    tools=list(spec.tools),
                    requires=[r.value for r in spec.requires],
                    currently_granted=(spec.scope in granted),
                )
                for spec in specs
            ]

        recommended = [s.scope.value for s in MANIFEST if s.recommended_default]
        state = permissions.state

        user_msg = _build_user_message(state.granted, recommended, categories)

        return PermissionManifestResponse(
            environment=state.environment or "",
            peo_id=state.peo_id or "",
            consent_file=str(_consent_path(permissions)),
            granted=sorted(s.value for s in granted),
            total_scopes=len(MANIFEST),
            granted_count=len(granted),
            categories=categories,
            recommended_defaults=recommended,
            user_message=user_msg,
        )

    async def meta_grant_permissions(
        granted: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Scopes to ADD to the current grant set. Use scope identifiers "
                    "from meta_request_permissions (e.g. 'client:read')."
                ),
            ),
        ] = None,
        revoked: Annotated[
            list[str] | None,
            Field(
                description="Scopes to REMOVE from the current grant set.",
            ),
        ] = None,
        replace: Annotated[
            bool,
            Field(
                description=(
                    "If true, replace the entire granted set with `granted` "
                    "(ignores `revoked`). Use for 'start fresh' flows."
                ),
            ),
        ] = False,
        accept_recommended_defaults: Annotated[
            bool,
            Field(
                description=(
                    "If true, grant exactly the scopes flagged as recommended "
                    "in the manifest (reads only). Combines with `granted` as union."
                ),
            ),
        ] = False,
    ) -> PermissionGrantResponse:
        """Grant, revoke, or replace the set of scopes this server may use.

        Prerequisite scopes are auto-included: granting 'employee:read' also
        grants 'client:read' because the search tool needs it. Revoking a
        prerequisite cascades — dependent scopes get dropped to stay consistent.
        """
        before = set(permissions.granted)

        asked_granted = [Scope(s) for s in (granted or [])]
        if accept_recommended_defaults:
            asked_granted.extend(
                spec.scope for spec in MANIFEST if spec.recommended_default
            )

        if replace:
            new_state = permissions.replace(asked_granted)
        else:
            if asked_granted:
                permissions.grant(asked_granted)
            if revoked:
                permissions.revoke([Scope(s) for s in revoked])
            new_state = permissions.state

        after = set(new_state.granted)
        added = sorted(s.value for s in (after - before))
        removed = sorted(s.value for s in (before - after))

        msg = _grant_message(added, removed, after)

        return PermissionGrantResponse(
            granted=sorted(s.value for s in after),
            granted_count=len(after),
            added=added,
            removed=removed,
            consent_file=str(_consent_path(permissions)),
            user_message=msg,
        )

    async def meta_list_permissions() -> PermissionCurrentResponse:
        """Show the currently granted scopes without the full manifest.

        Use this when you just want to know what's active right now.
        Use meta_request_permissions to see the full catalog.
        """
        state = permissions.state
        return PermissionCurrentResponse(
            environment=state.environment or "",
            peo_id=state.peo_id or "",
            granted=sorted(s.value for s in permissions.granted),
            granted_count=len(permissions.granted),
            consent_file=str(_consent_path(permissions)),
        )

    async def meta_about() -> AboutResponse:
        """Describe what this MCP server is, who runs it, and what commercial options exist.

        Always callable — no scope required. Surfaces commercial offerings
        (Solution Architect white-label, Enterprise support) so Claude can
        help users understand what's available beyond the free OSS core.
        """
        return AboutResponse(
            server="prismhr-mcp",
            version=__version__,
            description=(
                "Open-source Model Context Protocol server that exposes PrismHR "
                "PEO workflows and Microsoft 365 connectors as composable tools "
                "for Claude and other MCP-aware agents. Designed as the "
                "fundamental layer for PrismHR × agentic AI."
            ),
            homepage="https://github.com/nikulk2992-jpg/prismhr-mcp",
            license="MIT",
            source_repository="https://github.com/nikulk2992-jpg/prismhr-mcp",
            reference_deployment=(
                "Simploy, Inc. — a PEO running its internal ops on top of this server. "
                "Simploy maintains the project and funds ongoing development."
            ),
            tool_groups_live=["meta", "client", "payroll"],
            tool_groups_planned=[
                "benefits",
                "compliance",
                "billing",
                "report",
                "m365",
            ],
            commercial_support=[
                CommercialTier(
                    name="Solution Architect — White-Label",
                    tagline=(
                        "Turnkey deployment of prismhr-mcp for your PEO brand: "
                        "custom tools, client SharePoint mapping, Graph tenant "
                        "setup, branded reporting assets, and staff training."
                    ),
                    includes=[
                        "Brand config authoring (logo, palette, typography, footer)",
                        "Per-client SharePoint site mapping + Graph tenant setup",
                        "Custom PrismHR tool development for PEO-specific workflows",
                        "Migration from spreadsheets / legacy scripts to MCP tools",
                        "PEO ops team onboarding + Claude workflow coaching",
                        "Quarterly updates aligned with upstream releases",
                        "Priority issue response + named slack/email contact",
                    ],
                    suited_for=(
                        "PEOs with 50–5,000 clients who want Claude/Cowork-first "
                        "operations without building the plumbing themselves."
                    ),
                    contact="nihar@simploy.com",
                ),
                CommercialTier(
                    name="Enterprise Support",
                    tagline=(
                        "SLA-backed support for teams already running prismhr-mcp "
                        "and need predictable response times + security review."
                    ),
                    includes=[
                        "4-hour response SLA on Sev-1 (prod outage) tickets",
                        "Annual security review + SOC-2-friendly deployment guidance",
                        "Signed release artifacts + SBOM",
                        "Private vulnerability disclosure channel",
                    ],
                    suited_for=(
                        "Mid/large PEOs in regulated industries or with existing "
                        "procurement requirements."
                    ),
                    contact="nihar@simploy.com",
                ),
            ],
        )

    async def meta_upstream_permissions() -> UpstreamPermissionsResponse:
        """Ask PrismHR which API methods this account is actually allowed to call.

        Calls `/login/v1/getAPIPermissions`. If the account lacks a method,
        even a fully-scope-granted MCP tool will 403 at the PrismHR edge.
        Use this to diagnose 'permission denied' errors when
        `meta_list_permissions` shows the scope is granted.

        Always callable — no scope required.
        """
        try:
            raw = await prismhr.get("/login/v1/getAPIPermissions")
        except Exception as exc:  # noqa: BLE001
            return UpstreamPermissionsResponse(
                authorized_method_count=0,
                services_by_prefix={},
                methods=[],
                error=f"getAPIPermissions failed: {exc}",
            )

        methods: list[str] = []
        if isinstance(raw, dict):
            cp = raw.get("currentPermissions") or {}
            allowed = cp.get("allowedMethods") if isinstance(cp, dict) else None
            if isinstance(allowed, list):
                for item in allowed:
                    if isinstance(item, dict) and item.get("service"):
                        methods.append(str(item["service"]))

        methods.sort()
        by_prefix: dict[str, int] = {}
        for m in methods:
            prefix = m.split(".", 1)[0]
            by_prefix[prefix] = by_prefix.get(prefix, 0) + 1

        return UpstreamPermissionsResponse(
            authorized_method_count=len(methods),
            services_by_prefix=dict(sorted(by_prefix.items(), key=lambda kv: -kv[1])),
            methods=methods,
        )

    registry.register(server, "meta_ping", meta_ping)
    registry.register(server, "meta_about", meta_about)
    registry.register(server, "meta_request_permissions", meta_request_permissions)
    registry.register(server, "meta_grant_permissions", meta_grant_permissions)
    registry.register(server, "meta_list_permissions", meta_list_permissions)
    registry.register(server, "meta_upstream_permissions", meta_upstream_permissions)


def _consent_path(permissions: PermissionManager) -> str:
    # Access the underlying store — kept simple for now.
    store = permissions._store  # noqa: SLF001
    return store.path


def _build_user_message(
    granted_set: set[Scope],
    recommended: list[str],
    categories: dict[str, list[ScopeEntry]],
) -> str:
    if granted_set:
        return (
            f"{len(granted_set)} scopes granted. "
            f"Call meta_grant_permissions to adjust. "
            f"Use replace=true to start fresh."
        )

    summary_lines = []
    for cat, entries in categories.items():
        entries_summary = ", ".join(
            f"{e.scope}{'*' if e.recommended_default else ''}" for e in entries
        )
        summary_lines.append(f"- {cat}: {entries_summary}")
    joined = "\n".join(summary_lines)

    return (
        "No scopes are currently granted — the server cannot touch PrismHR "
        "or Microsoft 365 until you approve something. Scopes marked with * "
        "are the server's recommended defaults (reads only; nothing that "
        "modifies live data).\n\n"
        f"{joined}\n\n"
        "To accept the recommended defaults, call meta_grant_permissions "
        "with accept_recommended_defaults=true. To pick specific scopes, "
        "pass them in the `granted` list."
    )


def _grant_message(added: list[str], removed: list[str], after: set[Scope]) -> str:
    bits: list[str] = []
    if added:
        bits.append(f"Granted {len(added)}: {', '.join(added)}")
    if removed:
        bits.append(f"Revoked {len(removed)}: {', '.join(removed)}")
    if not bits:
        bits.append("No changes.")
    bits.append(f"Total granted: {len(after)}.")
    return " ".join(bits)
