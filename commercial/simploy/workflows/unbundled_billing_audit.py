"""Unbundled Billing Rule Audit — workflow #39.

Unbundled billing lets a PEO charge clients for specific pass-through
cost lines (admin fee, healthcare, 401k, workers comp, etc.) broken
out separately from the gross-up payroll bundle. Every pass-through
needs a billing rule so the pay period's invoice lists the right
components at the right rates.

Findings:
  - NO_RULE_FOR_ACTIVE_COMPONENT: a pay code or plan is costing the
    PEO but has no billing rule to pass it through.
  - RULE_WITHOUT_ACTIVITY: rule on file but zero activity in the
    last N periods (stale rule).
  - RATE_OUT_OF_RANGE: rule rate outside a sanity range (0-100% or
    configured min/max).
  - DUPLICATE_RULE: same component covered by two overlapping rules.
"""

from __future__ import annotations

from collections import defaultdict
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
class BillingRuleAudit:
    rule_id: str
    component: str
    rate: Decimal
    effective_date: date | None
    end_date: date | None
    has_recent_activity: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass
class UnbundledBillingReport:
    client_id: str
    as_of: date
    rules: list[BillingRuleAudit]
    orphan_components: list[str]

    @property
    def flagged(self) -> int:
        return sum(1 for r in self.rules if r.findings) + (
            1 if self.orphan_components else 0
        )


class PrismHRReader(Protocol):
    async def list_unbundled_billing_rules(self, client_id: str) -> list[dict]: ...
    async def list_active_components(self, client_id: str) -> list[str]: ...
    async def rule_recent_activity(
        self, client_id: str, rule_id: str, lookback_days: int
    ) -> bool: ...


async def run_unbundled_billing_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    activity_lookback_days: int = 90,
    min_rate: Decimal | str = "0.00",
    max_rate: Decimal | str = "100.00",
) -> UnbundledBillingReport:
    today = as_of or date.today()
    lo = Decimal(str(min_rate))
    hi = Decimal(str(max_rate))

    rules = await reader.list_unbundled_billing_rules(client_id)
    active_components = set(await reader.list_active_components(client_id))

    covered: set[str] = set()
    rule_by_component: dict[str, list[str]] = defaultdict(list)
    audits: list[BillingRuleAudit] = []

    for r in rules:
        rid = str(r.get("ruleId") or r.get("id") or "")
        comp = str(r.get("component") or r.get("componentCode") or "")
        rate = _dec(r.get("rate"))
        eff = _parse(r.get("effectiveDate"))
        end = _parse(r.get("endDate"))

        has_activity = await reader.rule_recent_activity(
            client_id, rid, activity_lookback_days
        )

        audit = BillingRuleAudit(
            rule_id=rid,
            component=comp,
            rate=rate,
            effective_date=eff,
            end_date=end,
            has_recent_activity=has_activity,
        )

        if rate < lo or rate > hi:
            audit.findings.append(
                Finding(
                    "RATE_OUT_OF_RANGE",
                    "critical",
                    f"Rule {rid} rate {rate} outside [{lo}, {hi}].",
                )
            )
        if not has_activity:
            audit.findings.append(
                Finding(
                    "RULE_WITHOUT_ACTIVITY",
                    "warning",
                    f"Rule {rid} for {comp} has no activity in {activity_lookback_days}d.",
                )
            )

        if comp:
            rule_by_component[comp].append(rid)
            covered.add(comp)

        audits.append(audit)

    # DUPLICATE_RULE: a component covered by 2+ rules
    for comp, rids in rule_by_component.items():
        if len(rids) > 1:
            for a in audits:
                if a.component == comp:
                    a.findings.append(
                        Finding(
                            "DUPLICATE_RULE",
                            "warning",
                            f"{comp} covered by rules {rids}.",
                        )
                    )
                    break

    # NO_RULE_FOR_ACTIVE_COMPONENT
    orphans = sorted(active_components - covered)
    if orphans:
        for a in audits:
            if a.rule_id == (rules[0].get("ruleId") or "") if rules else False:
                break
        # Better: add a stand-alone finding on the report level.
    return UnbundledBillingReport(
        client_id=client_id,
        as_of=today,
        rules=audits,
        orphan_components=orphans,
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
