# `prismhr-mcp-portal` — Client-Facing Tier (Tier 2.5)

**Status:** proposal
**Owner:** Nihar Kulkarni / Simploy
**Created:** 2026-04-19

---

## The gap this fills

PrismHR's ecosystem has three audiences, but the integration story only
serves two today:

| Audience | Count (PrismHR ecosystem) | Existing tooling |
|---|---|---|
| **PEOs running PrismHR** | ~400–600 | PrismHR admin UI + internal scripts |
| **Carriers / ERPs / EDI partners** | ~1,000+ | detamoov, EDI file drops, custom per-PEO integrations |
| **PEO client companies** (end employers) | **~50,000–100,000** | Email the PEO rep. Wait hours-to-days. |

The third group is the largest by an order of magnitude and the most
underserved. Every PEO client company has the same experience today:

- Need to check last pay period's register? → email rep.
- Need to confirm a terminated employee's final check? → email rep.
- Want 2025 W2 totals? → email rep.
- Want to know who's on PTO next week? → email rep.
- Need I-9 expiration roster? → email rep.

Every request is a human in the loop on the PEO side, usually a Payroll
Ops Specialist or Benefits Admin with a queue of 20+ tickets per day.

**The opportunity:** give PEO client companies scoped, read-only,
AI-native access to their own PrismHR data. Claude / ChatGPT / Cursor
answers in seconds. PEO rep freed up for the 10% of requests that
actually need human judgment.

---

## Positioning in the tier stack

```
┌──────────────────────────────────────────────────────────────────┐
│ Tier 1 — prismhr-mcp (MIT, free)                                 │
│   Infrastructure for developers + any PEO wanting raw access     │
├──────────────────────────────────────────────────────────────────┤
│ Tier 2 — prismhr-mcp-simploy (paid, source-available)            │
│   Named AI Assistants + carrier models + workflow tools          │
│   ICP: PEOs running ops                                          │
├──────────────────────────────────────────────────────────────────┤
│ ★ Tier 2.5 — prismhr-mcp-portal (paid SaaS, hosted, multi-tenant)│
│   Scoped read-only client-company portal                         │
│   ICP: 50K+ small/mid employers under a PEO                      │
├──────────────────────────────────────────────────────────────────┤
│ Tier 3 — prismhr-mcp-broker (paid platform, hosted)              │
│   Carrier / ERP / EDI integration hub                            │
│   ICP: 1K+ data-consuming third parties                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## Who it's for

Primary ICP: **small-to-mid US employers (25–500 employees) outsourcing
HR to a PEO running PrismHR.**

Typical buyer profile:
- Company size: 25–500 FTEs
- HR staff: 0–2 people (owner-operator or part-time HR manager)
- Current workflow: email-based, 1–5 PEO rep tickets per week
- Tech comfort: comfortable with SaaS dashboards, familiar with ChatGPT
- Pain: slow PEO turnaround on simple data questions

Secondary ICP: **HR-of-one companies** that left a PEO and want the
same self-serve feel against their own PrismHR license (smaller market).

---

## Product surface

### What a client-company user can do

Read-only, conversational access to their own PrismHR data:

**Payroll**
- "Show me last pay period's register"
- "What did we pay Jane in Q1?"
- "YTD gross wages per employee as a table"
- "Did anyone get overtime last cycle?"

**People**
- "Active employee roster as CSV"
- "Who got hired in the last 90 days?"
- "Upcoming terminations this month"
- "Birthday list for October"

**Benefits**
- "Who's enrolled in medical?"
- "Our monthly premium total by plan"
- "Employees eligible for COBRA right now"
- "401(k) participation rate"

**Compliance**
- "I-9 expirations in next 60 days"
- "E-Verify status per employee"
- "Garnishment balances"

**Time off**
- "PTO balances per employee"
- "Who's on PTO next week?"
- "Sick-leave usage this quarter"

**Billing**
- "Our invoice history YTD"
- "Breakdown of our last monthly bill"
- "WC exposure by department"

### What they explicitly cannot do

- Finalize or approve payroll
- Edit employee records (address, DOB, pay rate)
- Add/remove garnishments
- Modify benefit elections
- Post GL entries
- Send carrier files
- Anything in PrismHR's write path

Write actions remain exclusively in Tier 2 (Simploy's Named Assistants)
or via the PEO rep's own tooling. This is a feature, not a limitation
— it's what makes the portal safe to hand to every client company by
default.

---

## Authentication + authorization

The hard problem: client companies don't have PrismHR credentials. Those
live under the PEO's umbrella session.

### Token flow

```
┌────────────────────────┐
│ Client company user    │ 1. Clicks magic link from PEO invite email
│ (employer admin)       │    OR signs in with Google/Microsoft SSO
└────────────┬───────────┘
             │
             ▼
