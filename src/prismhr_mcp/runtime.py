"""Composition root — wires settings, HTTP, auth, clients, and permissions.

Kept separate from `server.py` so tests can build a runtime with injected
fakes (httpx.MockTransport, pre-authenticated session, explicit scope grants)
without booting the MCP server.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .auth.credentials import build_credential_source
from .auth.prismhr_session import SessionManager
from .clients.prismhr import PrismHRClient
from .config import Settings, get_settings
from .permissions import ConsentStore, PermissionManager


@dataclass
class Runtime:
    settings: Settings
    http: httpx.AsyncClient
    session: SessionManager
    prismhr: PrismHRClient
    permissions: PermissionManager

    async def aclose(self) -> None:
        await self.http.aclose()


def build_runtime(settings: Settings | None = None) -> Runtime:
    """Construct a live Runtime. Requires creds already in env/1Password."""
    s = settings or get_settings()
    http = httpx.AsyncClient(timeout=30.0)
    creds = build_credential_source(s)
    session = SessionManager(s, creds, http)
    prismhr = PrismHRClient(s, session, http)
    store = ConsentStore(
        cache_dir=s.cache_dir,
        peo_id=s.prismhr_peo_id,
        environment=s.environment,
    )
    permissions = PermissionManager(store=store)
    return Runtime(
        settings=s,
        http=http,
        session=session,
        prismhr=prismhr,
        permissions=permissions,
    )
