"""Tax Remittance Tracking — workflow #58.

Every tax return (941, 940, state quarterly, state monthly, local)
comes with a deposit schedule. Missing a deposit by even one day is
an FTD (failure-to-deposit) penalty of 2-15%. This workflow ties
ledger-side tax liability to the actual ACH deposits PrismHR sent
to the taxing authority.

Findings:
  - DEPOSIT_MISSING: liability posted, no deposit recorded within
    the statutory window.
  - DEPOSIT_LATE: deposit recorded past the due date.
  - DEPOSIT_UNDER: deposit amount < liability amount.
  - DEPOSIT_OVER: deposit > liability by more than tolerance (may
    indicate double-deposit).
  - NO_DUE_DATE: deposit on file with no due-date attribution.

Input: client_id, tax_jurisdiction (federal|state:XX|local:NYC|...),
tax_code (FIT|SS|MED|SUTA|SWH), year, quarter optional.
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
class DepositAudit:
    liability_date: date | None
    due_date: date | None
    liability_amount: Decimal
    deposit_date: date | None
    deposit_amount: Decimal
    deposit_reference: str
    findings: list[Finding] = field(default_factory=list)


@dataclass
class RemittanceReport:
    client_id: str
    jurisdiction: str
    tax_code: str
    year: int
    as_of: date
    deposits: list[DepositAudit]
    tolerance: Decimal

    @property
    def total_liability(self) -> Decimal:
        return sum((d.liability_amount for d in self.deposits), Decimal("0"))

    @property
    def total_deposits(self) -> Decimal:
        return sum((d.deposit_amount for d in self.deposits), Decimal("0"))

    @property
    def flagged(self) -> int:
        return sum(1 for d in self.deposits if d.findings)


class PrismHRReader(Protocol):
    async def list_tax_liabilities(
        self, client_id: str, jurisdiction: str, tax_code: str, year: int
    ) -> list[dict]: ...
    async def list_tax_deposits(
        self, client_id: str, jurisdiction: str, tax_code: str, year: int
    ) -> list[dict]: ...


async def run_tax_remittance_tracking(
    reader: PrismHRReader,
    *,
    client_id: str,
    jurisdiction: str,
    tax_code: str,
    year: int,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
    grace_days: int = 0,
) -> RemittanceReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))

    liabilities = await reader.list_tax_liabilities(
        client_id, jurisdiction, tax_code, year
    )
    deposits = await reader.list_tax_deposits(
        client_id, jurisdiction, tax_code, year
    )

    # Match deposits to liabilities by liability-id or (date, amount)
    dep_by_liab: dict[str, dict] = {}
    for d in deposits:
        lid = str(d.get("liabilityId") or d.get("liability_id") or "")
        if lid:
            dep_by_liab[lid] = d

    audits: list[DepositAudit] = []
    for liab in liabilities:
        liab_id = str(liab.get("id") or liab.get("liabilityId") or "")
        liab_date = _parse(liab.get("liabilityDate") or liab.get("postDate"))
        due = _parse(liab.get("dueDate"))
        liab_amt = _dec(liab.get("amount") or liab.get("liabilityAmount"))

        dep = dep_by_liab.get(liab_id, {})
        dep_date = _parse(dep.get("depositDate") or dep.get("effectiveDate"))
        dep_amt = _dec(dep.get("amount") or dep.get("depositAmount"))
        ref = str(dep.get("reference") or dep.get("confirmation") or "")

        audit = DepositAudit(
            liability_date=liab_date,
            due_date=due,
            liability_amount=liab_amt,
            deposit_date=dep_date,
            deposit_amount=dep_amt,
            deposit_reference=ref,
        )

        if dep_date is None and liab_amt > tol:
            audit.findings.append(
                Finding(
                    "DEPOSIT_MISSING",
                    "critical",
                    f"Liability ${liab_amt} on {liab_date.isoformat() if liab_date else '?'} has no deposit.",
                )
            )
        else:
            if due and dep_date and dep_date > due + timedelta(days=grace_days):
                days_late = (dep_date - due).days
                audit.findings.append(
                    Finding(
                        "DEPOSIT_LATE",
                        "critical",
                        f"Due {due.isoformat()}, deposited {dep_date.isoformat()} ({days_late}d late).",
                    )
                )
            delta = dep_amt - liab_amt
            if delta < -tol:
                audit.findings.append(
                    Finding(
                        "DEPOSIT_UNDER",
                        "critical",
                        f"Liability ${liab_amt}, deposit ${dep_amt} (short ${-delta}).",
                    )
                )
            elif delta > tol:
                audit.findings.append(
                    Finding(
                        "DEPOSIT_OVER",
                        "warning",
                        f"Deposit ${dep_amt} exceeds liability ${liab_amt} by ${delta}.",
                    )
                )
            if dep_date and not due:
                audit.findings.append(
                    Finding(
                        "NO_DUE_DATE",
                        "warning",
                        "Deposit on file but no due-date on the liability.",
                    )
                )
        audits.append(audit)

    return RemittanceReport(
        client_id=client_id,
        jurisdiction=jurisdiction,
        tax_code=tax_code,
        year=year,
        as_of=today,
        deposits=audits,
        tolerance=tol,
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
