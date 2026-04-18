"""Config loading + base URL selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from prismhr_mcp.config import Settings


def test_defaults_target_uat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRISMHR_MCP_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("PRISMHR_MCP_ENVIRONMENT", raising=False)
    s = Settings()
    assert s.environment == "uat"
    assert "uatapi" in s.prismhr_base_url
    assert s.prismhr_peo_id == "TEST-PEO"
    assert s.cache_dir.exists()


def test_prod_switch_requires_allow_prod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRISMHR_MCP_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("PRISMHR_MCP_ENVIRONMENT", "prod")
    from prismhr_mcp.config import ProductionNotAllowedError

    with pytest.raises(ProductionNotAllowedError):
        Settings()


def test_prod_switch_with_allow_prod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRISMHR_MCP_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("PRISMHR_MCP_ENVIRONMENT", "prod")
    monkeypatch.setenv("PRISMHR_MCP_ALLOW_PROD", "true")
    s = Settings()
    assert s.environment == "prod"
    assert "api.prismhr.com" in s.prismhr_base_url
    assert "uatapi" not in s.prismhr_base_url


def test_direct_credentials_override_onepassword(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRISMHR_MCP_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("PRISMHR_MCP_USERNAME", "test-user")
    monkeypatch.setenv("PRISMHR_MCP_PASSWORD", "s3cret")
    s = Settings()
    assert s.prismhr_credentials_direct == ("test-user", "s3cret")


def test_no_direct_credentials_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRISMHR_MCP_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("PRISMHR_MCP_USERNAME", raising=False)
    monkeypatch.delenv("PRISMHR_MCP_PASSWORD", raising=False)
    s = Settings()
    assert s.prismhr_credentials_direct is None
