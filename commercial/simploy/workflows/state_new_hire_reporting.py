"""State new-hire reporting audit.

Federal PRWORA (1996) requires every employer to report each new hire
to the state directory of new hires within 20 days of hire (some states
require faster — 10, 14, 15 days — or more frequent — within a day of
ACH issuance).

Each state has its own format: W-4 image, flat file, web portal upload,
or XML via SDNH API. PrismHR tracks hire date + report-sent flag per
employee; this workflow audits the gap.

Findings per employee:
  NOT_REPORTED_OVERDUE     past state deadline, no report sent
  NOT_REPORTED_UPCOMING    deadline within 5 days, no report sent
  MISSING_REQUIRED_FIELD   SSN/DOB/address missing — can't file
  REHIRE_NOT_REPORTED      rehire event (if gap > 60 days, some states
                            require re-reporting)
  REPORTED_LATE            report went out but past deadline
  REPORT_SENT_OK           informational — shows what's been handled

Reference: federal minimum is 20 days; some states are tighter.
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


# State-specific new-hire reporting deadlines in calendar days from
# hire. Defaults to federal 20 if state not listed.
_STATE_DEADLINES = {
    # Tighter-than-federal states
    "AL": 7, "CA": 20, "CT": 20, "DE": 20, "FL": 20,
    "GA": 10, "IA": 15, "IL": 20, "IN": 20, "KS": 20,
    "KY": 20, "LA": 20, "MA": 14, "MD": 20, "ME": 7,
    "MI": 20, "MN": 20, "MO": 20, "MS": 15, "MT": 20,
    "NC": 20, "ND": 20, "NE": 20, "NH": 20, "NJ": 20,
    "NM": 20, "NV": 20, "NY": 20, "OH": 20, "OK": 20,
    "OR": 20, "PA": 20, "RI": 14, "SC": 20, "SD": 20,
    "TN": 20, "TX": 20, "UT": 20, "VA": 20, "VT": 10,
    "WA": 20, "WI": 20, "WV": 14, "WY": 20,
    # No state income tax, but still must report federally — use federal
    "AK": 20, "FL_": 20, "HI": 20, "DC": 20,
    "AZ": 20, "AR": 20, "CO": 20, "ID": 20,
}


_REHIRE_GAP_DAYS = 60


@dataclass
class HireAudit:
    employee_id: str
    first_name: str
    last_name: str
    state: str
    hire_date: date | None
    reported_date: date | None
    deadline: date | None
    is_rehire: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass
class NewHireReport:
    client_id: str
    as_of: date
    hires: list[HireAudit]

    @property
    def total(self) -> int:
        return len(self.hires)

    @property
    def overdue(self) -> int:
        return sum(
            1 for h in self.hires
            if any(f.code == "NOT_REPORTED_OVERDUE" for f in h.findings)
        )

    @property
    def upcoming(self) -> int:
        return sum(
            1 for h in self.hires
            if any(f.code == "NOT_REPORTED_UPCOMING" for f in h.findings)
        )


class PrismHRReader(Protocol):
    async def list_new_hires(
        self, client_id: str, hired_since: date
    ) -> list[dict]:
        """Rows: {employeeId, firstName, lastName, state, hireDate,
        priorTerminationDate, newHireReportSentDate, ssn, dob, address}"""
        ...


def _deadline_for(state: str, hire: date) -> date:
    days = _STATE_DEADLINES.get(state.upper(), 20)
    return hire + timedelta(days=days)


async def run_state_new_hire_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    hired_since: date,
    as_of: date | None = None,
    upcoming_window: int = 5,
) -> NewHireReport:
    today = as_of or date.today()
    rows = await reader.list_new_hires(client_id, hired_since)

    audits: list[HireAudit] = []
    for row in rows:
        eid = str(row.get("employeeId") or "")
        first = str(row.get("firstName") or "")
        last = str(row.get("lastName") or "")
        state = str(row.get("state") or "").upper()
        hire = _parse(row.get("hireDate"))
        reported = _parse(row.get("newHireReportSentDate"))
        prior_term = _parse(row.get("priorTerminationDate"))
        ssn = (row.get("ssn") or "").strip()
        dob = _parse(row.get("dob"))
        addr = row.get("address") or {}
        is_rehire = (
            prior_term is not None
            and hire is not None
            and (hire - prior_term).days >= _REHIRE_GAP_DAYS
        )

        deadline = _deadline_for(state, hire) if hire else None

        audit = HireAudit(
            employee_id=eid,
            first_name=first,
            last_name=last,
            state=state,
            hire_date=hire,
            reported_date=reported,
            deadline=deadline,
            is_rehire=is_rehire,
        )

        # Missing data check
        missing = []
        if not ssn:
            missing.append("SSN")
        if not dob:
            missing.append("DOB")
        if not (addr.get("line1") and addr.get("city")
                and addr.get("state") and addr.get("zip")):
            missing.append("address")
        if missing:
            audit.findings.append(
                Finding(
                    "MISSING_REQUIRED_FIELD",
                    "critical",
                    f"Cannot file new-hire report: missing {', '.join(missing)}.",
                )
            )

        if not hire:
            audits.append(audit)
            continue

        if reported:
            if deadline and reported > deadline:
                audit.findings.append(
                    Finding(
                        "REPORTED_LATE",
                        "warning",
                        f"Report sent {reported.isoformat()} — deadline was "
                        f"{deadline.isoformat()}, {(reported - deadline).days}d late.",
                    )
                )
            else:
                audit.findings.append(
                    Finding(
                        "REPORT_SENT_OK",
                        "info",
                        f"Reported on {reported.isoformat()}.",
                    )
                )
        else:
            if deadline and today > deadline:
                audit.findings.append(
                    Finding(
                        "NOT_REPORTED_OVERDUE",
                        "critical",
                        f"Hired {hire.isoformat()} in {state} "
                        f"({_STATE_DEADLINES.get(state, 20)}d deadline). "
                        f"{(today - deadline).days}d overdue.",
                    )
                )
            elif deadline and (deadline - today).days <= upcoming_window:
                audit.findings.append(
                    Finding(
                        "NOT_REPORTED_UPCOMING",
                        "warning",
                        f"Report due {deadline.isoformat()} "
                        f"({(deadline - today).days}d).",
                    )
                )

        if is_rehire:
            audit.findings.append(
                Finding(
                    "REHIRE_NOT_REPORTED",
                    "warning" if reported else "critical",
                    f"Rehire event ({(hire - prior_term).days}d gap since "
                    f"prior term on {prior_term.isoformat()}); most states "
                    f"require re-reporting.",
                )
            )

        audits.append(audit)

    return NewHireReport(client_id=client_id, as_of=today, hires=audits)


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
