# Benefit Carrier Integration Map — US (Top 20)

Source: live web research 2026-04-19. Basis for `Carrier Enrollment Assistant`
(Tier 2 Named Assistant) and the `prismhr-mcp-broker` third-party integration
surface (Tier 3).

## Summary

| # | Carrier | Verticals | Standard | Channel | Cadence | CG Public? | Dev/API |
|---|---|---|---|---|---|---|---|
| 1 | Humana | Medical, Dental, Vision, Life, Disability, Medicare | 834 5010 + proprietary | SFTP, AS2 | Daily/Weekly | No (NDA) | Availity + Humana Dev |
| 2 | Allstate Benefits | Voluntary (Accident, CI, Hospital, Life, STD) | 834 5010 + CSV | SFTP | Weekly/Monthly | No | Via BenAdmin (Ease, Employee Nav) |
| 3 | BCBS (36 regional plans) | Medical, Dental, Vision | 834 5010 (per-plan CG) | SFTP, AS2 | Daily/Weekly | **Yes** per plan | Availity common |
| 4 | Aetna (CVS) | Medical, Dental, Vision, Behavioral, Medicare | 834 5010 | SFTP, AS2 | Weekly/Biweekly | No (NDA) | Availity + Aetna Dev Portal |
| 5 | Cigna | Medical, Dental, Vision, Behavioral | 834 5010 | SFTP, AS2 | Weekly | No | CHCP portal |
| 6 | UnitedHealthcare / Optum | Medical, Dental, Vision, Behavioral | 834 5010 + 007030X333 | SFTP via Optum EDI | Daily/Weekly | **Yes** (uhcprovider.com) | Optum/UHC Dev APIs |
| 7 | Delta Dental (39 members) | Dental | 834 5010 + flat-file | SFTP + PGP | Weekly/Monthly | **Yes** per member | Per-member portals |
| 8 | MetLife | Dental, Vision, Life, Disability, Accident, Legal, Pet | 834 5010 + proprietary | SFTP (MetLink) | Weekly | No (NDA) | MetLink employer portal |
| 9 | Guardian | Dental, Vision, Life, Disability, Accident, CI, Hospital | 834 5010 | SFTP | Weekly/Biweekly | **Semi-public** ("leaked" PDF) | Guardian Anytime |
| 10 | Principal | Life, Disability, Dental, Vision, 401(k) | 834 5010 (partial) + 401k flat | SFTP | Weekly (insurance) / Per payroll (401k) | No (case-based) | Principal Connect |
| 11 | Lincoln Financial | Life, Disability, Dental, 401(k) | 834 5010 + proprietary | SFTP | Monthly preferred | No (case manager) | LFG employer tools |
| 12 | Sun Life | Dental, Life, Disability, Vision, Stop-Loss, Voluntary | 834 5010 + EDX flat-file | SFTP | Weekly | **Yes** (Sun Life Onboard articles) | Sun Life Onboard |
| 13 | Colonial Life (Unum) | Voluntary | Proprietary Harmony® + limited 834 | SFTP / Harmony | Enrollment windows | No | Harmony + Ease |
| 14 | Aflac | Voluntary | Proprietary (SmartApp/Everwell) + limited 834 | API iframe + SFTP | Real-time / Weekly | No | Everwell iframe + Ease |
| 15 | Unum | Life, Disability, Dental, Vision, Voluntary | 834 5010 | SFTP | Weekly/Biweekly | No | Unum employer portal |
| 16 | Kaiser Permanente | Medical, Dental (bundled), Vision | 834 5010 | SFTP (AS2 fallback) | Daily/Weekly Δ + Monthly full | No (co-authored with employer) | Limited public API |
| 17 | Fidelity Workplace | 401(k), HSA, Health & Welfare | Proprietary tape-spec (fixed-width) | SFTP + PSW | Per payroll | No (PSW docs) | PSW |
| 18 | Voya Financial | 401(k), 403(b), 457, Life, Disability | Proprietary fixed-width + CSV feedback | SFTP / SponsorWeb | Per payroll | **Yes** ("Payroll Admin Quick Start") | SponsorWeb |
| 19 | Empower | 401(k), 403(b), 457, NQDC | Proprietary PDI fixed-width | SFTP / PSC upload | Per payroll | **Yes** ("PDI File Layout" PDF) | PSC |
| 20 | John Hancock / Manulife | 401(k) | Proprietary spec | SFTP (SSH key) | Per payroll | **Semi-public** (TPA e-download guide) | bcomplete.com |

## Takeaways

