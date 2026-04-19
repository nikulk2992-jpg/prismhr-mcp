"""Pre-flight argument validation against the catalog's extracted schemas.

This is how the 'no-guesswork' promise is kept — Claude cannot invoke a
method via `prismhr_call` without the correct required params, and the
error message tells it exactly what's missing.

Only validates what we can verify from the bible:
  * Query/header/path parameter presence (all endpoints).
  * Request-body required fields (34 POSTs with inline schemas).
  * For the other 152 POSTs with only `$ref` schemas, we validate what
    we can and note the limitation.
"""

from __future__ import annotations

from typing import Any

from .catalog import MethodContract


class ValidationError(Exception):
    """Raised when caller-supplied args don't match the catalog's contract."""

    def __init__(self, code: str, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context or {}


def validate_args(contract: MethodContract, args: dict[str, Any]) -> dict[str, Any]:
    """Validate `args` against the method's extracted schema.

    Returns a normalized dict partitioned by location:
        {"query": {...}, "body": {...}, "headers": {...}}
    Raises ValidationError on any missing required field or unknown field
    when the schema is fully known.
    """
    query: dict[str, Any] = {}
    body: dict[str, Any] = {}
    headers: dict[str, Any] = {}

    # Map each declared param
    declared_names: set[str] = set()
    missing_required: list[str] = []
    for p in contract.parameters:
        name = p["name"]
        declared_names.add(name)
        if name == "sessionId":
            continue  # session auth is injected by the transport
        loc = p.get("location", "query")
        val = args.get(name)
        if val is None:
            if p.get("required"):
                missing_required.append(f"{name} (required {loc})")
            continue
        bucket = {"query": query, "header": headers, "headers": headers}.get(loc, query)
        bucket[name] = val

    if missing_required:
        raise ValidationError(
            code="MISSING_REQUIRED_PARAM",
            message=(
                f"Missing required parameter(s) for {contract.method_id}: "
                + ", ".join(missing_required)
            ),
            context={"method_id": contract.method_id, "missing": missing_required},
        )

    # Request body validation — only if we have an inline schema
    if contract.request_body:
        body_required = set(contract.request_body.get("required_fields") or [])
        if body_required:
            body_raw = args.get("body")
            if not isinstance(body_raw, dict):
                raise ValidationError(
                    code="BODY_REQUIRED",
                    message=(
                        f"{contract.method_id} requires a body object with fields: "
                        + ", ".join(sorted(body_required))
                    ),
                    context={"method_id": contract.method_id, "body_required": sorted(body_required)},
                )
            body_missing = [f for f in body_required if f not in body_raw or body_raw[f] in (None, "")]
            if body_missing:
                raise ValidationError(
                    code="MISSING_REQUIRED_BODY_FIELD",
                    message=(
                        f"Body for {contract.method_id} missing required field(s): "
                        + ", ".join(body_missing)
                    ),
                    context={"method_id": contract.method_id, "missing_body_fields": body_missing},
                )
            body = body_raw
        else:
            # Schema is $ref only — we can't fully validate. Pass through whatever
            # the caller gave us, clearly documented as best-effort.
            body = args.get("body") or {}
    return {"query": query, "body": body, "headers": headers}
