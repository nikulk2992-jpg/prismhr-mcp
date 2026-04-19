"""Local .env encryption using the same scrypt + AES-GCM primitive as
`auth/onepassword.py`.

Scope: a developer's own machine. Key = scrypt(hostname + username).
Threat model: prevents casual disk exfiltration (backup tools, cloud
sync folders). Does NOT protect against an attacker who can run code
as the same user on the same host. For production secrets, use a real
secret manager (1Password service account, Azure Key Vault, etc.).

Stored format (little endian is not used; everything big endian):
  ┌────────┬──────────┬──────────┬──────────────┐
  │ u8 ver │ 16 bytes │ 12 bytes │  ciphertext  │
  │   =1   │   salt   │  nonce   │ + GCM tag    │
  └────────┴──────────┴──────────┴──────────────┘
"""

from __future__ import annotations

import getpass
import hashlib
import os
import socket
import struct
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION = 1
SALT_LEN = 16
NONCE_LEN = 12
KEY_LEN = 32
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
_HEADER = struct.Struct(">B")


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


def encrypt_bytes(plaintext: bytes) -> bytes:
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(salt)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, associated_data=None)
    return _HEADER.pack(VERSION) + salt + nonce + ciphertext


def decrypt_bytes(blob: bytes) -> bytes:
    if len(blob) < 1 + SALT_LEN + NONCE_LEN + 16:
        raise ValueError("encrypted blob too short")
    (version,) = _HEADER.unpack(blob[:1])
    if version != VERSION:
        raise ValueError(f"unsupported secure_env version: {version}")
    cursor = 1
    salt = blob[cursor : cursor + SALT_LEN]
    cursor += SALT_LEN
    nonce = blob[cursor : cursor + NONCE_LEN]
    cursor += NONCE_LEN
    ciphertext = blob[cursor:]
    key = _derive_key(salt)
    return AESGCM(key).decrypt(nonce, ciphertext, associated_data=None)


def write_encrypted(path: Path, plaintext: bytes) -> None:
    path.write_bytes(encrypt_bytes(plaintext))
    try:
        path.chmod(0o600)
    except OSError:
        pass  # Windows ignores POSIX modes; NTFS ACLs are another path.


def read_encrypted(path: Path) -> bytes:
    return decrypt_bytes(path.read_bytes())


def load_into_environ(path: Path) -> list[str]:
    """Decrypt a dotenv-style file and inject into os.environ.

    Returns the list of keys that were loaded (for logging). Values are
    NEVER returned, printed, or otherwise leaked.
    """
    text = read_encrypted(path).decode("utf-8")
    loaded: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        # Strip optional surrounding quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value
        loaded.append(key)
    return loaded
