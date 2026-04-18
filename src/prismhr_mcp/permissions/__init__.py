"""Connect-time consent system.

Users grant the MCP server the scopes they're comfortable with. Tools check
their scope at call time; ungranted calls return a structured error that
names the scope so Claude can tell the user how to grant it.

Default policy: DENY ALL. The user must explicitly run `meta_grant_permissions`
(usually via `meta_request_permissions` → review → grant). This favors
auditability and surprise-minimization over demo-friendliness.
"""

from .manager import PermissionDeniedError, PermissionManager
from .scopes import (
    CATEGORY_ORDER,
    MANIFEST,
    Scope,
    ScopeCategory,
    ScopeSpec,
    lookup,
    manifest_by_category,
)
from .store import ConsentState, ConsentStore

__all__ = [
    "CATEGORY_ORDER",
    "ConsentState",
    "ConsentStore",
    "MANIFEST",
    "PermissionDeniedError",
    "PermissionManager",
    "Scope",
    "ScopeCategory",
    "ScopeSpec",
    "lookup",
    "manifest_by_category",
]
