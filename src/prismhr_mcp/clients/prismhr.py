"""Authenticated PrismHR REST client with concurrency, retries, and known quirks.

Behavioral parity with `simploy-prismhr-app/src/main/services/prismhr-client.ts`:

* Max N concurrent outbound requests (settings.prismhr_max_concurrency).
* Up to `max_attempts` retries with exponential backoff `base * 2^attempt`.
* `401` → force session refresh, retry once.
* `404` on list-ish endpoints → return empty list (some endpoints use this
  instead of 200 + empty array).
* `500` with body text indicating "no data found" → treat as empty.
* After N consecutive `500`s across requests, force a session refresh — the
  live app has seen the session go sour without a matching 401.

The client is async. A single instance is intended to be long-lived for
the MCP server process lifetime.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any, TypeVar

import httpx

from ..auth.prismhr_session import SessionManager
from ..config import Settings
from ..errors import PrismHRAuthError, PrismHRRequestError, RateLimitedError

log = logging.getLogger(__name__)

T = TypeVar("T")

NO_DATA_MARKERS = (
    "no data found",
    "no records found",
    "no result",
    "not found",
)

CONSECUTIVE_500_THRESHOLD = 10
DEFAULT_BATCH_SIZE = 20
DEFAULT_PAGE_SIZE = 100


class PrismHRClient:
    def __init__(
        self,
        settings: Settings,
        session: SessionManager,
        http: httpx.AsyncClient,
    ) -> None:
        self._settings = settings
        self._session = session
        self._http = http
        self._sem = asyncio.Semaphore(settings.prismhr_max_concurrency)
        self._consecutive_500s = 0

    # ------------- public API -------------

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return await self._request("POST", path, data=data, json=json, params=params)

    async def paginate(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        count: int = DEFAULT_PAGE_SIZE,
        results_key: str | None = None,
    ) -> AsyncIterator[Any]:
        """Yield records across pages using PrismHR's `startpage` + `count` params.

        If `results_key` is set, pulls the list from `response[results_key]`;
        otherwise assumes the response itself is a list.
        """
        start = 1
        while True:
            merged = dict(params or {})
            merged["startpage"] = start
            merged["count"] = count
            page = await self.get(path, params=merged)
            rows = page if results_key is None else (page or {}).get(results_key) or []
            if not rows:
                return
            for row in rows:
                yield row
            if len(rows) < count:
                return
            start += 1

    async def batch(
        self,
        items: Sequence[T],
        fn: Callable[[Sequence[T]], Awaitable[list[Any]]],
        chunk_size: int = DEFAULT_BATCH_SIZE,
    ) -> list[Any]:
        """Chunk `items` and fan out to `fn` respecting the client's concurrency cap."""
        chunks = [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]
        results = await asyncio.gather(*(fn(chunk) for chunk in chunks))
        return [row for chunk_result in results for row in chunk_result]

    # ------------- internals -------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        url = f"{self._settings.prismhr_base_url}{path}"
        attempts = self._settings.prismhr_max_attempts
        base = self._settings.prismhr_backoff_base_seconds
        last_exc: Exception | None = None

        for attempt in range(attempts):
            async with self._sem:
                token = await self._session.token()
                # PrismHR expects its session token in a custom `sessionId`
                # header, not HTTP Bearer auth. Confirmed against UAT during
                # Phase 2 dogfood: Bearer auth returns 401 for every endpoint.
                headers = {"sessionId": token, "Accept": "application/json"}
                try:
                    resp = await self._http.request(
                        method,
                        url,
                        params=params,
                        data=data,
                        json=json,
                        headers=headers,
                    )
                    self._session.note_api_call()
                except httpx.HTTPError as exc:
                    last_exc = exc
                    log.warning(
                        "PrismHR %s %s transport error (attempt %d/%d): %s",
                        method, path, attempt + 1, attempts, exc,
                    )
                    await asyncio.sleep(self._backoff(attempt, base))
                    continue

            status = resp.status_code

            if status == 200:
                self._consecutive_500s = 0
                return self._parse_body(resp)

            if status == 401:
                log.info("PrismHR 401 on %s — forcing session refresh", path)
                await self._session.force_refresh()
                # Don't sleep — credential was probably stale, not rate limit.
                continue

            if status == 404 and method == "GET":
                self._consecutive_500s = 0
                return _empty_for_path(path)

            if status == 429:
                retry_after = _parse_retry_after(resp)
                if attempt + 1 < attempts:
                    await asyncio.sleep(retry_after or self._backoff(attempt, base))
                    continue
                raise RateLimitedError(
                    code="PRISMHR_RATE_LIMITED",
                    message=f"PrismHR throttled {method} {path}",
                    context={"retry_after": retry_after},
                    retriable=True,
                )

            if 500 <= status < 600:
                self._consecutive_500s += 1
                if _is_empty_500(resp):
                    self._consecutive_500s = 0
                    return _empty_for_path(path)
                if self._consecutive_500s >= CONSECUTIVE_500_THRESHOLD:
                    log.warning(
                        "PrismHR hit %d consecutive 500s — forcing session refresh",
                        self._consecutive_500s,
                    )
                    await self._session.force_refresh()
                    self._consecutive_500s = 0
                if attempt + 1 < attempts:
                    await asyncio.sleep(self._backoff(attempt, base))
                    continue

            # Unrecoverable — surface structured error. If PrismHR returned
            # its usual `{errorCode, errorMessage}` JSON envelope, include
            # that text so Claude can relay a specific remediation to the user
            # (e.g. "not authorized for method" → admin must grant privilege).
            prismhr_error_message: str | None = None
            prismhr_error_code: str | None = None
            try:
                body_json = resp.json()
                if isinstance(body_json, dict):
                    prismhr_error_message = body_json.get("errorMessage") or None
                    raw_err_code = body_json.get("errorCode")
                    if raw_err_code not in (None, "", "0"):
                        prismhr_error_code = str(raw_err_code)
            except ValueError:
                pass  # non-JSON body, fall through to generic message
            if prismhr_error_message:
                hint = f" PrismHR says: {prismhr_error_message}"
                if prismhr_error_code:
                    hint += f" (errorCode={prismhr_error_code})"
            else:
                hint = ""
            raise PrismHRRequestError(
                code="PRISMHR_HTTP_ERROR",
                message=f"{method} {path} failed (status={status}).{hint}",
                context={
                    "status": status,
                    "body": resp.text[:500],
                    "prismhr_error_code": prismhr_error_code,
                    "prismhr_error_message": prismhr_error_message,
                    "attempt": attempt + 1,
                },
            )

        # Exhausted retries on transport errors.
        raise PrismHRAuthError(
            code="PRISMHR_UNREACHABLE",
            message=f"PrismHR {method} {path} unreachable after {attempts} attempts",
            context={"last_error": repr(last_exc)},
            retriable=True,
        )

    @staticmethod
    def _backoff(attempt: int, base: float) -> float:
        # Jitter by ±10% so reconnects don't thundering-herd.
        return base * (2**attempt) * (0.9 + random.random() * 0.2)

    @staticmethod
    def _parse_body(resp: httpx.Response) -> Any:
        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return resp.text


def _is_empty_500(resp: httpx.Response) -> bool:
    body = (resp.text or "").lower()
    return any(marker in body for marker in NO_DATA_MARKERS)


def _parse_retry_after(resp: httpx.Response) -> float | None:
    raw = resp.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _empty_for_path(path: str) -> Any:
    """Empty-response shape convention: list endpoints return [], else {}."""
    if "list" in path.lower() or path.endswith("s"):
        return []
    return {}
