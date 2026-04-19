"""Garnishment Payment History — workflow #26.

Per PrismHR's Deductions chapter: garnishments must be withheld
per-paycheck and remitted to the issuing agency on the statutory
schedule. Missed remittances create liability exposure + potential
contempt-of-court penalties.

Findings:
  - NO_PAYMENTS_AT_ALL: garnishment active, never paid.
  - PAYMENT_OVERDUE: last payment older than N days (default 45).
  - BALANCE_INCREASING: balance higher than prior check (e.g.,
    wage ceiling hit, deduction not taking).
  - MULTIPLE_GARNISHMENTS: employee has 2+ active garnishments
    (priority / aggregate-cap check needed).
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


@dataclass
class GarnishmentAudit:
    employee_id: str
    garnishment_id: str
    garnishment_type: str
    active: bool
    balance_outstanding: Decimal
    last_payment_date: date | None
    last_payment_amount: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class GarnishmentHistoryReport:
    client_id: str
    as_of: date
    audits: list[GarnishmentAudit]

    @property
    def total(self) -> int:
        return len(self.audits)

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_garnishment_holders(self, client_id: str) -> list[dict]: ...
    async def get_garnishment_details(self, client_id: str, employee_id: str) -> list[dict]: ...
    async def get_garnishment_payments(self, client_id: str, employee_id: str) -> list[dict]: ...


async def run_garnishment_history_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    overdue_days: int = 45,
) -> GarnishmentHistoryReport:
    today = as_of or date.today()

    holders = await reader.list_garnishment_holders(client_id)

    audits: list[GarnishmentAudit] = []
    for h in holders:
        eid = str(h.get("employeeId") or "")
        if not eid:
            continue
        details = await reader.get_garnishment_details(client_id, eid)
        payments = await reader.get_garnishment_payments(client_id, eid)

        # Group payments by garnishment id for per-garnishment timeline
        pays_by_garn: dict[str, list[dict]] = {}
        for p in payments:
            gid = str(p.get("garnishmentId") or p.get("id") or "")
            if gid:
                pays_by_garn.setdefault(gid, []).append(p)

        for d in details:
            gid = str(d.get("garnishmentId") or d.get("id") or "")
            active = bool(d.get("active", True))
            balance = _dec(d.get("balanceOutstanding") or d.get("balance"))
            gtype = str(d.get("garnishmentType") or d.get("type") or "")

            garn_pays = pays_by_garn.get(gid) or []
            last_pay_date = None
            last_pay_amt = Decimal("0")
            if garn_pays:
                parsed = [(p, _parse(p.get("paymentDate") or p.get("date"))) for p in garn_pays]
                parsed = [(p, d) for (p, d) in parsed if d is not None]
                if parsed:
                    parsed.sort(key=lambda t: t[1], reverse=True)
                    last_pay_date = parsed[0][1]
                    last_pay_amt = _dec(parsed[0][0].get("amount") or parsed[0][0].get("paymentAmount"))

            audit = GarnishmentAudit(
                employee_id=eid,
                garnishment_id=gid,
                garnishment_type=gtype,
                active=active,
                balance_outstanding=balance,
                last_payment_date=last_pay_date,
                last_payment_amount=last_pay_amt,
            )

            if active and balance > Decimal("0"):
                if last_pay_date is None:
                    audit.findings.append(
                        Finding(
                            "NO_PAYMENTS_AT_ALL",
                            "critical",
                            f"Garnishment {gid} active, balance ${balance}, no payments recorded.",
                        )
                    )
                else:
                    days_since = (today - last_pay_date).days
                    if days_since > overdue_days:
                        audit.findings.append(
                            Finding(
                                "PAYMENT_OVERDUE",
                                "critical",
                                f"Last payment {days_since} days ago (threshold {overdue_days}d).",
                            )
                        )
            audits.append(audit)

        # MULTIPLE_GARNISHMENTS marker
        active_count = sum(1 for a in audits if a.employee_id == eid and a.active)
        if active_count >= 2:
            # add an informational finding to the first audit for this employee
            for a in audits:
                if a.employee_id == eid and not any(f.code == "MULTIPLE_GARNISHMENTS" for f in a.findings):
                    a.findings.append(
                        Finding(
                            "MULTIPLE_GARNISHMENTS",
                            "warning",
                            f"{active_count} active garnishments — review priority + CCPA cap.",
                        )
                    )
                    break

    return GarnishmentHistoryReport(client_id=client_id, as_of=today, audits=audits)


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
