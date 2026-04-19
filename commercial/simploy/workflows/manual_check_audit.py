"""Manual Check Audit — workflow #7.

Manual checks bypass the normal payroll cycle. Every one is a
potential fraud vector or process-control failure. PrismHR allows
them but doesn't run the same validation as regular payroll, so the
PEO must audit each.

Findings per manual check:
  - NO_REASON_CODE: check has no documented reason.
  - EXCESSIVE_AMOUNT: check exceeds the per-check threshold.
  - DUPLICATE_WITHIN_WINDOW: same employee received multiple manual
    checks within N days.
  - REPEAT_MONTHLY: same employee received manual checks in 3+ consecutive months.
  - OFF_CYCLE_NO_APPROVAL: manual check without a documented approver.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class ManualCheckAudit:
    check_id: str
    employee_id: str
    check_date: date | None
    amount: Decimal
    reason_code: str
    approver: str
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ManualCheckReport:
    client_id: str
    window_start: date
    window_end: date
    audits: list[ManualCheckAudit]
    excessive_threshold: Decimal

    @property
    def total(self) -> int:
        return len(self.audits)

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_manual_checks(
        self, client_id: str, start: date, end: date
    ) -> list[dict]: ...


async def run_manual_check_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    window_start: date,
    window_end: date,
    excessive_threshold: Decimal | str = "10000.00",
    duplicate_window_days: int = 14,
) -> ManualCheckReport:
    threshold = Decimal(str(excessive_threshold))
    checks = await reader.list_manual_checks(client_id, window_start, window_end)

    # Group by employee for duplicate / repeat-monthly detection.
    by_emp: dict[str, list[dict]] = defaultdict(list)
    for c in checks:
        eid = str(c.get("employeeId") or "")
        if eid:
            by_emp[eid].append(c)

    audits: list[ManualCheckAudit] = []
    for c in checks:
        check_id = str(c.get("checkId") or c.get("voucherId") or c.get("id") or "")
        eid = str(c.get("employeeId") or "")
        dt = _parse(c.get("checkDate") or c.get("payDate"))
        amt = _dec(c.get("amount") or c.get("netPay") or c.get("grossPay"))
        reason = str(c.get("reasonCode") or c.get("reason") or "").strip()
        approver = str(c.get("approver") or c.get("approvedBy") or "").strip()

        audit = ManualCheckAudit(
            check_id=check_id,
            employee_id=eid,
            check_date=dt,
            amount=amt,
            reason_code=reason,
            approver=approver,
        )

        if not reason:
            audit.findings.append(
                Finding("NO_REASON_CODE", "warning", "Manual check has no documented reason.")
            )

        if amt > threshold:
            audit.findings.append(
                Finding(
                    "EXCESSIVE_AMOUNT",
                    "critical",
                    f"Check amount ${amt} exceeds threshold ${threshold}.",
                )
            )

        if not approver:
            audit.findings.append(
                Finding(
                    "OFF_CYCLE_NO_APPROVAL",
                    "critical",
                    "Off-cycle manual check with no approver on file.",
                )
            )

        # Duplicate-within-window check
        if dt and eid:
            for other in by_emp[eid]:
                if other is c:
                    continue
                other_id = str(other.get("checkId") or other.get("voucherId") or other.get("id") or "")
                if other_id == check_id:
                    continue
                other_dt = _parse(other.get("checkDate") or other.get("payDate"))
                if other_dt and abs((dt - other_dt).days) <= duplicate_window_days:
                    audit.findings.append(
                        Finding(
                            "DUPLICATE_WITHIN_WINDOW",
                            "warning",
                            f"Another manual check for this employee within {duplicate_window_days}d: {other_id}.",
                        )
                    )
                    break

        audits.append(audit)

    # Repeat-monthly: employees with manual checks in 3+ consecutive months.
    for eid, rows in by_emp.items():
        months = sorted({
            (_parse(r.get("checkDate") or r.get("payDate")) or date.min).month
            for r in rows
            if _parse(r.get("checkDate") or r.get("payDate")) is not None
        })
        streak = 1
        longest = 1
        for i in range(1, len(months)):
            if months[i] == months[i - 1] + 1:
                streak += 1
                longest = max(longest, streak)
            else:
                streak = 1
        if longest >= 3:
            for a in audits:
                if a.employee_id == eid and not any(
                    f.code == "REPEAT_MONTHLY" for f in a.findings
                ):
                    a.findings.append(
                        Finding(
                            "REPEAT_MONTHLY",
                            "warning",
                            f"Employee has manual checks in {longest} consecutive months.",
                        )
                    )
                    break

    return ManualCheckReport(
        client_id=client_id,
        window_start=window_start,
        window_end=window_end,
        audits=audits,
        excessive_threshold=threshold,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
