"""Benefit Adjustment Trail — workflow #15.

Benefit adjustments (retro credits, corrections, claw-backs) are an
audit flashpoint. PrismHR logs each one, but nothing enforces
reason-code discipline or catches clusters. This workflow surfaces
anomalies for review.

Findings:
  - LARGE_ADJUSTMENT: single adjustment > threshold (default $1K).
  - NO_REASON_CODE: adjustment with no documented reason.
  - NEGATIVE_WITHOUT_JUSTIFICATION: reversal (negative amount)
    without a paired approval record.
  - REPEATED_EMPLOYEE: same employee received 3+ adjustments in
    the window.
  - ADJUSTMENT_AFTER_TERM: adjustment dated after employee's
    termination.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class AdjustmentAudit:
    adjustment_id: str
    employee_id: str
    date_applied: date | None
    amount: Decimal
    reason_code: str
    findings: list[Finding] = field(default_factory=list)


@dataclass
class AdjustmentTrailReport:
    client_id: str
    window_start: date
    window_end: date
    audits: list[AdjustmentAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_benefit_adjustments(
        self, client_id: str, start: date, end: date
    ) -> list[dict]: ...
    async def get_termination_date(
        self, client_id: str, employee_id: str
    ) -> date | None: ...


async def run_benefit_adjustment_trail(
    reader: PrismHRReader,
    *,
    client_id: str,
    window_start: date,
    window_end: date,
    large_threshold: Decimal | str = "1000.00",
) -> AdjustmentTrailReport:
    threshold = Decimal(str(large_threshold))

    rows = await reader.list_benefit_adjustments(client_id, window_start, window_end)

    audits: list[AdjustmentAudit] = []
    counts: Counter = Counter()
    for r in rows:
        aid = str(r.get("adjustmentId") or r.get("id") or "")
        eid = str(r.get("employeeId") or "")
        dt = _parse(r.get("dateApplied") or r.get("effectiveDate"))
        amt = _dec(r.get("amount"))
        reason = str(r.get("reasonCode") or r.get("reason") or "").strip()

        counts[eid] += 1
        audit = AdjustmentAudit(
            adjustment_id=aid,
            employee_id=eid,
            date_applied=dt,
            amount=amt,
            reason_code=reason,
        )

        if amt.copy_abs() > threshold:
            audit.findings.append(
                Finding(
                    "LARGE_ADJUSTMENT",
                    "warning",
                    f"Adjustment ${amt} exceeds threshold ${threshold}.",
                )
            )
        if not reason:
            audit.findings.append(
                Finding("NO_REASON_CODE", "warning", "Benefit adjustment with no documented reason.")
            )
        if amt < 0 and not r.get("approver"):
            audit.findings.append(
                Finding(
                    "NEGATIVE_WITHOUT_JUSTIFICATION",
                    "critical",
                    f"Negative adjustment ${amt} with no approver on record.",
                )
            )
        if dt and eid:
            term_dt = await reader.get_termination_date(client_id, eid)
            if term_dt and dt > term_dt:
                audit.findings.append(
                    Finding(
                        "ADJUSTMENT_AFTER_TERM",
                        "warning",
                        f"Adjustment dated {dt.isoformat()}, employee termed {term_dt.isoformat()}.",
                    )
                )
        audits.append(audit)

    # REPEATED_EMPLOYEE: 3+ adjustments in window
    for eid, n in counts.items():
        if n >= 3:
            for a in audits:
                if a.employee_id == eid:
                    a.findings.append(
                        Finding(
                            "REPEATED_EMPLOYEE",
                            "warning",
                            f"Employee received {n} adjustments in the window.",
                        )
                    )
                    break

    return AdjustmentTrailReport(
        client_id=client_id,
        window_start=window_start,
        window_end=window_end,
        audits=audits,
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
