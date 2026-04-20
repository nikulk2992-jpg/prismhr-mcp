"""State new-hire reporting audit — unit tests."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.state_new_hire_reporting import run_state_new_hire_audit  # noqa: E402


class FakeReader:
    def __init__(self, rows): self.rows = rows
    async def list_new_hires(self, cid, since): return self.rows


def _full_addr():
    return {"line1": "1 Main", "city": "Austin", "state": "TX", "zip": "78701"}


async def _run(reader, today=date(2026, 4, 20)):
    return await run_state_new_hire_audit(
        reader, client_id="T",
        hired_since=date(2026, 1, 1),
        as_of=today,
    )


@pytest.mark.asyncio
async def test_overdue_is_critical() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "state": "TX", "hireDate": "2026-03-01",
        "ssn": "123-45-6789", "dob": "1990-01-01", "address": _full_addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.hires[0].findings}
    assert "NOT_REPORTED_OVERDUE" in codes
    assert r.overdue == 1


@pytest.mark.asyncio
async def test_upcoming_is_warning() -> None:
    # Hire 17 days before today = 3 days from deadline (TX 20d)
    today = date(2026, 4, 20)
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "state": "TX", "hireDate": (today - timedelta(days=17)).isoformat(),
        "ssn": "123-45-6789", "dob": "1990-01-01", "address": _full_addr(),
    }])
    r = await _run(reader, today=today)
    codes = {f.code for f in r.hires[0].findings}
    assert "NOT_REPORTED_UPCOMING" in codes


@pytest.mark.asyncio
async def test_tight_deadline_state_al_7_days() -> None:
    today = date(2026, 4, 20)
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "state": "AL",
        "hireDate": (today - timedelta(days=10)).isoformat(),
        "ssn": "123-45-6789", "dob": "1990-01-01", "address": _full_addr(),
    }])
    r = await _run(reader, today=today)
    codes = {f.code for f in r.hires[0].findings}
    assert "NOT_REPORTED_OVERDUE" in codes  # AL = 7 day deadline


@pytest.mark.asyncio
async def test_missing_ssn_critical() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "state": "TX", "hireDate": "2026-04-10",
        "ssn": "", "dob": "1990-01-01", "address": _full_addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.hires[0].findings}
    assert "MISSING_REQUIRED_FIELD" in codes


@pytest.mark.asyncio
async def test_reported_on_time_info_only() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "state": "TX", "hireDate": "2026-04-01",
        "newHireReportSentDate": "2026-04-08",
        "ssn": "123-45-6789", "dob": "1990-01-01", "address": _full_addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.hires[0].findings}
    assert "REPORT_SENT_OK" in codes
    assert "NOT_REPORTED_OVERDUE" not in codes


@pytest.mark.asyncio
async def test_reported_late_is_warning() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "state": "AL", "hireDate": "2026-03-01",  # AL = 7d deadline
        "newHireReportSentDate": "2026-03-15",     # sent 14d after hire
        "ssn": "123-45-6789", "dob": "1990-01-01", "address": _full_addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.hires[0].findings}
    assert "REPORTED_LATE" in codes


@pytest.mark.asyncio
async def test_rehire_after_60_day_gap_critical() -> None:
    reader = FakeReader([{
        "employeeId": "E1", "firstName": "Ada", "lastName": "Smith",
        "state": "TX", "hireDate": "2026-04-01",
        "priorTerminationDate": "2025-10-01",
        "ssn": "123-45-6789", "dob": "1990-01-01", "address": _full_addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.hires[0].findings}
    assert "REHIRE_NOT_REPORTED" in codes
