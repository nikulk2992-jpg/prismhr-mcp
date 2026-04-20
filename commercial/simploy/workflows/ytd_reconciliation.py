"""YTD Payroll Reconciliation — workflow #4.

Cross-checks the bulk YTD totals against the sum of payroll vouchers
for the same period. Catches the silent drift where a voucher was
edited, voided, or re-posted in a way that didn't flow back to the YTD
aggregate — the exact failure mode that blows up during W2/941 season.

Findings per employee:
  - YTD_MISMATCH_GROSS: YTD gross wages != sum(voucher totalEarnings)
  - YTD_MISMATCH_NET: YTD net pay != sum(voucher netPay)
  - YTD_MISMATCH_TAX: YTD tax withholding != sum(voucher employeeTax)
  - YTD_MISSING: no YTD record but vouchers exist
  - VOUCHERS_MISSING: YTD record exists but no vouchers in window

Input: client_id, year (defaults to current year), tolerance (cents).
Output: per-employee mismatch list with the actual deltas.

Data sources (all verified reads):
  - payroll.v1.getBulkYearToDateValues       (async download pattern)
  - payroll.v1.getPayrollVouchers            (voucher detail by date range)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Protocol


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class EmployeeYTDRecon:
    employee_id: str
    ytd_gross: Decimal = Decimal("0")
    ytd_net: Decimal = Decimal("0")
    ytd_tax: Decimal = Decimal("0")
    voucher_gross: Decimal = Decimal("0")
    voucher_net: Decimal = Decimal("0")
    voucher_tax: Decimal = Decimal("0")
    voucher_count: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "critical" for f in self.findings)


@dataclass
class YTDReconciliationReport:
    client_id: str
    year: int
    as_of: date
    employees: list[EmployeeYTDRecon]
    tolerance: Decimal

    @property
    def total(self) -> int:
        return len(self.employees)

    @property
    def passed(self) -> int:
        return sum(1 for e in self.employees if e.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed


class PrismHRReader(Protocol):
    """Minimal read surface."""

    async def get_bulk_ytd(self, client_id: str, year: int) -> list[dict]: ...
    async def get_vouchers(
        self, client_id: str, year: int
    ) -> list[dict]: ...


async def run_ytd_reconciliation(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int | None = None,
    as_of: date | None = None,
    tolerance: Decimal | str | float = "0.02",
) -> YTDReconciliationReport:
    """Reconcile YTD totals against voucher sums for a client."""
    today = as_of or date.today()
    target_year = year or today.year
    tol = Decimal(str(tolerance))

    ytd_rows = await reader.get_bulk_ytd(client_id, target_year)
    voucher_rows = await reader.get_vouchers(client_id, target_year)

    # Aggregate vouchers per employee.
    voucher_agg: dict[str, dict[str, Decimal | int]] = {}
    for v in voucher_rows:
        eid = str(v.get("employeeId") or "")
        if not eid:
            continue
        bucket = voucher_agg.setdefault(
            eid,
            {"gross": Decimal("0"), "net": Decimal("0"), "tax": Decimal("0"), "count": 0},
        )
        bucket["gross"] = bucket["gross"] + _dec(v.get("totalEarnings"))
        bucket["net"] = bucket["net"] + _dec(v.get("netPay"))
        bucket["tax"] = bucket["tax"] + _sum_voucher_tax(v.get("employeeTax"))
        bucket["count"] = int(bucket["count"]) + 1  # type: ignore[assignment]

    ytd_by_emp: dict[str, dict] = {
        str(r.get("employeeId") or ""): r for r in ytd_rows if r.get("employeeId")
    }

    all_ids = set(voucher_agg.keys()) | set(ytd_by_emp.keys())
    audits: list[EmployeeYTDRecon] = []
    for eid in sorted(all_ids):
        ytd_row = ytd_by_emp.get(eid, {})
        ytd_block = ytd_row.get("YTD") or ytd_row
        v = voucher_agg.get(eid, {})

        audit = EmployeeYTDRecon(
            employee_id=eid,
            ytd_gross=_dec(ytd_block.get("grossWages") or ytd_block.get("totalEarned")),
            ytd_net=_dec(ytd_block.get("netPay") or ytd_block.get("voucherNetPay")),
            ytd_tax=_dec_tax(ytd_block.get("taxWithholding")),
            voucher_gross=Decimal(v.get("gross", 0)) if v else Decimal("0"),
            voucher_net=Decimal(v.get("net", 0)) if v else Decimal("0"),
            voucher_tax=Decimal(v.get("tax", 0)) if v else Decimal("0"),
            voucher_count=int(v.get("count", 0)) if v else 0,
        )

        has_ytd = eid in ytd_by_emp
        has_vouchers = eid in voucher_agg and audit.voucher_count > 0

        if not has_ytd and has_vouchers:
            audit.findings.append(
                Finding(
                    "YTD_MISSING",
                    "critical",
                    f"{audit.voucher_count} vouchers found totalling {audit.voucher_gross} gross, no YTD record.",
                )
            )
        elif has_ytd and not has_vouchers:
            # Skip employees whose YTD is all zero — dormant records,
            # not a reconciliation failure.
            if audit.ytd_gross == 0 and audit.ytd_net == 0 and audit.ytd_tax == 0:
                audits.append(audit)
                continue
            audit.findings.append(
                Finding(
                    "VOUCHERS_MISSING",
                    "critical",
                    f"YTD shows {audit.ytd_gross} gross but no vouchers in the period.",
                )
            )
        else:
            for code, ytd_val, voucher_val, label in (
                ("YTD_MISMATCH_GROSS", audit.ytd_gross, audit.voucher_gross, "gross wages"),
                ("YTD_MISMATCH_NET", audit.ytd_net, audit.voucher_net, "net pay"),
                ("YTD_MISMATCH_TAX", audit.ytd_tax, audit.voucher_tax, "tax withholding"),
            ):
                delta = (ytd_val - voucher_val).copy_abs()
                if delta > tol:
                    audit.findings.append(
                        Finding(
                            code,
                            "critical",
                            f"{label}: YTD={ytd_val}, sum(vouchers)={voucher_val}, delta={ytd_val - voucher_val}.",
                        )
                    )

        audits.append(audit)

    return YTDReconciliationReport(
        client_id=client_id,
        year=target_year,
        as_of=today,
        employees=audits,
        tolerance=tol,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw is None:
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _sum_voucher_tax(raw) -> Decimal:  # type: ignore[no-untyped-def]
    """Voucher employeeTax may be a flat number or a list of tax lines."""
    if raw is None:
        return Decimal("0")
    if isinstance(raw, list):
        total = Decimal("0")
        for row in raw:
            if isinstance(row, dict):
                total += _dec(row.get("empTaxAmount"))
        return total
    return _dec(raw)


def _dec_tax(raw) -> Decimal:  # type: ignore[no-untyped-def]
    """taxWithholding may be a flat number or a nested breakdown. Must
    sum ALL numeric children, not a hand-picked subset — otherwise
    city/local/PFML/SDIF/county taxes appear in voucher-side sum but
    not in YTD sum, causing false YTD_MISMATCH_TAX flags for every
    employee in CA / NY / Philadelphia / NYC / STL / KC / Detroit etc."""
    if raw is None:
        return Decimal("0")
    if isinstance(raw, dict):
        total = Decimal("0")
        for k, v in raw.items():
            # Skip nested structures (e.g. taxCodes list) — they carry
            # identification, not amounts the voucher side sums.
            if isinstance(v, (int, float, str)):
                total += _dec(v)
            elif isinstance(v, dict):
                # Recurse for edge cases where a sub-dict holds amounts.
                total += _dec_tax(v)
        return total
    return _dec(raw)
