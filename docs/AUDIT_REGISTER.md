# Audit Register

This file documents every entry in `.codex-audit-allow`. Each allowlisted
finding needs a rationale so future reviewers (and you, in six months) can
tell the difference between a deliberate exception and rot.

## F1:tests/:0 — "pytest failed: No module named 'prismhr_mcp'"

**Status:** Allowlisted. Not a real failure.

**Why the gate trips:** The global pre-push hook runs `pytest` directly. This
project is managed by `uv`, so the `prismhr_mcp` package is only importable
inside the uv-managed virtualenv. A bare `pytest` invocation executed outside
`uv run` cannot find the package.

**Why it's safe to allowlist:** The test suite passes cleanly — 62 passing,
0 failing — when invoked the way every developer and CI runs it:

```powershell
uv run pytest -q
```

The gate is correctly detecting that bare `pytest` fails; that's not a signal
about test quality, it's a signal that the gate assumes a different Python
environment model than uv projects use.

**When to revisit:** If/when we add CI (GitHub Actions) the workflow will run
`uv run pytest` and surface real failures there. We can also drop this entry
once the global hook is updated to use `uv run pytest` in uv-managed repos.

**Owner:** @nikulk2992-jpg
**Added:** 2026-04-18
