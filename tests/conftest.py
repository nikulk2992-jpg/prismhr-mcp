"""Shared pytest fixtures — primarily for building a test Runtime."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.permissions import ConsentStore, PermissionManager, Scope
from prismhr_mcp.runtime import Runtime


def _base_settings(tmp_path: Path) -> Settings:
    return Settings(  # type: ignore[arg-type]
        cache_dir=tmp_path,
        prismhr_max_attempts=2,
        prismhr_backoff_base_seconds=0.001,
    )


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return _base_settings(tmp_path)


@pytest_asyncio.fixture
async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client


@pytest_asyncio.fixture
async def runtime(
    test_settings: Settings, http_client: httpx.AsyncClient
) -> AsyncIterator[Runtime]:
    """Runtime with ALL read scopes pre-granted so tests aren't blocked by consent."""
    creds = DirectCredentialSource("624*D", "claudedemo", "s3cret")
    session = SessionManager(test_settings, creds, http_client)
    prismhr = PrismHRClient(test_settings, session, http_client)
    store = ConsentStore(
        cache_dir=test_settings.cache_dir,
        peo_id=test_settings.prismhr_peo_id,
        environment=test_settings.environment,
    )
    permissions = PermissionManager(store=store)
    # Pre-grant all reads so existing tool tests don't have to plumb consent.
    permissions.grant(
        [
            Scope.CLIENT_READ,
            Scope.EMPLOYEE_READ,
            Scope.PAYROLL_READ,
            Scope.BENEFITS_READ,
            Scope.COMPLIANCE_READ,
            Scope.BILLING_READ,
            Scope.REPORTS_GENERATE,
        ]
    )
    rt = Runtime(
        settings=test_settings,
        http=http_client,
        session=session,
        prismhr=prismhr,
        permissions=permissions,
    )
    yield rt


@pytest_asyncio.fixture
async def runtime_no_grants(
    test_settings: Settings, http_client: httpx.AsyncClient
) -> AsyncIterator[Runtime]:
    """Runtime with NO scopes granted — use to test permission enforcement."""
    creds = DirectCredentialSource("624*D", "claudedemo", "s3cret")
    session = SessionManager(test_settings, creds, http_client)
    prismhr = PrismHRClient(test_settings, session, http_client)
    store = ConsentStore(
        cache_dir=test_settings.cache_dir,
        peo_id=test_settings.prismhr_peo_id,
        environment=test_settings.environment,
    )
    permissions = PermissionManager(store=store)
    rt = Runtime(
        settings=test_settings,
        http=http_client,
        session=session,
        prismhr=prismhr,
        permissions=permissions,
    )
    yield rt
