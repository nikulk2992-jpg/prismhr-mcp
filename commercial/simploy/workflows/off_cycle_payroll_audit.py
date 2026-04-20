"""Off-cycle payroll audit — bonus runs, termination runs, manual checks.

Off-cycle vouchers (type = M manual, B bonus, C correction, F final
termination) have different approval + tax + audit paths than regular
payroll. This workflow sweeps them as a cohort and flags anomalies.

Finding codes:
  NO_APPROVER             off-cycle voucher with no approval record
  UNUSUAL_AMOUNT          amount > 5x employee's average regular check
  TAX_METHOD_MISSING      supplemental wages with no withholding method
                          declared (flat 22% or aggregate)
  MULTIPLE_BONUS_RUNS     same employee has 3+ bonus checks in 30 days
                          (usually a correction loop)
  TERMINATION_NO_FINAL    term date logged but no F-type voucher
  MANUAL_NO_REASON        manual check issued without reason/note
  PRE_DATED_VOUCHER       voucher issued with pay date in the past
                          beyond a 7-day grace
  POST_DATED_FUTURE       voucher pay date > 14 days in future
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
class VoucherAudit:
    voucher_id: str
    employee_id: str
    voucher_type: str
    pay_date: date | None
    amount: Decimal
    approver: str
    findings: list[Finding] = field(default_factory=list)


@dataclass
class OffCycleReport:
    client_id: str
    period_start: date
    period_end: date
    as_of: date
    vouchers: list[VoucherAudit]

    @property
    def total(self) -> int:
        return len(self.vouchers)

    @property
    def flagged(self) -> int:
        return sum(1 for v in self.vouchers if v.findings)


class PrismHRReader(Protocol):
    async def list_off_cycle_vouchers(
        self, client_id: str, period_start: date, period_end: date
    ) -> list[dict]:
        """Rows: {voucherId, employeeId, type, payDate, totalEarnings,
        approver, reason, supplementalTaxMethod, terminationDate}"""
        ...

    async def get_employee_avg_regular_check(
        self, client_id: str, employee_id: str
    ) -> str | Decimal:
        """Avg net of recent R-type vouchers for baseline comparison."""
        ...


async def run_off_cycle_payroll_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    period_start: date,
    period_end: date,
    as_of: date | None = None,
    unusual_multiple: Decimal | str = "5",
    bonus_loop_threshold: int = 3,
    grace_days_past: int = 7,
    grace_days_future: int = 14,
) -> OffCycleReport:
    today = as_of or date.today()
    threshold = Decimal(str(unusual_multiple))

    rows = await reader.list_off_cycle_vouchers(
        client_id, period_start, period_end
    )

    bonus_counts: dict[str, list[date]] = defaultdict(list)
    term_vouchers_by_emp: dict[str, list[dict]] = defaultdict(list)

    audits: list[VoucherAudit] = []
    for row in rows:
        vid = str(row.get("voucherId") or "")
        eid = str(row.get("employeeId") or "")
        vtype = str(row.get("type") or "").upper()
        pay_date = _parse(row.get("payDate"))
        amount = _dec(row.get("totalEarnings"))
        approver = str(row.get("approver") or "")
        reason = str(row.get("reason") or "").strip()
        supp_method = str(row.get("supplementalTaxMethod") or "").upper()
        term_date = _parse(row.get("terminationDate"))

        audit = VoucherAudit(
            voucher_id=vid,
            employee_id=eid,
            voucher_type=vtype,
            pay_date=pay_date,
            amount=amount,
            approver=approver,
        )

        # Approver present?
        if not approver:
            audit.findings.append(
                Finding(
                    "NO_APPROVER",
                    "critical",
                    f"Off-cycle voucher {vid} ({vtype}) has no approver on record.",
                )
            )

        # Amount sanity
        if eid:
            try:
                avg = _dec(await reader.get_employee_avg_regular_check(client_id, eid))
            except Exception:  # noqa: BLE001
                avg = Decimal("0")
            if avg > 0 and amount > avg * threshold:
                audit.findings.append(
                    Finding(
                        "UNUSUAL_AMOUNT",
                        "warning",
                        f"${amount} is {amount / avg:.1f}x the employee's "
                        f"average regular check (${avg}).",
                    )
                )

        # Bonus-run supplemental tax method
        if vtype == "B" and not supp_method:
            audit.findings.append(
                Finding(
                    "TAX_METHOD_MISSING",
                    "critical",
                    f"Bonus voucher {vid} missing supplemental tax method "
                    f"(FLAT_22 or AGGREGATE).",
                )
            )

        # Manual check reason
        if vtype == "M" and not reason:
            audit.findings.append(
                Finding(
                    "MANUAL_NO_REASON",
                    "warning",
                    f"Manual check {vid} issued without note/reason.",
                )
            )

        # Pay date sanity
        if pay_date:
            if pay_date < today - timedelta(days=grace_days_past):
                audit.findings.append(
                    Finding(
                        "PRE_DATED_VOUCHER",
                        "warning",
                        f"Voucher pay date {pay_date.isoformat()} > "
                        f"{grace_days_past}d in the past.",
                    )
                )
            elif pay_date > today + timedelta(days=grace_days_future):
                audit.findings.append(
                    Finding(
                        "POST_DATED_FUTURE",
                        "warning",
                        f"Voucher pay date {pay_date.isoformat()} > "
                        f"{grace_days_future}d in the future.",
                    )
                )

        # Track for cohort checks
        if vtype == "B" and pay_date:
            bonus_counts[eid].append(pay_date)
        if vtype == "F":
            term_vouchers_by_emp[eid].append(row)
        elif term_date and vtype != "F":
            # Employee terminated but no F-type voucher
            existing_F = any(
                str(r.get("type") or "").upper() == "F"
                for r in rows
                if str(r.get("employeeId") or "") == eid
            )
            if not existing_F:
                audit.findings.append(
                    Finding(
                        "TERMINATION_NO_FINAL",
                        "critical",
                        f"Termination date {term_date.isoformat()} on "
                        f"record but no F-type final voucher found.",
                    )
                )

        audits.append(audit)

    # Cohort: bonus loop
    for eid, dates in bonus_counts.items():
        if len(dates) >= bonus_loop_threshold:
            span = (max(dates) - min(dates)).days
            if span <= 30:
                for a in audits:
                    if a.employee_id == eid and a.voucher_type == "B":
                        a.findings.append(
                            Finding(
                                "MULTIPLE_BONUS_RUNS",
                                "warning",
                                f"Employee {eid} has {len(dates)} bonus "
                                f"vouchers within {span}d — correction loop?",
                            )
                        )
                        break

    return OffCycleReport(
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        as_of=today,
        vouchers=audits,
    )


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
