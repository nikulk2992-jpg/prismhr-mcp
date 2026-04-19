"""PTO Balance Reconciliation — workflow #45.

Per PrismHR's PTO setup chapter: employees get a PTO class assignment
that drives accrual rate, cap, carryover, and reset rules. Drift
between class setup + actual balance is common, especially after
anniversary dates or job-class changes.

Findings:
  - NO_PTO_CLASS_ASSIGNED: active employee with no class.
  - NEGATIVE_BALANCE: balance below zero (borrowed PTO without approval).
  - OVER_CAP: balance exceeds plan's ceiling — employer liability.
  - CARRYOVER_EXCEEDED: rolled more hours than plan allows.
  - ACCRUAL_STALLED: last accrual transaction > N days ago (default 60).
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
class PTOEmployeeAudit:
    employee_id: str
    pto_class: str
    balance_hours: Decimal
    last_accrual_date: date | None
    plan_cap: Decimal
    carryover_limit: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class PTOReconciliationReport:
    client_id: str
    as_of: date
    audits: list[PTOEmployeeAudit]

    @property
    def total(self) -> int:
        return len(self.audits)

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def get_pto_classes(self, client_id: str) -> list[dict]: ...
    async def get_pto_plans(self, client_id: str) -> list[dict]: ...
    async def get_employee_pto_rows(self, client_id: str) -> list[dict]: ...


async def run_pto_reconciliation(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    accrual_stale_days: int = 60,
) -> PTOReconciliationReport:
    today = as_of or date.today()

    classes = {str(c.get("classCode") or ""): c for c in await reader.get_pto_classes(client_id)}
    plans = {str(p.get("id") or p.get("planId") or ""): p for p in await reader.get_pto_plans(client_id)}
    emp_rows = await reader.get_employee_pto_rows(client_id)

    audits: list[PTOEmployeeAudit] = []
    for r in emp_rows:
        eid = str(r.get("employeeId") or "")
        if not eid:
            continue
        pto_class = str(r.get("ptoClass") or r.get("classCode") or "")
        balance = _dec(r.get("balanceHours") or r.get("balance"))
        last_accrual = _parse(r.get("lastAccrualDate") or r.get("lastAccrual"))

        # Look up plan rules via class -> plan linkage
        plan_id = str(classes.get(pto_class, {}).get("planId") or "")
        plan = plans.get(plan_id, {})
        cap = _dec(plan.get("maxHours") or plan.get("cap"))
        carryover = _dec(plan.get("carryoverLimit") or plan.get("ltdCarryoverHours"))

        audit = PTOEmployeeAudit(
            employee_id=eid,
            pto_class=pto_class,
            balance_hours=balance,
            last_accrual_date=last_accrual,
            plan_cap=cap,
            carryover_limit=carryover,
        )

        if not pto_class:
            audit.findings.append(
                Finding("NO_PTO_CLASS_ASSIGNED", "critical", "Employee has no PTO class code.")
            )
        if balance < Decimal("0"):
            audit.findings.append(
                Finding("NEGATIVE_BALANCE", "critical", f"Balance is {balance} (negative).")
            )
        if cap > 0 and balance > cap:
            audit.findings.append(
                Finding(
                    "OVER_CAP",
                    "warning",
                    f"Balance {balance} exceeds plan cap {cap}.",
                )
            )
        if last_accrual:
            days = (today - last_accrual).days
            if days > accrual_stale_days:
                audit.findings.append(
                    Finding(
                        "ACCRUAL_STALLED",
                        "warning",
                        f"Last accrual {days} days ago (threshold {accrual_stale_days}d).",
                    )
                )
        audits.append(audit)

    return PTOReconciliationReport(client_id=client_id, as_of=today, audits=audits)


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
