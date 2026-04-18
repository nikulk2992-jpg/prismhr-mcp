"""Session manager tests — login, proactive refresh, forced refresh, keepalive."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx
import pytest
import respx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import (
    KEEPALIVE_PATH,
    LOGIN_PATH,
    SessionError,
    SessionManager,
)
from prismhr_mcp.config import Settings


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    defaults: dict[str, object] = {"cache_dir": tmp_path}
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def _creds() -> DirectCredentialSource:
    return DirectCredentialSource("624*D", "claudedemo", "s3cret")


async def test_login_caches_token(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            route = mock.post(LOGIN_PATH).mock(
                return_value=httpx.Response(200, json={"token": "abc123"})
            )
            mgr = SessionManager(s, _creds(), http)
            t1 = await mgr.token()
            t2 = await mgr.token()
            assert t1 == "abc123"
            assert t2 == "abc123"
            assert route.call_count == 1  # second call hits cached session


async def test_force_refresh_re_logs_in(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            route = mock.post(LOGIN_PATH).mock(
                side_effect=[
                    httpx.Response(200, json={"token": "first"}),
                    httpx.Response(200, json={"token": "second"}),
                ]
            )
            mgr = SessionManager(s, _creds(), http)
            assert await mgr.token() == "first"
            await mgr.force_refresh()
            assert await mgr.token() == "second"
            assert route.call_count == 2


async def test_proactive_refresh_near_expiry(tmp_path: Path) -> None:
    s = _settings(
        tmp_path,
        session_ttl_seconds=10,
        session_refresh_margin_seconds=8,
    )  # first session will refresh almost immediately
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            mock.post(LOGIN_PATH).mock(
                side_effect=[
                    httpx.Response(200, json={"token": "a"}),
                    httpx.Response(200, json={"token": "b"}),
                ]
            )
            mgr = SessionManager(s, _creds(), http)
            assert await mgr.token() == "a"
            # Force "expiry window" by rewinding acquired_at.
            mgr._session.expires_at = time.time() + 1  # type: ignore[union-attr]
            assert await mgr.token() == "b"


async def test_login_failure_surfaces_session_error(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            mock.post(LOGIN_PATH).mock(
                return_value=httpx.Response(401, text="bad peo/user/pass")
            )
            mgr = SessionManager(s, _creds(), http)
            with pytest.raises(SessionError, match="rejected"):
                await mgr.token()


async def test_keepalive_skipped_when_recent_activity(tmp_path: Path) -> None:
    s = _settings(tmp_path, session_keepalive_seconds=60)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url, assert_all_called=False) as mock:
            mock.post(LOGIN_PATH).mock(
                return_value=httpx.Response(200, json={"token": "t"})
            )
            keepalive = mock.get(KEEPALIVE_PATH)
            mgr = SessionManager(s, _creds(), http)
            await mgr.token()
            mgr.note_api_call()  # resets idle timer
            await mgr.keepalive_if_idle()
            assert keepalive.call_count == 0


async def test_keepalive_fires_when_idle(tmp_path: Path) -> None:
    s = _settings(tmp_path, session_keepalive_seconds=0)  # always idle
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            mock.post(LOGIN_PATH).mock(
                return_value=httpx.Response(200, json={"token": "t"})
            )
            ka = mock.get(KEEPALIVE_PATH).mock(
                return_value=httpx.Response(200, json={"clients": []})
            )
            mgr = SessionManager(s, _creds(), http)
            await mgr.token()
            await mgr.keepalive_if_idle()
            assert ka.call_count == 1


async def test_keepalive_401_triggers_refresh(tmp_path: Path) -> None:
    s = _settings(tmp_path, session_keepalive_seconds=0)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            login = mock.post(LOGIN_PATH).mock(
                side_effect=[
                    httpx.Response(200, json={"token": "stale"}),
                    httpx.Response(200, json={"token": "fresh"}),
                ]
            )
            mock.get(KEEPALIVE_PATH).mock(return_value=httpx.Response(401))
            mgr = SessionManager(s, _creds(), http)
            await mgr.token()
            await mgr.keepalive_if_idle()
            assert login.call_count == 2
            assert await mgr.token() == "fresh"


async def test_concurrent_token_calls_share_single_login(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            route = mock.post(LOGIN_PATH).mock(
                return_value=httpx.Response(200, json={"token": "t"})
            )
            mgr = SessionManager(s, _creds(), http)
            results = await asyncio.gather(*(mgr.token() for _ in range(10)))
            assert all(r == "t" for r in results)
            assert route.call_count == 1  # lock collapses concurrent logins
