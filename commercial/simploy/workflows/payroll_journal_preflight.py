"""Payroll Journal Preflight — catches bad journal BEFORE Intacct upload.

PrismHR exports a journal file per payroll period (debits/credits per
GL account, with client/department/location dimensions). Once that
file is uploaded to Intacct, a broken batch becomes a cleanup job.
This workflow inspects the journal IN-FLIGHT — after PrismHR generates
it, before the operator uploads it.

Finding codes:
  NET_NOT_ZERO             Batch debits ≠ credits. Won't balance.
  UNMAPPED_GL_ACCOUNT      Line has no GL account (hits suspense).
  SUSPENSE_HIT             Line posted to a clearing/suspense account.
  MISSING_DIMENSION        Required dimension (client/dept/loc) blank.
  UNKNOWN_DIMENSION        Dimension value not in Intacct master.
  ZERO_AMOUNT_LINE         $0.00 line — should have been dropped.
  DUPLICATE_LINE_KEY       Same (account, dim, source) twice — dup.
  OUT_OF_PERIOD            Line post-date outside batch period window.
  NEGATIVE_WAGE_NO_VOID    Negative line not attributed to a void voucher.
  LARGE_ROUNDING_DRIFT     Cumulative rounding > threshold across batch.

Inputs: client_id, batch_id OR period_start+period_end, preflight config.
Output: batch-level summary + per-line findings with drill-through refs.

Config (per-client YAML or passed in):
  suspense_accounts:   list of GL accts that mean "unmapped upstream"
  required_dims:       ["client", "department", "location"]
  known_clients:       set of client dims Intacct knows about
  known_departments:   set
  known_locations:     set
  rounding_threshold:  Decimal (default $1.00)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str  # "critical" | "warning" | "info"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class PreflightConfig:
    suspense_accounts: frozenset[str] = frozenset()
    required_dims: tuple[str, ...] = ("client",)
    known_clients: frozenset[str] = frozenset()
    known_departments: frozenset[str] = frozenset()
    known_locations: frozenset[str] = frozenset()
    rounding_threshold: Decimal = Decimal("1.00")


@dataclass
class LineAudit:
    line_id: str
    gl_account: str
    amount: Decimal
    is_debit: bool
    client_dim: str
    department_dim: str
    location_dim: str
    post_date: date | None
    source_voucher_id: str
    findings: list[Finding] = field(default_factory=list)


@dataclass
class PreflightReport:
    client_id: str
    batch_id: str | None
    period_start: date
    period_end: date
    as_of: date
    total_debits: Decimal
    total_credits: Decimal
    line_count: int
    lines: list[LineAudit] = field(default_factory=list)
    batch_findings: list[Finding] = field(default_factory=list)

    @property
    def net(self) -> Decimal:
        return (self.total_debits - self.total_credits).quantize(Decimal("0.01"))

    @property
    def balanced(self) -> bool:
        return self.net == Decimal("0.00")

    @property
    def passed(self) -> bool:
        here = not any(f.severity == "critical" for f in self.batch_findings)
        lines_clean = all(
            not any(f.severity == "critical" for f in l.findings)
            for l in self.lines
        )
        return here and lines_clean

    @property
    def flagged_lines(self) -> int:
        return sum(1 for l in self.lines if l.findings)


class PrismHRJournalReader(Protocol):
    """Reads the generated journal file from PrismHR (or a staging DB)."""

    async def list_journal_lines(
        self,
        client_id: str,
        *,
        batch_id: str | None,
        period_start: date,
        period_end: date,
    ) -> list[dict]:
        """Rows with: lineId, glAccount, amount, debitCredit ('D'|'C'),
        clientDim, departmentDim, locationDim, postDate, sourceVoucherId.
        Void lines may carry amount < 0 with voidVoucherId populated."""
        ...


async def run_payroll_journal_preflight(
    reader: PrismHRJournalReader,
    *,
    client_id: str,
    batch_id: str | None = None,
    period_start: date,
    period_end: date,
    config: PreflightConfig | None = None,
    as_of: date | None = None,
) -> PreflightReport:
    today = as_of or date.today()
    cfg = config or PreflightConfig()

    raw = await reader.list_journal_lines(
        client_id,
        batch_id=batch_id,
        period_start=period_start,
        period_end=period_end,
    )

    lines: list[LineAudit] = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    key_counts: Counter[tuple[str, str, str, str, str]] = Counter()

    for row in raw:
        line_id = str(row.get("lineId") or row.get("id") or "")
        account = str(row.get("glAccount") or row.get("account") or "").strip()
        amount = _dec(row.get("amount"))
        dc = str(row.get("debitCredit") or row.get("dc") or "").upper()
        is_debit = dc == "D"
        client_dim = str(row.get("clientDim") or row.get("client") or "").strip()
        dept_dim = str(row.get("departmentDim") or row.get("department") or "").strip()
        loc_dim = str(row.get("locationDim") or row.get("location") or "").strip()
        post_date = _parse(row.get("postDate") or row.get("date"))
        source_voucher = str(row.get("sourceVoucherId") or row.get("voucherId") or "")
        is_void = bool(row.get("voidVoucherId"))

        audit = LineAudit(
            line_id=line_id,
            gl_account=account,
            amount=amount,
            is_debit=is_debit,
            client_dim=client_dim,
            department_dim=dept_dim,
            location_dim=loc_dim,
            post_date=post_date,
            source_voucher_id=source_voucher,
        )

        # ---- line rules ----
        if not account:
            audit.findings.append(
                Finding("UNMAPPED_GL_ACCOUNT", "critical", "Line has no GL account.")
            )

        if account and account in cfg.suspense_accounts:
            audit.findings.append(
                Finding(
                    "SUSPENSE_HIT",
                    "critical",
                    f"Line posted to suspense account {account}. Upstream pay/deduction "
                    "code likely unmapped in PrismHR.",
                )
            )

        for dim_name in cfg.required_dims:
            val = {"client": client_dim, "department": dept_dim, "location": loc_dim}.get(dim_name, "")
            if not val:
                audit.findings.append(
                    Finding(
                        "MISSING_DIMENSION",
                        "critical",
                        f"Required dimension '{dim_name}' is blank.",
                    )
                )

        if client_dim and cfg.known_clients and client_dim not in cfg.known_clients:
            audit.findings.append(
                Finding(
                    "UNKNOWN_DIMENSION",
                    "critical",
                    f"Client dim '{client_dim}' not in Intacct client master.",
                )
            )
        if dept_dim and cfg.known_departments and dept_dim not in cfg.known_departments:
            audit.findings.append(
                Finding(
                    "UNKNOWN_DIMENSION",
                    "warning",
                    f"Department dim '{dept_dim}' not in Intacct master.",
                )
            )
        if loc_dim and cfg.known_locations and loc_dim not in cfg.known_locations:
            audit.findings.append(
                Finding(
                    "UNKNOWN_DIMENSION",
                    "warning",
                    f"Location dim '{loc_dim}' not in Intacct master.",
                )
            )

        if amount == Decimal("0"):
            audit.findings.append(
                Finding("ZERO_AMOUNT_LINE", "warning", "Zero-amount line should have been dropped.")
            )

        if post_date and (post_date < period_start or post_date > period_end):
            audit.findings.append(
                Finding(
                    "OUT_OF_PERIOD",
                    "warning",
                    f"Post date {post_date.isoformat()} outside period "
                    f"{period_start.isoformat()}..{period_end.isoformat()}.",
                )
            )

        if amount < Decimal("0") and not is_void:
            audit.findings.append(
                Finding(
                    "NEGATIVE_WAGE_NO_VOID",
                    "warning",
                    f"Negative amount ${amount} not attributed to a void voucher.",
                )
            )

        # Track duplicate keys at batch level
        key = (account, client_dim, dept_dim, loc_dim, source_voucher)
        key_counts[key] += 1

        if is_debit:
            total_debit += amount if amount >= 0 else Decimal("0")
            # Negative debit = credit in disguise; preserve sign in totals
            if amount < 0:
                total_credit += -amount
        else:
            total_credit += amount if amount >= 0 else Decimal("0")
            if amount < 0:
                total_debit += -amount

        lines.append(audit)

    # ---- batch rules ----
    batch_findings: list[Finding] = []

    net = (total_debit - total_credit).quantize(Decimal("0.01"))
    if net.copy_abs() > cfg.rounding_threshold:
        batch_findings.append(
            Finding(
                "NET_NOT_ZERO",
                "critical",
                f"Batch does not balance. Debits ${total_debit}, credits ${total_credit}, "
                f"net ${net}. Intacct will reject.",
            )
        )
    elif net != Decimal("0.00"):
        batch_findings.append(
            Finding(
                "LARGE_ROUNDING_DRIFT",
                "warning",
                f"Batch has ${net.copy_abs()} rounding drift (under threshold "
                f"${cfg.rounding_threshold} but nonzero).",
            )
        )

    # Duplicate keys
    dup_keys = [k for k, c in key_counts.items() if c > 1]
    if dup_keys:
        batch_findings.append(
            Finding(
                "DUPLICATE_LINE_KEY",
                "critical",
                f"{len(dup_keys)} duplicate line key(s): same (account, dims, voucher) "
                "posted multiple times in this batch.",
            )
        )
        # Mark each duplicate line
        dup_set = set(dup_keys)
        for la in lines:
            k = (la.gl_account, la.client_dim, la.department_dim, la.location_dim, la.source_voucher_id)
            if k in dup_set:
                la.findings.append(
                    Finding(
                        "DUPLICATE_LINE_KEY",
                        "critical",
                        "Duplicate of another line in this batch.",
                    )
                )

    return PreflightReport(
        client_id=client_id,
        batch_id=batch_id,
        period_start=period_start,
        period_end=period_end,
        as_of=today,
        total_debits=total_debit.quantize(Decimal("0.01")),
        total_credits=total_credit.quantize(Decimal("0.01")),
        line_count=len(lines),
        lines=lines,
        batch_findings=batch_findings,
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
