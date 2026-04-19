"""SUTA Billing Rate Drift — workflow #37.

Each state sends annual SUTA rate notices to every employer. Missing
the rate update = over- or under-billing clients. PrismHR stores
both accrual (state-side) rate + billing (PEO markup) rate; both
must track together.

Findings per (client, state):
  - ACCRUAL_RATE_STALE: no rate effective-date change in 18+ months
    (typical state rate cycle is annual).
  - BILLING_RATE_STALE: same for billing side.
  - RATE_MISALIGNMENT: billing rate < accrual rate — PEO is paying
    more than charging (revenue leak).
  - LARGE_YOY_CHANGE: rate changed more than 50% year-over-year —
    probable data entry error.
  - MULTIPLE_RATES_SAME_YEAR: more than one effective-date entry
    within a year (usually wrong — states issue once).
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
class StateRateAudit:
    state: str
    accrual_rate: Decimal
    billing_rate: Decimal
    accrual_effective: date | None
    billing_effective: date | None
    findings: list[Finding] = field(default_factory=list)


@dataclass
class SUTARateDriftReport:
    client_id: str
    as_of: date
    audits: list[StateRateAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def get_suta_accrual_rates(
        self, client_id: str
    ) -> list[dict]: ...
    async def get_suta_billing_rates(
        self, client_id: str
    ) -> list[dict]: ...


async def run_suta_rate_drift(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    stale_threshold_months: int = 18,
    yoy_change_pct: Decimal | str = "0.5",
) -> SUTARateDriftReport:
    today = as_of or date.today()
    yoy_threshold = Decimal(str(yoy_change_pct))

    accrual = await reader.get_suta_accrual_rates(client_id)
    billing = await reader.get_suta_billing_rates(client_id)

    def _by_state(rows: list[dict]) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for r in rows:
            s = str(r.get("state") or "").upper()
            if s:
                out.setdefault(s, []).append(r)
        return out

    acc_by_state = _by_state(accrual)
    bill_by_state = _by_state(billing)

    all_states = set(acc_by_state) | set(bill_by_state)
    audits: list[StateRateAudit] = []
    for state in sorted(all_states):
        acc_rows = sorted(
            acc_by_state.get(state, []),
            key=lambda r: _parse(r.get("effectiveDate")) or date.min,
        )
        bill_rows = sorted(
            bill_by_state.get(state, []),
            key=lambda r: _parse(r.get("effectiveDate")) or date.min,
        )
        latest_acc = acc_rows[-1] if acc_rows else {}
        latest_bill = bill_rows[-1] if bill_rows else {}

        acc_rate = _dec(latest_acc.get("rate"))
        bill_rate = _dec(latest_bill.get("rate"))
        acc_eff = _parse(latest_acc.get("effectiveDate"))
        bill_eff = _parse(latest_bill.get("effectiveDate"))

        audit = StateRateAudit(
            state=state,
            accrual_rate=acc_rate,
            billing_rate=bill_rate,
            accrual_effective=acc_eff,
            billing_effective=bill_eff,
        )

        stale_cutoff = today - timedelta(days=stale_threshold_months * 30)
        if acc_eff and acc_eff < stale_cutoff:
            audit.findings.append(
                Finding(
                    "ACCRUAL_RATE_STALE",
                    "warning",
                    f"{state}: accrual rate effective {acc_eff.isoformat()} — over {stale_threshold_months}mo old.",
                )
            )
        if bill_eff and bill_eff < stale_cutoff:
            audit.findings.append(
                Finding(
                    "BILLING_RATE_STALE",
                    "warning",
                    f"{state}: billing rate effective {bill_eff.isoformat()}.",
                )
            )

        if bill_rate > 0 and acc_rate > 0 and bill_rate < acc_rate:
            audit.findings.append(
                Finding(
                    "RATE_MISALIGNMENT",
                    "critical",
                    f"{state}: billing rate {bill_rate} < accrual rate {acc_rate} — PEO revenue leak.",
                )
            )

        # Year-over-year delta on accrual rate
        if len(acc_rows) >= 2:
            prev_rate = _dec(acc_rows[-2].get("rate"))
            if prev_rate > 0:
                delta_pct = (abs(acc_rate - prev_rate) / prev_rate)
                if delta_pct > yoy_threshold:
                    audit.findings.append(
                        Finding(
                            "LARGE_YOY_CHANGE",
                            "warning",
                            f"{state}: accrual rate jumped {delta_pct*100:.1f}% from {prev_rate} to {acc_rate}.",
                        )
                    )

        # Multiple rate rows within same calendar year
        if len([r for r in acc_rows if (_parse(r.get("effectiveDate")) or date.min).year == today.year]) > 1:
            audit.findings.append(
                Finding(
                    "MULTIPLE_RATES_SAME_YEAR",
                    "warning",
                    f"{state}: more than one accrual-rate entry in {today.year}.",
                )
            )
        audits.append(audit)

    return SUTARateDriftReport(
        client_id=client_id, as_of=today, audits=audits
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
