# prismhr-mcp

**The open-source Model Context Protocol (MCP) server for PrismHR.**
Connect Claude, Cursor, or any MCP-compatible AI agent directly to your
PrismHR PEO platform. Automate payroll, benefits enrollment, compliance
reporting, AR/billing, carrier EDI files, and Microsoft 365 actions — with
verified-schema tools, scope-gated consent, and zero custom integration code.

Built for PEOs, brokers, and payroll operators who want **AI agents that
actually work against PrismHR** — not another brittle script farm.

Maintained by [Simploy](https://simploy.com). MIT-licensed, PyPI-distributed,
plugin-friendly. The fundamental layer for **PrismHR × agentic AI**.

`mcp-name: io.github.nikulk2992-jpg/prismhr-mcp`

**Keywords:** PrismHR API, PrismHR integration, MCP server, Model Context
Protocol, PEO automation, payroll automation, AI for HR, Claude for PrismHR,
agentic AI, benefits enrollment automation, 834 EDI, 401(k) file automation,
HRIS AI agent, PEO software integration.

---

## Why this exists

Every PEO running PrismHR ends up with the same Frankenstein stack: Python
scripts, Postman collections, Playwright automations, one-off Node apps.
Each one re-implements login, session keepalive, retry logic, pagination,
and PrismHR's quirks (camelCase schemas, `500 "No data found"` gotchas,
batch-of-20 caps, silent 401s).

`prismhr-mcp` centralizes all of that once, as a production-grade MCP server.
The AI agent orchestrates; the server owns auth, caching, retries,
normalization, and PEO domain logic. Any PEO drops it in and gets a
productive AI experience against their own PrismHR tenant — no glue code,
no guesswork, no hallucinated endpoints.

**Who this is for:**
- PEOs running PrismHR who want to wire Claude / Cursor / ChatGPT Desktop
  directly into their ops stack
- Benefit brokers and carriers building enrollment automations
- Payroll teams replacing brittle Postman / Playwright workflows
- Consultants shipping PEO AI pilots on tight timelines

---

## Status

Production-ready core. Live on PyPI and the MCP Registry.

- **Auth + session + HTTP client:** done. 1Password CLI integration,
  scrypt-encrypted disk credential cache, PrismHR session with proactive
  keepalive (no mid-workflow 401s), automatic refresh on failure,
  concurrency cap, retry with jittered backoff, 500→empty quirk handling,
  pagination, batching.
- **Verified-schema gate:** every tool grounded in a live UAT probe —
  **no guessed endpoints, no invented fields**. 102 response shapes
  verified and rising.
- **447-method catalog:** full PrismHR REST surface indexed across 18
  services. `meta_call` lets the agent invoke any verified method safely.
- **Connect-time consent system:** 15-scope manifest, per-(peo, env) JSON
  consent store with prerequisite expansion and cascade revoke. Default
  posture = **deny all**. Tools enforce scope at call time.
- **Production safety gate:** `PRISMHR_MCP_ALLOW_PROD=true` required to
  point at prod PrismHR. Prevents accidental first-run blast radius.
- **MCP Registry listed:** discoverable by every MCP-aware client.
- **Test suite:** passing via pytest + respx.

See `.planning/architecture.md` for the full roadmap and
`.planning/assistants-roadmap.md` for the paid tier details.

---

## Editions

`prismhr-mcp` ships in three tiers. Core is free forever. Paid tiers layer
commercial PEO intelligence on top.

### Tier 1 — `prismhr-mcp` (this repo, MIT, free)

The foundation. What's in the box:

- PrismHR session manager with keepalive + auto-refresh
- 447-method catalog + verified-schema `meta_call`
- Scope-gated consent, prod safety gate, encrypted credential cache
- `meta_find`, `meta_describe`, `meta_capabilities`
- Client + employee + payroll read tools grounded in live UAT
- MCP Registry listing, PyPI distribution

Use this if you want to run Claude against your PrismHR tenant today with
zero custom code.

### Tier 2 — `prismhr-mcp-simploy` (paid, source-available) — *in active build*

Named AI Assistants that ship PEO workflows end-to-end. Built on the OSS
core. Licensed per-PEO.

**Shipping now:**
- **Carrier Enrollment Assistant** — generic 834 5010 EDI writer + carrier
  companion-guide configs. Guardian model prototype live (8 tests green).
  BCBS Michigan, Sun Life EDX, Voya PDI, Empower PDI on deck for Phase 1
  pilot. SFTP delivery + delta tracking next.
- **401(k) file automation** — Empower PDI, Voya payroll, Fidelity
  tape-spec fixed-width formats.

**On the roadmap:**
- **Payroll Ops Assistant** — void/correction workflows, deduction
  conflict detection, overtime anomaly flags, superbatch reconciliation
- **Benefits Admin Assistant** — benefit election audits, COBRA
  eligibility, ACA status, carrier sync verification
- **Compliance Assistant** — W2/941 reconciliation, garnishment tracking,
  state tax setup, I-9 audits, workers' comp codes
- **AR / Billing Assistant** — billing-vs-payroll audits, invoice
  summaries, employer tax liability
- **Branded reporting** — Simploy-branded PDF/XLSX via pluggable brand +
  template registry (white-label ready)
- **Microsoft 365 connectors** — Graph API email, SharePoint upload,
  Teams posts, Outlook events/tasks

### Tier 3 — `prismhr-mcp-broker` (paid, hosted) — *planned*

Multi-tenant hosted MCP endpoint so carriers, ERPs, and EDI providers can
reach any PrismHR PEO through a single integration. One endpoint, many
tenants, centralized compliance. Deferred until Tier 2 ships with a second
PEO.

Interested in Tier 2 or Tier 3? Contact `nihar@simploy.com`.

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
$env:PRISMHR_MCP_PEO_ID   = "<your-peo-id>"
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
        "PRISMHR_MCP_PEO_ID": "<your-peo-id>"
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
The `peo_id` is tenant-specific; ask your PrismHR admin. Prod and UAT have different values.

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