┌────────────────────────┐ 2. Portal issues scoped JWT:
│ Portal auth service    │    {
│ (Auth0 / WorkOS /      │      sub: user@company.com,
│  custom OIDC)          │      clientId: "TEST-CLIENT",
│                        │      peoId: "TEST-PEO",
│                        │      scopes: [portal.read.*],
│                        │      exp: +4h
│                        │    }
└────────────┬───────────┘
             │
             ▼ JWT as MCP auth
┌────────────────────────────────────────────────────────────┐
│ prismhr-mcp-portal (hosted)                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Scoping middleware                                   │  │
│  │   - verify JWT signature                             │  │
│  │   - extract clientId claim                           │  │
│  │   - inject `clientId=<claim>` into every call        │  │
│  │   - enforce read-only allowlist at method level      │  │
│  │   - redact cross-tenant fields in response           │  │
│  │   - apply PII defaults (SSN last-4, no full DOB)     │  │
│  │   - log every call (who, what, when, result_size)    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ PEO session pool                                     │  │
│  │   - one session per PEO tenant, shared across        │  │
│  │     that PEO's client-company users                  │  │
│  │   - keepalive, refresh on 401                        │  │
│  │   - concurrency cap per PEO                          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────────┘
                         │ PrismHR REST (PEO's credentials)
                         ▼
               ┌──────────────────┐
               │ PrismHR UAT/Prod │
               └──────────────────┘
```

### Trust boundary

- **PEO controls the tenant relationship.** PEO admin onboards each
  client-company user, sets their `clientId`, and can revoke access.
- **Portal controls the scope.** Even if a client user crafts a raw
  MCP call, middleware rewrites `clientId` to the one bound to their
  JWT. Cross-tenant data is impossible by construction.
- **PrismHR sees only the PEO.** From PrismHR's perspective, it's the
  same PEO session making every call — no new API footprint.

### Scope model (client-side)

Six portal scopes, all read-only:

| Scope | Covers |
|---|---|
| `portal.read.roster` | Employee list, basic contact info |
| `portal.read.payroll` | Vouchers, YTD, pay history |
| `portal.read.benefits` | Enrollments, plans, COBRA |
| `portal.read.pto` | PTO balances, classes |
| `portal.read.compliance` | I-9, E-Verify, garnishments |
| `portal.read.billing` | Invoices, WC exposure |

PEO admin grants scopes per client-company user. Default bundle =
`roster + payroll + pto`. Sensitive scopes (`compliance`, `benefits`)
opt-in per customer.

---

## PII handling (non-negotiable)

### Default redaction

| Field | Default |
|---|---|
| SSN | last 4 digits only (`***-**-1234`) |
| Date of birth | year only |
| Home address | city + state (no street) |
| Bank routing/account | redacted entirely |
| Dependent SSN/DOB | redacted entirely |

### Opt-in expansion

PEO admin can lift redactions per client-company user (e.g., controller
needs full SSN for I-9). Audit log records the grant + justification.

### Data retention

- Chat transcripts: 30 days (for audit + debugging), then deleted
- Response payloads: never stored server-side beyond the request
- Client-side: user's MCP client controls its own memory

---

## Workflows included (Tier 2.5 MVP)

Subset of the 15 workflows proposed in the Tier 2 roadmap — read-only ones only:

| # | Workflow | Data sources |
|---|---|---|
| 1 | New hire audit (own employees) | employee + address + everify |
| 3 | Doc expiration tracker (own) | `getDocExpirations` |
| 5 | Benefits-deduction reconciliation | benefits + deductions |
| 6 | YTD payroll reconciliation | bulk YTD + vouchers |
| 8 | PTO balance report | PTO plans + balances |
| 9 | ACA snapshot (own only) | ACA monthly + offered employees |
| 10 | Workers comp exposure | WC modifiers + standard hours |
| 11 | OSHA 300A assist | OSHA stats |

Excluded: payroll finalization, garnishment edits, carrier 834 feeds,
all write-path workflows.

### Branded experience

Portal UI shell is white-label per PEO:
- Logo + primary color from PEO brand config
- PEO's domain (`portal.simploy.com`, `portal.examplepeo.com`)
- PEO support email on every screen
- Client company's own logo visible once logged in (co-brand)

---

## Business model options

### Option A — PEO-paid, per-seat
- PEO charges client `$5–15/employee/month` on top of standard PEO bill
- PEO keeps 30–50% margin
- We bill PEO directly at wholesale rate
- Adoption: slow-rolling per-PEO, each PEO decides to resell

### Option B — Direct-to-client with PEO revenue share
- Client company pays `$99–299/month` flat fee (tiered by employee count)
- PEO gets 30% referral commission
- We handle billing + support
- Adoption: faster, but PEO needs buy-in to route clients

### Option C — Freemium lead-gen for PEOs
- Free read-only tier with rate limits + PEO upsell CTAs
- Paid tier removes limits + unlocks advanced workflows
- PEO pays for branded upgrade
- Adoption: widest funnel, weakest revenue per user

### Simploy's play

Start with **Option A, Simploy-exclusive** for first 3–5 pilot clients.
Validate:
- PEO client companies actually use it daily
- Reduction in PEO rep ticket volume is measurable
- PEOs are willing to resell vs. build in-house

After 60-day pilot, open to other PEOs via **Option A wholesale**. Keep
Option C on the roadmap for when Tier 3 (broker) is live and we can
absorb freemium traffic cheaply.

---

## Competitive positioning

| | Existing PEO client portals | prismhr-mcp-portal |
|---|---|---|
| Interface | Dashboard + filters | Conversational (any MCP client) |
| Onboarding | 2–4 weeks | Magic link, 5 minutes |
| Customization | PEO IT ticket | Client user asks in chat |
| Data freshness | Nightly ETL, often stale | Live PrismHR read |
| Reports | Pre-built, fixed layout | Ad-hoc, any shape |
| Integration | Portal-only | Works inside Claude, Cursor, ChatGPT Desktop |
| White-label | Expensive custom build | Brand YAML, deployed same day |

PEO incumbents like iSolved, ADP TotalSource, and Rippling have client
portals but they're built on pre-2015 ETL pipelines and dashboard UX.
None are agent-native.

---

## Hard constraints (engineering contract)

1. **Scoping cannot be bypassed.** Every tool call goes through middleware
   that enforces `clientId` injection from JWT. No tool, not even
   `meta_call`, can reach PrismHR without scoping.
2. **Read-only method allowlist.** A declarative registry of verified-
   read methods; anything not on it returns 403 at the middleware layer
   even if the underlying PrismHR session would succeed.
3. **Response filtering pass.** Even on verified reads, response filter
   strips `clientId` fields not matching the JWT claim, in case PrismHR
   ever returns cross-tenant data (defense in depth).
4. **Rate limits per client-company user.** Default 60 calls/hour
   baseline; PEO can raise.
5. **Audit log every request.** Immutable append-only log, queryable by
   PEO admin. Includes JWT claims, method, params, result size, duration.
6. **PII redaction default-on.** Explicit PEO admin grant required to
   unredact any SSN/DOB/address.
7. **No write methods in the registry, period.** Even if a workflow
   claims read-only behavior, its constituent calls are vetted.

---

## Build sequence

Depends on Tier 2 shipping first (Carrier Enrollment Assistant).

**Prerequisites (blocked on Tier 2 delivery):**
- Tier 2 first Named Assistant live at ≥1 PEO
- Carrier model proven (Guardian 834 in production)

**Phase P0 — spec + security design (1 week)**
- Write middleware contract
- Pick auth provider (Auth0 / WorkOS / custom OIDC)
- Data protection review + PII redaction spec
- PEO admin panel wireframes

**Phase P1 — middleware + auth (2 weeks)**
- JWT issuance + validation
- Scoping middleware (clientId injection)
- Read-only method allowlist
- Response filter pass
- Rate limit + audit log

**Phase P2 — portal UI shell (2 weeks)**
- Next.js white-label front end
- Embedded MCP client (Claude Agent SDK)
- PEO brand YAML consumption
- Onboarding magic-link flow

**Phase P3 — 5 read workflows + pilot launch (1–2 weeks)**
- Adapt workflows 1, 3, 5, 6, 8 from Tier 2 roadmap
- Dogfood against Simploy clients
- Admin panel MVP (user management, scope grants, audit log viewer)

**Phase P4 — pilot → GA (4–8 weeks)**
- 60-day pilot with 3–5 Simploy client companies
- Ticket-volume reduction measurement
- PEO reseller onboarding docs
- GA launch

**Total:** ~10–14 weeks after Tier 2 first Assistant ships.

---

## Open questions

1. **Auth provider.** Auth0 (fast, expensive), WorkOS (dev-friendly,
   mid-tier), or custom OIDC (cheap at scale, slower to ship). Default
   lean: WorkOS for MVP, reassess at 1K users.
2. **Hosting.** Fly.io, Render, or AWS? Default lean: Fly.io for P0–P3
   (fast deploy, cheap), migrate to AWS if compliance demands it.
3. **Where does PEO admin panel live?** Separate app or embedded into
   existing Tier 2 `prismhr-mcp-simploy` admin surface?
4. **Can a client-company user invite their own team members?** Or does
   every user come through PEO admin? Default lean: PEO admin only for
   MVP (simpler trust model), self-service invites in v2.
5. **Pricing unit.** Per-employee per-month vs. per-admin-seat? Per-
   employee aligns with PEO billing; per-admin-seat aligns with SaaS
   norms. Default lean: per-employee wholesale to PEO, PEO can package
   however they want.
6. **Compliance scope.** SOC 2 Type 1 before GA? Or wait for Type 2
   during first post-GA year? Default lean: Type 1 before GA (sales
   blocker for mid-market PEOs), Type 2 within 12 months of GA.

---

## Success metrics

**Pilot (60 days, 3–5 Simploy clients):**
- ≥60% of enrolled client-company admins use portal ≥1×/week
- ≥30% reduction in PEO rep data-pull tickets for participating clients
- NPS ≥40 from pilot users
- Zero cross-tenant data leakage incidents

**Year 1 post-GA:**
- 5+ PEO resellers signed
- 500+ paying client-company seats
- $500K+ ARR
- <0.1% monthly churn

---

## Why this matters strategically

Tier 2.5 is **the flywheel that makes Tier 2 and Tier 3 inevitable**.

- Every PEO that resells the portal becomes a Tier 2 prospect (they see
  workflow value, want the internal Ops Assistant).
- Every PEO that resells the portal becomes a Tier 3 prospect (their
  carrier partners want to talk to the broker that serves the portal).
- Every client-company user who gets used to agent-native HR becomes a
  future Tier 2/3 buyer when they outgrow the PEO model.

The portal is the only tier that touches non-technical end buyers. It's
the product that pulls PrismHR × agentic AI into mainstream SMB
visibility — and once there, the infrastructure tiers compound.
