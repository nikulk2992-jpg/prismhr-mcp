"""Batch 8 — workflows #8, #9, #10, #42, #47."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.overtime_anomaly import run_overtime_anomaly  # noqa: E402
from simploy.workflows.pay_group_balance import run_pay_group_balance  # noqa: E402
from simploy.workflows.pay_group_schedule_adherence import run_pay_group_schedule_adherence  # noqa: E402
from simploy.workflows.pto_class_assignment import run_pto_class_assignment  # noqa: E402
from simploy.workflows.scheduled_payment_integrity import run_scheduled_payment_integrity  # noqa: E402


# ---- #8 OT anomaly ----


class OTFake:
    def __init__(self, rows, avgs): self.rows = rows; self.avgs = avgs
    async def list_employee_hours_for_period(self, cid, pe): return self.rows
    async def avg_ot_last_90d(self, cid, eid, asof): return self.avgs.get(eid, Decimal("0"))


@pytest.mark.asyncio
async def test_non_exempt_over_40_no_ot_critical() -> None:
    r = OTFake(
        rows=[{"employeeId": "E1", "flsaStatus": "NON_EXEMPT", "regularHours": "48", "otHours": "0"}],
        avgs={},
    )
    rep = await run_overtime_anomaly(r, client_id="T", period_end=date(2026, 4, 15))
    codes = {f.code for f in rep.audits[0].findings}
    assert "NON_EXEMPT_NO_OT_BUT_OVER_40" in codes


@pytest.mark.asyncio
async def test_exempt_with_ot_warning() -> None:
    r = OTFake(
        rows=[{"employeeId": "E2", "flsaStatus": "EXEMPT", "regularHours": "40", "otHours": "5"}],
        avgs={},
    )
    rep = await run_overtime_anomaly(r, client_id="T", period_end=date(2026, 4, 15))
    codes = {f.code for f in rep.audits[0].findings}
    assert "EXEMPT_WITH_OT" in codes


@pytest.mark.asyncio
async def test_ot_spike_warning() -> None:
    r = OTFake(
        rows=[{"employeeId": "E3", "flsaStatus": "NON_EXEMPT", "regularHours": "40", "otHours": "30", "otApprover": "Sup"}],
        avgs={"E3": Decimal("5")},
    )
    rep = await run_overtime_anomaly(r, client_id="T", period_end=date(2026, 4, 15))
    codes = {f.code for f in rep.audits[0].findings}
    assert "OT_SPIKE" in codes


# ---- #9 Pay group schedule adherence ----


class PGSchedFake:
    def __init__(self, groups, orphans): self.g = groups; self.o = orphans
    async def list_pay_groups(self, cid): return self.g
    async def employees_without_pay_group(self, cid): return self.o


@pytest.mark.asyncio
async def test_pg_late_call_in_critical() -> None:
    today = date(2026, 4, 19)
    r = PGSchedFake(
        groups=[{"payGroupId": "B", "scheduleId": "B5PE5B", "currentPeriodEnd": "2026-04-11", "callInDate": (today - timedelta(days=2)).isoformat(), "payDate": (today + timedelta(days=3)).isoformat(), "currentBatchStatus": "TS.READY", "employeeCount": 20}],
        orphans=[],
    )
    rep = await run_pay_group_schedule_adherence(r, client_id="T", as_of=today)
    codes = {f.code for f in rep.audits[0].findings}
    assert "LATE_CALL_IN" in codes


@pytest.mark.asyncio
async def test_pg_no_schedule_critical() -> None:
    r = PGSchedFake(
        groups=[{"payGroupId": "X", "scheduleId": "", "employeeCount": 5}],
        orphans=[],
    )
    rep = await run_pay_group_schedule_adherence(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "NO_SCHEDULE" in codes


# ---- #10 Scheduled payment integrity ----


class SPFake:
    def __init__(self, payments, active_codes, term_dates):
        self.p = payments
        self.a = active_codes
        self.t = term_dates
    async def list_scheduled_payments(self, cid): return self.p
    async def is_pay_code_active(self, cid, code): return self.a.get(code, True)
    async def get_termination_date(self, cid, eid): return self.t.get(eid)


@pytest.mark.asyncio
async def test_sp_overdue_critical() -> None:
    today = date(2026, 4, 19)
    r = SPFake(
        payments=[{"paymentId": "P1", "employeeId": "E1", "effectiveDate": (today - timedelta(days=30)).isoformat(), "amount": "500", "payCode": "BONUS"}],
        active_codes={"BONUS": True},
        term_dates={},
    )
    rep = await run_scheduled_payment_integrity(r, client_id="T", as_of=today)
    codes = {f.code for f in rep.audits[0].findings}
    assert "OVERDUE" in codes


@pytest.mark.asyncio
async def test_sp_deactivated_code_critical() -> None:
    today = date(2026, 4, 19)
    r = SPFake(
        payments=[{"paymentId": "P2", "employeeId": "E2", "effectiveDate": today.isoformat(), "amount": "500", "payCode": "OLDCODE"}],
        active_codes={"OLDCODE": False},
        term_dates={},
    )
    rep = await run_scheduled_payment_integrity(r, client_id="T", as_of=today)
    codes = {f.code for f in rep.audits[0].findings}
    assert "DEACTIVATED_PAY_CODE" in codes


# ---- #42 Pay group balance ----


class PGBalFake:
    def __init__(self, groups, freq_map): self.g = groups; self.fm = freq_map
    async def list_pay_groups_with_employees(self, cid): return self.g
    async def default_frequency_for_employment_type(self, cid, et): return self.fm.get(et, "")


@pytest.mark.asyncio
async def test_pg_bal_inactive_with_employees_critical() -> None:
    r = PGBalFake(
        groups=[{"payGroupId": "OLD", "frequency": "W", "active": False, "employees": [{"employeeId": "E1", "employmentType": "FT"}]}],
        freq_map={"FT": "B"},
    )
    rep = await run_pay_group_balance(r, client_id="T")
    codes = {f.code for a in rep.audits for f in a.findings}
    assert "INACTIVE_PAY_GROUP" in codes


@pytest.mark.asyncio
async def test_pg_bal_frequency_mismatch_warning() -> None:
    r = PGBalFake(
        groups=[{"payGroupId": "W", "frequency": "W", "active": True, "employees": [{"employeeId": "E1", "employmentType": "FT"}]}],
        freq_map={"FT": "B"},
    )
    rep = await run_pay_group_balance(r, client_id="T")
    assert rep.mismatches and rep.mismatches[0]["employeeId"] == "E1"


# ---- #47 PTO class assignment ----


class PTOClassFake:
    def __init__(self, rows, retired_plans, expected):
        self.rows = rows
        self.retired = retired_plans
        self.expected = expected
    async def list_employees_with_pto_class(self, cid): return self.rows
    async def get_retired_pto_plans(self, cid): return self.retired
    async def expected_pto_class_for_tenure(self, cid, et, years): return self.expected.get((et, years), "")


@pytest.mark.asyncio
async def test_pto_class_missing_critical() -> None:
    r = PTOClassFake(
        rows=[{"employeeId": "E1", "employmentType": "FT", "ptoClass": ""}],
        retired_plans=set(),
        expected={},
    )
    rep = await run_pto_class_assignment(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "MISSING_PTO_CLASS" in codes


@pytest.mark.asyncio
async def test_pto_class_retired_plan_critical() -> None:
    r = PTOClassFake(
        rows=[{"employeeId": "E2", "employmentType": "FT", "ptoClass": "FTSTD", "ptoPlanId": "OLD-PLAN"}],
        retired_plans={"OLD-PLAN"},
        expected={},
    )
    rep = await run_pto_class_assignment(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "CLASS_POINTS_TO_RETIRED_PLAN" in codes


@pytest.mark.asyncio
async def test_pto_class_wrong_type_warning() -> None:
    r = PTOClassFake(
        rows=[{"employeeId": "E3", "employmentType": "FT", "ptoClass": "PT_STANDARD"}],
        retired_plans=set(),
        expected={},
    )
    rep = await run_pto_class_assignment(r, client_id="T")
    codes = {f.code for f in rep.audits[0].findings}
    assert "UNUSUAL_CLASS_FOR_EMPLOYMENT_TYPE" in codes
