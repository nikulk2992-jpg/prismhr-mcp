"""Reference tax engine for cross-checking PrismHR calculations.

Not a production payroll-tax engine — a diagnostic one. PrismHR uses
Vertex + Symmetry underneath; this engine exists to:

  1. Catch multi-state allocation errors (voucher says all MO wages
     but employee actually worked MO + IL — common Simploy case).
  2. Detect wrong reciprocity cert application (IL resident, MO work,
     MO withheld when IL should have been the only one).
  3. Validate statutory math on single-state vouchers (federal FIT +
     FICA + FUTA + state FIT for the Simploy footprint states).
  4. Flag configuration drift (wrong SUTA state, wrong state wage base).

Scope per phase:
  federal.py          Phase 1 — Pub 15-T percentage method + FICA + FUTA
  states/mo.py        Phase 2 — Missouri
  states/il.py        Phase 2 — Illinois
  states/oh.py        Phase 2 — Ohio
  states/ca.py        Phase 2 — California
  states/ny.py        Phase 2 — New York
  states/ma.py        Phase 2 — Massachusetts
  states/nj.py        Phase 2 — New Jersey
  states/pa.py        Phase 2 — Pennsylvania (flat 3.07%)
  multi_state.py      Phase 3 — allocation + reciprocity validator

Each state module exposes `compute(wages_per_period, ...)` returning
the expected withholding for the period. Callers (diff workflows)
compare against voucher.employeeTax rows.

Tables are 2026-tax-year as a default; versioned in tables/ and
dispatched by tax_year parameter.
"""

TAX_YEAR_DEFAULT = 2026
