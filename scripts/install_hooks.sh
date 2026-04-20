#!/usr/bin/env bash
# Install the tenant-PII blocking hooks so every commit is scanned.
# Run once per clone:
#     bash scripts/install_hooks.sh

set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg 2>/dev/null || true
echo "Installed .githooks as core.hooksPath."
echo ""
echo "Scanners active:"
echo "  .githooks/pre-commit   — blocks staged files containing PII"
echo "  .githooks/commit-msg   — blocks commit messages containing PII"
echo ""
echo "Run scripts/scan_pii.py anytime to audit the working tree."
echo "Run scripts/scan_pii.py --history origin/main..HEAD to audit"
echo "pending-push commit messages."
