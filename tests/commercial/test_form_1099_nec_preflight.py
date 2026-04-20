"""1099-NEC pre-flight — unit tests."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.form_1099_nec_preflight import (  # noqa: E402
    LocalTINChecksum,
    run_form_1099_nec_preflight,
)


class FakeReader:
    def __init__(self, rows): self.rows = rows
    async def list_contractors_paid_in_year(self, cid, year):
        return self.rows


def _addr(ok=True):
    if ok:
        return {"line1": "1 Main", "city": "Austin", "state": "TX", "zip": "78701"}
    return {}


async def _run(reader, matcher=None):
    return await run_form_1099_nec_preflight(
        reader, client_id="T", tax_year=2025,
        as_of=date(2026, 1, 15), tin_matcher=matcher,
    )


@pytest.mark.asyncio
async def test_below_threshold_is_info_no_1099() -> None:
    reader = FakeReader([{
        "contractorId": "C1", "legalName": "Ada LLC", "ein": "12-3456789",
        "ytdNonempComp": "450.00", "w9OnFile": True, "address": _addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.contractors[0].findings}
    assert "BELOW_600_THRESHOLD" in codes
    assert r.contractors[0].ready_to_file is False  # below threshold
    assert r.contractors[0].above_threshold is False


@pytest.mark.asyncio
async def test_no_w9_is_critical() -> None:
    reader = FakeReader([{
        "contractorId": "C1", "legalName": "Ada LLC",
        "ytdNonempComp": "5000", "w9OnFile": False, "address": _addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.contractors[0].findings}
    assert "NO_W9_ON_FILE" in codes


@pytest.mark.asyncio
async def test_invalid_tin_format_critical() -> None:
    reader = FakeReader([{
        "contractorId": "C1", "legalName": "Ada LLC", "ein": "BAD-TIN",
        "ytdNonempComp": "5000", "w9OnFile": True, "address": _addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.contractors[0].findings}
    assert "TIN_INVALID_FORMAT" in codes


@pytest.mark.asyncio
async def test_tin_match_failed_triggers_bwh_requirement() -> None:
    """Bogus SSN prefix 000 should fail the local checksum matcher."""
    reader = FakeReader([{
        "contractorId": "C1", "legalName": "Ada LLC", "ssn": "000-12-3456",
        "ytdNonempComp": "5000", "ytdBackupWithholding": "0",
        "w9OnFile": True, "address": _addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.contractors[0].findings}
    assert "TIN_MATCH_FAILED" in codes
    assert "BACKUP_WITHHOLDING_REQUIRED" in codes
    # Expected BWH = $1,200 (24% of $5,000)
    assert r.contractors[0].expected_backup_withholding == __import__("decimal").Decimal("1200.00")


@pytest.mark.asyncio
async def test_address_incomplete_critical() -> None:
    reader = FakeReader([{
        "contractorId": "C1", "legalName": "Ada LLC", "ein": "12-3456789",
        "ytdNonempComp": "5000", "w9OnFile": True, "address": _addr(ok=False),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.contractors[0].findings}
    assert "ADDRESS_INCOMPLETE" in codes


@pytest.mark.asyncio
async def test_box1_mismatch_critical() -> None:
    reader = FakeReader([{
        "contractorId": "C1", "legalName": "Ada LLC", "ein": "12-3456789",
        "ytdNonempComp": "5000", "box1Expected": "4800",
        "w9OnFile": True, "address": _addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.contractors[0].findings}
    assert "BOX1_MISMATCH" in codes


@pytest.mark.asyncio
async def test_clean_contractor_ready_to_file() -> None:
    reader = FakeReader([{
        "contractorId": "C1", "legalName": "Ada LLC", "ein": "12-3456789",
        "ytdNonempComp": "5000",
        "w9OnFile": True, "address": _addr(),
    }])
    r = await _run(reader)
    assert r.contractors[0].ready_to_file
    assert r.ready_to_file == 1
    assert r.blocked == 0


@pytest.mark.asyncio
async def test_name_mismatch_warning_only() -> None:
    reader = FakeReader([{
        "contractorId": "C1", "legalName": "Ada Lovelace LLC",
        "voucherPayeeName": "Babbage Analytics",
        "ein": "12-3456789", "ytdNonempComp": "5000",
        "w9OnFile": True, "address": _addr(),
    }])
    r = await _run(reader)
    codes = {f.code for f in r.contractors[0].findings}
    assert "NAME_TIN_MISMATCH" in codes
    # Warning-only: still ready to file
    assert r.contractors[0].ready_to_file


@pytest.mark.asyncio
async def test_report_rollups() -> None:
    reader = FakeReader([
        {"contractorId": "C1", "legalName": "Ada", "ein": "12-3456789",
         "ytdNonempComp": "5000", "w9OnFile": True, "address": _addr()},
        {"contractorId": "C2", "legalName": "Babb",
         "ytdNonempComp": "5000", "w9OnFile": False, "address": _addr()},
        {"contractorId": "C3", "legalName": "Tiny",
         "ytdNonempComp": "100", "w9OnFile": True, "address": _addr()},
    ])
    r = await _run(reader)
    assert r.total_above_threshold == 2
    assert r.ready_to_file == 1  # C1 clean, C2 blocked by NO_W9
    assert r.blocked == 1
