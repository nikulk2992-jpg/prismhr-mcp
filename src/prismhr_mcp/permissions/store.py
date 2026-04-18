"""Consent state persisted as plain JSON on disk.

Structure:
  {
    "version": 1,
    "peo_id": "TEST-PEO",
    "environment": "uat",
    "granted": ["client:read", "employee:read", ...],
    "granted_at": "2026-04-18T12:34:56+00:00",
    "updated_at": "..."
  }

The consent file is per-(peo_id, environment) so switching between UAT and
prod or between PEO accounts doesn't silently inherit grants.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .scopes import Scope

log = logging.getLogger(__name__)

CONSENT_VERSION = 1


@dataclass
class ConsentState:
    granted: set[Scope] = field(default_factory=set)
    peo_id: str = ""
    environment: str = ""
    granted_at: str | None = None
    updated_at: str | None = None

    def is_granted(self, scope: Scope) -> bool:
        return scope in self.granted

    def to_dict(self) -> dict:
        return {
            "version": CONSENT_VERSION,
            "peo_id": self.peo_id,
            "environment": self.environment,
            "granted": sorted(s.value for s in self.granted),
            "granted_at": self.granted_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "ConsentState":
        granted_raw = raw.get("granted") or []
        granted: set[Scope] = set()
        for value in granted_raw:
            try:
                granted.add(Scope(value))
            except ValueError:
                log.warning("Dropping unknown scope from consent file: %r", value)
        return cls(
            granted=granted,
            peo_id=str(raw.get("peo_id") or ""),
            environment=str(raw.get("environment") or ""),
            granted_at=raw.get("granted_at"),
            updated_at=raw.get("updated_at"),
        )


class ConsentStore:
    """Loads + writes a single consent file per (peo_id, environment) pair."""

    def __init__(self, cache_dir: Path, peo_id: str, environment: str) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._peo_id = peo_id
        self._environment = environment
        self._path = cache_dir / self._filename(peo_id, environment)

    @staticmethod
    def _filename(peo_id: str, environment: str) -> str:
        # Replace characters that Windows filesystems dislike (asterisk, slash).
        safe = "".join(ch if ch.isalnum() else "_" for ch in peo_id)
        return f"consent-{environment}-{safe}.json"

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> ConsentState:
        if not self._path.exists():
            return ConsentState(
                granted=set(), peo_id=self._peo_id, environment=self._environment
            )
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Corrupt consent file at %s (%s); treating as empty", self._path, exc)
            return ConsentState(
                granted=set(), peo_id=self._peo_id, environment=self._environment
            )
        state = ConsentState.from_dict(raw)
        # Reset if the file was for a different PEO/env (defense-in-depth).
        if state.peo_id != self._peo_id or state.environment != self._environment:
            log.info(
                "Ignoring consent file for peo=%s env=%s; current context is peo=%s env=%s",
                state.peo_id, state.environment, self._peo_id, self._environment,
            )
            return ConsentState(
                granted=set(), peo_id=self._peo_id, environment=self._environment
            )
        return state

    def save(self, state: ConsentState) -> None:
        state.peo_id = self._peo_id
        state.environment = self._environment
        now = datetime.now(timezone.utc).isoformat()
        if state.granted_at is None and state.granted:
            state.granted_at = now
        state.updated_at = now

        # Atomic write: tmp file in same dir, then rename.
        payload = json.dumps(state.to_dict(), indent=2, sort_keys=True)
        fd, tmp_name = tempfile.mkstemp(dir=self._cache_dir, prefix="consent-", suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with open(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            tmp.replace(self._path)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        try:
            self._path.chmod(0o600)
        except OSError:
            pass
        time.time()  # silence unused-import warnings; real timestamps come from datetime.
