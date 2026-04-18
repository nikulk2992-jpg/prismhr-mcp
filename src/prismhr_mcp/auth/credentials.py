"""Credential sources for PrismHR session login.

Abstracts away whether the peo_id/username/password came from 1Password,
direct env vars, or a test fixture. The session manager only sees the triple.
"""

from __future__ import annotations

from typing import Protocol

from ..config import Settings
from .onepassword import OnePasswordClient


class CredentialSource(Protocol):
    async def get(self) -> tuple[str, str, str]:
        """Return (peo_id, username, password)."""
        ...


class DirectCredentialSource:
    """Reads creds straight from env-configured settings — used in CI/dev."""

    def __init__(self, peo_id: str, username: str, password: str) -> None:
        self._peo_id = peo_id
        self._username = username
        self._password = password

    async def get(self) -> tuple[str, str, str]:
        return self._peo_id, self._username, self._password


class OnePasswordCredentialSource:
    """Fetches creds from a 1Password item via `op` CLI (with disk cache).

    The item is expected to expose fields labeled `username`, `password`,
    and optionally `peoId`. If the item doesn't include `peoId`, the value
    from settings is used as the fallback.
    """

    def __init__(
        self,
        client: OnePasswordClient,
        vault: str,
        item: str,
        fallback_peo_id: str,
    ) -> None:
        self._client = client
        self._vault = vault
        self._item = item
        self._fallback_peo_id = fallback_peo_id

    async def get(self) -> tuple[str, str, str]:
        fields = self._client.get(item=self._item, vault=self._vault)
        try:
            username = fields["username"]
            password = fields["password"]
        except KeyError as exc:
            raise RuntimeError(
                f"1Password item {self._item!r} missing required field: {exc.args[0]!r}"
            ) from exc
        peo_id = fields.get("peoId", self._fallback_peo_id)
        return peo_id, username, password


def build_credential_source(settings: Settings) -> CredentialSource:
    """Pick the right credential source based on env. Direct overrides win."""
    direct = settings.prismhr_credentials_direct
    if direct is not None:
        username, password = direct
        return DirectCredentialSource(settings.prismhr_peo_id, username, password)

    if settings.onepassword_vault and settings.onepassword_item_prismhr:
        op_client = OnePasswordClient(cache_dir=settings.cache_dir)
        return OnePasswordCredentialSource(
            client=op_client,
            vault=settings.onepassword_vault,
            item=settings.onepassword_item_prismhr,
            fallback_peo_id=settings.prismhr_peo_id,
        )

    raise RuntimeError(
        "No PrismHR credentials configured. Set PRISMHR_MCP_USERNAME + "
        "PRISMHR_MCP_PASSWORD, or PRISMHR_MCP_ONEPASSWORD_VAULT + "
        "PRISMHR_MCP_ONEPASSWORD_ITEM_PRISMHR."
    )
