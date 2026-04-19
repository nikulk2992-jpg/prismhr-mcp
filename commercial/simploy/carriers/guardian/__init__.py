"""Guardian Life (benefit carrier) — 834 5010 enrollment renderer.

Public companion-guide reference: Guardian Electronic User Guide 834
Enrollment and Maintenance (circulated publicly via docplayer).

Scope of this subpackage:
- `companion.py` — Guardian-specific overrides on top of the generic 834 writer
- `render.py` — `render_guardian(enrollment)` → 834 5010 text
- `deliver.py` — SFTP delivery (deferred until test-partner creds available)

Guardian's 834 is considered a "clean" 834 5010 — few custom qualifiers.
This model is the Phase-1 reference implementation for other 834 carriers
(Cigna, MetLife, Unum) to parameterize.
"""

from .render import render_guardian

__all__ = ["render_guardian"]