- **834 5010 (005010X220A1)** dominates medical/dental/vision/life/disability. Differences = companion-guide qualifiers + loop usage, not segment structure.
- **SFTP** is near-universal delivery. AS2 for large carriers (Aetna, UHC, BCBS regionals). Real-time API enrollment is rare — Aflac Everwell iframe is the exception.
- **401(k) is NOT 834.** Proprietary fixed-width — Fidelity tape-spec, Empower PDI, John Hancock plan-alias, Voya. Separate engine required.
- **BCBS is N plans, not one.** Per-plan CG registry is mandatory.
- **Voluntary carriers** (Aflac, Colonial, Allstate Benefits) route through proprietary platforms (Everwell, Harmony, SmartApp) — 834 is secondary.
- **Companion-guide acquisition is NDA-gated** for most nationals. Public CGs exist for BCBS regionals, Delta Dental members, Guardian (leaked), Sun Life, Empower, Voya, John Hancock. Simploy should build an internal CG library as a commercial asset.

## Phase-1 pilot set (recommendation)

Build deep, tested models against a small set with **public documentation**
first — each pick is a different dialect, so we stress-test the framework:

### 834 EDI side

1. **Guardian (834 5010)** — Dental + ancillary. Public user guide circulating
   ([docplayer link](https://docplayer.net/22518825-Guardian-electronic-user-guide-834-enrollment-and-maintenance.html)).
   Clean, classic 834 5010. Strong weekly/biweekly cadence — realistic volume.
2. **BCBS Michigan (834 5010)** — Medical big-volume. Public CG PDF (bcbsm.com).
   Regional-plan dialect covers the per-plan CG pattern we need for the other
   35 BCBS plans later. Tests loop-level qualifier handling.

One carrier with a proprietary flat-file variation to round out the 834 side:

3. **Sun Life EDX** — Proprietary flat-file alongside 834. Public onboard
   articles document the variants. Tests our non-834 rendering path without
   going all the way to 401k fixed-width.

### 401(k) side (separate engine)

4. **Voya (payroll fixed-width + CSV feedback)** — Public "Payroll Admin Quick
   Start" + "Payroll Feedback Info" guides. Two-direction (send + receive
   feedback) exercises both upload and feedback-reconciliation.
5. **Empower PDI (fixed-width)** — Public PDI File Layout PDF. Different
   field lengths + control header structure from Voya. Validates the engine
   generalizes.

### What this pilot set teaches us

- 834 5010 backbone (Guardian) → generalizes to Cigna, MetLife, Unum
- Regional-plan CG pattern (BCBS MI) → generalizes to Anthem, BSCA,
  CareFirst, Premera, Highmark, etc.
- Carrier-proprietary flat-file (Sun Life EDX) → generalizes to Colonial
  Harmony, Aflac EDI
- 401(k) payroll + feedback (Voya) → generalizes to Principal 401(k),
  Lincoln 401(k), Fidelity tape-spec
- 401(k) PDI fixed-width (Empower) → generalizes to John Hancock

Ship **5 verified carrier models**, and we have coverage patterns that
extend to ~15 more carriers without new engine work — each added carrier
becomes a config + CG mapping, not new code.

## Architecture implications

### `prismhr-mcp-simploy` (Tier 2) adds:

- `carriers/` package with one subpackage per pilot carrier
  - `carriers/guardian/` — 834 5010 renderer + companion-guide config
  - `carriers/bcbs_mi/` — 834 5010 + per-plan qualifier overrides
  - `carriers/sun_life/` — EDX flat-file renderer
  - `carriers/voya/` — payroll fixed-width + feedback parser
  - `carriers/empower/` — PDI fixed-width renderer
- Shared `carriers/render/` engine
  - `edi_834.py` — generic 834 5010 writer parameterized by companion guide
  - `flat_file.py` — fixed-width renderer with field-layout schema
  - `csv_ascii.py` — CSV + ASCII variants
- Delivery layer
  - `delivery/sftp.py` — paramiko-backed SFTP with per-carrier creds
  - `delivery/api.py` — for carriers with HTTPS intake (future)
- State
  - `state/last_sent.sqlite` — per (client, carrier, plan, employee) hash for
    delta detection

### Named Assistant: **Carrier Enrollment Assistant**

Prompt surface for Claude:
> "Send this week's enrollments to Guardian for Acme Corp"
> "What changed on the BCBS MI file we sent Monday?"
> "Generate Voya payroll feed for pay period ending 2026-04-18"

Behind the scenes:
1. `meta_call payroll.getActiveBenefitPlans` across roster
2. Compute delta vs state store
3. Render via carrier module
4. Deliver via SFTP
5. Log to audit trail
6. Return human-readable summary

### Broker role (Tier 3)

Carriers that don't want files can poll `prismhr-mcp-broker` directly:
`GET /carriers/v1/enrollments?clientId=...&asOfDate=...` → live list, no EDI
round-trip. Broker shapes PrismHR data to carrier's preferred JSON schema.
