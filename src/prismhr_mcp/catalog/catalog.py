"""Runtime catalog of PrismHR API methods + verified response shapes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from typing import Any

# Services we refuse to call via the generic `prismhr_call` tool regardless
# of scope. These are admin / internal / high-impact surfaces that should
# never be accessible from an LLM prompt without a purpose-built tool.
ADMIN_ONLY_SERVICES: frozenset[str] = frozenset(
    {
        "prismSecurity",
        "subscription",
        # login handled via session auth; requestAPIPermissions must not be
        # callable from generic `prismhr_call` even by admins.
        "login",
    }
)


def method_id_from_path(path: str, method: str) -> str:
    """Canonical identifier for a PrismHR method — stable across renames.

    Format: `<service>.<version>.<operation>.<verb>`, e.g.
    `payroll.v1.getBatchListByDate.GET`.
    """
    parts = path.strip("/").split("/")
    service = parts[0] if parts else ""
    version = parts[1] if len(parts) > 1 else ""
    operation = parts[2] if len(parts) > 2 else ""
    return f"{service}.{version}.{operation}.{method.upper()}"


@dataclass(slots=True)
class MethodContract:
    """What the catalog knows about a single endpoint."""

    method_id: str
    path: str
    http_method: str
    service: str
    operation: str
    summary: str
    description: str
    parameters: list[dict[str, Any]]
    request_body: dict[str, Any] | None
    responses: dict[str, dict[str, Any]]
    # Verification state from the public matrix
    verification_status: str = "unprobed"  # verified | prismhr_error | transport_error | unprobed
    verified_response_keys: list[str] = field(default_factory=list)
    prismhr_error_code: str | None = None
    prismhr_error_message: str | None = None
    # Hand-curated overlay from quirks.json — PrismHR gotchas we learned the hard way
    quirks: list[str] = field(default_factory=list)
    param_enums: dict[str, dict[str, str]] = field(default_factory=dict)
    required_batch_status: list[str] = field(default_factory=list)
    rate_limited: bool = False

    @property
    def is_admin(self) -> bool:
        return self.service in ADMIN_ONLY_SERVICES

    @property
    def is_verified(self) -> bool:
        return self.verification_status == "verified"

    @property
    def required_params(self) -> list[dict[str, Any]]:
        return [p for p in self.parameters if p.get("required") and p.get("name") != "sessionId"]

    @property
    def required_body_fields(self) -> list[str]:
        if not self.request_body:
            return []
        return list(self.request_body.get("required_fields") or [])

    def to_summary(self) -> dict[str, Any]:
        return {
            "method_id": self.method_id,
            "path": self.path,
            "http_method": self.http_method,
            "service": self.service,
            "operation": self.operation,
            "summary": self.summary,
            "verification_status": self.verification_status,
            "is_admin": self.is_admin,
            "required_params": [p["name"] for p in self.required_params],
            "required_body_fields": self.required_body_fields,
            "has_quirks": bool(self.quirks),
            "rate_limited": self.rate_limited,
        }


class Catalog:
    """Read-only index over bundled methods + verification data."""

    def __init__(self, methods: dict[str, MethodContract]) -> None:
        self._methods = methods

    # ---- lookups -------------------------------------------------

    def __contains__(self, method_id: str) -> bool:
        return method_id in self._methods

    def __len__(self) -> int:
        return len(self._methods)

    def get(self, method_id: str) -> MethodContract | None:
        return self._methods.get(method_id)

    def require(self, method_id: str) -> MethodContract:
        c = self.get(method_id)
        if c is None:
            raise KeyError(f"unknown method_id: {method_id!r}")
        return c

    def all(self) -> list[MethodContract]:
        return list(self._methods.values())

    def by_service(self, service: str) -> list[MethodContract]:
        return [m for m in self._methods.values() if m.service == service]

    def verified(self) -> list[MethodContract]:
        return [m for m in self._methods.values() if m.is_verified]

    # ---- search --------------------------------------------------

    def search(self, query: str, limit: int = 20) -> list[MethodContract]:
        """Case-insensitive fuzzy search over method_id, summary, description."""
        q = query.strip().lower()
        if not q:
            return []
        terms = [t for t in q.split() if t]
        scored: list[tuple[int, MethodContract]] = []
        for m in self._methods.values():
            blob = " ".join([m.method_id, m.summary, m.description, m.service, m.operation]).lower()
            score = 0
            if q in blob:
                score += 5
            for t in terms:
                if t in blob:
                    score += 1
            if score:
                scored.append((score, m))
        scored.sort(key=lambda kv: (-kv[0], kv[1].method_id))
        return [m for _, m in scored[:limit]]


def _load_methods_file() -> list[dict[str, Any]]:
    data_files = resources.files("prismhr_mcp").joinpath("data/methods.json")
    return json.loads(data_files.read_text(encoding="utf-8"))


def _load_verification_file() -> dict[str, Any]:
    data_files = resources.files("prismhr_mcp").joinpath("data/verification.json")
    return json.loads(data_files.read_text(encoding="utf-8"))


def _load_quirks_file() -> dict[str, Any]:
    data_files = resources.files("prismhr_mcp").joinpath("data/quirks.json")
    try:
        return json.loads(data_files.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    """Build the in-memory catalog, cached for the life of the process."""
    raw_methods = _load_methods_file()
    verification = _load_verification_file()
    quirks_doc = _load_quirks_file()

    # Build path -> verification lookup
    verification_by_path: dict[str, dict[str, Any]] = {}
    for probe in verification.get("probes", []) or []:
        verification_by_path[probe["path"]] = probe

    quirks_by_id = quirks_doc.get("quirks") or {}
    enums_by_id = quirks_doc.get("param_enums") or {}
    status_gated = quirks_doc.get("status_gated") or {}
    rate_limited = set(quirks_doc.get("rate_limited") or [])

    contracts: dict[str, MethodContract] = {}
    for row in raw_methods:
        mid = method_id_from_path(row["path"], row["method"])
        probe = verification_by_path.get(row["path"], {})
        status = probe.get("status", "unprobed")
        contracts[mid] = MethodContract(
            method_id=mid,
            path=row["path"],
            http_method=row["method"],
            service=row["service"],
            operation=row["operation"],
            summary=row["summary"],
            description=row["description"],
            parameters=row.get("parameters") or [],
            request_body=row.get("request_body"),
            responses=row.get("responses") or {},
            verification_status=status,
            verified_response_keys=list(probe.get("response_keys") or []),
            prismhr_error_code=probe.get("prismhr_error_code"),
            prismhr_error_message=probe.get("prismhr_error_message"),
            quirks=list(quirks_by_id.get(mid) or []),
            param_enums=dict(enums_by_id.get(mid) or {}),
            required_batch_status=list(
                (status_gated.get(mid) or {}).get("required_batch_status") or []
            ),
            rate_limited=mid in rate_limited,
        )
    return Catalog(contracts)
