"""Benefit Rate Change Drift — workflow #19.

Carriers publish new premium rates annually (sometimes quarterly).
PrismHR stores both the employer + employee rate per plan per tier.
Common failure: renewal rates land but operator only updates one
side — employer rate uploaded, employee share forgotten.

Findings per plan:
  - NO_RATE_CHANGE_AT_RENEWAL: plan renewal date passed, no new
    rate effective in the last 90d.
  - EMPLOYER_ONLY_UPDATED: employer rate changed but employee rate
    stayed flat (likely missed upload).
  - EMPLOYEE_ONLY_UPDATED: symmetric — employee changed without
    employer.
  - LARGE_RATE_JUMP: rate change > N% YoY (data entry check).
  - NEGATIVE_RATE: rate < 0.
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
class BenefitRateAudit:
    plan_id: str
    tier: str
    current_employer_rate: Decimal
    previous_employer_rate: Decimal
    current_employee_rate: Decimal
    previous_employee_rate: Decimal
    effective_date: date | None
    findings: list[Finding] = field(default_factory=list)


@dataclass
class BenefitRateDriftReport:
    client_id: str
    as_of: date
    audits: list[BenefitRateAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_plan_rate_history(
        self, client_id: str
    ) -> list[dict]: ...


async def run_benefit_rate_drift(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    renewal_window_days: int = 90,
    large_jump_pct: Decimal | str = "0.25",
) -> BenefitRateDriftReport:
    today = as_of or date.today()
    threshold = Decimal(str(large_jump_pct))

    rows = await reader.list_plan_rate_history(client_id)

    audits: list[BenefitRateAudit] = []
    for row in rows:
        pid = str(row.get("planId") or "")
        tier = str(row.get("tier") or "")
        cur_er = _dec(row.get("currentEmployerRate"))
        prev_er = _dec(row.get("previousEmployerRate"))
        cur_ee = _dec(row.get("currentEmployeeRate"))
        prev_ee = _dec(row.get("previousEmployeeRate"))
        eff = _parse(row.get("effectiveDate"))
        renewal = _parse(row.get("renewalDate"))

        audit = BenefitRateAudit(
            plan_id=pid,
            tier=tier,
            current_employer_rate=cur_er,
            previous_employer_rate=prev_er,
            current_employee_rate=cur_ee,
            previous_employee_rate=prev_ee,
            effective_date=eff,
        )

        if cur_er < 0 or cur_ee < 0:
            audit.findings.append(
                Finding("NEGATIVE_RATE", "critical", f"Plan {pid}/{tier}: negative rate on file.")
            )

        er_changed = cur_er != prev_er and prev_er > 0
        ee_changed = cur_ee != prev_ee and prev_ee > 0
        if er_changed and not ee_changed and prev_ee > 0:
            audit.findings.append(
                Finding(
                    "EMPLOYER_ONLY_UPDATED",
                    "warning",
                    f"Plan {pid}/{tier}: employer {prev_er}->{cur_er}, employee unchanged at {cur_ee}.",
                )
            )
        if ee_changed and not er_changed and prev_er > 0:
            audit.findings.append(
                Finding(
                    "EMPLOYEE_ONLY_UPDATED",
                    "warning",
                    f"Plan {pid}/{tier}: employee {prev_ee}->{cur_ee}, employer unchanged at {cur_er}.",
                )
            )

        if er_changed and prev_er > 0:
            delta = (abs(cur_er - prev_er) / prev_er)
            if delta > threshold:
                audit.findings.append(
                    Finding(
                        "LARGE_RATE_JUMP",
                        "warning",
                        f"Plan {pid}/{tier}: employer rate jumped {delta*100:.1f}%.",
                    )
                )

        if renewal and renewal < today:
            if not eff or (today - eff).days > renewal_window_days:
                audit.findings.append(
                    Finding(
                        "NO_RATE_CHANGE_AT_RENEWAL",
                        "critical",
                        f"Plan {pid}: renewal was {renewal.isoformat()}, no rate update in last {renewal_window_days}d.",
                    )
                )

        audits.append(audit)

    return BenefitRateDriftReport(client_id=client_id, as_of=today, audits=audits)


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
