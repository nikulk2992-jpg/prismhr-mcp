"""Multi-state reciprocal withholding audit.

Employees who live in one state and work in another have complex
withholding rules. Some state pairs have full reciprocity (certify
once, employer withholds home-state only); some partial; most none.

Common cases:
  NY/NJ, NJ/PA       partial — NJ and PA have reciprocity; NY/NJ does not
  OH/KY              full reciprocity
  OH/PA              full reciprocity
  OH/MI              full reciprocity
  IL/IN              full reciprocity
  IL/IA              full reciprocity
  IL/KY              full reciprocity
  IL/MI              full reciprocity
  IL/WI              full reciprocity
  IN/KY              full reciprocity
  IN/MI              full reciprocity
  IN/OH              full reciprocity
  IN/PA              full reciprocity
  IN/WI              full reciprocity
  KY/MI              full reciprocity
  KY/OH              full reciprocity
  KY/VA              full reciprocity
  KY/WV              full reciprocity
  KY/WI              full reciprocity
  MD/DC              full reciprocity
  MD/PA              full reciprocity
  MD/VA              full reciprocity
  MD/WV              full reciprocity
  MI/WI              full reciprocity
  MN/ND              full reciprocity
  MN/MI              partial (military only)
  ND/MT              full reciprocity
  PA/VA              full reciprocity
  PA/WV              full reciprocity
  VA/DC              full reciprocity
  VA/KY              full reciprocity
  VA/MD              full reciprocity
  VA/PA              full reciprocity
  VA/WV              full reciprocity
  WV/KY              full reciprocity
  WV/MD              full reciprocity
  WV/OH              full reciprocity
  WV/PA              full reciprocity
  WV/VA              full reciprocity
  WI/IL              full reciprocity
  WI/IN              full reciprocity
  WI/KY              full reciprocity
  WI/MI              full reciprocity

Each reciprocity requires the employee to file a certificate with the
work-state employer (e.g. OH form IT-4NR, PA form REV-419, KY form
42A809).

Findings:
  WRONG_STATE_WITHHELD   work state withheld when reciprocity applies
  NO_HOME_STATE_WITHHELD reciprocity applies but home state had nothing
                          withheld (employee owes underpayment at filing)
  MISSING_RECIPROCITY_CERT  reciprocal pair but no cert on file
  BOTH_STATES_WITHHELD   both home and work withheld (over-withholding;
                          employee gets refund but mid-year cash squeeze)
  NON_RECIPROCAL_NO_CERT_NEEDED  OK — no reciprocity, expected behavior
  MULTI_STATE_NO_ALLOCATION  > 1 work state but no percentage allocation
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


# Full reciprocity pairs (bidirectional). Source: state DOR circulars
# as of 2026. Maintain as a set of sorted tuples for O(1) lookup.
_FULL_RECIPROCITY: frozenset[tuple[str, str]] = frozenset(
    tuple(sorted(p))
    for p in [
        ("OH", "KY"), ("OH", "PA"), ("OH", "MI"),
        ("IL", "IN"), ("IL", "IA"), ("IL", "KY"), ("IL", "MI"), ("IL", "WI"),
        ("IN", "KY"), ("IN", "MI"), ("IN", "OH"), ("IN", "PA"), ("IN", "WI"),
        ("KY", "MI"), ("KY", "VA"), ("KY", "WV"), ("KY", "WI"),
        ("MD", "DC"), ("MD", "PA"), ("MD", "VA"), ("MD", "WV"),
        ("MI", "WI"),
        ("MN", "ND"),
        ("ND", "MT"),
        ("NJ", "PA"),
        ("PA", "VA"), ("PA", "WV"),
        ("VA", "DC"), ("VA", "WV"),
        ("WV", "OH"),
    ]
)


def is_reciprocal(state_a: str, state_b: str) -> bool:
    if not state_a or not state_b:
        return False
    return tuple(sorted([state_a.upper(), state_b.upper()])) in _FULL_RECIPROCITY


@dataclass
class EmployeeAudit:
    employee_id: str
    home_state: str
    work_states: list[str]
    home_withheld: Decimal
    work_withholding_by_state: dict[str, Decimal]
    certs_on_file: list[str]
    findings: list[Finding] = field(default_factory=list)

    @property
    def reciprocal(self) -> bool:
        return any(
            is_reciprocal(self.home_state, ws) for ws in self.work_states
        )


@dataclass
class ReciprocalReport:
    client_id: str
    period_start: date
    period_end: date
    as_of: date
    employees: list[EmployeeAudit]

    @property
    def total(self) -> int:
        return len(self.employees)

    @property
    def flagged(self) -> int:
        return sum(1 for e in self.employees if e.findings)


class PrismHRReader(Protocol):
    async def list_multistate_employees(
        self, client_id: str, period_start: date, period_end: date
    ) -> list[dict]:
        """Rows: {employeeId, homeState, workStates: [state, ...],
        homeStateWithholding, workStateWithholding: {state: amount},
        reciprocalCertsOnFile: [cert codes], allocationPct: {state: pct}}"""
        ...


async def run_reciprocal_withholding_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    period_start: date,
    period_end: date,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
) -> ReciprocalReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))
    rows = await reader.list_multistate_employees(
        client_id, period_start, period_end
    )

    audits: list[EmployeeAudit] = []
    for row in rows:
        eid = str(row.get("employeeId") or "")
        home = str(row.get("homeState") or "").upper()
        work_states = [str(s).upper() for s in (row.get("workStates") or [])]
        home_wh = _dec(row.get("homeStateWithholding"))
        work_wh_raw = row.get("workStateWithholding") or {}
        work_wh = {str(k).upper(): _dec(v) for k, v in work_wh_raw.items()}
        certs = [str(c).upper() for c in (row.get("reciprocalCertsOnFile") or [])]
        alloc = row.get("allocationPct") or {}

        audit = EmployeeAudit(
            employee_id=eid,
            home_state=home,
            work_states=work_states,
            home_withheld=home_wh,
            work_withholding_by_state=work_wh,
            certs_on_file=certs,
        )

        if not home or not work_states:
            audits.append(audit)
            continue

        # Multi-state allocation sanity
        if len(work_states) > 1 and not alloc:
            audit.findings.append(
                Finding(
                    "MULTI_STATE_NO_ALLOCATION",
                    "warning",
                    f"Employee {eid} has {len(work_states)} work states "
                    f"({', '.join(work_states)}) but no allocation percentages on file.",
                )
            )

        # Reciprocity rules per work state
        for ws in work_states:
            if ws == home:
                continue
            if is_reciprocal(home, ws):
                ws_wh = work_wh.get(ws, Decimal("0"))
                if ws_wh > tol:
                    audit.findings.append(
                        Finding(
                            "WRONG_STATE_WITHHELD",
                            "critical",
                            f"Employee {eid} lives {home} works {ws} "
                            f"(reciprocal pair). Work state withheld "
                            f"${ws_wh} but should withhold only home state.",
                        )
                    )
                if home_wh <= tol:
                    audit.findings.append(
                        Finding(
                            "NO_HOME_STATE_WITHHELD",
                            "critical",
                            f"Employee {eid}: reciprocity {home}/{ws} applies "
                            f"but home state ({home}) withheld only ${home_wh}. "
                            f"Employee will owe at filing.",
                        )
                    )
                if ws_wh > tol and home_wh > tol:
                    audit.findings.append(
                        Finding(
                            "BOTH_STATES_WITHHELD",
                            "warning",
                            f"Employee {eid}: both {home} (${home_wh}) and "
                            f"{ws} (${ws_wh}) withheld. Reciprocity fix "
                            f"mid-year won't retroactively unwithhold.",
                        )
                    )
                # Cert on file?
                if not any(_cert_matches(c, home, ws) for c in certs):
                    audit.findings.append(
                        Finding(
                            "MISSING_RECIPROCITY_CERT",
                            "critical",
                            f"Employee {eid}: reciprocity {home}/{ws} but "
                            f"no cert on file (expect IT-4NR / REV-419 / "
                            f"42A809 / WH-47 etc. per state pair).",
                        )
                    )
            else:
                # Non-reciprocal: work state should withhold, home may too
                # (employee takes credit on home return). No alert needed.
                audit.findings.append(
                    Finding(
                        "NON_RECIPROCAL_NO_CERT_NEEDED",
                        "info",
                        f"Employee {eid}: {home}/{ws} is not a reciprocal "
                        f"pair; work-state withholding is expected.",
                    )
                )

        audits.append(audit)

    return ReciprocalReport(
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        as_of=today,
        employees=audits,
    )


def _cert_matches(cert_code: str, home: str, work: str) -> bool:
    cc = cert_code.upper()
    # Loose match: cert codes usually contain the state pair or form id.
    for s in (home, work):
        if s in cc:
            return True
    known = {"IT-4NR", "REV-419", "42A809", "WH-47", "IT-140NRS", "MW-507",
             "VA-4", "W-220", "D-4A", "NDW-R", "MWR", "44-016"}
    return cc in known


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
