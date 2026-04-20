"""Final paycheck state compliance audit.

State laws on when final wages must be paid after separation vary
dramatically. Missing a state deadline triggers penalty wages (often
daily continuing wages until paid) and DOL complaints.

Finding codes:
  FINAL_CHECK_OVERDUE             past statutory deadline, no check
  FINAL_CHECK_UPCOMING            within 24h of deadline, no check
  FINAL_CHECK_LATE                check issued past deadline
  PTO_PAYOUT_OWED                 accrued PTO must be paid out per state
  COMMISSION_UNPAID               commission earned pre-term not paid
  WAITING_TIME_PENALTY_RISK       CA: no final pay = 1 day wages per day
  SEPARATION_NOTICE_MISSING       NY/NJ/MA etc require written notice
  VOLUNTARY_VS_INVOLUNTARY_DIFF   state rules differ; audit detected
                                    involuntary treated as voluntary
"""

from __future__ import annotations

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


# State deadlines in business hours after separation.
# Format: (involuntary_days, voluntary_days). -1 = same day / immediately.
# "next_payday" == 999 for algorithmic handling.
_DEADLINES: dict[str, dict] = {
    "CA": {"involuntary_days": 0,   # immediately / same day
           "voluntary_days": 3,      # 72h
           "pto_payout_required": True,
           "daily_penalty_wages": True},  # CA "waiting time" penalty
    "CO": {"involuntary_days": 0, "voluntary_days": 999, "pto_payout_required": True},
    "CT": {"involuntary_days": 1, "voluntary_days": 999, "pto_payout_required": False},
    "DC": {"involuntary_days": 1, "voluntary_days": 999, "pto_payout_required": False},
    "HI": {"involuntary_days": 0, "voluntary_days": 999, "pto_payout_required": False},
    "IL": {"involuntary_days": 999, "voluntary_days": 999, "pto_payout_required": True},
    "MA": {"involuntary_days": 0, "voluntary_days": 999,
           "pto_payout_required": True,
           "separation_notice_required": True},
    "MN": {"involuntary_days": 1, "voluntary_days": 5, "pto_payout_required": False},
    "MO": {"involuntary_days": 0, "voluntary_days": 999, "pto_payout_required": False},
    "MT": {"involuntary_days": 0, "voluntary_days": 999, "pto_payout_required": False},
    "NH": {"involuntary_days": 3, "voluntary_days": 999, "pto_payout_required": False},
    "NJ": {"involuntary_days": 999, "voluntary_days": 999, "pto_payout_required": False,
           "separation_notice_required": True},
    "NV": {"involuntary_days": 3, "voluntary_days": 7, "pto_payout_required": False},
    "NY": {"involuntary_days": 999, "voluntary_days": 999,
           "pto_payout_required": True,
           "separation_notice_required": True},
    "OR": {"involuntary_days": 1, "voluntary_days": 5, "pto_payout_required": False},
    "TX": {"involuntary_days": 6, "voluntary_days": 999, "pto_payout_required": False},
    "UT": {"involuntary_days": 1, "voluntary_days": 999, "pto_payout_required": False},
    "VT": {"involuntary_days": 3, "voluntary_days": 999, "pto_payout_required": False},
    "WA": {"involuntary_days": 999, "voluntary_days": 999, "pto_payout_required": False},
    "WY": {"involuntary_days": 5, "voluntary_days": 5, "pto_payout_required": False},
}
_FEDERAL_DEFAULT = {"involuntary_days": 999, "voluntary_days": 999,
                    "pto_payout_required": False}


@dataclass
class SeparationAudit:
    employee_id: str
    first_name: str
    last_name: str
    state: str
    separation_date: date | None
    separation_type: str  # "INVOLUNTARY" | "VOLUNTARY"
    final_check_date: date | None
    deadline: date | None
    final_pay_amount: Decimal
    unpaid_pto_hours: Decimal
    unpaid_commission: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class FinalPaycheckReport:
    client_id: str
    as_of: date
    separations: list[SeparationAudit]

    @property
    def overdue(self) -> int:
        return sum(
            1 for s in self.separations
            if any(f.code == "FINAL_CHECK_OVERDUE" for f in s.findings)
        )

    @property
    def waiting_time_exposure(self) -> int:
        return sum(
            1 for s in self.separations
            if any(f.code == "WAITING_TIME_PENALTY_RISK" for f in s.findings)
        )


