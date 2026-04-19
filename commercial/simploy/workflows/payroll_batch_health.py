"""Payroll Batch Health Check — workflow #2.

Sweeps open payroll batches at a client and flags:
  - batches stuck in INIT status past the freshness window
  - batches stuck in AP.PEND (awaiting approval) past the freshness window
  - batches with zero vouchers attached
  - batches whose pay date is past but status is not POSTCOMP/COMP
  - batches with any voucher carrying a negative net pay
  - INIT batches with an approval summary ready to review

Input: client_id, optional max_days_in_init, max_days_awaiting_approval.
Output: structured per-batch findings with severity + remediation hint.

Data sources (all verified reads against the OSS core's catalog):
  - payroll.v1.getBatchListForApproval       (AP.PEND batches)
  - payroll.v1.getBatchListForInitialization (INIT/TS.READY batches)
  - payroll.v1.getBatchStatus                (status for a batch)
  - payroll.v1.getBatchInfo                  (pay date, period, client)
  - payroll.v1.getPayrollVoucherForBatch     (vouchers inside a batch)
  - payroll.v1.getApprovalSummary            (INIT-only; totals)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol


Severity = str  # "critical" | "warning" | "info"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class BatchAudit:
    batch_id: str
    status: str
    status_description: str
    pay_date: date | None
    period_end: date | None
    voucher_count: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)


@dataclass
class PayrollBatchHealthReport:
    client_id: str
    as_of: date
    batches: list[BatchAudit]

    @property
    def total(self) -> int:
        return len(self.batches)

    @property
    def clean(self) -> int:
        return sum(1 for b in self.batches if b.passed and not b.findings)

    @property
    def flagged(self) -> int:
        return sum(1 for b in self.batches if b.findings)


class PrismHRReader(Protocol):
    """Minimal read surface for this workflow."""

    async def list_open_batches(self, client_id: str) -> list[dict]: ...
    async def get_batch_status(self, client_id: str, batch_id: str) -> dict: ...
    async def get_batch_info(self, client_id: str, batch_id: str) -> dict: ...
    async def get_batch_vouchers(self, client_id: str, batch_id: str) -> list[dict]: ...
    async def get_approval_summary(self, client_id: str, batch_id: str) -> dict: ...


# Status code families from PrismHR's batch-status taxonomy (see
# getBatchStatus docs). Used for state-machine decisions below.
_INIT_STATES: frozenset[str] = frozenset({"INITIAL", "INITOK", "INITWARN", "INITFAIL", "INITCOMP"})
_AWAITING_APPROVAL_STATES: frozenset[str] = frozenset({"AP.PEND"})
_POSTED_STATES: frozenset[str] = frozenset({"POSTCOMP", "COMP", "PRINTCOMP"})


async def run_payroll_batch_health(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    max_days_in_init: int = 3,
    max_days_awaiting_approval: int = 1,
) -> PayrollBatchHealthReport:
    """Run the batch-health sweep for a client and return a report.

    Pure orchestration — all PrismHR I/O goes through `reader`. Unit
    tests exercise logic with an in-memory fake.
    """
    today = as_of or date.today()
    open_batches = await reader.list_open_batches(client_id)

    audits: list[BatchAudit] = []
    for b in open_batches:
        bid = str(b.get("batchId") or b.get("id") or "")
        if not bid:
            continue

        status_block = await reader.get_batch_status(client_id, bid)
        status = (status_block.get("status") or b.get("status") or "").upper()
        status_desc = status_block.get("statusDescription") or b.get("statusDescription") or ""

        info = await reader.get_batch_info(client_id, bid)
        pay_date = _parse_iso_prefix(info.get("payDate") or b.get("payDate"))
        period_end = _parse_iso_prefix(info.get("periodEnd") or b.get("periodEnd"))

        vouchers = await reader.get_batch_vouchers(client_id, bid)
        voucher_count = len(vouchers)

        audit = BatchAudit(
            batch_id=bid,
            status=status,
            status_description=status_desc,
            pay_date=pay_date,
            period_end=period_end,
            voucher_count=voucher_count,
        )

        # --- Finding rules ---

        # Stale INIT
        if status in _INIT_STATES and period_end:
            days_since = (today - period_end).days
            if days_since > max_days_in_init:
                audit.findings.append(
                    Finding(
                        "STALE_IN_INIT",
                        "warning",
                        f"Batch in {status} for {days_since} days (period ended {period_end.isoformat()}).",
                    )
                )

        # Stuck in approval
        if status in _AWAITING_APPROVAL_STATES and period_end:
            days_since = (today - period_end).days
            if days_since > max_days_awaiting_approval:
                audit.findings.append(
                    Finding(
                        "STUCK_APPROVAL",
                        "critical",
                        f"Batch AP.PEND for {days_since} days awaiting approval.",
                    )
                )

        # Zero vouchers
        if voucher_count == 0 and status not in _INIT_STATES:
            # INIT batches may legitimately have zero vouchers before calc;
            # only flag post-INIT zero-voucher batches.
            audit.findings.append(
                Finding(
                    "ZERO_VOUCHERS",
                    "critical",
                    "Batch has no vouchers attached.",
                )
            )

        # Pay date past but not posted
        if pay_date and pay_date < today and status not in _POSTED_STATES:
            days_past = (today - pay_date).days
            audit.findings.append(
                Finding(
                    "PAYDATE_PAST",
                    "critical",
                    f"Pay date was {pay_date.isoformat()} ({days_past} days ago); batch status is {status}.",
                )
            )

        # Negative nets
        for v in vouchers:
            net_raw = v.get("netPay") if isinstance(v, dict) else None
            try:
                if net_raw is not None and float(net_raw) < 0:
                    eid = (v.get("employeeId") if isinstance(v, dict) else "") or "unknown"
                    audit.findings.append(
                        Finding(
                            "NEGATIVE_NET",
                            "critical",
                            f"Employee {eid} has net pay {net_raw}.",
                        )
                    )
                    break  # one flag per batch is enough
            except (TypeError, ValueError):
                continue

        # INIT summary ready
        if status in _INIT_STATES and status != "INITIAL":
            summary = await reader.get_approval_summary(client_id, bid)
            if summary.get("approvalStatus") or summary.get("total"):
                audit.findings.append(
                    Finding(
                        "APPROVAL_SUMMARY_READY",
                        "info",
                        f"Approval summary available (status={summary.get('approvalStatus') or 'n/a'}).",
                    )
                )

        audits.append(audit)

    return PayrollBatchHealthReport(client_id=client_id, as_of=today, batches=audits)


def _parse_iso_prefix(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None
