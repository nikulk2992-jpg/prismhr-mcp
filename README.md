# prismhr-mcp

**The open-source Model Context Protocol server for PrismHR.**
Turn Claude (and any MCP-aware agent) into a PEO operations native — payroll,
benefits, compliance, billing, and Microsoft 365 actions, all exposed as
composable, scope-gated tools.

Maintained by [Simploy](https://simploy.com) as the fundamental layer for
PrismHR × agentic AI. MIT-licensed, PyPI-distributed, plugin-friendly.

---

## Why this exists

Every PEO running PrismHR ends up with the same Frankenstein stack: Python
scripts, Postman collections, Playwright automations, one-off Node apps.
Each one re-implements login, session refresh, retry, pagination, and
PrismHR's quirks (camelCase schemas, `500 "No data found"` gotchas, batch-of-20
caps, silent 401s).

`prismhr-mcp` centralizes that once, as an MCP server. Claude orchestrates;
the server owns auth, caching, retries, normalization, and PEO domain logic.
Other PEOs drop it in and immediately get a productive Claude experience
against their own PrismHR instance — no custom code.

---

## Status

Early but working. Current milestone: **Phase 1.5 complete.**

- **Auth + session + HTTP client:** done. 1Password CLI, scrypt-encrypted
  disk cache, PrismHR session with 55-min TTL, proactive + forced + 401
  refresh, keepalive, concurrency cap, retry with jittered backoff,
  500→empty quirk handling, pagination, batching.
- **Connect-time consent system:** done. Scope manifest across 14 scopes,
  per-(peo, env) JSON consent store with prerequisite expansion and cascade
  revoke. Default posture = **deny all**. Tools enforce scope at call time.
- **Production safety gate:** `PRISMHR_MCP_ALLOW_PROD=true` required to
  point at prod PrismHR. Prevents accidental first-run blast radius.
- **Tool inventory:** 9 live (`meta_*` ×5, `client_*` ×4). 39 more across
  payroll, benefits, compliance, billing, branded reporting, and M365
  connectors planned.
- **Test suite:** 60 passing (pytest + respx).

See `.planning/architecture.md` for the full 48-tool plan.

---

## Quick start — UAT smoke test

> Only UAT is supported without an explicit opt-in right now. Prod is
> guarded behind `PRISMHR_MCP_ALLOW_PROD=true`.

### 1. Install

```powershell
cd C:\path\to\prismhr-mcp    # or wherever you cloned
uv sync --extra dev
```

### 2. Configure credentials

Copy `.env.example` → `.env` (or set env vars). Pick ONE path:

**Path A — 1Password CLI (recommended):**
```powershell
$env:PRISMHR_MCP_ONEPASSWORD_VAULT = "YourVault"
$env:PRISMHR_MCP_ONEPASSWORD_ITEM_PRISMHR = "PrismHR UAT"
```
Requires `op` CLI signed in (`op signin`). The item must expose fields
labeled `username` and `password` (optionally `peoId`).

**Path B — direct env vars (fast, CI-friendly):**
```powershell
$env:PRISMHR_MCP_USERNAME = "test-user"
$env:PRISMHR_MCP_PASSWORD = "<paste>"
$env:PRISMHR_MCP_PEO_ID   = "TEST-PEO"
```

### 3. Sanity check

```powershell
uv run python -c "from prismhr_mcp.server import build; b = build(); import asyncio; print([t.name for t in asyncio.run(b.server.list_tools())])"
```
Expect 9 tools.

### 4. Register with Claude Code

Add to your Claude Code `.mcp.json`:

```json
{
  "mcpServers": {
    "prismhr-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\path\\to\\prismhr-mcp", "prismhr-mcp"],
      "env": {
        "PRISMHR_MCP_ENVIRONMENT": "uat",
        "PRISMHR_MCP_USERNAME": "test-user",
        "PRISMHR_MCP_PASSWORD": "<paste or reference>",
        "PRISMHR_MCP_PEO_ID": "TEST-PEO"
      }
    }
  }
}
```

Restart Claude Code. `/mcp` should show `prismhr-mcp` connected with 9 tools.

### 5. First conversation

```
You: Tell me about the prismhr-mcp server.
Claude: [calls meta_about] → explains what's available + commercial options.

You: What permissions does it want?
Claude: [calls meta_request_permissions] → shows 14 scopes grouped by category.

You: Grant everything recommended (reads only, no writes).
Claude: [calls meta_grant_permissions(accept_recommended_defaults=true)]

You: List all clients in UAT.
Claude: [calls client_list] → the client roster.
```