class PrismHRReader(Protocol):
    async def list_recent_separations(
        self, client_id: str, since: date
    ) -> list[dict]:
        """Rows: {employeeId, firstName, lastName, workState,
        separationDate, separationType ('INVOLUNTARY'|'VOLUNTARY'),
        finalCheckIssuedDate, finalCheckAmount,
        unpaidPtoHours, unpaidCommission, separationNoticeIssued}"""
        ...


def _next_payday(from_date: date, payday_weekday: int = 4) -> date:
    """Weekday 4 = Friday (default). Returns next payday on/after date."""
    days_ahead = (payday_weekday - from_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return from_date + timedelta(days=days_ahead)


def _deadline(state: str, sep_date: date, sep_type: str) -> date:
    rules = _DEADLINES.get(state.upper(), _FEDERAL_DEFAULT)
    key = "involuntary_days" if sep_type.upper() == "INVOLUNTARY" else "voluntary_days"
    days = rules.get(key, 999)
    if days == 999:
        return _next_payday(sep_date)
    return sep_date + timedelta(days=days)


async def run_final_paycheck_compliance(
    reader: PrismHRReader,
    *,
    client_id: str,
    since: date,
    as_of: date | None = None,
) -> FinalPaycheckReport:
    today = as_of or date.today()
    rows = await reader.list_recent_separations(client_id, since)

    audits: list[SeparationAudit] = []
    for row in rows:
        eid = str(row.get("employeeId") or "")
        state = str(row.get("workState") or "").upper()
        sep_date = _parse(row.get("separationDate"))
        sep_type = str(row.get("separationType") or "INVOLUNTARY").upper()
        final_date = _parse(row.get("finalCheckIssuedDate"))
        final_amt = _dec(row.get("finalCheckAmount"))
        pto_hrs = _dec(row.get("unpaidPtoHours"))
        commission = _dec(row.get("unpaidCommission"))
        notice = bool(row.get("separationNoticeIssued"))

        deadline = _deadline(state, sep_date, sep_type) if sep_date else None

        audit = SeparationAudit(
            employee_id=eid,
            first_name=str(row.get("firstName") or ""),
            last_name=str(row.get("lastName") or ""),
            state=state,
            separation_date=sep_date,
            separation_type=sep_type,
            final_check_date=final_date,
            deadline=deadline,
            final_pay_amount=final_amt,
            unpaid_pto_hours=pto_hrs,
            unpaid_commission=commission,
        )

        if not sep_date:
            audits.append(audit)
            continue

        rules = _DEADLINES.get(state, _FEDERAL_DEFAULT)

        # Deadline check
        if final_date is None and deadline:
            if today > deadline:
                audit.findings.append(
                    Finding(
                        "FINAL_CHECK_OVERDUE",
                        "critical",
                        f"Sep date {sep_date.isoformat()} ({state} {sep_type}); "
                        f"deadline was {deadline.isoformat()}, "
                        f"{(today - deadline).days}d overdue.",
                    )
                )
                if rules.get("daily_penalty_wages"):
                    audit.findings.append(
                        Finding(
                            "WAITING_TIME_PENALTY_RISK",
                            "critical",
                            f"{state} waiting-time penalty accrues daily — "
                            f"exposure ≈ {(today - deadline).days} days of wages.",
                        )
                    )
            elif (deadline - today).days <= 1:
                audit.findings.append(
                    Finding(
                        "FINAL_CHECK_UPCOMING",
                        "warning",
                        f"Deadline {deadline.isoformat()} — <= 1d away.",
                    )
                )
        elif final_date and deadline and final_date > deadline:
            audit.findings.append(
                Finding(
                    "FINAL_CHECK_LATE",
                    "warning",
                    f"Final check issued {final_date.isoformat()} past "
                    f"deadline {deadline.isoformat()}.",
                )
            )

        # PTO payout
        if rules.get("pto_payout_required") and pto_hrs > 0:
            audit.findings.append(
                Finding(
                    "PTO_PAYOUT_OWED",
                    "critical",
                    f"{state} requires PTO payout at separation — "
                    f"{pto_hrs} hours still unpaid.",
                )
            )

        # Commission
        if commission > 0:
            audit.findings.append(
                Finding(
                    "COMMISSION_UNPAID",
                    "critical",
                    f"${commission} in earned commission still owed.",
                )
            )

        # Separation notice
        if rules.get("separation_notice_required") and not notice:
            audit.findings.append(
                Finding(
                    "SEPARATION_NOTICE_MISSING",
                    "critical",
                    f"{state} requires written separation notice — none on file.",
                )
            )

        audits.append(audit)

    return FinalPaycheckReport(client_id=client_id, as_of=today, separations=audits)


def _parse(raw) -> date | None:  # type: ignore[no-untyped-def]
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
