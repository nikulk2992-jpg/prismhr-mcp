"""Encrypt dotenv content from stdin into `.env.local.enc`.

Usage:
    cat creds.txt | uv run python scripts/encrypt_env.py
    printf 'KEY=value\n' | uv run python scripts/encrypt_env.py

The plaintext never touches disk. The encrypted file is machine-local:
key is derived from scrypt(hostname+username), so it only decrypts on
the same machine under the same user account.

.gitignore excludes the output — verify with `git status` after.
"""

from __future__ import annotations

import sys
from pathlib import Path

from prismhr_mcp.secure_env import write_encrypted

DEFAULT_TARGET = Path(".env.local.enc")


def main() -> int:
    data = sys.stdin.buffer.read()
    if not data.strip():
        print("refusing to encrypt empty input", file=sys.stderr)
        return 2

    target = DEFAULT_TARGET
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])

    write_encrypted(target, data)
    keys = [
        line.split("=", 1)[0].strip()
        for line in data.decode("utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#") and "=" in line
    ]
    print(f"wrote {target} ({len(data)} bytes plaintext -> {target.stat().st_size} bytes ciphertext)")
    print(f"keys: {keys}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
