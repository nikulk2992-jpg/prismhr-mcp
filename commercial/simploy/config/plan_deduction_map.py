"""Plan-to-deduction-code mapping loaded from a YAML config.

The Benefits-Deduction Audit workflow needs to know which payroll
deduction code to expect for each enrolled plan. PrismHR stores this
on the Group Benefit Plans form, but the API endpoints that expose it
(`getGroupBenefitPlan`, `getClientBenefitPlanSetupDetails`) are
permission-gated on many tenants. Until those land, operators declare
the mapping in YAML and this module loads it.

YAML schema:

    _default:                             # applies to every client
      <planId>:
        deduction_codes: [CODE_A, CODE_B]
        section125_deduction_codes: [CODE_C]
        bill_codes: [BILL_A]

    <clientId>:                           # per-client override
      <planId>:
        deduction_codes: [CODE_X]

Lookup order per (clientId, planId): client override -> _default.
Unlisted plans return an empty map, which the workflow interprets as
"cannot evaluate — skip."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover — PyYAML is optional at import time
    yaml = None  # type: ignore[assignment]


@dataclass(frozen=True)
class PlanMapping:
    deduction_codes: list[str] = field(default_factory=list)
    section125_deduction_codes: list[str] = field(default_factory=list)
    bill_codes: list[str] = field(default_factory=list)

    @property
    def all_expected_deduction_codes(self) -> list[str]:
        return list(self.deduction_codes) + list(self.section125_deduction_codes)


@dataclass
class PlanDeductionMap:
    """In-memory lookup for plan -> deduction codes, per client."""

    _by_client: dict[str, dict[str, PlanMapping]]
    _defaults: dict[str, PlanMapping]

    def lookup(self, client_id: str, plan_id: str) -> PlanMapping | None:
        client_block = self._by_client.get(client_id) or {}
        hit = client_block.get(plan_id)
        if hit is not None:
            return hit
        return self._defaults.get(plan_id)

    def expected_deduction_codes(self, client_id: str, plan_id: str) -> list[str]:
        hit = self.lookup(client_id, plan_id)
        return hit.all_expected_deduction_codes if hit else []

    def __bool__(self) -> bool:
        return bool(self._by_client) or bool(self._defaults)


def load_plan_deduction_map(path: str | Path) -> PlanDeductionMap:
    """Parse a YAML file into a PlanDeductionMap.

    Returns an empty map if the file is missing or empty. Raises
    RuntimeError if PyYAML is not installed.
    """
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required to load plan_deduction_map.yaml. "
            "Add `pyyaml` to the commercial package dependencies."
        )

    p = Path(path)
    if not p.exists():
        return PlanDeductionMap(_by_client={}, _defaults={})

    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return PlanDeductionMap(_by_client={}, _defaults={})

    defaults: dict[str, PlanMapping] = {}
    by_client: dict[str, dict[str, PlanMapping]] = {}
    for key, block in raw.items():
        if not isinstance(block, dict):
            continue
        parsed_block = {pid: _parse_mapping(entry) for pid, entry in block.items()}
        if key == "_default":
            defaults.update(parsed_block)
        else:
            by_client[str(key)] = parsed_block
    return PlanDeductionMap(_by_client=by_client, _defaults=defaults)


def _parse_mapping(entry: Any) -> PlanMapping:
    if not isinstance(entry, dict):
        return PlanMapping()
    return PlanMapping(
        deduction_codes=_as_list(entry.get("deduction_codes")),
        section125_deduction_codes=_as_list(entry.get("section125_deduction_codes")),
        bill_codes=_as_list(entry.get("bill_codes")),
    )


def _as_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    return []
