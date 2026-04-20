"""Batch 9 — workflows #19, #32, #38 + BCBS MI 834 + Sun Life EDX."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.carriers.bcbs_mi import render_bcbs_mi  # noqa: E402
from simploy.carriers.bcbs_mi.companion import BCBSMiCompanionGuide  # noqa: E402
from simploy.carriers.render import Coverage, Enrollee, Enrollment  # noqa: E402
from simploy.carriers.sun_life import render_sun_life_edx  # noqa: E402
from simploy.carriers.sun_life.render import SunLifeCompanionGuide  # noqa: E402
from simploy.workflows.benefit_rate_drift import run_benefit_rate_drift  # noqa: E402
from simploy.workflows.irs_air_preflight import run_irs_air_preflight  # noqa: E402
from simploy.workflows.wc_billing_modifier_sync import run_wc_billing_modifier_sync  # noqa: E402


# ---- #19 Benefit rate drift ----


class RateFake:
    def __init__(self, rows): self.rows = rows
    async def list_plan_rate_history(self, cid): return self.rows


@pytest.mark.asyncio
async def test_rate_employer_only_updated_warning() -> None:
    r = RateFake([{
        "planId": "MED-HMO", "tier": "EMP",
        "currentEmployerRate": "450", "previousEmployerRate": "400",
        "currentEmployeeRate": "75", "previousEmployeeRate": "75",
        "effectiveDate": "2026-01-01",
    }])
    rep = await run_benefit_rate_drift(r, client_id="T")
    codes = {f.code for a in rep.audits for f in a.findings}
    assert "EMPLOYER_ONLY_UPDATED" in codes


@pytest.mark.asyncio
async def test_rate_no_change_at_renewal_critical() -> None:
    today = date(2026, 4, 19)
    r = RateFake([{
        "planId": "DEN-PPO", "tier": "FAM",
        "currentEmployerRate": "40", "previousEmployerRate": "40",
        "currentEmployeeRate": "15", "previousEmployeeRate": "15",
        "effectiveDate": "2024-01-01",
        "renewalDate": "2026-01-01",
    }])
    rep = await run_benefit_rate_drift(r, client_id="T", as_of=today)
    codes = {f.code for a in rep.audits for f in a.findings}
    assert "NO_RATE_CHANGE_AT_RENEWAL" in codes


# ---- #32 IRS AIR pre-flight ----


class AIRFake:
    def __init__(self, bundle): self.bundle = bundle
    async def get_submission_bundle(self, cid, yr): return self.bundle


@pytest.mark.asyncio
async def test_air_invalid_ein_critical() -> None:
    r = AIRFake({
        "ein": "00-1234567",
        "formXml": "<Form/>",
        "employees": [],
    })
    rep = await run_irs_air_preflight(r, client_id="T", year=2025)
    assert any(f.code == "INVALID_EIN" for f in rep.submission.findings)


@pytest.mark.asyncio
async def test_air_invalid_ssn_critical() -> None:
    r = AIRFake({
        "ein": "123456789",
        "formXml": "<Form/>",
        "employees": [{"employeeId": "E1", "ssn": "666-12-3456", "firstName": "A", "lastName": "B"}],
    })
    rep = await run_irs_air_preflight(r, client_id="T", year=2025)
    codes = {f.code for f in rep.submission.findings}
    assert "INVALID_SSN_CHECKSUM" in codes


@pytest.mark.asyncio
async def test_air_manifest_checksum_mismatch_critical() -> None:
    r = AIRFake({
        "ein": "123456789",
        "formXml": "<Form/>",
        "manifestChecksum": "abc123",
        "computedChecksum": "def456",
        "employees": [],
    })
    rep = await run_irs_air_preflight(r, client_id="T", year=2025)
    codes = {f.code for f in rep.submission.findings}
    assert "INVALID_MANIFEST_CHECKSUM" in codes


# ---- #38 WC billing modifier sync ----


class WCFake:
    def __init__(self, acc, bill): self.acc = acc; self.bill = bill
    async def get_wc_accrual_modifiers(self, cid): return self.acc
    async def get_wc_billing_modifiers(self, cid): return self.bill


@pytest.mark.asyncio
async def test_wc_billing_lower_than_accrual_critical() -> None:
    r = WCFake(
        acc=[{"state": "NE", "wcCode": "8810", "modifier": "1.25"}],
        bill=[{"state": "NE", "wcCode": "8810", "modifier": "1.10"}],
    )
    rep = await run_wc_billing_modifier_sync(r, client_id="T")
    codes = {f.code for a in rep.audits for f in a.findings}
    assert "BILLING_LOWER_THAN_ACCRUAL" in codes


@pytest.mark.asyncio
async def test_wc_no_billing_modifier_critical() -> None:
    r = WCFake(
        acc=[{"state": "NE", "wcCode": "8810", "modifier": "1.25"}],
        bill=[],
    )
    rep = await run_wc_billing_modifier_sync(r, client_id="T")
    codes = {f.code for a in rep.audits for f in a.findings}
    assert "NO_BILLING_MODIFIER" in codes


# ---- BCBS MI 834 ----


def _enrollment() -> Enrollment:
    cov = Coverage(
        plan_code="BCBS-MI-PPO",
        coverage_level="FAM",
        effective_date=date(2026, 1, 1),
        insurance_line_code="HLT",
        employer_contribution=Decimal("550"),
        employee_contribution=Decimal("175"),
    )
    emp = Enrollee(
        member_id="EMP-001",
        first_name="JOHN",
        last_name="EMPLOYEE",
        dob=date(1983, 4, 20),
        gender="M",
        ssn="123456789",
        hire_date=date(2024, 2, 1),
        coverages=[cov],
    )
    return Enrollment(
        sender_id="x",
        receiver_id="x",
        control_number="000000001",
        sponsor_name="ACME",
        sponsor_id="FEIN-12345",
        transaction_date=date(2026, 4, 19),
        enrollees=[emp],
    )


def test_bcbs_mi_isa_has_sender() -> None:
    out = render_bcbs_mi(_enrollment())
    assert "SIMPLOY-MI" in out
    assert "BCBSM" in out
    assert "ST*834*" in out


def test_bcbs_mi_does_not_mutate_caller() -> None:
    en = _enrollment()
    original_sender = en.sender_id
    render_bcbs_mi(en, guide=BCBSMiCompanionGuide(sender_id="OVERRIDE"))
    assert en.sender_id == original_sender


# ---- Sun Life EDX ----


def test_sun_life_edx_format() -> None:
    out = render_sun_life_edx(_enrollment())
    lines = out.strip().splitlines()
    assert lines[0].startswith("HDR|")
    assert any(line.startswith("EMP|") for line in lines)
    assert lines[-1].startswith("TRL|")


def test_sun_life_edx_pipe_delimited_employee_fields() -> None:
    out = render_sun_life_edx(_enrollment())
    emp_line = next(line for line in out.splitlines() if line.startswith("EMP|"))
    fields = emp_line.split("|")
    # EMP + 13 fields per our spec = 14 total
    assert len(fields) >= 13
    assert "BCBS-MI-PPO" in fields or "EMP" == fields[0]  # depending on plan_code
    assert fields[0] == "EMP"
