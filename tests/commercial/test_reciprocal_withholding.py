"""Reciprocal withholding audit — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.reciprocal_withholding import (  # noqa: E402
    is_reciprocal,
    run_reciprocal_withholding_audit,
)


class FakeReader:
    def __init__(self, rows): self.rows = rows
    async def list_multistate_employees(self, cid, ps, pe): return self.rows


async def _run(reader):
    return await run_reciprocal_withholding_audit(
        reader, client_id="T",
        period_start=date(2026, 1, 1), period_end=date(2026, 3, 31),
        as_of=date(2026, 4, 15),
    )


def test_reciprocity_table_samples() -> None:
    assert is_reciprocal("OH", "KY")
    assert is_reciprocal("KY", "OH")
    assert is_reciprocal("PA", "NJ")
    assert is_reciprocal("MD", "DC")
    assert not is_reciprocal("NY", "NJ")
    assert not is_reciprocal("CA", "NV")
    assert not is_reciprocal("OH", "OH")  # same state


@pytest.mark.asyncio
async def test_wrong_state_withheld_critical() -> None:
    """OH resident works in KY. Reciprocal pair. KY withheld instead of OH."""
    reader = FakeReader([{
        "employeeId": "E1",
        "homeState": "OH",
        "workStates": ["KY"],
        "homeStateWithholding": "0",
        "workStateWithholding": {"KY": "500"},
        "reciprocalCertsOnFile": ["42A809"],
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "WRONG_STATE_WITHHELD" in codes
    assert "NO_HOME_STATE_WITHHELD" in codes


@pytest.mark.asyncio
async def test_missing_cert_critical() -> None:
    reader = FakeReader([{
        "employeeId": "E1",
        "homeState": "IN",
        "workStates": ["OH"],
        "homeStateWithholding": "500",
        "workStateWithholding": {},
        "reciprocalCertsOnFile": [],
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "MISSING_RECIPROCITY_CERT" in codes


@pytest.mark.asyncio
async def test_both_states_withheld_warning() -> None:
    reader = FakeReader([{
        "employeeId": "E1",
        "homeState": "IN",
        "workStates": ["KY"],
        "homeStateWithholding": "400",
        "workStateWithholding": {"KY": "300"},
        "reciprocalCertsOnFile": ["WH-47"],
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "BOTH_STATES_WITHHELD" in codes


@pytest.mark.asyncio
async def test_non_reciprocal_is_info_only() -> None:
    """NY resident works NJ — no reciprocity. Work-state withholding expected."""
    reader = FakeReader([{
        "employeeId": "E1",
        "homeState": "NY",
        "workStates": ["NJ"],
        "homeStateWithholding": "0",
        "workStateWithholding": {"NJ": "500"},
        "reciprocalCertsOnFile": [],
    }])
    r = await _run(reader)
    codes_crit = {f.code for f in r.employees[0].findings if f.severity == "critical"}
    codes_any = {f.code for f in r.employees[0].findings}
    assert "NON_RECIPROCAL_NO_CERT_NEEDED" in codes_any
    assert "WRONG_STATE_WITHHELD" not in codes_crit
    assert "MISSING_RECIPROCITY_CERT" not in codes_crit


@pytest.mark.asyncio
async def test_multi_state_no_allocation_warning() -> None:
    reader = FakeReader([{
        "employeeId": "E1",
        "homeState": "IL",
        "workStates": ["IL", "WI"],
        "homeStateWithholding": "200",
        "workStateWithholding": {"IL": "200", "WI": "0"},
        "reciprocalCertsOnFile": ["W-220"],
    }])
    r = await _run(reader)
    codes = {f.code for f in r.employees[0].findings}
    assert "MULTI_STATE_NO_ALLOCATION" in codes


@pytest.mark.asyncio
async def test_single_state_employee_no_findings() -> None:
    reader = FakeReader([{
        "employeeId": "E1",
        "homeState": "TX",
        "workStates": ["TX"],
        "homeStateWithholding": "0",
        "workStateWithholding": {"TX": "0"},
        "reciprocalCertsOnFile": [],
    }])
    r = await _run(reader)
    assert r.employees[0].findings == []
