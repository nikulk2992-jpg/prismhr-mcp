"""Smoke tests for commercial orchestration-pack MCP tool registrations."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.tools.pack_tools import _build_step_registry, register_pack_tools  # noqa: E402


def test_register_pack_tools_registers_five() -> None:
    from mcp.server.fastmcp import FastMCP

    class _FakeClient:
        async def get(self, *a, **k): return {}

    class _FakeRegistry:
        def __init__(self): self.names = []
        def register(self, server, name, fn, **kw):
            self.names.append(name)

    class _FakePerms:
        def check(self, scope): pass

    server = FastMCP("test")
    reg = _FakeRegistry()
    register_pack_tools(server, reg, _FakeClient(), _FakePerms())
    assert len(reg.names) == 5
    for name in reg.names:
        assert name.startswith("commercial_"), name
        assert name.endswith("_pack"), name


def test_step_registry_keys_match_pack_step_names() -> None:
    """Every step the packs chain must resolve in the registry."""

    class _FakeClient:
        async def get(self, *a, **k): return {}

    steps = _build_step_registry(
        _FakeClient(), "T",
        date(2026, 4, 1), date(2026, 4, 30),
    )
    # Each pack references step names; all must be either in the
    # registry or will be skipped by the pack. These are the steps
    # the live packs actually chain:
    known_live_steps = {
        "payroll_batch_health",
        "voucher_classification_audit",
        "form_1099_nec_preflight",
        "bonus_gross_up_audit",
        "retirement_ndt",
        "reciprocal_withholding_audit",
        "state_new_hire_audit",
        "final_paycheck_compliance",
        "off_cycle_payroll_audit",
        "dependent_age_out",
        "cobra_eligibility_sweep",
        "pto_reconciliation",
        "retirement_loan_status",
    }
    for name in known_live_steps:
        assert name in steps, f"Step {name} missing from registry"
