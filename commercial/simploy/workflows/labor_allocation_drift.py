"""Labor Allocation Drift — workflow #44.

Labor allocations split employee wages across multiple cost centers
(departments, divisions, projects, jobs). Drift = allocations that
sum to ≠ 100% per employee, or allocations pointing to closed cost
centers.

Findings:
  - ALLOCATION_NOT_100_PCT: sum of employee allocation percents is
    not within tolerance of 100%.
  - ALLOCATION_TO_INACTIVE_CODE: allocation points to a department /
    division / project code that is marked inactive.
  - ZERO_PCT_ALLOCATION: row with 0% weight present (dead row).
  - OVER_ALLOCATED: total > 100% (double-booked).
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
class AllocationAudit:
    employee_id: str
    total_pct: Decimal
    rows: list[dict] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


@dataclass
class LaborAllocationReport:
    client_id: str
    as_of: date
    audits: list[AllocationAudit]
    tolerance_pct: Decimal

    @property
    def flagged(self) -> int:
        return sum(1 for a in self.audits if a.findings)


class PrismHRReader(Protocol):
    async def list_labor_allocations(
        self, client_id: str
    ) -> list[dict]: ...
    async def list_inactive_codes(
        self, client_id: str
    ) -> set[str]: ...


async def run_labor_allocation_drift(
    reader: PrismHRReader,
    *,
    client_id: str,
    as_of: date | None = None,
    tolerance_pct: Decimal | str = "0.01",
) -> LaborAllocationReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance_pct))

    rows = await reader.list_labor_allocations(client_id)
    inactive = await reader.list_inactive_codes(client_id)

    by_emp: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        eid = str(r.get("employeeId") or "")
        if eid:
            by_emp[eid].append(r)

    audits: list[AllocationAudit] = []
    for eid, allocs in by_emp.items():
        total = Decimal("0")
        audit = AllocationAudit(employee_id=eid, total_pct=Decimal("0"), rows=list(allocs))
        for a in allocs:
            pct = _dec(a.get("percent") or a.get("pct"))
            total += pct
            code_key = f"{a.get('codeType','')}:{a.get('code','')}"
            if pct == 0:
                audit.findings.append(
                    Finding("ZERO_PCT_ALLOCATION", "warning", f"Row for {code_key} has 0% — dead row.")
                )
            if code_key in inactive or str(a.get("code", "")) in inactive:
                audit.findings.append(
                    Finding(
                        "ALLOCATION_TO_INACTIVE_CODE",
                        "critical",
                        f"Allocation row points to inactive {code_key}.",
                    )
                )
        audit.total_pct = total

        if (total - Decimal("100")).copy_abs() > tol:
            if total > Decimal("100"):
                audit.findings.append(
                    Finding(
                        "OVER_ALLOCATED",
                        "critical",
                        f"Allocations total {total}% (over 100%).",
                    )
                )
            else:
                audit.findings.append(
                    Finding(
                        "ALLOCATION_NOT_100_PCT",
                        "critical",
                        f"Allocations total {total}% (expected 100%).",
                    )
                )

        audits.append(audit)

    return LaborAllocationReport(
        client_id=client_id, as_of=today, audits=audits, tolerance_pct=tol
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
