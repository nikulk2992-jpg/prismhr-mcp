"""Payroll-to-GL Reconciliation — ties PrismHR journal export to what
actually posted in Intacct.

This is the "why are we off" workflow. PrismHR generates a journal per
pay period, ops uploads to Intacct. Sometimes they don't match:
  - upload dropped lines mid-batch
  - manual JE in Intacct hit the same account (contamination)
  - voucher reissued in PrismHR after the upload (orphan in PrismHR)
  - dimension mismatch between PrismHR and Intacct masters
  - rounding accumulates across cost centers

Match key: (gl_account, client_dim, department_dim, location_dim)
Summed both sides. Flag deltas, extras, missing.

Finding codes:
  LINE_MISSING_IN_INTACCT   PrismHR sent, Intacct has nothing on key.
  LINE_EXTRA_IN_INTACCT     Intacct has payroll-source line, no origin
                            in PrismHR. Manual JE OR reissued voucher.
  AMOUNT_DRIFT              Both sides have the key, amounts differ.
  DIMENSION_PARTIAL         PrismHR dim populated, Intacct blank.
  BATCH_TOTALS_DRIFT        Sum(PrismHR) ≠ sum(Intacct) at batch level.

Inputs: client_id, period_start, period_end, tolerance per-account map.
Output: per-key audit with both-side amounts + findings.
"""

from __future__ import annotations

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


MatchKey = tuple[str, str, str, str]  # (account, client_dim, dept_dim, loc_dim)


@dataclass
class KeyAudit:
    key: MatchKey
    gl_account: str
    client_dim: str
    department_dim: str
    location_dim: str
    prismhr_amount: Decimal
    intacct_amount: Decimal
    source_voucher_ids: list[str] = field(default_factory=list)
    intacct_doc_refs: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def delta(self) -> Decimal:
        return (self.prismhr_amount - self.intacct_amount).quantize(Decimal("0.01"))


@dataclass
class GLReconReport:
    client_id: str
    period_start: date
    period_end: date
    as_of: date
    keys: list[KeyAudit]
    batch_findings: list[Finding] = field(default_factory=list)

    @property
    def total_prismhr(self) -> Decimal:
        return sum((k.prismhr_amount for k in self.keys), Decimal("0")).quantize(Decimal("0.01"))

    @property
    def total_intacct(self) -> Decimal:
        return sum((k.intacct_amount for k in self.keys), Decimal("0")).quantize(Decimal("0.01"))

    @property
    def batch_delta(self) -> Decimal:
        return (self.total_prismhr - self.total_intacct).quantize(Decimal("0.01"))

    @property
    def flagged(self) -> int:
        here = 1 if any(f.severity == "critical" for f in self.batch_findings) else 0
        return here + sum(1 for k in self.keys if k.findings)

    @property
    def matched_clean(self) -> int:
        return sum(1 for k in self.keys if not k.findings)


class PrismHRJournalReader(Protocol):
    async def list_journal_lines(
        self, client_id: str, *, period_start: date, period_end: date
    ) -> list[dict]:
        """Same shape as preflight reader. Rows with glAccount, amount,
        debitCredit, dims, sourceVoucherId."""
        ...


class IntacctReader(Protocol):
    async def list_payroll_gl_lines(
        self, client_id: str, *, period_start: date, period_end: date
    ) -> list[dict]:
        """Intacct GL detail filtered to payroll-source lines.
        Rows: {glAccount, amount, debitCredit, clientDim, departmentDim,
        locationDim, postDate, docRef (Intacct GL entry ref)}."""
        ...


