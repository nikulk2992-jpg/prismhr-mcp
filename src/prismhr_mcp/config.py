"""Runtime configuration, loaded from environment with safe defaults.

Env prefix: `PRISMHR_MCP_`.

Two credential sources are supported for PrismHR:
  1. 1Password CLI (`op`) — preferred; credentials never touch shell history.
  2. Direct env vars — `PRISMHR_MCP_USERNAME` / `PRISMHR_MCP_PASSWORD` — for CI and dev.

Graph settings live here too but are stubbed until Phase 5.

Safety gate: the `prod` environment requires `PRISMHR_MCP_ALLOW_PROD=true`.
This keeps the default posture safe for a fundamental-layer OSS product —
a developer trying the server for the first time can't accidentally hit
production PrismHR data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["uat", "prod"]


class ProductionNotAllowedError(RuntimeError):
    """Raised when environment=prod without an explicit opt-in via PRISMHR_MCP_ALLOW_PROD."""


class Settings(BaseSettings):
    """Top-level server settings. Populated from `PRISMHR_MCP_*` env vars."""

    model_config = SettingsConfigDict(
        env_prefix="PRISMHR_MCP_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )

    environment: Environment = "uat"
    allow_prod: bool = Field(
        default=False,
        description=(
            "Must be true to allow environment=prod. Default deny prevents "
            "accidental first-run impact on production PrismHR data."
        ),
    )

    prismhr_uat_base_url: str = "https://uatapi.prismhr.com/demo/prismhr-api/services/rest"
    prismhr_prod_base_url: str = "https://api.prismhr.com/prismhr-api/services/rest"

    # PrismHR PEO ID — UAT default is "624*D".
    prismhr_peo_id: str = Field(
        default="624*D",
        validation_alias=AliasChoices("PRISMHR_MCP_PEO_ID", "prismhr_peo_id"),
    )

    # 1Password item reference (used when direct creds not provided).
    onepassword_vault: str | None = None
    onepassword_item_prismhr: str | None = None
    onepassword_item_graph: str | None = None

    # Direct overrides. When set, skip 1Password entirely.
    # Env var names are the user-friendly `PRISMHR_MCP_USERNAME` / `PRISMHR_MCP_PASSWORD`.
    prismhr_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PRISMHR_MCP_USERNAME", "prismhr_username"),
    )
    prismhr_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("PRISMHR_MCP_PASSWORD", "prismhr_password"),
    )

    # Azure AD / Graph — populated in Phase 5.
    graph_tenant_id: str | None = None
    graph_client_id: str | None = None
    graph_client_secret: SecretStr | None = None

    # Where to keep the scrypt-encrypted credential cache + SQLite cache.
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".prismhr-mcp")

    # PrismHR session TTL and keepalive cadence — match the Electron app.
    session_ttl_seconds: int = 55 * 60
    session_keepalive_seconds: int = 10 * 60
    session_refresh_margin_seconds: int = 5 * 60

    # HTTP concurrency + retry.
    prismhr_max_concurrency: int = 5
    prismhr_max_attempts: int = 3
    prismhr_backoff_base_seconds: float = 1.5

    @property
    def prismhr_base_url(self) -> str:
        return self.prismhr_uat_base_url if self.environment == "uat" else self.prismhr_prod_base_url

    @property
    def prismhr_credentials_direct(self) -> tuple[str, str] | None:
        """Returns (username, password) if both env overrides are set, else None."""
        if self.prismhr_username and self.prismhr_password is not None:
            return self.prismhr_username, self.prismhr_password.get_secret_value()
        return None

    @model_validator(mode="after")
    def _ensure_cache_dir(self) -> "Settings":
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return self

    @model_validator(mode="after")
    def _gate_production(self) -> "Settings":
        if self.environment == "prod" and not self.allow_prod:
            raise ProductionNotAllowedError(
                "environment=prod requires PRISMHR_MCP_ALLOW_PROD=true. "
                "This is a safety default for prismhr-mcp: production access is "
                "opt-in to prevent first-run accidents. Set the flag explicitly "
                "once you have reviewed the permission grants you want to apply."
            )
        return self


def load_settings() -> Settings:
    """Explicit loader so tests can patch env before construction."""
    return Settings()


# Optional: allow `import prismhr_mcp.config as cfg; cfg.settings` for convenience.
# The factory form in load_settings() is preferred for tests.
settings: Settings | None = None


def get_settings() -> Settings:
    """Lazy-cached settings accessor for runtime code paths."""
    global settings
    if settings is None:
        settings = load_settings()
    return settings


def reset_settings() -> None:
    """Test helper — forces the next `get_settings()` to re-read env."""
    global settings
    settings = None
