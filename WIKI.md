# prismhr-mcp — Project Wiki

**The open-source Model Context Protocol (MCP) server for PrismHR.**

This wiki is the orientation doc for new contributors, PEO operators, and
anyone evaluating `prismhr-mcp` for their own tenant. If you just want to
install and run, the [README](https://github.com/nikulk2992-jpg/prismhr-mcp#readme)
is the place to go. This page explains **what we're building and why**.

---

## What this is

`prismhr-mcp` is a production-grade MCP server that lets an AI agent
(Claude, Cursor, ChatGPT Desktop, any MCP-aware client) talk directly to
the PrismHR REST API without glue code, hand-written wrappers, or
hallucinated endpoints.

At its core it does three things:

1. **Owns the hard parts of PrismHR integration** — session auth,
   keepalive, retry logic, pagination, concurrency caps, quirks like
   `500 "No data found"`, batch-of-20 caps, and silent 401s.
2. **Gates every call through a verified-schema catalog** — 447 PrismHR
   methods indexed across 18 services; each tool ships only when its
   response shape has been observed live against UAT. No guessing. No
   invented fields.
3. **Enforces a scope consent model** — default posture is deny-all; the
   operator grants scopes per-(peo, env); tools check scope at call time.

Everything else — workflow tools, carrier EDI files, branded reports,
Microsoft 365 connectors — is layered on top of this core.

---

## Why this exists

Every PEO running PrismHR ends up building the same Frankenstein stack:
Python scripts, Postman collections, Playwright automations, one-off
Node apps. Each one re-implements login, session refresh, retries, and
pagination. Each one hallucinates field names until something breaks in
production.

The thesis: **the integration layer should be written once, open-source,
and become the default substrate** for PrismHR × AI. The PEO industry is
small, tight-knit, and underserved by generic automation tools. A single
well-maintained MCP server serving every operator is a better outcome
than each PEO rebuilding the wheel in private.

That's this repo.

---

## Who this is for

- **PEOs running PrismHR** who want AI agents wired into daily ops
  (payroll audits, benefit reconciliation, new-hire onboarding checks)
- **Benefit brokers and carriers** building enrollment file automations
  on top of PrismHR census data
- **Payroll teams** replacing brittle scripts with a single MCP endpoint
- **PEO consultants and solution architects** shipping pilots on tight
  timelines — drop in the server, get Claude productive in an afternoon

---

## Architecture at a glance

```
┌──────────────────────────────────────────────────────┐
│  AI agent (Claude / Cursor / any MCP client)         │
└──────────────────────┬───────────────────────────────┘
                       │  MCP stdio
┌──────────────────────▼───────────────────────────────┐
│  prismhr-mcp server                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────┐   │
│  │ Tools layer  │  │ Scope consent │  │ Catalog  │   │
│  │ (meta_*,     │  │ (per-peo/env) │  │ (447     │   │
│  │  client_*,   │  │               │  │ methods, │   │
│  │  payroll_*)  │  │               │  │ 102+     │   │
│  │              │  │               │  │ verified)│   │
│  └──────┬───────┘  └───────┬───────┘  └────┬─────┘   │
│         │                  │                │         │
│  ┌──────▼──────────────────▼────────────────▼─────┐  │
│  │ Session + HTTP client (httpx async)            │  │
│  │   keepalive, retry, concurrency cap, paging    │  │
│  └────────────────────┬───────────────────────────┘  │
└───────────────────────┼──────────────────────────────┘
                        │  HTTPS (sessionId header)
               ┌────────▼─────────┐
               │  PrismHR REST    │
               │  UAT or Prod     │
               └──────────────────┘
```

Credentials come from 1Password CLI or direct env vars, cached on disk
with scrypt + AES-GCM. Prod access is gated behind an explicit opt-in
env flag to prevent accidental first-run damage.

---

## Editions (tiers)

`prismhr-mcp` ships in three tiers. Core is MIT and free forever. Paid
tiers layer commercial PEO intelligence on top.

### Tier 1 — `prismhr-mcp` (MIT, free)

This repo. The foundation. Auth stack, session manager, 447-method
catalog, `meta_call`, scope consent, verified-schema gate, calibrated
probe harness, prod safety gate, PyPI distribution, MCP Registry listing.

Use this if you want to run an AI agent against your PrismHR tenant
today with zero custom code.

### Tier 2 — `prismhr-mcp-simploy` (paid, source-available, in active build)

Named AI Assistants that ship end-to-end PEO workflows. Licensed per-PEO.

**Shipping now:**
- **Carrier Enrollment Assistant** — generic ANSI X12 834 5010 EDI
  writer + per-carrier companion-guide configs. Guardian model prototype
  live; BCBS Michigan, Sun Life EDX, Voya PDI, Empower PDI on deck.
- **401(k) file automation** — fixed-width formats for the major
  recordkeepers.

**Planned:**
- Payroll Ops Assistant (void / correction / superbatch reconciliation)
- Benefits Admin Assistant (election audits, COBRA, ACA, carrier sync)
- Compliance Assistant (W2/941, garnishments, state tax, I-9)
- AR / Billing Assistant (billing-vs-payroll audits, invoice summaries)
- Branded reporting (pluggable brand + template registry, white-label)
- Microsoft 365 connectors (Graph email, SharePoint, Teams, Outlook)

### Tier 3 — `prismhr-mcp-broker` (paid, hosted, planned)

Multi-tenant hosted MCP endpoint so carriers, ERPs, and EDI providers
can reach any PrismHR PEO through a single integration. Deferred until
Tier 2 ships to a second PEO.

---

## Core principles

**No guesswork, ever.** Every tool is grounded in a live UAT probe.
If we haven't observed the response shape, the tool doesn't ship.
Hallucinated fields are worse than missing features.

**Deny-all by default.** No tool runs without explicit scope consent
for the (peo, env) pair. First-run opens a plain-text consent prompt,
not a firehose of API access.

**Prod is opt-in.** `PRISMHR_MCP_ALLOW_PROD=true` required. UAT is the
default for everything — development, demos, CI.

**Keepalive, not TTL magic.** Sessions stay warm via a 10-minute
keepalive ping. No mysterious mid-workflow 401s. Refresh-on-failure is
a fallback, not the primary contract.

**Simploy configs stay local.** The OSS core has no tenant-specific
defaults baked in. Anything PEO-specific (carrier trading-partner IDs,
plan code maps, SharePoint site paths) lives in the commercial tier or
in operator-supplied config.

**Commercial tier pays for itself.** Workflow automations, carrier
models, and white-label reporting are paid. The core that makes PrismHR
accessible to any AI agent is free — because the industry needs it.

---

## How verification works

Every entry in the catalog has a verification state:

| State | Meaning |
|---|---|
| `verified` | Response shape observed live in UAT; tool ships |
| `authorized_no_fixture` | Service authorized, no fixture yet; tool gated |
| `unauthorized` | Permission not granted by PrismHR admin yet |
| `admin_only` | Hard-blocked at the catalog layer |

Coverage progression so far: 3 → 24 → 28 → 48 → 66 → 79 → 89 → 91 → 102
verified shapes across four PrismHR admin grant rounds (134 → 168 → 189
→ 209 authorized services).

The calibrated probe harness under `scripts/` drives this. It learns
real IDs from successful responses, never invents them, and only probes
methods whose required params are satisfied. Raw responses are gitignored
(PII); sanitized verification matrix is committed to `.planning/`.

---

## Getting started

1. Read the [README](https://github.com/nikulk2992-jpg/prismhr-mcp#readme)
   for install + quick start.
2. Review `.planning/architecture.md` for the full tool roadmap.
3. Review `.planning/assistants-roadmap.md` for the paid tier plan.
4. Review `.planning/carrier-map.md` for the carrier EDI strategy.
5. Install from PyPI (`pip install prismhr-mcp`) or clone + `uv sync`.

---

## Contributing

Issues and PRs welcome. A few ground rules:

- **No guessing in the catalog.** If a schema isn't observed in UAT,
  it doesn't land. Add a probe first, then the tool.
- **No tenant data in commits.** Raw API responses contain PII; they
  stay in gitignored dirs. Sanitize before committing anything derived.
- **Scope before action.** Every new tool must declare its scope and be
  deny-all by default.
- **Commit authorship is the human author only.** No AI co-author
  trailers in commit messages.

---

## Contact

- Issues: https://github.com/nikulk2992-jpg/prismhr-mcp/issues
- Commercial tier inquiries: `nihar@simploy.com`
- Maintainer: Nihar Kulkarni, Simploy
