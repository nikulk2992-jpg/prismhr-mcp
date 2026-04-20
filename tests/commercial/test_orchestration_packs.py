"""Orchestration pack — unit tests with fake step coroutines."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.orchestration_packs import (  # noqa: E402
    run_month_end_close_pack,
    run_quarter_end_close_pack,
    run_year_end_close_pack,
    run_new_client_golive_pack,
    run_payroll_run_preflight_pack,
)


@dataclass
class _Finding:
    code: str
    severity: str
    message: str = ""


@dataclass
class _Report:
    findings: list = field(default_factory=list)


def _make_step(findings: list[_Finding]):
    async def step():
        return _Report(findings=findings)
    return step


def _make_failing_step(exc: Exception):
    async def step():
        raise exc
    return step


@pytest.mark.asyncio
async def test_month_end_pack_all_clean() -> None:
    steps = {
        "payroll_batch_health": _make_step([]),
        "voucher_classification_audit": _make_step([]),
        "gl_template_integrity": _make_step([]),
        "payroll_journal_preflight": _make_step([]),
    }
    r = await run_month_end_close_pack(
        client_id="T", as_of=date(2026, 4, 30), steps=steps
    )
    assert r.ready_to_proceed
    assert r.total_critical == 0
    assert len(r.steps) == 4


@pytest.mark.asyncio
async def test_month_end_pack_critical_blocks() -> None:
    steps = {
        "payroll_batch_health": _make_step([]),
        "voucher_classification_audit": _make_step([
            _Finding("FICA_EXEMPT_MISFLAG", "critical"),
        ]),
        "gl_template_integrity": _make_step([]),
        "payroll_journal_preflight": _make_step([]),
    }
    r = await run_month_end_close_pack(
        client_id="T", steps=steps
    )
    assert not r.ready_to_proceed
    assert r.total_critical == 1


@pytest.mark.asyncio
async def test_quarter_end_pack_step_order() -> None:
    steps = {
        "form_941_reconciliation": _make_step([]),
        "state_withholding_recon": _make_step([]),
        "tax_remittance_tracking": _make_step([]),
        "state_filings_orchestrator": _make_step([]),
    }
    r = await run_quarter_end_close_pack(client_id="T", steps=steps)
    names = [s.name for s in r.steps]
    assert names == [
        "form_941_reconciliation", "state_withholding_recon",
        "tax_remittance_tracking", "state_filings_orchestrator",
    ]


@pytest.mark.asyncio
async def test_year_end_pack_includes_ndt() -> None:
    steps = {
        "w2_readiness": _make_step([]),
        "form_1095c_consistency": _make_step([_Finding("X", "warning")]),
        "irs_air_preflight": _make_step([]),
        "form_1099_nec_preflight": _make_step([]),
        "retirement_ndt": _make_step([_Finding("ADP_TEST_FAILED", "critical")]),
    }
    r = await run_year_end_close_pack(client_id="T", steps=steps)
    assert r.total_critical == 1
    assert r.total_warning == 1
    assert len(r.steps) == 5


@pytest.mark.asyncio
async def test_new_client_golive_chain() -> None:
    steps = {
        "client_golive_readiness": _make_step([]),
        "prior_peo_conversion_recon": _make_step([
            _Finding("YTD_NOT_LOADED", "critical"),
        ]),
        "state_tax_setup": _make_step([]),
        "gl_template_integrity": _make_step([]),
        "benefit_rate_drift": _make_step([]),
    }
    r = await run_new_client_golive_pack(client_id="T", steps=steps)
    assert not r.ready_to_proceed
    assert any(s.name == "prior_peo_conversion_recon" and s.critical == 1 for s in r.steps)


@pytest.mark.asyncio
async def test_step_error_surfaces_as_blocked() -> None:
    steps = {
        "payroll_batch_health": _make_failing_step(RuntimeError("network boom")),
        "voucher_classification_audit": _make_step([]),
    }
    r = await run_payroll_run_preflight_pack(client_id="T", steps=steps)
    assert not r.ready_to_proceed
    failing = next(s for s in r.steps if s.name == "payroll_batch_health")
    assert failing.blocked
    assert "RuntimeError" in failing.error
    assert "network boom" in failing.error


@pytest.mark.asyncio
async def test_missing_step_is_skipped_not_error() -> None:
    steps = {
        "voucher_classification_audit": _make_step([]),
        # other three pack steps not supplied
    }
    r = await run_payroll_run_preflight_pack(client_id="T", steps=steps)
    assert len(r.steps) == 1
    assert r.ready_to_proceed


@pytest.mark.asyncio
async def test_findings_nested_in_children_are_tallied() -> None:
    # Report where findings live inside .vouchers[].findings
    @dataclass
    class Sub:
        findings: list = field(default_factory=list)

    @dataclass
    class Nested:
        vouchers: list = field(default_factory=list)

    report = Nested(vouchers=[
        Sub(findings=[_Finding("A", "critical"), _Finding("B", "warning")]),
        Sub(findings=[_Finding("C", "critical")]),
    ])

    async def step():
        return report

    steps = {"voucher_classification_audit": step}
    r = await run_payroll_run_preflight_pack(client_id="T", steps=steps)
    assert r.total_critical == 2
    assert r.total_warning == 1
