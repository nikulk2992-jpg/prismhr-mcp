"""1Password CLI credential fetcher with scrypt-encrypted disk cache.

Mirrors the pattern in `simploy-prismhr-app/src/main/services/onepassword-auth.ts`:
  1. Invoke `op item get <item> --vault <vault> --format json`.
  2. Parse the `fields[]` array into a `{label: value}` map.
  3. Encrypt with AES-GCM using scrypt(hostname + username) as key.
  4. Cache on disk for 24h so repeat boots don't re-hit the vault.

The `runner` callable is injectable — tests substitute a fake subprocess.
"""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import socket
import struct
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CACHE_VERSION = 1
CACHE_TTL_SECONDS = 24 * 60 * 60
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 32  # AES-256
SALT_LEN = 16
NONCE_LEN = 12
_HEADER_STRUCT = struct.Struct(">BQ")  # version (u8) + expires_at_epoch (u64)

# Runner signature: (cmd: list[str]) -> (returncode, stdout, stderr)
Runner = Callable[[list[str]], tuple[int, str, str]]


def _default_runner(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


class CredentialError(RuntimeError):
    """Raised when we cannot obtain a credential from 1Password or cache."""


@dataclass(slots=True)
class CachedCredential:
    fields: dict[str, str]
    expires_at: float

    @property
    def valid(self) -> bool:
        return time.time() < self.expires_at


class OnePasswordClient:
    """Fetches credentials via `op` CLI and caches them encrypted at rest."""

    def __init__(
        self,
        cache_dir: Path,
        runner: Runner | None = None,
        binary: str = "op",
    ) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._runner = runner or _default_runner
        self._binary = binary

    # ------------- public API -------------

    def get(self, item: str, vault: str) -> dict[str, str]:
        """Return `{label: value}` for the requested 1Password item.

        Hits the disk cache first. If absent or expired, calls `op` and
        re-encrypts. Raises `CredentialError` if neither path yields data.
        """
        cached = self._load_cached(item, vault)
        if cached is not None and cached.valid:
            return cached.fields

        fields = self._fetch_remote(item, vault)
        self._store_cached(item, vault, fields)
        return fields

    def invalidate(self, item: str, vault: str) -> None:
        path = self._cache_path(item, vault)
        if path.exists():
            path.unlink()

    # ------------- internals -------------

    def _fetch_remote(self, item: str, vault: str) -> dict[str, str]:
        cmd = [self._binary, "item", "get", item, "--vault", vault, "--format", "json"]
        code, stdout, stderr = self._runner(cmd)
        if code != 0:
            raise CredentialError(
                f"`op item get {item}` failed (exit={code}): {stderr.strip() or stdout.strip()}"
            )
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise CredentialError(f"Malformed 1Password response: {exc}") from exc
        return self._flatten_fields(payload)

    @staticmethod
    def _flatten_fields(payload: dict[str, Any]) -> dict[str, str]:
        fields: dict[str, str] = {}
        for entry in payload.get("fields") or []:
            label = entry.get("label")
            value = entry.get("value")
            if label and value:
                fields[label] = value
        return fields

    # --- encryption -----------------------------------------------------

    @staticmethod
    def _derive_key(salt: bytes) -> bytes:
        passphrase = f"{socket.gethostname()}::{getpass.getuser()}".encode()
        return hashlib.scrypt(
            password=passphrase,
            salt=salt,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=KEY_LEN,
        )

    def _cache_path(self, item: str, vault: str) -> Path:
        safe = hashlib.sha256(f"{vault}::{item}".encode()).hexdigest()[:32]
        return self._cache_dir / f"cred-{safe}.enc"

    def _store_cached(self, item: str, vault: str, fields: dict[str, str]) -> None:
        salt = os.urandom(SALT_LEN)
        nonce = os.urandom(NONCE_LEN)
        key = self._derive_key(salt)
        expires_at = int(time.time()) + CACHE_TTL_SECONDS
        plaintext = json.dumps(fields, separators=(",", ":")).encode()
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, associated_data=None)

        path = self._cache_path(item, vault)
        with path.open("wb") as fh:
            fh.write(_HEADER_STRUCT.pack(CACHE_VERSION, expires_at))
            fh.write(salt)
            fh.write(nonce)
            fh.write(ciphertext)
        # Best-effort file-mode lockdown; Windows ignores.
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def _load_cached(self, item: str, vault: str) -> CachedCredential | None:
        path = self._cache_path(item, vault)
        if not path.exists():
            return None
        try:
            raw = path.read_bytes()
            header_size = _HEADER_STRUCT.size
            version, expires_at = _HEADER_STRUCT.unpack(raw[:header_size])
            if version != CACHE_VERSION:
                return None
            cursor = header_size
            salt = raw[cursor : cursor + SALT_LEN]
            cursor += SALT_LEN
            nonce = raw[cursor : cursor + NONCE_LEN]
            cursor += NONCE_LEN
            ciphertext = raw[cursor:]
            key = self._derive_key(salt)
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, associated_data=None)
            fields = json.loads(plaintext.decode())
            if not isinstance(fields, dict):
                return None
            return CachedCredential(fields=fields, expires_at=float(expires_at))
        except Exception:  # noqa: BLE001 — corrupt cache should be treated as miss.
            # Corrupt cache or machine changed (hostname/user). Drop it.
            path.unlink(missing_ok=True)
            return None
