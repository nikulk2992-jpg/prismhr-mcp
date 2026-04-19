# prismhr-mcp — Product Roadmap

Two-tier model confirmed during dev8:

## Tier 1 — `prismhr-mcp` (OSS, MIT)

The plumbing layer. Free forever. Anyone running PrismHR can install.

Ships:
- Auth + session + HTTP client (sessionId header, 401-refresh, 500→empty,
  10-consecutive-500 refresh, keepalive, encrypted disk cache via scrypt+AES-GCM)
- Bundled method catalog (447 PrismHR endpoints from the bible)
- Verified-schema gate — `meta_capabilities`, `meta_describe`, `meta_find`, `meta_call`
- Connect-time consent system (scope-gated, per-PEO, per-environment)
- Upstream permission introspection (`meta_upstream_permissions`)
- Calibrated probe harness — consumers run locally to build their own verified
  response matrix against their own tenant
- Prod-safety gate — opt-in via `PRISMHR_MCP_ALLOW_PROD=true`

Distributed via `pip install prismhr-mcp` and MCP Registry.

## Tier 2 — `prismhr-mcp-simploy` (Commercial, paid)

The product layer. Turnkey AI for PEO ops. Source-available; paid license.

### Named AI Assistants

Each assistant = curated tool bundle + verified response parsers + system prompts
+ branded outputs, shipped as a config drop-in. PEOs deploy without wiring tools.

- **Payroll Ops Assistant** — SuperBatch status, batch reconciliation, exception
  report, OT anomaly scan, deduction conflict audit, morning-of-pay checks
- **Benefits Admin Assistant** — ACA offering tracking, COBRA eligibility,
  open enrollment workflows, retirement plan audit, PTO accrual integrity
- **Client Onboarding Assistant** — new client setup (pay groups, SUTA rates,
  tax setup), new hire Employee Portal flow, document handoff
- **Compliance Assistant** — W2/1099 readiness, 941 reconciliation, state-tax
  audit, I-9/E-Verify roster, garnishment payment history
- **AR / Billing Assistant** — outstanding invoice summary, cash receipt
  reconciliation, AR aging, invoice-vs-payroll discrepancy explanation
- **Reporting Assistant** — branded PDF/XLSX generation with Simploy templates,
  per-client co-brand overlays, multi-client batch reports

### Workflow Tools (45+)

The original 48-tool plan lives here, not in OSS core:
- Group 1: Client & Employee Management (7 tools)
- Group 2: Payroll Operations (9 tools)
- Group 3: Benefits & Deductions (6 tools)
- Group 4: Compliance & Reporting (6 tools)
- Group 5: Billing & Client Financials (5 tools)
- Group 6: Branded Reporting (8 tools — pluggable template + brand registry)
- Group 7: Microsoft 365 Connectors (7 tools — Graph, SharePoint, Outlook, Teams)

Each tool = composed from verified `meta_call` primitives + domain logic
(reconciliation, anomaly detection, aggregation) + optional branded output.

### White-Label Deployment

- Brand config YAML (logo, palette, typography, footer, legal disclaimer)
- Per-client co-brand overlays (`brands/clients/<client>.yaml`)
- Simploy Solution Architect engagement — per-PEO setup + staff training

## OSS adoption → Commercial funnel

1. PEO developer installs `prismhr-mcp` from PyPI, runs against their tenant
2. Calibrated probe builds their private verification matrix
3. `meta_capabilities` shows Claude what's callable
4. Dev tries `meta_call("payroll.v1.getBatchListByDate.GET", {...})` — works,
   but they hit the ceiling: raw data in, raw data out, no workflow
5. Dev sees `meta_about` commercial tiers + visits Simploy site
6. Buys **Payroll Ops Assistant** → immediate business value

## Current state (as of v0.1.0.dev8)

| Component | OSS ships | Status |
|---|---|---|
| Auth + session + HTTP | Yes | Verified against UAT |
| Method catalog (447) | Yes | Shipped as package data |
| `meta_capabilities/describe/find/call` | Yes | 4 tools live |
| Consent + scope system | Yes | 15 scopes |
| Probe harness | Yes | `scripts/calibrated_probe.py` |
| Verified response matrix | Yes (sanitized) | 24 verified shapes |
| Group 1-7 workflow tools | Partially | `client_*` + `payroll_*` currently in OSS; will move to commercial in dev9 |
| Branded reporting | No | Commercial only |
| M365 connectors | No | Commercial only |
| Named AI assistants | No | Commercial only |

## Next moves (dev9+)

- **Move Simploy-specific workflow tools out of OSS core** into
  `prismhr-mcp-simploy` package (paid, source-available)
- **Heuristic constants → Settings** with Simploy defaults documented
- **Declarative tool-group registry** for dev9 scale (10+ groups)
- **Scope bundle collapse** (14 scopes → 6-8 human categories)
- **First Named Assistant prototype** — Payroll Ops Assistant — shipped as
  a reference commercial package alongside dev9
