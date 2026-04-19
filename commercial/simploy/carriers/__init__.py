"""Carrier enrollment models.

Each carrier subpackage owns:
- `render.py` — generates the carrier's file format from a generic enrollment
  payload
- `companion.py` — carrier-specific qualifiers, overrides, and field mappings
- `deliver.py` — SFTP/API delivery logic (deferred until a carrier is wired
  against real test credentials)

Common primitives live under `commercial/simploy/carriers/render/`.
"""
