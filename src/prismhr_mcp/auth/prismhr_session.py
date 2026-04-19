"""PrismHR session lifecycle: login, keepalive, forced refresh on 401.

Ports the behavior from `simploy-prismhr-app/src/main/services/prismhr-client.ts`:
- Keepalive pings `/clientMaster/v1/getClientList` every 10 min if the client
  hasn't made an API call; keeps the session warm indefinitely and prevents
  surprise 401s mid-workflow.
- A forced refresh is what a 401 handler triggers before retrying the request.
- The proactive expiry check (`session_ttl_seconds`) is an internal fallback
  for edge cases where keepalive couldn't run (e.g., process suspend); not
  part of the documented user contract.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from ..config import Settings
from .credentials import CredentialSource

log = logging.getLogger(__name__)

LOGIN_PATH = "/login/v1/createPeoSession"
KEEPALIVE_PATH = "/clientMaster/v1/getClientList"


class SessionError(RuntimeError):
    """Raised when PrismHR login or refresh fails unrecoverably."""


@dataclass(slots=True)
class Session:
    token: str
    acquired_at: float
    expires_at: float

    def should_refresh(self, margin_seconds: int) -> bool:
        return time.time() >= self.expires_at - margin_seconds


class SessionManager:
    """Owns a single PrismHR auth session. Safe for concurrent callers."""

    def __init__(
        self,
        settings: Settings,
        credentials: CredentialSource,
        http: httpx.AsyncClient,
    ) -> None:
        self._settings = settings
        self._credentials = credentials
        self._http = http
        self._session: Session | None = None
        self._lock = asyncio.Lock()
        self._last_api_call = time.monotonic()

    # ------------- public API -------------

    async def current(self) -> Session:
        """Return a usable session, refreshing proactively if near expiry."""
        s = self._session
        if s is not None and not s.should_refresh(self._settings.session_refresh_margin_seconds):
            return s
        return await self._refresh_locked()

    async def force_refresh(self) -> Session:
        """Invalidate current session and re-login (401 handler path)."""
        async with self._lock:
            self._session = None
        return await self._refresh_locked()

    async def token(self) -> str:
        return (await self.current()).token

    def note_api_call(self) -> None:
        """Called by the HTTP client whenever it hits PrismHR — resets keepalive idle timer."""
        self._last_api_call = time.monotonic()

    async def keepalive_if_idle(self) -> None:
        """Ping the lightest endpoint if no API call has happened in the keepalive window."""
        if self._session is None:
            return
        idle = time.monotonic() - self._last_api_call
        if idle < self._settings.session_keepalive_seconds:
            return

        token = await self.token()
        url = f"{self._settings.prismhr_base_url}{KEEPALIVE_PATH}"
        try:
            resp = await self._http.get(
                url, headers={"sessionId": token, "Accept": "application/json"}
            )
        except httpx.HTTPError as exc:
            log.warning("Keepalive request failed: %s", exc)
            return

        if resp.status_code == 401:
            log.info("Keepalive hit 401 — forcing session refresh")
            await self.force_refresh()
        self._last_api_call = time.monotonic()

    async def run_keepalive_loop(self, stop: asyncio.Event) -> None:
        """Background task: call `keepalive_if_idle` on a timer until stopped."""
        interval = self._settings.session_keepalive_seconds
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
                return  # stop.set() returned True
            except asyncio.TimeoutError:
                pass
            try:
                await self.keepalive_if_idle()
            except Exception as exc:  # noqa: BLE001 — keepalive must not die silently
                log.exception("keepalive loop error: %s", exc)

    # ------------- internals -------------

    async def _refresh_locked(self) -> Session:
        async with self._lock:
            # Double-check — another coroutine may have refreshed while we waited.
            s = self._session
            if s is not None and not s.should_refresh(
                self._settings.session_refresh_margin_seconds
            ):
                return s
            self._session = await self._login()
            self._last_api_call = time.monotonic()
            return self._session

    async def _login(self) -> Session:
        peo_id, username, password = await self._credentials.get()
        url = f"{self._settings.prismhr_base_url}{LOGIN_PATH}"
        data = {"peoId": peo_id, "username": username, "password": password}
        try:
            resp = await self._http.post(url, data=data)
        except httpx.HTTPError as exc:
            raise SessionError(f"PrismHR login request failed: {exc}") from exc

        if resp.status_code != 200:
            raise SessionError(
                f"PrismHR login rejected (status={resp.status_code}): "
                f"{resp.text[:200]}"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise SessionError(f"PrismHR login response not JSON: {exc}") from exc

        # PrismHR UAT returns `sessionId`; some older tenants use `token` or
        # `sessionToken`. Accept any of them.
        token = (
            payload.get("sessionId")
            or payload.get("token")
            or payload.get("sessionToken")
        )
        if not token:
            raise SessionError(f"PrismHR login response missing token field: {payload}")

        now = time.time()
        return Session(
            token=str(token),
            acquired_at=now,
            expires_at=now + self._settings.session_ttl_seconds,
        )
