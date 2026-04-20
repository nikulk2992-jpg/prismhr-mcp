"""Root conftest — runs once per test session.

Enforces the pre-commit PII scanner is installed. If `core.hooksPath`
isn't `.githooks`, prints a warning (doesn't fail the session — we
still want tests to run for fresh clones, but the warning is loud).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


_REPO = Path(__file__).resolve().parent


def pytest_configure(config):
    """Warn if the PII scanner hooks aren't installed on this clone."""
    try:
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            cwd=_REPO, capture_output=True, text=True, check=False,
        )
        hooks_path = result.stdout.strip()
    except Exception:  # noqa: BLE001
        return

    if hooks_path != ".githooks":
        banner = [
            "",
            "=" * 70,
            "WARNING: tenant-PII pre-commit hooks NOT installed on this clone.",
            "",
            "Run once to activate:",
            "    bash scripts/install_hooks.sh",
            "",
            "Or manually:",
            "    git config core.hooksPath .githooks",
            "",
            "CI (.github/workflows/pii-scan.yml) will still block pushes",
            "that leak tenant identifiers into files or commit messages,",
            "but local hooks are the first line of defense.",
            "=" * 70,
            "",
        ]
        print("\n".join(banner), file=sys.stderr)
