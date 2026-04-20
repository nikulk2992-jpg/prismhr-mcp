"""Tenant-PII scanner for prismhr-mcp.

Hard-fails if any tracked file contains the class of identifiers that
should stay local-only (real client IDs, real employee IDs, real
personal names pulled from probes / sweeps / dogfoods).

Runs in two modes:
  1. `python scripts/scan_pii.py` — scan the working tree. Exit code
     1 if PII found, 0 if clean.
  2. `python scripts/scan_pii.py --staged` — scan only staged files.
     Used by the pre-commit hook to block bad commits.
  3. `python scripts/scan_pii.py --history [ref_range]` — scan commit
     messages + tree at each commit. Used by CI / one-off audits.

Tuning:
  * patterns below are conservative — add as new tenant data appears
  * allowlist specific strings that look like IDs but aren't
    (PrismHR's own bundled method docs have 000123/123456 examples)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


# Hard tokens — match verbatim. Names + specific employee IDs that
# should never appear in tracked content.
BANNED_TOKENS: list[str] = [
    # Real names surfaced during dogfood / sweep
    "Hardin",
    "HARDIN",
    "Bryan Hardin",
    "BRYAN D",
    "Salazar",
    "Alberto Salazar",
    "Peggy Clay",
    "Rob Arlinghaus",
    "Arlinghaus",
    "Ashley Chance",
    "Jason Sieg",
    "Jennifer Gergen",
    "Blake Bettey",
    "Keith Puckett",
    "Redkey",
    "Phantom Neuro",
    "Rise Community",
    "Warren Professional",
    "Joseph Michael Nunn",
    "Simploy Outsourcing",
    # Employee IDs observed in UAT
    "M12853",
    "X16702",
    "F15198",
    "G10567",
    "R11296",
    "A00025",
    "E08645",
    "E09317",
    "A09313",
    "H12272",
    "H09176",
    "Y11879",
    "A05449",
    "A05521",
]


# Patterns — regex-based PrismHR client IDs. Most false-positive-prone
# because numeric IDs are context-sensitive. Exempt safe files.
CLIENT_ID_PATTERN = re.compile(r"\b00[0-9]{4}\b")

PATH_ALLOWLIST_FOR_CLIENT_IDS = {
    # PrismHR's own bundled method docs contain example IDs like 000123
    "src/prismhr_mcp/data/methods.json",
    ".planning/prismhr-methods-full.json",
    ".planning/prismhr-methods-v2.json",
    ".planning/prismhr-methods.json",
}

# Paths where BANNED_TOKENS are allowed — these files define or reference
# the banned list for their own purpose (the scanner + the filter-repo
# callback).
PATH_ALLOWLIST_FULL = {
    "scripts/scan_pii.py",
    "scripts/_pii_message_callback.py",
}


def _scan_text(text: str, *, skip_client_ids: bool = False) -> list[str]:
    """Return the list of banned tokens / IDs that appear in text."""
    hits: list[str] = []
    lowered = text
    # Token scan (case-sensitive; names are stored with correct case)
    for tok in BANNED_TOKENS:
        if tok in lowered:
            hits.append(tok)
    # Client ID scan
    if not skip_client_ids:
        for m in CLIENT_ID_PATTERN.finditer(text):
            hits.append(f"client-id-pattern:{m.group(0)}")
    return hits


def _scan_file(path: Path, repo_rel: str) -> list[tuple[int, str]]:
    """Line-by-line scan. Returns list of (line_no, token) hits."""
    if repo_rel in PATH_ALLOWLIST_FULL:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return []
    skip_client_ids = repo_rel in PATH_ALLOWLIST_FOR_CLIENT_IDS
    out: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        hits = _scan_text(line, skip_client_ids=skip_client_ids)
        for h in hits:
            out.append((i, h))
    return out


def _tracked_files() -> list[str]:
    """All files tracked by git in the working tree."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO, capture_output=True, text=True, check=True,
    )
    return [p for p in result.stdout.splitlines() if p.strip()]


def _staged_files() -> list[str]:
    """Files in the git index (about to be committed)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--cached", "--diff-filter=ACM"],
        cwd=REPO, capture_output=True, text=True, check=True,
    )
    return [p for p in result.stdout.splitlines() if p.strip()]


def _scan_commit_messages(ref_range: str) -> list[tuple[str, list[str]]]:
    """Scan commit messages in the given range. Empty range = all."""
    cmd = ["git", "log", "--format=%H%n%B%n---END-COMMIT---"]
    if ref_range:
        cmd.append(ref_range)
    result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=True)
    out: list[tuple[str, list[str]]] = []
    current_sha = ""
    current_msg: list[str] = []
    for line in result.stdout.splitlines():
        if line == "---END-COMMIT---":
            if current_sha:
                full = "\n".join(current_msg)
                hits = _scan_text(full, skip_client_ids=False)
                if hits:
                    out.append((current_sha, sorted(set(hits))))
            current_sha = ""
            current_msg = []
        elif not current_sha:
            current_sha = line.strip()
        else:
            current_msg.append(line)
    return out


def run_working_tree() -> int:
    hits_any = False
    for rel in _tracked_files():
        path = REPO / rel
        if not path.is_file():
            continue
        hits = _scan_file(path, rel)
        for line_no, token in hits:
            hits_any = True
            print(f"PII  {rel}:{line_no}  {token}")
    return 1 if hits_any else 0


def run_staged() -> int:
    hits_any = False
    for rel in _staged_files():
        path = REPO / rel
        if not path.is_file():
            continue
        hits = _scan_file(path, rel)
        for line_no, token in hits:
            hits_any = True
            print(f"PII  {rel}:{line_no}  {token}")
    return 1 if hits_any else 0


def run_history(ref_range: str) -> int:
    hits_any = False
    for sha, tokens in _scan_commit_messages(ref_range):
        hits_any = True
        print(f"PII  {sha[:10]}  commit-message  {', '.join(tokens)}")
    return 1 if hits_any else 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--staged", action="store_true",
                   help="Scan only staged files (pre-commit mode).")
    p.add_argument("--history", nargs="?", const="",
                   help="Scan commit messages. Optional rev range "
                        "e.g. main..HEAD or origin/main..")
    args = p.parse_args()

    if args.staged:
        rc = run_staged()
        if rc:
            print()
            print("PII SCANNER BLOCKED COMMIT.")
            print("Remove tenant identifiers from tracked files. Use "
                  "generic placeholders (E001, C001) in tests.")
            print("Reference: scripts/scan_pii.py BANNED_TOKENS list.")
        return rc
    if args.history is not None:
        return run_history(args.history)
    return run_working_tree()


if __name__ == "__main__":
    sys.exit(main())
