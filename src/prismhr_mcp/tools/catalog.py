"""Catalog tools — meta_capabilities, meta_describe, prismhr_call.

These form the OSS core's tier-2 surface: verified raw access to every
PrismHR endpoint the bundled bible documents, with schema-backed argument
validation and explicit verification status per method.

Claude-visible contract:
  - `meta_capabilities` — 'What can this server do?' Returns verified vs
    unprobed counts, fixture-key coverage, and method lists (paginated).
  - `meta_describe` — 'Tell me about method X.' Returns full parameter,
    body, response contract + verification status.
  - `prismhr_call` — 'Call method X with these args.' Schema-validated
    invocation. Refuses admin services unconditionally.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..catalog import (
    Catalog,
    MethodContract,
    ValidationError,
    load_catalog,
    validate_args,
)
from ..catalog.catalog import ADMIN_ONLY_SERVICES
from ..clients.prismhr import PrismHRClient
from ..errors import MCPError
from ..permissions import PermissionManager, Scope
from ..registry import ToolRegistry


# ---------- response models ----------


class MethodSummary(BaseModel):
    method_id: str
    path: str
    http_method: str
    service: str
    operation: str
    summary: str
    verification_status: str
    is_admin: bool
    required_params: list[str]
    required_body_fields: list[str]


class CapabilitiesResponse(BaseModel):
    catalog_size: int = Field(description="Total endpoints documented in the bundled bible.")
    verified_count: int = Field(description="Endpoints with a response shape verified against live PrismHR.")
    admin_blocked_count: int = Field(description="Endpoints hard-blocked (admin services never exposed).")
    unprobed_count: int = Field(description="Endpoints documented but not yet probed for response shape.")
    prismhr_error_count: int = Field(description="Endpoints that returned a structured PrismHR error when probed (data, 400, 403, etc.).")
    services: list[str]
    sample_verified: list[MethodSummary] = Field(
        description="First 25 verified methods to help Claude pick relevant ones."
    )


class DescribeParameter(BaseModel):
    name: str
    location: str
    required: bool
    description: str | None = None


class DescribeBodyField(BaseModel):
    name: str
    type: str | None = None
    description: str | None = None
    required: bool = False
    format: str | None = None
    enum: list[str] | None = None


class DescribeResponseBlock(BaseModel):
    status: str
    description: str
    schema_refs: list[str] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)


class MethodDescribeResponse(BaseModel):
    method_id: str
    path: str
    http_method: str
    service: str
    operation: str
    summary: str
    description: str
    parameters: list[DescribeParameter]
    request_body_content_types: list[str] = Field(default_factory=list)
    request_body_required_fields: list[str] = Field(default_factory=list)
    request_body_fields: list[DescribeBodyField] = Field(default_factory=list)
    request_body_inline_schema_present: bool = False
    responses: list[DescribeResponseBlock]
    verification_status: str
    verified_response_keys: list[str] = Field(default_factory=list)
    is_admin: bool
    remediation_if_admin: str | None = None


class PrismHRCallResponse(BaseModel):
    method_id: str
    status: Literal["ok", "prismhr_error", "validation_error", "admin_blocked", "unverified_warning"]
    http_status: int | None = None
    prismhr_error_code: str | None = None
    prismhr_error_message: str | None = None
    body: Any = None
    note: str | None = None


# ---------- module-scope for catalog load ----------

_catalog: Catalog | None = None


def _get_catalog() -> Catalog:
    global _catalog
    if _catalog is None:
        _catalog = load_catalog()
    return _catalog


# ---------- register ----------


def register(
    server: FastMCP,
    registry: ToolRegistry,
    prismhr: PrismHRClient,
    permissions: PermissionManager,
) -> None:

    async def meta_capabilities(
        service: Annotated[
            str | None,
            Field(description="Optional service filter (e.g. 'payroll', 'clientMaster')."),
        ] = None,
        verified_only: Annotated[
            bool,
            Field(description="If true, `sample_verified` filters to verified methods only."),
        ] = True,
        limit: Annotated[
            int,
            Field(description="How many sample methods to include (max 100).", ge=1, le=100),
        ] = 25,
    ) -> CapabilitiesResponse:
        """What does this server know how to call against PrismHR?

        Returns counts (catalog size, verified, admin-blocked, unprobed) and
        a sample of callable methods. Use this when the user asks 'what can
        you do?' or before picking a specific method via `meta_describe`.
        """
        catalog = _get_catalog()
        all_methods = catalog.all()
        if service:
            all_methods = [m for m in all_methods if m.service == service]

        verified = [m for m in all_methods if m.is_verified]
        admin_blocked = [m for m in all_methods if m.is_admin]
        prismhr_err = [m for m in all_methods if m.verification_status == "prismhr_error"]
        unprobed = [m for m in all_methods if m.verification_status == "unprobed"]

        pool = verified if verified_only else all_methods
        sample = [
            MethodSummary(
                method_id=m.method_id,
                path=m.path,
                http_method=m.http_method,
                service=m.service,
                operation=m.operation,
                summary=m.summary,
                verification_status=m.verification_status,
                is_admin=m.is_admin,
                required_params=[p["name"] for p in m.required_params],
                required_body_fields=m.required_body_fields,
            )
            for m in pool[:limit]
        ]
        services = sorted({m.service for m in all_methods})
        return CapabilitiesResponse(
            catalog_size=len(all_methods),
            verified_count=len(verified),
            admin_blocked_count=len(admin_blocked),
            unprobed_count=len(unprobed),
            prismhr_error_count=len(prismhr_err),
            services=services,
            sample_verified=sample,
        )

    async def meta_describe(
        method_id: Annotated[
            str,
            Field(
                description=(
                    "Catalog method id, e.g. 'payroll.v1.getBatchListByDate.GET'. "
                    "Get candidates from meta_capabilities or by searching via meta_find."
                ),
            ),
        ],
    ) -> MethodDescribeResponse:
        """Full contract for a single PrismHR method.

        Returns every parameter, inline body schema (when available), response
        codes, and verification status. Call this before `prismhr_call` so
        you know exactly which args the method wants.
        """
        catalog = _get_catalog()
        try:
            m = catalog.require(method_id)
        except KeyError as exc:
            raise MCPError(
                code="UNKNOWN_METHOD_ID",
                message=(
                    f"No method with id {method_id!r} in the bundled catalog. "
                    "Call meta_capabilities or meta_find to see available ids."
                ),
            ) from exc

        return MethodDescribeResponse(
            method_id=m.method_id,
            path=m.path,
            http_method=m.http_method,
            service=m.service,
            operation=m.operation,
            summary=m.summary,
            description=m.description,
            parameters=[
                DescribeParameter(
                    name=p["name"],
                    location=p.get("location", "query"),
                    required=bool(p.get("required")),
                    description=p.get("description"),
                )
                for p in m.parameters
            ],
            request_body_content_types=(m.request_body or {}).get("content_types") or [],
            request_body_required_fields=(m.request_body or {}).get("required_fields") or [],
            request_body_fields=[
                DescribeBodyField(**{k: v for k, v in field.items() if k in DescribeBodyField.model_fields})
                for field in (m.request_body or {}).get("fields") or []
            ],
            request_body_inline_schema_present=bool(
                m.request_body and m.request_body.get("inline_schema_present")
            ),
            responses=[
                DescribeResponseBlock(
                    status=code,
                    description=block.get("description", ""),
                    schema_refs=block.get("schema_refs", []) or [],
                    content_types=block.get("content_types", []) or [],
                )
                for code, block in sorted(m.responses.items())
            ],
            verification_status=m.verification_status,
            verified_response_keys=m.verified_response_keys,
            is_admin=m.is_admin,
            remediation_if_admin=(
                "This service is hard-blocked in the generic prismhr_call tool "
                "because it modifies security, subscription, or login state. A "
                "purpose-built workflow tool is required."
            )
            if m.is_admin
            else None,
        )

    async def meta_find(
        query: Annotated[
            str,
            Field(description="Words to search for — method id, summary, or description fragments.", min_length=1),
        ],
        limit: Annotated[
            int,
            Field(description="Max results.", ge=1, le=100),
        ] = 20,
    ) -> list[MethodSummary]:
        """Find PrismHR methods by intent.

        Use when you don't know the exact method id. Claude should pick the
        best hit + follow up with `meta_describe` to see the contract.
        """
        catalog = _get_catalog()
        hits = catalog.search(query, limit=limit)
        return [
            MethodSummary(
                method_id=m.method_id,
                path=m.path,
                http_method=m.http_method,
                service=m.service,
                operation=m.operation,
                summary=m.summary,
                verification_status=m.verification_status,
                is_admin=m.is_admin,
                required_params=[p["name"] for p in m.required_params],
                required_body_fields=m.required_body_fields,
            )
            for m in hits
        ]

    async def prismhr_call(
        method_id: Annotated[
            str,
            Field(
                description=(
                    "Catalog method id, e.g. 'payroll.v1.getBatchListByDate.GET'. "
                    "Find valid ids via meta_capabilities or meta_find."
                ),
            ),
        ],
        args: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Arguments. Query/header parameters are top-level keys; "
                    "POST body fields go under a nested 'body' key. Consult "
                    "meta_describe(method_id) for the exact shape."
                ),
            ),
        ],
    ) -> PrismHRCallResponse:
        """Generic, schema-validated invocation of any PrismHR method in the catalog.

        Pre-flight: checks the method_id, refuses admin services, validates
        required query + header + body fields against the bundled bible
        schemas. Only after validation passes does the request hit PrismHR.

        Every call returns a structured PrismHRCallResponse — ok | prismhr_error
        | validation_error | admin_blocked | unverified_warning. The
        `unverified_warning` status is attached when the call succeeds but
        the response shape has not been verified by the maintainer's probe
        pass; treat the body as best-effort.
        """
        permissions.check(Scope.CATALOG_CALL)
        catalog = _get_catalog()

        try:
            contract = catalog.require(method_id)
        except KeyError:
            raise MCPError(
                code="UNKNOWN_METHOD_ID",
                message=(
                    f"Unknown method_id {method_id!r}. Use meta_capabilities or "
                    "meta_find to look up a valid id."
                ),
            )

        # Admin hard-block
        if contract.is_admin:
            return PrismHRCallResponse(
                method_id=method_id,
                status="admin_blocked",
                note=(
                    f"{contract.service!r} is on the admin-only list "
                    f"({sorted(ADMIN_ONLY_SERVICES)}) and cannot be called via "
                    "the generic prismhr_call tool. If you need this endpoint, "
                    "request a purpose-built workflow tool from Simploy."
                ),
            )

        # Pre-flight schema validation
        try:
            partitioned = validate_args(contract, args)
        except ValidationError as exc:
            return PrismHRCallResponse(
                method_id=method_id,
                status="validation_error",
                note=exc.message,
            )

        # Dispatch
        try:
            if contract.http_method == "GET":
                raw = await prismhr.get(contract.path, params=partitioned["query"])
            elif contract.http_method == "POST":
                raw = await prismhr.post(
                    contract.path,
                    params=partitioned["query"] or None,
                    json=partitioned["body"] or None,
                )
            else:
                return PrismHRCallResponse(
                    method_id=method_id,
                    status="validation_error",
                    note=f"Unsupported HTTP method {contract.http_method!r} for prismhr_call.",
                )
        except MCPError as exc:
            return PrismHRCallResponse(
                method_id=method_id,
                status="prismhr_error",
                note=exc.message,
                prismhr_error_code=str(exc.context.get("prismhr_error_code")) if exc.context else None,
                prismhr_error_message=exc.context.get("prismhr_error_message") if exc.context else None,
                http_status=exc.context.get("status") if exc.context else None,
            )

        # Even 200 can carry a PrismHR-level error envelope
        if isinstance(raw, dict):
            err = raw.get("errorCode")
            if err not in (None, "", "0"):
                return PrismHRCallResponse(
                    method_id=method_id,
                    status="prismhr_error",
                    prismhr_error_code=str(err),
                    prismhr_error_message=str(raw.get("errorMessage") or ""),
                    body=raw,
                )

        note = None
        if not contract.is_verified:
            note = (
                "Response shape not verified by the maintainer — treat fields "
                "as best-effort. Help us by running scripts/calibrated_probe.py "
                "with an account authorized for this method."
            )
            return PrismHRCallResponse(
                method_id=method_id,
                status="unverified_warning",
                body=raw,
                note=note,
            )

        return PrismHRCallResponse(method_id=method_id, status="ok", body=raw)

    registry.register(server, "meta_capabilities", meta_capabilities)
    registry.register(server, "meta_describe", meta_describe)
    registry.register(server, "meta_find", meta_find)
    registry.register(server, "meta_call", prismhr_call)
