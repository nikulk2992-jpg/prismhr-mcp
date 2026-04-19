"""State Tax Setup Validator — workflow #27.

Clients new to a state (or new to remote workers in a state) need
registrations with that state's taxing authorities BEFORE posting
their first voucher. Missing registrations = late deposits + state
audit exposure + employer of record liability.

Findings per state:
  - NO_SUTA_ACCOUNT: wages posted in state but no SUTA account ID.
  - NO_WH_ACCOUNT: state with income tax + wages posted but no
    withholding account.
  - SUTA_RATE_MISSING: no SUTA rate on file for the client.
  - WH_RATE_MISSING: state-level WH rate not configured.
  - UNUSED_REGISTRATION: state has an account but no wages posted
    in 2+ years (inactive — maybe de-register).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

# States with state income tax (as of 2025). Others: AK, FL, NH, NV,
# SD, TN, TX, WA, WY. New Hampshire taxes investment only.
_NO_STATE_INCOME_TAX = {"AK", "FL", "NH", "NV", "SD", "TN", "TX", "WA", "WY"}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class StateSetupAudit:
    state: str
    has_wages: bool
    suta_account_id: str
    suta_rate: Decimal
    wh_account_id: str
    wh_rate: Decimal
    last_wage_year: int | None
    findings: list[Finding] = field(default_factory=list)


@dataclass
class StateSetupReport:
    client_id: str
    as_of: date
    audits: list[StateSetupAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_state_setups(
        self, client_id: str
    ) -> list[dict]: ...


async def run_state_tax_setup_validator(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
) -> StateSetupReport:
    today = as_of or date.today()
    rows = await reader.list_state_setups(client_id)

    audits: list[StateSetupAudit] = []
    for r in rows:
        state = str(r.get("state") or "").upper()
        if not state:
            continue
        has_wages = bool(r.get("hasWagesCurrentPeriod", False))
        suta_acct = str(r.get("sutaAccountId") or "").strip()
        suta_rate = _dec(r.get("sutaRate"))
        wh_acct = str(r.get("withholdingAccountId") or "").strip()
        wh_rate = _dec(r.get("withholdingRate"))
        last_year = int(r.get("lastWageYear") or 0) or None

        audit = StateSetupAudit(
            state=state,
            has_wages=has_wages,
            suta_account_id=suta_acct,
            suta_rate=suta_rate,
            wh_account_id=wh_acct,
            wh_rate=wh_rate,
            last_wage_year=last_year,
        )

        if has_wages and not suta_acct:
            audit.findings.append(
                Finding("NO_SUTA_ACCOUNT", "critical", f"{state} has wages but no SUTA account ID on file.")
            )
        if has_wages and suta_acct and suta_rate <= 0:
            audit.findings.append(
                Finding("SUTA_RATE_MISSING", "critical", f"{state}: SUTA account exists but no rate configured.")
            )
        if has_wages and state not in _NO_STATE_INCOME_TAX and not wh_acct:
            audit.findings.append(
                Finding(
                    "NO_WH_ACCOUNT",
                    "critical",
                    f"{state}: taxable state + wages posted but no withholding account.",
                )
            )
        if has_wages and state not in _NO_STATE_INCOME_TAX and wh_acct and wh_rate <= 0:
            audit.findings.append(
                Finding("WH_RATE_MISSING", "warning", f"{state}: WH account exists but no rate configured.")
            )
        if not has_wages and last_year and (today.year - last_year) >= 2:
            audit.findings.append(
                Finding(
                    "UNUSED_REGISTRATION",
                    "info",
                    f"{state}: registered but no wages since {last_year} — consider de-registering.",
                )
            )
        audits.append(audit)

    return StateSetupReport(client_id=client_id, as_of=today, audits=audits)


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
