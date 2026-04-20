"""Pure-function tests for commercial payroll normalizers."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from prismhr_mcp.models.payroll import PayVoucher  # noqa: E402
from simploy.normalizers.payroll_compliance import (  # noqa: E402
    detect_deduction_conflicts,
    detect_overtime_anomalies,
)


# ---------- deduction conflict detector ----------


def test_priority_clash_detected() -> None:
    rows = [
        {"status": "active", "code": "401K", "priority": 10},
        {"status": "active", "code": "GARN", "priority": 10},
    ]
    conflicts = detect_deduction_conflicts(rows)
    assert any(c.kind == "priority_clash" for c in conflicts)
    clash = [c for c in conflicts if c.kind == "priority_clash"][0]
    assert set(clash.deduction_codes) == {"401K", "GARN"}
    assert clash.severity == "high"


def test_same_code_duplicate_detected() -> None:
    rows = [
        {"status": "active", "code": "401K", "priority": 5},
        {"status": "active", "code": "401K", "priority": 7},
    ]
    conflicts = detect_deduction_conflicts(rows)
    assert any(c.kind == "same_code_duplicate" for c in conflicts)


def test_expired_active_detected_when_today_provided() -> None:
    rows = [
        {"status": "active", "code": "LOAN", "priority": 1, "endDate": "2024-12-31"},
    ]
    conflicts = detect_deduction_conflicts(rows, today="2026-04-18")
    assert any(c.kind == "expired_active" for c in conflicts)
    # No priority clash should also fire.
    assert not any(c.kind == "priority_clash" for c in conflicts)


def test_no_goal_set_flagged_for_goal_based_deductions() -> None:
    rows = [
        {"status": "active", "code": "GARN-01", "priority": 1, "goalAmount": 0},
        {"status": "active", "code": "401K", "priority": 2, "goalAmount": 0},  # 401K ≠ goal-based
    ]
    conflicts = detect_deduction_conflicts(rows)
    goal_conflicts = [c for c in conflicts if c.kind == "no_goal_set"]
    assert len(goal_conflicts) == 1
    assert "GARN-01" in goal_conflicts[0].deduction_codes


def test_inactive_rows_ignored() -> None:
    rows = [
        {"status": "inactive", "code": "401K", "priority": 5},
        {"status": "inactive", "code": "401K", "priority": 5},  # duplicate + clash would fire if active
    ]
    assert detect_deduction_conflicts(rows) == []


# ---------- overtime anomaly detector ----------


def _v(
    *,
    reg: Decimal = Decimal("0"),
    ot: Decimal = Decimal("0"),
    reg_pay: Decimal = Decimal("0"),
    ot_pay: Decimal = Decimal("0"),
    vid: str = "V1",
) -> PayVoucher:
    return PayVoucher(
        voucher_id=vid,
        pay_date="2026-04-18",
        regular_hours=reg,
        overtime_hours=ot,
        regular_pay=reg_pay,
        overtime_pay=ot_pay,
    )


def test_negative_regular_flagged() -> None:
    anomalies = detect_overtime_anomalies([_v(reg=Decimal("-5"))])
    assert any(a.kind == "negative_regular" for a in anomalies)


def test_ot_without_regular_flagged() -> None:
    anomalies = detect_overtime_anomalies([_v(ot=Decimal("5"))])
    assert any(a.kind == "ot_without_regular" for a in anomalies)


def test_excessive_overtime_flagged() -> None:
    anomalies = detect_overtime_anomalies(
        [_v(reg=Decimal("40"), ot=Decimal("40"), reg_pay=Decimal("800"), ot_pay=Decimal("1200"))]
    )
    assert any(a.kind == "excessive_overtime" for a in anomalies)


def test_rate_mismatch_flagged() -> None:
    # Regular rate = $20/hr, OT rate = $25/hr -> ratio 1.25x (expected ~1.5x).
    anomalies = detect_overtime_anomalies(
        [_v(reg=Decimal("40"), ot=Decimal("5"), reg_pay=Decimal("800"), ot_pay=Decimal("125"))]
    )
    assert any(a.kind == "rate_mismatch" for a in anomalies)


def test_clean_voucher_produces_no_anomalies() -> None:
    # Regular $20/hr, OT $30/hr = exactly 1.5x.
    anomalies = detect_overtime_anomalies(
        [_v(reg=Decimal("40"), ot=Decimal("5"), reg_pay=Decimal("800"), ot_pay=Decimal("150"))]
    )
    assert anomalies == []
