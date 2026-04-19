"""Benefits-Deduction Audit — unit tests with in-memory reader fake."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.benefits_deduction_audit import (  # noqa: E402
    run_benefits_deduction_audit,
)


class FakeReader:
    def __init__(self, data: dict) -> None:
        self.data = data

    async def get_active_benefit_plans(self, client_id):
        return self.data["plans"]

    async def get_benefit_confirmations(self, client_id):
        return self.data["confirmations"]

    async def get_scheduled_deductions(self, client_id, employee_id):
        return self.data["deductions"].get(employee_id, [])


@pytest.mark.asyncio
async def test_clean_enrollment_passes() -> None:
    reader = FakeReader({
        "plans": [{"planId": "MED-HMO", "expectedDeductionCodes": ["MED"]}],
        "confirmations": [
            {"employeeId": "E1", "firstName": "A", "lastName": "B",
             "plans": [{"planId": "MED-HMO"}]}
        ],
        "deductions": {"E1": [{"code": "MED", "amount": "125.00"}]},
    })
    report = await run_benefits_deduction_audit(
        reader, client_id="TEST", as_of=date(2026, 4, 19)
    )
    assert report.total == 1
    assert report.passed == 1
    assert report.employees[0].findings == []


@pytest.mark.asyncio
async def test_enrolled_no_deduction_is_critical() -> None:
    reader = FakeReader({
        "plans": [{"planId": "MED-HMO", "expectedDeductionCodes": ["MED"]}],
        "confirmations": [
            {"employeeId": "E2", "firstName": "A", "lastName": "B",
             "plans": [{"planId": "MED-HMO"}]}
        ],
        "deductions": {"E2": []},
    })
    report = await run_benefits_deduction_audit(reader, client_id="TEST")
    codes = {f.code: f.severity for f in report.employees[0].findings}
    assert codes["ENROLLED_NO_DEDUCTION"] == "critical"
    assert not report.employees[0].passed


@pytest.mark.asyncio
async def test_zero_amount_deduction_is_critical() -> None:
    reader = FakeReader({
        "plans": [{"planId": "MED-HMO", "expectedDeductionCodes": ["MED"]}],
        "confirmations": [
            {"employeeId": "E3", "plans": [{"planId": "MED-HMO"}]}
        ],
        "deductions": {"E3": [{"code": "MED", "amount": "0"}]},
    })
    report = await run_benefits_deduction_audit(reader, client_id="TEST")
    codes = {f.code for f in report.employees[0].findings}
    assert "ZERO_AMOUNT_DEDUCTION" in codes


@pytest.mark.asyncio
async def test_orphan_deduction_is_warning() -> None:
    reader = FakeReader({
        "plans": [
            {"planId": "MED-HMO", "expectedDeductionCodes": ["MED"]},
            {"planId": "DEN-PPO", "expectedDeductionCodes": ["DEN"]},
        ],
        "confirmations": [
            {"employeeId": "E4", "plans": [{"planId": "MED-HMO"}]}
        ],
        # DEN deduction exists but employee not enrolled in DEN-PPO
        "deductions": {"E4": [
            {"code": "MED", "amount": "100"},
            {"code": "DEN", "amount": "30"},
        ]},
    })
    report = await run_benefits_deduction_audit(reader, client_id="TEST")
    findings = report.employees[0].findings
    orphans = [f for f in findings if f.code == "ORPHAN_DEDUCTION"]
    assert len(orphans) == 1
    assert orphans[0].severity == "warning"
    # MED should NOT be orphan — it matches MED-HMO enrollment
    assert "MED" not in orphans[0].message


@pytest.mark.asyncio
async def test_plan_with_no_expected_code_is_skipped() -> None:
    reader = FakeReader({
        "plans": [{"planId": "LIFE-BASIC"}],  # no expectedDeductionCodes
        "confirmations": [
            {"employeeId": "E5", "plans": [{"planId": "LIFE-BASIC"}]}
        ],
        "deductions": {"E5": []},
    })
    report = await run_benefits_deduction_audit(reader, client_id="TEST")
    assert report.employees[0].findings == []


@pytest.mark.asyncio
async def test_empty_confirmations_produces_empty_report() -> None:
    reader = FakeReader({"plans": [], "confirmations": [], "deductions": {}})
    report = await run_benefits_deduction_audit(reader, client_id="TEST")
    assert report.total == 0
    assert report.passed == 0


@pytest.mark.asyncio
async def test_partition_pass_fail() -> None:
    reader = FakeReader({
        "plans": [{"planId": "MED", "expectedDeductionCodes": ["MED"]}],
        "confirmations": [
            {"employeeId": "PASS1", "plans": [{"planId": "MED"}]},
            {"employeeId": "FAIL1", "plans": [{"planId": "MED"}]},
        ],
        "deductions": {
            "PASS1": [{"code": "MED", "amount": "100"}],
            "FAIL1": [],
        },
    })
    report = await run_benefits_deduction_audit(reader, client_id="TEST")
    assert report.passed == 1
    assert report.failed == 1
