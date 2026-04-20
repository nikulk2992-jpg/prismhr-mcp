"""State-level tax engines. Scope: MO, IL, OH, CA, NY, MA, NJ, PA.

Each module exposes a `compute(...)` that returns the expected
state withholding for a pay period. Used by the reference-diff
workflow to cross-check PrismHR's Vertex output.
"""
