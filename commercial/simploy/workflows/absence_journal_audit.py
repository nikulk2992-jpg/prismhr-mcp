"""Absence Journal Audit — workflow #46.

PrismHR logs every absence (PTO, sick, FMLA, jury duty, etc.) into
an absence journal tied to a pay code. Every journal entry must
eventually roll into a paid voucher or an unpaid-absence record; a
stale entry means the employee took time off that neither got paid
nor reduced their balance, usually a setup bug.

Findings:
  - ORPHAN_ENTRY: absence journaled but no matching voucher or
    balance draw.
  - ENTRY_BALANCE_MISMATCH: hours journaled != hours deducted from
    the employee's PTO balance.
  - NEGATIVE_JOURNAL_ENTRY: credit journaled without a paired
    approver.
  - CONCURRENT_OVERLAPPING: two absence entries for the same
    employee overlap on the same day (PTO + sick both logged).
"""

from __future__ import annotations

from collections import defaultdict
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
class AbsenceEntryAudit:
    journal_id: str
    employee_id: str
    entry_date: date | None
    hours: Decimal
    absence_code: str
    voucher_hours_paid: Decimal
    balance_delta: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class AbsenceJournalReport:
    client_id: str
    window_start: date
    window_end: date
    audits: list[AbsenceEntryAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_absence_journal(
        self, client_id: str, start: date, end: date
    ) -> list[dict]: ...


async def run_absence_journal_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    window_start: date,
    window_end: date,
    tolerance: Decimal | str = "0.25",
) -> AbsenceJournalReport:
    tol = Decimal(str(tolerance))

    rows = await reader.list_absence_journal(client_id, window_start, window_end)

    by_emp_day: dict[tuple[str, date], list[dict]] = defaultdict(list)
    audits: list[AbsenceEntryAudit] = []
    for r in rows:
        jid = str(r.get("journalId") or r.get("id") or "")
        eid = str(r.get("employeeId") or "")
        dt = _parse(r.get("entryDate") or r.get("absenceDate"))
        hours = _dec(r.get("hours"))
        code = str(r.get("absenceCode") or r.get("code") or "")
        paid = _dec(r.get("voucherHoursPaid"))
        balance_delta = _dec(r.get("balanceDelta"))

        audit = AbsenceEntryAudit(
            journal_id=jid,
            employee_id=eid,
            entry_date=dt,
            hours=hours,
            absence_code=code,
            voucher_hours_paid=paid,
            balance_delta=balance_delta,
        )

        if hours > 0 and paid == 0 and balance_delta == 0:
            audit.findings.append(
                Finding(
                    "ORPHAN_ENTRY",
                    "critical",
                    f"{hours}h journaled on {dt.isoformat() if dt else '?'} — no voucher and no balance draw.",
                )
            )

        if hours > 0 and balance_delta != 0:
            if (hours - balance_delta.copy_abs()).copy_abs() > tol:
                audit.findings.append(
                    Finding(
                        "ENTRY_BALANCE_MISMATCH",
                        "warning",
                        f"Journaled {hours}h, balance dropped {balance_delta}.",
                    )
                )

        if hours < 0 and not r.get("approver"):
            audit.findings.append(
                Finding(
                    "NEGATIVE_JOURNAL_ENTRY",
                    "critical",
                    f"Credit entry ({hours}h) with no approver.",
                )
            )

        if dt:
            by_emp_day[(eid, dt)].append(r)
        audits.append(audit)

    for (eid, day), entries in by_emp_day.items():
        if len(entries) > 1:
            for a in audits:
                if a.employee_id == eid and a.entry_date == day:
                    a.findings.append(
                        Finding(
                            "CONCURRENT_OVERLAPPING",
                            "warning",
                            f"{len(entries)} overlapping absence entries on {day.isoformat()}.",
                        )
                    )

    return AbsenceJournalReport(
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