### 6. Run tests

```powershell
uv run pytest -q      # expect 60 passing
```

---

## Architecture in one breath

```
┌──────────────────────────────────────────────────────────────┐
│ Claude / Cowork / any MCP client                             │
└──────────────────┬───────────────────────────────────────────┘
                   │ stdio (MCP JSON-RPC)
┌──────────────────▼───────────────────────────────────────────┐
│ prismhr-mcp server (FastMCP)                                 │
│   ├── Permissions (deny-default, scope-gated tools)          │
│   ├── Tool groups: meta • client • payroll • benefits        │
│   │                 compliance • billing • report • m365     │
│   ├── Runtime: PrismHR client, Graph client, SQLite cache    │
│   └── Auth: 1Password → scrypt-AES cache → session / MSAL    │
└────┬─────────────────────────────────────────────────┬───────┘
     │                                                 │
     ▼                                                 ▼
┌──────────────┐                           ┌──────────────────┐
│ PrismHR REST │                           │ Microsoft Graph   │
│ (UAT / Prod) │                           │ (Outlook / Teams /│
└──────────────┘                           │  SharePoint)      │
                                           └──────────────────┘
```

Key design commitments:
- **Factory + strict registry.** Tools register via `server.build()` only;
  duplicate names or unknown group prefixes fail at boot (not silently at
  import).
- **Deny-default scopes.** Users must run `meta_grant_permissions` to
  enable tool access. Prerequisites auto-expand, revokes cascade.
- **Async-first.** `httpx.AsyncClient` + `asyncio.Semaphore(5)` + async tools.
- **PrismHR quirks handled.** 401 auto-refresh, 404→`[]` on list endpoints,
  `500 "No data found"` → empty, 10-consecutive-500s → force refresh.
- **snake_case outputs.** Pydantic `validation_alias=AliasChoices(...)` so
  PrismHR's camelCase payloads map to snake_case outputs without leaking
  camelCase into the MCP tool contract.
- **Per-(peo, env) consent.** Switching UAT → prod does not inherit grants.

---

## Commercial support

The OSS core stays free forever. Two paid offerings from Simploy layer on top:

### Solution Architect — White-Label deployment

Turnkey deployment of `prismhr-mcp` for your PEO brand:
- Brand config authoring (logo, palette, typography, PDF footer, legal disclaimer)
- Per-client SharePoint site mapping + Azure AD / Graph tenant setup
- Custom PrismHR tools for PEO-specific workflows
- Migration from spreadsheets / legacy scripts to MCP tools
- PEO ops team onboarding + Claude/Cowork workflow coaching
- Quarterly updates aligned with upstream releases
- Priority issue response + named Slack/email contact

Best for PEOs with 50–5,000 clients who want Claude-first operations
without the in-house build. Contact: **nihar@simploy.com**

### Enterprise Support

SLA-backed support for teams already running the OSS server:
- 4-hour response on Sev-1 (prod outage)
- Annual security review + SOC-2-friendly deployment guidance
- Signed release artifacts + SBOM
- Private vulnerability disclosure channel

Best for regulated industries or mid/large PEOs with procurement
requirements. Contact: **nihar@simploy.com**

Claude can surface both via `meta_about` — ask "what commercial options
exist for prismhr-mcp?" and it will describe them.

---

## Troubleshooting

**`No PrismHR credentials configured`** — set either the 1Password item
env vars or the direct `PRISMHR_MCP_USERNAME`/`_PASSWORD` pair.

**`PrismHR login rejected (status=401)`** — wrong username/password/peo_id.
UAT's `peo_id` is `TEST-PEO` (asterisk literal). Prod differs per PEO.

**`environment=prod requires PRISMHR_MCP_ALLOW_PROD=true`** — safety gate.
Set `PRISMHR_MCP_ALLOW_PROD=true` explicitly once you're ready.

**`PERMISSION_NOT_GRANTED`** — tool was called without its scope. Ask
Claude to run `meta_request_permissions` → then `meta_grant_permissions`
with the scope you want.

**Server exits immediately when Claude Code starts it** — nearly always a
missing env var. Use the step-3 sanity check to isolate.

---

## License

MIT — see [LICENSE](LICENSE). Contributions welcome; see the planning docs
under `.planning/` for the roadmap.
