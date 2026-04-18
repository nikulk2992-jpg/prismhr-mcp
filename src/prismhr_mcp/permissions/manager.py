"""Runtime enforcement: tool-time scope checks + grant/revoke API.

`PermissionManager` is the single object tools consult before doing work.
It holds the current `ConsentState`, validates grants against the static
manifest, and raises `PermissionDeniedError` when a tool is called without
its required scope.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from ..errors import MCPError
from .scopes import MANIFEST, Scope, lookup
from .store import ConsentState, ConsentStore

log = logging.getLogger(__name__)


class PermissionDeniedError(MCPError):
    """Raised when a tool is called without the scope it requires.

    The error message tells Claude exactly how to remediate: call
    `meta_grant_permissions(granted=[...])` with the missing scope.
    """


class PermissionManager:
    def __init__(self, store: ConsentStore) -> None:
        self._store = store
        self._state: ConsentState = store.load()

    # ------------- inspection -------------

    @property
    def state(self) -> ConsentState:
        return self._state

    @property
    def granted(self) -> frozenset[Scope]:
        return frozenset(self._state.granted)

    def is_granted(self, scope: Scope) -> bool:
        return self._state.is_granted(scope)

    # ------------- mutation -------------

    def grant(self, scopes: Iterable[Scope | str]) -> ConsentState:
        resolved = _resolve_and_expand(scopes)
        new = set(self._state.granted) | resolved
        return self._persist(new)

    def revoke(self, scopes: Iterable[Scope | str]) -> ConsentState:
        resolved = _resolve(scopes)
        new = set(self._state.granted) - resolved
        # Also revoke scopes that required any of the revoked ones.
        still_valid: set[Scope] = set()
        for scope in new:
            spec = lookup(scope)
            if all(prereq in new for prereq in spec.requires):
                still_valid.add(scope)
        if still_valid != new:
            dropped = new - still_valid
            log.info("Cascade-revoking %s because prerequisites were revoked", dropped)
        return self._persist(still_valid)

    def replace(self, scopes: Iterable[Scope | str]) -> ConsentState:
        resolved = _resolve_and_expand(scopes)
        return self._persist(resolved)

    def reset(self) -> ConsentState:
        return self._persist(set())

    # ------------- enforcement -------------

    def check(self, scope: Scope) -> None:
        if not self.is_granted(scope):
            spec = lookup(scope)
            missing_prereqs = [r for r in spec.requires if not self.is_granted(r)]
            remediation = (
                f"Call meta_grant_permissions with granted=['{scope.value}'"
                + "".join(f", '{p.value}'" for p in missing_prereqs)
                + "]"
            )
            raise PermissionDeniedError(
                code="PERMISSION_NOT_GRANTED",
                message=(
                    f"Scope {scope.value!r} not granted. "
                    f"{spec.description} "
                    f"Remediation: {remediation}. "
                    f"Full manifest available via meta_request_permissions."
                ),
                context={
                    "scope": scope.value,
                    "requires": [r.value for r in spec.requires],
                    "missing_prereqs": [p.value for p in missing_prereqs],
                },
            )

    # ------------- internals -------------

    def _persist(self, scopes: set[Scope]) -> ConsentState:
        self._state.granted = scopes
        self._store.save(self._state)
        return self._state


def _resolve(scopes: Iterable[Scope | str]) -> set[Scope]:
    out: set[Scope] = set()
    for s in scopes:
        if isinstance(s, Scope):
            out.add(s)
            continue
        try:
            out.add(Scope(s))
        except ValueError as exc:
            valid = sorted(scope.value for scope in Scope)
            raise ValueError(
                f"Unknown scope {s!r}. Valid scopes: {valid}"
            ) from exc
    return out


def _resolve_and_expand(scopes: Iterable[Scope | str]) -> set[Scope]:
    """Resolve strings to Scopes and auto-include declared prerequisites."""
    base = _resolve(scopes)
    expanded = set(base)
    # Walk the manifest: for each requested scope, include its requires.
    # (Don't silently add siblings — only what the spec says the scope needs.)
    frontier = list(base)
    seen: set[Scope] = set(base)
    while frontier:
        current = frontier.pop()
        spec = lookup(current)
        for prereq in spec.requires:
            if prereq not in seen:
                seen.add(prereq)
                expanded.add(prereq)
                frontier.append(prereq)
    return expanded


# Sanity check at import time — catch spec mistakes before runtime.
_spec_scopes = {spec.scope for spec in MANIFEST}
_enum_scopes = set(Scope)
if _spec_scopes != _enum_scopes:
    missing = _enum_scopes - _spec_scopes
    extra = _spec_scopes - _enum_scopes
    raise RuntimeError(
        f"permissions.scopes MANIFEST is out of sync with Scope enum. "
        f"Missing specs: {missing}. Extra specs: {extra}."
    )
