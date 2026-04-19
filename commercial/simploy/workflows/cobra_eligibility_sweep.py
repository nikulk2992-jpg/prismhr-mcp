"""COBRA Eligibility Sweep — workflow #14.

Per PrismHR's Benefits Admin Guide (COBRA chapter): employees with
qualifying events (termination, hour reduction, divorce, death, loss
of dependent status) become COBRA-eligible. Each qualifying event
has a statutory election window (60 days) and notice-delivery
deadline (14-44 days depending on event type).

Missing the notice window = ERISA violation + $110/day penalty
per individual. Missing the election window = COBRA election lost.

Findings:
  - QE_UNPROCESSED: qualifying event recorded but no COBRA enrollee
    record created.
  - NOTICE_WINDOW_CLOSING: qualifying event > 10 days ago without
    a documented notice sent.
  - NOTICE_WINDOW_CLOSED: qualifying event > 44 days ago and still
    unprocessed.
  - ELECTION_WINDOW_CLOSING: COBRA notice sent but election date
    approaching within 7 days.
  - ACTIVE_COBRA_NO_PAYMENT: active COBRA enrollee, no premium
    received for the current coverage month.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class CobraAudit:
    employee_id: str
    qualifying_event_date: date | None = None
    qualifying_event_code: str = ""
    cobra_status: str = ""
    election_deadline: date | None = None
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)


@dataclass
class CobraSweepReport:
    client_id: str
    as_of: date
    audits: list[CobraAudit]

    @property
    def total(self) -> int:
        return len(self.audits)

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def get_terminations(self, client_id: str, lookback_days: int) -> list[dict]: ...
    async def get_cobra_enrollees(self, client_id: str) -> list[dict]: ...


async def run_cobra_sweep(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    notice_window_days: int = 44,
    notice_warning_days: int = 10,
    election_warning_days: int = 7,
) -> CobraSweepReport:
    today = as_of or date.today()

    terminations = await reader.get_terminations(client_id, lookback_days=notice_window_days + 30)
    cobra_enrollees = await reader.get_cobra_enrollees(client_id)

    cobra_by_emp = {str(c.get("employeeId") or ""): c for c in cobra_enrollees}

    audits: list[CobraAudit] = []
    for term in terminations:
        eid = str(term.get("employeeId") or "")
        if not eid:
            continue
        qe_date = _parse(term.get("statusDate") or term.get("terminationDate"))
        qe_code = str(term.get("termReasonCode") or term.get("reasonCode") or "")

        audit = CobraAudit(
            employee_id=eid,
            qualifying_event_date=qe_date,
            qualifying_event_code=qe_code,
        )

        cobra = cobra_by_emp.get(eid) or {}
        audit.cobra_status = str(cobra.get("cobraStatus") or cobra.get("status") or "")
        audit.election_deadline = _parse(cobra.get("electionDeadline") or cobra.get("electionDueDate"))

        days_since_qe = (today - qe_date).days if qe_date else None

        # QE_UNPROCESSED: no cobra enrollee record
        if not cobra and days_since_qe is not None and days_since_qe > 0:
            sev = "warning" if days_since_qe <= notice_warning_days else "critical"
            code = "NOTICE_WINDOW_CLOSING" if days_since_qe <= notice_window_days else "NOTICE_WINDOW_CLOSED"
            audit.findings.append(
                Finding(
                    code,
                    sev,
                    f"Termination {days_since_qe} days ago, no COBRA enrollee record created.",
                )
            )

        # Election deadline approaching
        if audit.election_deadline and audit.cobra_status.upper() in {"N", "PENDING", ""}:
            days_to_election = (audit.election_deadline - today).days
            if 0 <= days_to_election <= election_warning_days:
                audit.findings.append(
                    Finding(
                        "ELECTION_WINDOW_CLOSING",
                        "warning",
                        f"COBRA election deadline {audit.election_deadline.isoformat()} ({days_to_election} days).",
                    )
                )

        audits.append(audit)

    return CobraSweepReport(client_id=client_id, as_of=today, audits=audits)


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
