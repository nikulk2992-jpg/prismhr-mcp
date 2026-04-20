"""Workers Comp Billing Modifier Sync — workflow #38.

Per state, the WC billing modifier (the multiplier the PEO applies
to the NCCI rate when charging the client) must keep pace with the
accrual modifier (what the PEO pays the WC carrier). Drift = PEO
revenue leak or client overcharge.

Findings per state + class code:
  - BILLING_LOWER_THAN_ACCRUAL: billing modifier < accrual —
    PEO is paying the carrier more than charging the client.
  - BILLING_EXCESSIVELY_HIGHER: billing modifier > accrual × cap
    (default 1.75) — probable overcharge.
  - NO_BILLING_MODIFIER: accrual exists but billing modifier is blank.
  - ORPHAN_BILLING_MODIFIER: billing modifier exists for a class
    code with no accrual rate (sanity fail).
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
class WCModifierAudit:
    state: str
    wc_class: str
    accrual_modifier: Decimal
    billing_modifier: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class WCModifierSyncReport:
    client_id: str
    as_of: date
    audits: list[WCModifierAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def get_wc_accrual_modifiers(self, client_id: str) -> list[dict]: ...
    async def get_wc_billing_modifiers(self, client_id: str) -> list[dict]: ...


async def run_wc_billing_modifier_sync(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    upper_cap_multiplier: Decimal | str = "1.75",
) -> WCModifierSyncReport:
    today = as_of or date.today()
    cap = Decimal(str(upper_cap_multiplier))

    acc_rows = await reader.get_wc_accrual_modifiers(client_id)
    bill_rows = await reader.get_wc_billing_modifiers(client_id)

    def _key(r: dict) -> tuple[str, str]:
        return (str(r.get("state") or "").upper(), str(r.get("wcCode") or r.get("classCode") or ""))

    acc = {_key(r): _dec(r.get("modifier") or r.get("rate")) for r in acc_rows}
    bill = {_key(r): _dec(r.get("modifier") or r.get("rate")) for r in bill_rows}

    all_keys = set(acc) | set(bill)
    audits: list[WCModifierAudit] = []
    for key in sorted(all_keys):
        state, cls = key
        acc_mod = acc.get(key, Decimal("0"))
        bill_mod = bill.get(key, Decimal("0"))
        audit = WCModifierAudit(
            state=state,
            wc_class=cls,
            accrual_modifier=acc_mod,
            billing_modifier=bill_mod,
        )

        if acc_mod > 0 and bill_mod == 0:
            audit.findings.append(
                Finding(
                    "NO_BILLING_MODIFIER",
                    "critical",
                    f"{state}/{cls}: accrual modifier {acc_mod}, no billing modifier.",
                )
            )
        if acc_mod == 0 and bill_mod > 0:
            audit.findings.append(
                Finding(
                    "ORPHAN_BILLING_MODIFIER",
                    "warning",
                    f"{state}/{cls}: billing modifier {bill_mod} but no accrual row.",
                )
            )
        if acc_mod > 0 and 0 < bill_mod < acc_mod:
            audit.findings.append(
                Finding(
                    "BILLING_LOWER_THAN_ACCRUAL",
                    "critical",
                    f"{state}/{cls}: billing {bill_mod} < accrual {acc_mod} — PEO revenue leak.",
                )
            )
        if acc_mod > 0 and bill_mod > acc_mod * cap:
            audit.findings.append(
                Finding(
                    "BILLING_EXCESSIVELY_HIGHER",
                    "warning",
                    f"{state}/{cls}: billing {bill_mod} > {cap}× accrual {acc_mod} — possible overcharge.",
                )
            )
        audits.append(audit)

    return WCModifierSyncReport(client_id=client_id, as_of=today, audits=audits)


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
