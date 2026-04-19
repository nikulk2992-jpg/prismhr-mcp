"""State Filings Orchestrator — workflow #59.

Meta-workflow. For a given client + year + quarter, checks filing
readiness + submission status for every state the client operates in.

Each state has its own:
- form name (CA: DE 9, NY: NYS-45, TX: C-3, etc.)
- due date (typically last day of month after quarter end)
- filing method (e-file required in some states, paper allowed elsewhere)
- employer-of-record requirement (for PEO co-employment)

This workflow doesn't generate the forms — it gives the ops team a
unified status dashboard across all states.

Findings per state:
  - READY_TO_FILE: wages posted + reconciled; form can be generated.
  - FILING_OVERDUE: past due date, not filed.
  - FILING_DUE_URGENT: < 7 days to due date.
  - FILING_DUE_SOON: < 30 days to due date.
  - ALREADY_FILED: filing confirmation on file (informational).
  - RECONCILIATION_BLOCKED: state withholding / SUTA reconciliation
    has open critical findings — block the file.
  - NO_WAGES: state shown on client config but no wages this period.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol


Severity = str


# Standard due dates (last day of month after quarter close). Override
# per jurisdiction if needed.
_QUARTER_END = {1: date(2000, 3, 31), 2: date(2000, 6, 30), 3: date(2000, 9, 30), 4: date(2000, 12, 31)}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class StateFilingStatus:
    state: str
    form_name: str
    has_wages: bool
    due_date: date
    already_filed: bool
    filing_reference: str
    recon_issues: int
    findings: list[Finding] = field(default_factory=list)


@dataclass
class StateFilingsReport:
    client_id: str
    year: int
    quarter: int
    as_of: date
    states: list[StateFilingStatus]

    @property
    def overdue(self) -> int:
        return sum(1 for s in self.states if any(f.code == "FILING_OVERDUE" for f in s.findings))

    @property
    def urgent(self) -> int:
        return sum(1 for s in self.states if any(f.code == "FILING_DUE_URGENT" for f in s.findings))


class PrismHRReader(Protocol):
    async def list_employer_states(
        self, client_id: str, year: int, quarter: int
    ) -> list[dict]: ...
    async def get_filing_status(
        self, client_id: str, state: str, year: int, quarter: int
    ) -> dict: ...
    async def get_state_recon_findings(
        self, client_id: str, state: str, year: int, quarter: int
    ) -> int:
        """Returns count of OPEN critical findings from the state withholding recon."""
        ...


# Form names per state — common ones. Lookups not covered default to
# generic "Quarterly Withholding Return" and "Quarterly UI Return".
STATE_FORMS: dict[str, str] = {
    "CA": "DE 9",
    "NY": "NYS-45",
    "TX": "C-3",
    "FL": "RT-6",
    "IL": "UI-3/40",
    "PA": "UC-2",
    "OH": "JFS-20125",
    "GA": "DOL-4N",
    "NC": "NCUI-101",
    "VA": "VEC-FC-20",
    "AZ": "UC-018",
    "WA": "EMS 5208",
    "MA": "WR-1",
    "MI": "UIA 1028",
    "NJ": "NJ-927",
    "MO": "MODES-4-7",
    "NE": "UI-11T",
    "CO": "UITR-1",
    "IN": "UC-1",
    "MN": "MW-5",
}


def _quarter_due_date(year: int, quarter: int) -> date:
    """Default due date = last day of the month following quarter end."""
    qend = _QUARTER_END[quarter].replace(year=year)
    next_month = qend.month + 1 if qend.month < 12 else 1
    next_year = year if qend.month < 12 else year + 1
    # Last day of next_month
    if next_month == 12:
        return date(next_year, 12, 31)
    return date(next_year, next_month + 1, 1) - timedelta(days=1)


async def run_state_filings_orchestrator(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    quarter: int,
    as_of: date | None = None,
    urgent_days: int = 7,
    soon_days: int = 30,
) -> StateFilingsReport:
    today = as_of or date.today()
    employer_states = await reader.list_employer_states(client_id, year, quarter)

    statuses: list[StateFilingStatus] = []
    for row in employer_states:
        state = str(row.get("state") or "").upper()
        if not state:
            continue
        has_wages = bool(row.get("hasWages", True))
        due = _parse(row.get("dueDate")) or _quarter_due_date(year, quarter)
        filing = await reader.get_filing_status(client_id, state, year, quarter)
        filed = bool(filing.get("filed") or filing.get("submissionConfirmation"))
        ref = str(filing.get("submissionConfirmation") or filing.get("reference") or "")
        recon_issues = await reader.get_state_recon_findings(client_id, state, year, quarter)

        audit = StateFilingStatus(
            state=state,
            form_name=STATE_FORMS.get(state, "Quarterly Withholding/UI Return"),
            has_wages=has_wages,
            due_date=due,
            already_filed=filed,
            filing_reference=ref,
            recon_issues=recon_issues,
        )

        if not has_wages:
            audit.findings.append(
                Finding("NO_WAGES", "info", f"{state}: no wages this period — may not need to file.")
            )
        elif filed:
            audit.findings.append(
                Finding("ALREADY_FILED", "info", f"{state} filed: {ref or 'confirmation on file'}.")
            )
        else:
            days_to_due = (due - today).days
            if days_to_due < 0:
                audit.findings.append(
                    Finding(
                        "FILING_OVERDUE",
                        "critical",
                        f"{state}: {abs(days_to_due)}d overdue (due {due.isoformat()}).",
                    )
                )
            elif days_to_due <= urgent_days:
                audit.findings.append(
                    Finding(
                        "FILING_DUE_URGENT",
                        "critical",
                        f"{state}: {days_to_due}d to due date ({due.isoformat()}).",
                    )
                )
            elif days_to_due <= soon_days:
                audit.findings.append(
                    Finding(
                        "FILING_DUE_SOON",
                        "warning",
                        f"{state}: {days_to_due}d to due date.",
                    )
                )

            if recon_issues > 0:
                audit.findings.append(
                    Finding(
                        "RECONCILIATION_BLOCKED",
                        "critical",
                        f"{state}: {recon_issues} open reconciliation finding(s) — block file until resolved.",
                    )
                )
            else:
                audit.findings.append(
                    Finding(
                        "READY_TO_FILE",
                        "info",
                        f"{state}: reconciled, clear to generate {audit.form_name}.",
                    )
                )
        statuses.append(audit)

    return StateFilingsReport(
        client_id=client_id,
        year=year,
        quarter=quarter,
        as_of=today,
        states=statuses,
    )


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
