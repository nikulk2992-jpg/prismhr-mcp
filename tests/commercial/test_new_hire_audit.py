"""New Hire Audit workflow — unit tests with in-memory reader fake."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.new_hire_audit import (  # noqa: E402
    PrismHRReader,
    run_new_hire_audit,
)


class FakeReader:
    """In-memory fake implementing the PrismHRReader protocol."""

    def __init__(self, data: dict) -> None:
        self.data = data

    async def get_employee_list(self, client_id, hired_since):
        return self.data["roster"]

    async def get_employee(self, client_id, employee_id):
        return self.data["employees"][employee_id]

    async def get_address(self, client_id, employee_id):
        return self.data["addresses"].get(employee_id, {})

    async def get_everify(self, client_id, employee_id):
        return self.data["everify"].get(employee_id, {})

    async def get_scheduled_deductions(self, client_id, employee_id):
        return self.data["deductions"].get(employee_id, {})

    async def check_garnishments(self, client_id, employee_id):
        return self.data["garnishments"].get(employee_id, {})


@pytest.mark.asyncio
async def test_clean_new_hire_passes() -> None:
    reader = FakeReader({
        "roster": [
            {"employeeId": "E1", "firstName": "Ada", "lastName": "Lovelace", "hireDate": "2026-03-15"},
        ],
        "employees": {"E1": {"ssn": "123456789"}},
        "addresses": {"E1": {"line1": "1 Analytical Engine Rd"}},
        "everify": {"E1": {"everifyStatus": "AUTHORIZED"}},
        "deductions": {"E1": {"scheduledDeductions": [{"code": "MED"}]}},
        "garnishments": {"E1": {"hasGarnishments": False}},
    })
    report = await run_new_hire_audit(reader, client_id="TEST-CLIENT", lookback_days=30,
                                      as_of=date(2026, 4, 1))
    assert report.total == 1
    assert report.passed == 1
    assert report.failed == 0
    assert report.employees[0].findings == []


@pytest.mark.asyncio
async def test_missing_address_flags_critical() -> None:
    reader = FakeReader({
        "roster": [{"employeeId": "E2", "firstName": "Grace", "lastName": "Hopper", "hireDate": "2026-03-20"}],
        "employees": {"E2": {"ssn": "987654321"}},
        "addresses": {"E2": {}},
        "everify": {"E2": {"everifyStatus": "AUTHORIZED"}},
        "deductions": {"E2": {"scheduledDeductions": [{"code": "MED"}]}},
        "garnishments": {"E2": {}},
    })
    report = await run_new_hire_audit(reader, client_id="TEST-CLIENT")
    audit = report.employees[0]
    codes = {f.code for f in audit.findings}
    assert "MISSING_ADDRESS" in codes
    assert not audit.passed


@pytest.mark.asyncio
async def test_everify_not_cleared_is_critical() -> None:
    reader = FakeReader({
        "roster": [{"employeeId": "E3", "firstName": "A", "lastName": "B", "hireDate": "2026-03-01"}],
        "employees": {"E3": {"ssn": "1"}},
        "addresses": {"E3": {"line1": "X"}},
        "everify": {"E3": {"everifyStatus": "TNC"}},
        "deductions": {"E3": {"scheduledDeductions": []}},
        "garnishments": {"E3": {}},
    })
    report = await run_new_hire_audit(reader, client_id="TEST-CLIENT")
    sev = {f.code: f.severity for f in report.employees[0].findings}
    assert sev["EVERIFY_NOT_CLEARED"] == "critical"


@pytest.mark.asyncio
async def test_garnishment_incomplete_flags_critical() -> None:
    reader = FakeReader({
        "roster": [{"employeeId": "E4", "firstName": "A", "lastName": "B", "hireDate": "2026-03-01"}],
        "employees": {"E4": {"ssn": "1"}},
        "addresses": {"E4": {"line1": "X"}},
        "everify": {"E4": {"everifyStatus": "AUTHORIZED"}},
        "deductions": {"E4": {"scheduledDeductions": [{"code": "MED"}]}},
        "garnishments": {"E4": {"hasGarnishments": True, "setupComplete": False}},
    })
    report = await run_new_hire_audit(reader, client_id="TEST-CLIENT")
    codes = {f.code for f in report.employees[0].findings}
    assert "GARNISHMENT_SETUP_INCOMPLETE" in codes


@pytest.mark.asyncio
async def test_report_partitions_pass_fail() -> None:
    reader = FakeReader({
        "roster": [
            {"employeeId": "P1", "firstName": "A", "lastName": "A", "hireDate": "2026-03-01"},
            {"employeeId": "F1", "firstName": "B", "lastName": "B", "hireDate": "2026-03-05"},
        ],
        "employees": {"P1": {"ssn": "1"}, "F1": {"ssn": "2"}},
        "addresses": {"P1": {"line1": "X"}, "F1": {}},
        "everify": {"P1": {"everifyStatus": "AUTHORIZED"}, "F1": {"everifyStatus": "AUTHORIZED"}},
        "deductions": {"P1": {"scheduledDeductions": [{}]}, "F1": {"scheduledDeductions": [{}]}},
        "garnishments": {"P1": {}, "F1": {}},
    })
    report = await run_new_hire_audit(reader, client_id="TEST-CLIENT")
    assert report.total == 2
    assert report.passed == 1
    assert report.failed == 1
