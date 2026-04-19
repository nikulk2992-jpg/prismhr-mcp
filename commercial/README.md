# `commercial/` — Tier 2 & 3 source (source-available, paid)

This directory holds the commercial layer of the prismhr-mcp product:

- **Tier 2 — Named AI Assistants + carrier models** under `commercial/simploy/`
- **Tier 3 — broker (integration platform)** under `commercial/broker/` (future)

The OSS core under `src/prismhr_mcp/` stays MIT. Anything in this `commercial/`
tree ships under a separate commercial license — source-available, not
OSS, requires a paid license to redistribute or run in production beyond
evaluation.

Repo co-located for now; will be extracted to its own package and release
pipeline once the carrier models + first Named Assistant stabilize.

## Carrier models (Phase 1 pilot)

Five carriers modeled in depth — each covers a distinct dialect so the
patterns generalize to the rest of the top 20:

| # | Carrier | Dialect | Path |
|---|---|---|---|
| 1 | Guardian | 834 5010 clean | `commercial/simploy/carriers/guardian/` |
| 2 | BCBS Michigan | 834 5010 regional-plan CG | `commercial/simploy/carriers/bcbs_mi/` (TODO) |
| 3 | Sun Life | EDX flat-file | `commercial/simploy/carriers/sun_life/` (TODO) |
| 4 | Voya | 401k fixed-width + CSV feedback | `commercial/simploy/carriers/voya/` (TODO) |
| 5 | Empower | 401k PDI fixed-width | `commercial/simploy/carriers/empower/` (TODO) |

See `.planning/carrier-map.md` for full carrier profiles + pilot rationale.
