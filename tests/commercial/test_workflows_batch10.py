"""Batch 10 — Voya/Empower/Fidelity 401(k) PDI + retirement census + OSHA 300A."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.carriers.empower import render_empower_pdi  # noqa: E402
from simploy.carriers.fidelity import render_fidelity_tape  # noqa: E402
from simploy.carriers.retirement_common import (  # noqa: E402
    ParticipantContribution,
    RetirementFeed,
)
from simploy.carriers.voya import render_voya_pdi  # noqa: E402
from simploy.workflows.osha_300a import run_osha_300a_assist  # noqa: E402
from simploy.workflows.retirement_census import run_retirement_census  # noqa: E402


def _sample_feed() -> RetirementFeed:
    p = ParticipantContribution(
        employee_id="E1",
        ssn="123456789",
        first_name="Ada",
        last_name="Lovelace",
        dob=date(1985, 1, 1),
        hire_date=date(2020, 2, 1),
        employment_status="A",
        ytd_gross_wages=Decimal("45000.00"),
        period_gross_wages=Decimal("3000.00"),
        period_hours=Decimal("80.00"),
        deferral_pretax=Decimal("150.00"),
        deferral_roth=Decimal("50.00"),
        employer_match=Decimal("75.00"),
    )
    return RetirementFeed(
        plan_id="SIMPLOY-401K",
        client_id="999999",
        period_start=date(2025, 4, 1),
        period_end=date(2025, 4, 15),
        pay_date=date(2025, 4, 18),
        participants=[p],
    )


# ---- Voya PDI ----


def test_voya_pdi_header_detail_trailer() -> None:
    out = render_voya_pdi(_sample_feed())
    lines = out.strip().splitlines()
    assert lines[0].startswith("H")
    assert any(line.startswith("D") for line in lines)
    assert lines[-1].startswith("T")


def test_voya_pdi_records_are_80_chars() -> None:
    out = render_voya_pdi(_sample_feed())
    # splitlines on un-stripped string to preserve trailing padding.
    for line in out.splitlines():
        if not line:
            continue
        assert len(line) >= 80, f"Record < 80 chars: {line!r}"


# ---- Empower PDI ----


def test_empower_pdi_has_hdr_trl() -> None:
    out = render_empower_pdi(_sample_feed())
    lines = out.strip().splitlines()
    assert lines[0].startswith("HDR|")
    assert lines[-1].startswith("TRL|")


def test_empower_pdi_splits_sources_per_line() -> None:
    out = render_empower_pdi(_sample_feed())
    lines = out.strip().splitlines()
    # Expect at least one PT line, one RT line, one EM line.
    pt_lines = [l for l in lines if "|PT|" in l]
    rt_lines = [l for l in lines if "|RT|" in l]
    em_lines = [l for l in lines if "|EM|" in l]
    assert len(pt_lines) == 1
    assert len(rt_lines) == 1
    assert len(em_lines) == 1


# ---- Fidelity tape ----


def test_fidelity_records_150_chars() -> None:
    out = render_fidelity_tape(_sample_feed())
    for line in out.splitlines():
        if not line:
            continue
        assert len(line) == 150, f"Record must be exactly 150 chars: {len(line)}"


def test_fidelity_encodes_amount_as_implied_decimal() -> None:
    out = render_fidelity_tape(_sample_feed())
    # 150.00 -> 15000 cents -> "0000000015000" in a 13-char field
    assert "0000000015000" in out


# ---- #23 Retirement census ----


class CensusFake:
    def __init__(self, rows): self.rows = rows
    async def list_all_participants(self, cid, pid, yr): return self.rows


@pytest.mark.asyncio
async def test_census_missing_hire_date_critical() -> None:
    r = CensusFake([{"employeeId": "E1", "ytdGross": "40000"}])
    rep = await run_retirement_census(r, client_id="T", plan_id="401K", year=2025)
    codes = {f.code for f in rep.rows[0].findings}
    assert "MISSING_HIRE_DATE" in codes


@pytest.mark.asyncio
async def test_census_hce_inconsistent_warning() -> None:
    r = CensusFake([{"employeeId": "E2", "hireDate": "2020-01-01", "ytdGross": "50000", "hce": True, "ownerPct": "0"}])
    rep = await run_retirement_census(r, client_id="T", plan_id="401K", year=2025)
    codes = {f.code for f in rep.rows[0].findings}
    assert "HCE_COMP_INCONSISTENT" in codes


# ---- #29 OSHA 300A ----


class OSHAFake:
    def __init__(self, stats): self.stats = stats
    async def get_osha300a_stats(self, cid, yr): return self.stats


@pytest.mark.asyncio
async def test_osha_case_count_inconsistent_critical() -> None:
    r = OSHAFake({
        "totalCases": 5,
        "casesWithDaysAway": 2,
        "casesWithRestriction": 1,
        "casesMedicalOnly": 1,
        "totalEmployees": 50,
        "byType": {"injury": 2, "illness": 2},  # sums to 4, not 5
    })
    rep = await run_osha_300a_assist(r, client_id="T", year=2025)
    codes = {f.code for f in rep.summary.findings}
    assert "CASE_COUNT_INCONSISTENT" in codes


@pytest.mark.asyncio
async def test_osha_under_10_employees_info() -> None:
    r = OSHAFake({"totalCases": 0, "totalEmployees": 8})
    rep = await run_osha_300a_assist(r, client_id="T", year=2025)
    codes = {f.code for f in rep.summary.findings}
    assert "UNDER_10_EMPLOYEES" in codes


@pytest.mark.asyncio
async def test_osha_negative_count_critical() -> None:
    r = OSHAFake({"totalCases": -2, "totalEmployees": 50})
    rep = await run_osha_300a_assist(r, client_id="T", year=2025)
    codes = {f.code for f in rep.summary.findings}
    assert "NEGATIVE_COUNT" in codes