async def run_payroll_gl_recon(
    *,
    prismhr: PrismHRJournalReader,
    intacct: IntacctReader,
    client_id: str,
    period_start: date,
    period_end: date,
    tolerance: Decimal | str = "1.00",
    per_account_tolerance: dict[str, Decimal] | None = None,
    as_of: date | None = None,
) -> GLReconReport:
    today = as_of or date.today()
    default_tol = Decimal(str(tolerance))
    per_acct_tol = per_account_tolerance or {}

    p_rows = await prismhr.list_journal_lines(
        client_id, period_start=period_start, period_end=period_end
    )
    i_rows = await intacct.list_payroll_gl_lines(
        client_id, period_start=period_start, period_end=period_end
    )

    p_by_key: dict[MatchKey, Decimal] = {}
    p_vouchers: dict[MatchKey, list[str]] = {}
    for row in p_rows:
        key = _key(row)
        amt = _signed(row)
        p_by_key[key] = p_by_key.get(key, Decimal("0")) + amt
        v = str(row.get("sourceVoucherId") or "")
        if v:
            p_vouchers.setdefault(key, []).append(v)

    i_by_key: dict[MatchKey, Decimal] = {}
    i_refs: dict[MatchKey, list[str]] = {}
    for row in i_rows:
        key = _key(row)
        amt = _signed(row)
        i_by_key[key] = i_by_key.get(key, Decimal("0")) + amt
        ref = str(row.get("docRef") or row.get("ref") or "")
        if ref:
            i_refs.setdefault(key, []).append(ref)

    all_keys = sorted(set(p_by_key) | set(i_by_key))
    audits: list[KeyAudit] = []
    for key in all_keys:
        account, client_dim, dept_dim, loc_dim = key
        p_amt = p_by_key.get(key, Decimal("0")).quantize(Decimal("0.01"))
        i_amt = i_by_key.get(key, Decimal("0")).quantize(Decimal("0.01"))
        tol = per_acct_tol.get(account, default_tol)

        audit = KeyAudit(
            key=key,
            gl_account=account,
            client_dim=client_dim,
            department_dim=dept_dim,
            location_dim=loc_dim,
            prismhr_amount=p_amt,
            intacct_amount=i_amt,
            source_voucher_ids=p_vouchers.get(key, []),
            intacct_doc_refs=i_refs.get(key, []),
        )

        if p_amt != Decimal("0") and i_amt == Decimal("0"):
            audit.findings.append(
                Finding(
                    "LINE_MISSING_IN_INTACCT",
                    "critical",
                    f"Account {account} / dims ({client_dim}/{dept_dim}/{loc_dim}): "
                    f"PrismHR ${p_amt}, Intacct $0. Upload may have dropped this line. "
                    f"Source vouchers: {', '.join(audit.source_voucher_ids) or 'n/a'}.",
                )
            )
        elif p_amt == Decimal("0") and i_amt != Decimal("0"):
            audit.findings.append(
                Finding(
                    "LINE_EXTRA_IN_INTACCT",
                    "critical",
                    f"Account {account} / dims ({client_dim}/{dept_dim}/{loc_dim}): "
                    f"Intacct ${i_amt} but no PrismHR origin. Manual JE OR reissued "
                    f"voucher not re-uploaded. Intacct refs: "
                    f"{', '.join(audit.intacct_doc_refs) or 'n/a'}.",
                )
            )
        else:
            delta = p_amt - i_amt
            if delta.copy_abs() > tol:
                audit.findings.append(
                    Finding(
                        "AMOUNT_DRIFT",
                        "critical",
                        f"Account {account}: PrismHR ${p_amt}, Intacct ${i_amt}, "
                        f"delta ${delta} (tolerance ${tol}).",
                    )
                )

        audits.append(audit)

    batch_findings: list[Finding] = []
    # Use gross magnitude (sum of absolute debit amounts per side) so that
    # an internally-balanced PrismHR batch whose Intacct posting is scaled
    # wrong still surfaces. Signed totals would both be $0 and hide it.
    p_gross = sum(
        (a.prismhr_amount for a in audits if a.prismhr_amount > 0),
        Decimal("0"),
    )
    i_gross = sum(
        (a.intacct_amount for a in audits if a.intacct_amount > 0),
        Decimal("0"),
    )
    total_delta = (p_gross - i_gross).quantize(Decimal("0.01"))
    if total_delta.copy_abs() > default_tol:
        batch_findings.append(
            Finding(
                "BATCH_TOTALS_DRIFT",
                "critical",
                f"Batch totals drift: PrismHR ${p_gross}, Intacct ${i_gross}, "
                f"net ${total_delta}.",
            )
        )

    return GLReconReport(
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        as_of=today,
        keys=audits,
        batch_findings=batch_findings,
    )


def _key(row: dict) -> MatchKey:
    return (
        str(row.get("glAccount") or row.get("account") or "").strip(),
        str(row.get("clientDim") or row.get("client") or "").strip(),
        str(row.get("departmentDim") or row.get("department") or "").strip(),
        str(row.get("locationDim") or row.get("location") or "").strip(),
    )


def _signed(row: dict) -> Decimal:
    """Debits positive, credits negative. Works for either side."""
    amt = _dec(row.get("amount"))
    dc = str(row.get("debitCredit") or row.get("dc") or "").upper()
    if dc == "C":
        return -amt
    return amt


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
