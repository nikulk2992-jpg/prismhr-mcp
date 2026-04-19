"""Method catalog — the single source of truth for PrismHR API metadata.

Two bundled JSON files power this:

* `data/methods.json` — 447 endpoints extracted from the bible PDF. Contains
  path, method, summary, description, parameters, request body schemas
  (34 with verified inline definitions, the rest with $ref only), response
  schema refs.

* `data/verification.json` — which endpoints have verified response shapes
  from a live probe pass, plus schema-key hints (structural only, no tenant
  data). Starts with the maintainer's probe results; every install can
  augment by running `scripts/calibrated_probe.py` against its own tenant.

The `Catalog` class is the runtime API. Tools consult it to answer
"what can this server call?" and "what does /payroll/v1/foo return?"
before we ever touch the wire.
"""

from .catalog import Catalog, MethodContract, load_catalog
from .validator import ValidationError, validate_args

__all__ = [
    "Catalog",
    "MethodContract",
    "load_catalog",
    "ValidationError",
    "validate_args",
]
