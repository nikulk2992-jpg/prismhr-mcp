"""PrismHR HTTP client tests — retry, 500->empty, 401 refresh, pagination, batch."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import LOGIN_PATH, SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.errors import PrismHRRequestError, RateLimitedError


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "cache_dir": tmp_path,
        "prismhr_max_attempts": 3,
        "prismhr_backoff_base_seconds": 0.001,  # keep tests fast
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def _creds() -> DirectCredentialSource:
    return DirectCredentialSource("TEST-PEO", "test-user", "s3cret")


def _login_ok(mock: respx.Router) -> None:
    mock.post(LOGIN_PATH).mock(return_value=httpx.Response(200, json={"token": "t"}))


async def test_get_success_returns_parsed_json(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            _login_ok(mock)
            mock.get("/ping").mock(return_value=httpx.Response(200, json={"ok": True}))
            client = PrismHRClient(s, SessionManager(s, _creds(), http), http)
            data = await client.get("/ping")
            assert data == {"ok": True}


async def test_401_triggers_session_refresh_then_success(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            login = mock.post(LOGIN_PATH).mock(
                side_effect=[
                    httpx.Response(200, json={"token": "stale"}),
                    httpx.Response(200, json={"token": "fresh"}),
                ]
            )
            mock.get("/protected").mock(
                side_effect=[
                    httpx.Response(401),
                    httpx.Response(200, json={"ok": 1}),
                ]
            )
            client = PrismHRClient(s, SessionManager(s, _creds(), http), http)
            data = await client.get("/protected")
            assert data == {"ok": 1}
            assert login.call_count == 2


async def test_500_with_no_data_marker_returns_empty(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            _login_ok(mock)
            mock.get("/getBatchListByDate").mock(
                return_value=httpx.Response(500, text="No data found for range")
            )
            client = PrismHRClient(s, SessionManager(s, _creds(), http), http)
            data = await client.get("/getBatchListByDate")
            assert data == []


async def test_404_on_list_endpoint_returns_empty(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            _login_ok(mock)
            mock.get("/clientMaster/v1/getClientList").mock(
                return_value=httpx.Response(404)
            )
            client = PrismHRClient(s, SessionManager(s, _creds(), http), http)
            data = await client.get("/clientMaster/v1/getClientList")
            assert data == []


async def test_500_retried_then_raises(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            _login_ok(mock)
            route = mock.get("/boom").mock(
                return_value=httpx.Response(500, text="internal failure")
            )
            client = PrismHRClient(s, SessionManager(s, _creds(), http), http)
            with pytest.raises(PrismHRRequestError, match="status=500"):
                await client.get("/boom")
            assert route.call_count == s.prismhr_max_attempts


async def test_429_with_retry_after_eventually_succeeds(tmp_path: Path) -> None:
    s = _settings(tmp_path, prismhr_max_attempts=2)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            _login_ok(mock)
            mock.get("/slow").mock(
                side_effect=[
                    httpx.Response(429, headers={"Retry-After": "0"}),
                    httpx.Response(200, json={"ok": 1}),
                ]
            )
            client = PrismHRClient(s, SessionManager(s, _creds(), http), http)
            data = await client.get("/slow")
            assert data == {"ok": 1}


async def test_429_exhausted_raises_rate_limited(tmp_path: Path) -> None:
    s = _settings(tmp_path, prismhr_max_attempts=2)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            _login_ok(mock)
            mock.get("/slow").mock(
                return_value=httpx.Response(429, headers={"Retry-After": "0"})
            )
            client = PrismHRClient(s, SessionManager(s, _creds(), http), http)
            with pytest.raises(RateLimitedError):
                await client.get("/slow")


async def test_paginate_yields_all_rows(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        with respx.mock(base_url=s.prismhr_base_url) as mock:
            _login_ok(mock)

            def handler(request: httpx.Request) -> httpx.Response:
                page = int(request.url.params["startpage"])
                if page == 1:
                    return httpx.Response(200, json=[{"i": 1}, {"i": 2}])
                if page == 2:
                    return httpx.Response(200, json=[{"i": 3}])
                return httpx.Response(200, json=[])

            mock.get("/list").mock(side_effect=handler)
            client = PrismHRClient(s, SessionManager(s, _creds(), http), http)
            rows = [r async for r in client.paginate("/list", count=2)]
            assert rows == [{"i": 1}, {"i": 2}, {"i": 3}]


async def test_batch_fans_out_chunks(tmp_path: Path) -> None:
    # `batch` orchestrates user-supplied fetchers — no HTTP happens unless the
    # fetcher itself issues one. This test keeps the fetcher pure to verify the
    # chunking logic in isolation.
    s = _settings(tmp_path)
    async with httpx.AsyncClient() as http:
        client = PrismHRClient(s, SessionManager(s, _creds(), http), http)

        ids = list(range(45))
        seen_chunks: list[list[int]] = []

        async def fetch(chunk: list[int]) -> list[dict]:
            seen_chunks.append(list(chunk))
            return [{"id": i} for i in chunk]

        results = await client.batch(ids, fetch, chunk_size=20)
        assert [r["id"] for r in results] == ids
        assert [len(c) for c in seen_chunks] == [20, 20, 5]
