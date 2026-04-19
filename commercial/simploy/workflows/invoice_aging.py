"""Outstanding Invoice Aging — workflow #33.

Per PrismHR's AR chapter: outstanding invoices slide into aging
buckets (0-30, 31-60, 61-90, 91+). Anything 61+ is a collections
risk; 91+ is typically reserved or written off per GAAP.

Findings:
  - INVOICE_90_PLUS: invoice past 90 days.
  - CLIENT_AT_RISK: single client has > $10K in 61+ day bucket.
  - LARGE_OUTSTANDING: any single invoice > $25K past 30 days.

Produces a rolled-up aging summary across all clients + a per-client
breakdown.
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


@dataclass
class ClientAgingSummary:
    client_id: str
    current: Decimal = Decimal("0")
    days_31_60: Decimal = Decimal("0")
    days_61_90: Decimal = Decimal("0")
    days_91_plus: Decimal = Decimal("0")
    invoice_count: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return self.current + self.days_31_60 + self.days_61_90 + self.days_91_plus


@dataclass
class InvoiceAgingReport:
    as_of: date
    clients: list[ClientAgingSummary]

    @property
    def total_outstanding(self) -> Decimal:
        return sum((c.total for c in self.clients), Decimal("0"))

    @property
    def total_91_plus(self) -> Decimal:
        return sum((c.days_91_plus for c in self.clients), Decimal("0"))


class PrismHRReader(Protocol):
    async def get_bulk_outstanding_invoices(self) -> list[dict]: ...


async def run_invoice_aging(
    reader: PrismHRReader,
    *,
    as_of: date | None = None,
    at_risk_threshold: Decimal | str = "10000",
    large_invoice_threshold: Decimal | str = "25000",
) -> InvoiceAgingReport:
    today = as_of or date.today()
    at_risk = Decimal(str(at_risk_threshold))
    large = Decimal(str(large_invoice_threshold))

    invoices = await reader.get_bulk_outstanding_invoices()

    by_client: dict[str, ClientAgingSummary] = {}
    for inv in invoices:
        cid = str(inv.get("clientId") or "")
        if not cid:
            continue
        invoice_date = _parse(inv.get("invoiceDate") or inv.get("dueDate"))
        amt = _dec(inv.get("outstandingAmount") or inv.get("amount") or inv.get("balance"))
        if amt <= 0:
            continue

        summary = by_client.setdefault(cid, ClientAgingSummary(client_id=cid))
        summary.invoice_count += 1

        age = (today - invoice_date).days if invoice_date else 0
        if age <= 30:
            summary.current += amt
        elif age <= 60:
            summary.days_31_60 += amt
        elif age <= 90:
            summary.days_61_90 += amt
        else:
            summary.days_91_plus += amt
            summary.findings.append(
                Finding(
                    "INVOICE_90_PLUS",
                    "critical",
                    f"Invoice {inv.get('invoiceNumber') or '?'} is {age}d old: ${amt}.",
                )
            )

        if age > 30 and amt > large:
            summary.findings.append(
                Finding(
                    "LARGE_OUTSTANDING",
                    "warning",
                    f"Invoice ${amt} past 30d (age {age}).",
                )
            )

    # Second-pass: client-at-risk check
    for summary in by_client.values():
        if summary.days_61_90 + summary.days_91_plus > at_risk:
            summary.findings.append(
                Finding(
                    "CLIENT_AT_RISK",
                    "critical",
                    f"${summary.days_61_90 + summary.days_91_plus} in 61+ bucket.",
                )
            )

    return InvoiceAgingReport(as_of=today, clients=list(by_client.values()))


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
