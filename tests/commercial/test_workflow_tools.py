"""Smoke tests for commercial MCP tool registrations."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.tools.workflow_tools import _to_dict, _parse_date  # noqa: E402


def test_parse_date_basic() -> None:
    from datetime import date
    assert _parse_date("2026-04-20") == date(2026, 4, 20)
    assert _parse_date("2026-04-20T12:00:00") == date(2026, 4, 20)


def test_to_dict_preserves_decimal_as_string() -> None:
    from decimal import Decimal
    assert _to_dict(Decimal("1234.56")) == "1234.56"


def test_to_dict_preserves_date_as_iso() -> None:
    from datetime import date
    assert _to_dict(date(2026, 4, 20)) == "2026-04-20"


def test_to_dict_walks_dataclass() -> None:
    from dataclasses import dataclass, field
    from decimal import Decimal
    from datetime import date

    @dataclass
    class Inner:
        amount: Decimal
        when: date

    @dataclass
    class Outer:
        id: str
        inner: Inner
        items: list

    obj = Outer(
        id="X",
        inner=Inner(amount=Decimal("9.99"), when=date(2026, 1, 1)),
        items=[Decimal("1"), Decimal("2")],
    )
    out = _to_dict(obj)
    assert out == {
        "id": "X",
        "inner": {"amount": "9.99", "when": "2026-01-01"},
        "items": ["1", "2"],
    }


def test_register_workflow_tools_registers_all() -> None:
    """Just confirm registrations run without exception."""
    from mcp.server.fastmcp import FastMCP
    from simploy.tools.workflow_tools import register_workflow_tools

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
    register_workflow_tools(server, reg, _FakeClient(), _FakePerms())
    assert len(reg.names) >= 20  # 15 ops + 5 tax recon
    expected_prefix = "commercial_"
    for name in reg.names:
        assert name.startswith(expected_prefix), name
    # Spot-check the tax-recon family is actually wired
    tax_tools = {
        "commercial_form_941_reconciliation",
        "commercial_form_940_reconciliation",
        "commercial_state_withholding_recon",
        "commercial_tax_remittance_tracking",
        "commercial_state_filings_orchestrator",
    }
    assert tax_tools.issubset(set(reg.names))
