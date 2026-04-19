"""Operator-supplied configuration loaded at runtime.

Separate from source code so PEO config can live in its own repo or
deployment artifact without forking the commercial package.
"""

from .plan_deduction_map import PlanDeductionMap, load_plan_deduction_map

__all__ = ["PlanDeductionMap", "load_plan_deduction_map"]
