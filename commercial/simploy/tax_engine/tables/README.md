# Tax engine tables

Authoritative tables, extracted from the Vertex Calculation Guide
monthly update PDF. Each table is versioned by effective date so
historical calculations replay identically.

## Layout

```
tables/
  federal/
    fit_2026.yaml          Pub 15-T annual percentage-method brackets
    fica_2026.yaml         SS rate + wage base + Medicare + Addl Medicare
    futa_2026.yaml         FUTA rate + wage cap + credit-reduction states
  states/
    mo_2026.yaml           Missouri (effective date Feb 2026)
    il_2026.yaml           Illinois
    oh_2026.yaml           Ohio
    ca_2026.yaml           California
    ny_2026.yaml           New York
    ma_2026.yaml           Massachusetts
    nj_2026.yaml           New Jersey
    pa_2026.yaml           Pennsylvania
  reciprocity/
    2026.yaml              All pair-wise reciprocity rules (from Vertex)
```

## Monthly update runbook

When a new Vertex Calculation Guide PDF arrives:

1. Drop the PDF anywhere accessible.
2. Run `scripts/extract_vertex_tables.py <new-pdf-path>` to produce a
   diff against the current `tables/*.yaml`.
3. Review the diff; approve or reject per change (state-by-state rate
   changes, new reciprocity agreements, etc.).
4. Bump the effective date suffix on any changed table
   (e.g., `mo_2026.yaml` -> `mo_2026_04.yaml`).
5. Run `scripts/scan_pii.py` + `pytest tests/commercial/test_tax_engine.py`.
6. Commit. CI re-runs the tests. Tag + publish next dev version.

## Versioning

Tables are keyed by effective date. The engine selects the table in
force on the voucher's pay date. This lets us re-run a historical
quarter against the tables that were in force at the time —
essential for audit defensibility.
