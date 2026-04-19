"""Overtime Anomaly Detection — workflow #8.

FLSA violations hide in routine payroll: non-exempt employees with
unreported overtime, exempt employees logging OT hours (category
error), or sudden OT spikes that signal scheduling errors.

Findings:
  - EXEMPT_WITH_OT: salaried-exempt employee has OT hours logged.
  - NON_EXEMPT_NO_OT_BUT_OVER_40: non-exempt worked > 40h but no OT
    hours recorded.
  - OT_SPIKE: OT hours in this period > 2× the employee's 90-day
    average — scheduling / data-entry anomaly.
  - UNAPPROVED_OT: OT logged without approver on record.
"""

from __future__ import annotations

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
class OvertimeAudit:
    employee_id: str
    flsa_status: str  # "EXEMPT" | "NON_EXEMPT"
    regular_hours: Decimal
    ot_hours: Decimal
    avg_ot_last_90d: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class OvertimeAnomalyReport:
    client_id: str
    period_end: date
    audits: list[OvertimeAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_employee_hours_for_period(
        self, client_id: str, period_end: date
    ) -> list[dict]: ...
    async def avg_ot_last_90d(
        self, client_id: str, employee_id: str, as_of: date
    ) -> Decimal: ...


async def run_overtime_anomaly(
    reader: PrismHRReader,
    *,
    client_id: str,
    period_end: date,
    spike_multiplier: Decimal | str = "2.0",
) -> OvertimeAnomalyReport:
    multiplier = Decimal(str(spike_multiplier))
    rows = await reader.list_employee_hours_for_period(client_id, period_end)

    audits: list[OvertimeAudit] = []
    for r in rows:
        eid = str(r.get("employeeId") or "")
        flsa = str(r.get("flsaStatus") or "").upper()
        reg = _dec(r.get("regularHours"))
        ot = _dec(r.get("otHours"))
        approver = str(r.get("otApprover") or "").strip()

        avg = await reader.avg_ot_last_90d(client_id, eid, period_end) if eid else Decimal("0")
        audit = OvertimeAudit(
            employee_id=eid,
            flsa_status=flsa,
            regular_hours=reg,
            ot_hours=ot,
            avg_ot_last_90d=avg,
        )

        if flsa == "EXEMPT" and ot > 0:
            audit.findings.append(
                Finding(
                    "EXEMPT_WITH_OT",
                    "warning",
                    f"Exempt employee has {ot}h OT logged — verify FLSA classification.",
                )
            )
        if flsa == "NON_EXEMPT" and reg > 40 and ot == 0:
            audit.findings.append(
                Finding(
                    "NON_EXEMPT_NO_OT_BUT_OVER_40",
                    "critical",
                    f"Non-exempt employee worked {reg}h regular — should have {reg - 40}h OT.",
                )
            )
        if ot > 0 and avg > 0 and ot > avg * multiplier:
            audit.findings.append(
                Finding(
                    "OT_SPIKE",
                    "warning",
                    f"OT {ot}h this period; 90d avg {avg}h ({multiplier}× threshold).",
                )
            )
        if ot > 0 and not approver:
            audit.findings.append(
                Finding(
                    "UNAPPROVED_OT",
                    "warning",
                    f"{ot}h OT logged with no approver.",
                )
            )
        audits.append(audit)

    return OvertimeAnomalyReport(
        client_id=client_id, period_end=period_end, audits=audits
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
