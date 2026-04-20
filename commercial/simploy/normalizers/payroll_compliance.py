"""Payroll heuristics — deduction conflict detection + overtime anomaly detection.

Moved from prismhr_mcp.normalizers.payroll (OSS) because the heuristics
are the core of commercial-tier compliance workflows. PayVoucher stays
in the OSS models (shared data contract); only the detection logic
moved to paid tier.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from prismhr_mcp.models.payroll import PayVoucher  # shared data contract

from simploy.models.payroll_compliance import (
    DeductionConflict,
    OvertimeAnomaly,
)


# Overtime thresholds — revisit with UAT data.
OT_EXCESSIVE_WEEKLY_HOURS = Decimal("30")  # OT beyond this is unusual
NEGATIVE_REGULAR_TOLERANCE = Decimal("-0.01")
RATE_MISMATCH_TOLERANCE_PCT = 5.0  # OT pay/hour should be ~1.5x regular


def detect_deduction_conflicts(
    scheduled_deductions: list[dict[str, Any]],
    today: str | None = None,
) -> list[DeductionConflict]:
    """Scan scheduled deductions for structural conflicts."""
    conflicts: list[DeductionConflict] = []
    by_priority: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in scheduled_deductions:
        if not isinstance(row, dict):
            continue
        status = _str(row.get("status") or row.get("statusType") or "").lower()
        if status not in ("active", "a", ""):
            continue

        code = _str(row.get("code") or row.get("deductionCode")).upper()
        if code:
            by_code[code].append(row)

        priority = row.get("priority") or row.get("deductionPriority")
        try:
            priority_int = int(priority) if priority is not None else None
        except (TypeError, ValueError):
            priority_int = None
        if priority_int is not None:
            by_priority[priority_int].append(row)

        end_date = _str(row.get("endDate") or row.get("scheduledEndDate"))
        if end_date and today and end_date < today:
            conflicts.append(
                DeductionConflict(
                    kind="expired_active",
                    deduction_codes=[code] if code else [],
                    severity="medium",
                    message=(
                        f"Deduction {code or '<unknown code>'} is marked active but "
                        f"scheduled end date {end_date} is before today ({today})."
                    ),
                    scheduled_for=end_date,
                )
            )

        if _requires_goal(row):
            goal = row.get("goalAmount") or row.get("goal_amount")
            try:
                goal_val = Decimal(str(goal)) if goal is not None else Decimal("0")
            except (ValueError, ArithmeticError):
                goal_val = Decimal("0")
            if goal_val == 0:
                conflicts.append(
                    DeductionConflict(
                        kind="no_goal_set",
                        deduction_codes=[code] if code else [],
                        severity="low",
                        message=(
                            f"Deduction {code or '<unknown code>'} appears goal-based "
                            "but has no goalAmount set. Likely misconfigured."
                        ),
                    )
                )

    for priority_int, rows in by_priority.items():
        if len(rows) < 2:
            continue
        codes = sorted({_str(r.get("code") or r.get("deductionCode")) for r in rows})
        codes = [c for c in codes if c]
        conflicts.append(
            DeductionConflict(
                kind="priority_clash",
                deduction_codes=codes,
                severity="high",
                message=(
                    f"{len(rows)} active deductions share priority {priority_int} "
                    f"({', '.join(codes) or 'unknown codes'}). Payroll will not "
                    "deterministically order them."
                ),
            )
        )

    for code, rows in by_code.items():
        if len(rows) < 2:
            continue
        conflicts.append(
            DeductionConflict(
                kind="same_code_duplicate",
                deduction_codes=[code],
                severity="medium",
                message=(
                    f"Deduction code {code} has {len(rows)} active schedules. "
                    "Usually only one is intended — review amounts."
                ),
            )
        )

    return conflicts


def detect_overtime_anomalies(
    vouchers: list[PayVoucher],
) -> list[OvertimeAnomaly]:
    """Flag payroll vouchers whose hours or pay don't reconcile to expectations."""
    anomalies: list[OvertimeAnomaly] = []

    for v in vouchers:
        reg = v.regular_hours or Decimal("0")
        ot = v.overtime_hours or Decimal("0")
        reg_pay = v.regular_pay or Decimal("0")
        ot_pay = v.overtime_pay or Decimal("0")

        if reg < NEGATIVE_REGULAR_TOLERANCE:
            anomalies.append(
                _anomaly(v, "negative_regular", "high",
                    f"Voucher has negative regular hours ({reg}). Almost always a correction artifact."
                )
            )

        if ot > Decimal("0") and reg <= Decimal("0"):
            anomalies.append(
                _anomaly(v, "ot_without_regular", "medium",
                    f"Voucher has overtime hours ({ot}) but no regular hours. Check pay type coding."
                )
            )

        if ot > OT_EXCESSIVE_WEEKLY_HOURS:
            anomalies.append(
                _anomaly(v, "excessive_overtime", "medium",
                    f"Overtime hours = {ot}, which exceeds the {OT_EXCESSIVE_WEEKLY_HOURS}-hour flag threshold."
                )
            )

        if reg > 0 and ot > 0 and reg_pay > 0 and ot_pay > 0:
            regular_rate = reg_pay / reg
            overtime_rate = ot_pay / ot
            if regular_rate > 0:
                ratio = float(overtime_rate / regular_rate)
                lower = 1.5 * (1 - RATE_MISMATCH_TOLERANCE_PCT / 100)
                upper = 1.5 * (1 + RATE_MISMATCH_TOLERANCE_PCT / 100)
                if ratio < lower or ratio > upper:
                    anomalies.append(
                        _anomaly(
                            v,
                            "rate_mismatch",
                            "low",
                            (
                                f"Overtime rate is {ratio:.2f}x regular rate "
                                f"(expected ~1.5x). Regular: {regular_rate:.2f}/hr, "
                                f"overtime: {overtime_rate:.2f}/hr."
                            ),
                        )
                    )

    return anomalies


def _anomaly(
    v: PayVoucher, kind: str, severity: str, message: str
) -> OvertimeAnomaly:
    return OvertimeAnomaly(
        voucher_id=v.voucher_id,
        employee_id=None,
        pay_date=v.pay_date,
        kind=kind,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=message,
        regular_hours=v.regular_hours,
        overtime_hours=v.overtime_hours,
    )


def _requires_goal(row: dict[str, Any]) -> bool:
    type_hint = _str(
        row.get("deductionType")
        or row.get("type")
        or row.get("code")
        or row.get("deductionCode")
    ).upper()
    goal_markers = ("GARN", "LOAN", "CHILD", "ADVANCE", "CATCHUP")
    return any(marker in type_hint for marker in goal_markers)


def _str(value: Any) -> str:
    return "" if value is None else str(value)
