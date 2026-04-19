"""941 Quarterly Reconciliation — workflow #25.

IRS Form 941 is the quarterly federal tax return for withholding +
employer SS/Medicare. It must tie to the payroll ledger within the
quarter: sum of voucher wages × applicable tax rates must match
what was actually remitted.

PrismHR generates the 941 from the voucher ledger; the failure mode
is drift between the generator and the ledger when vouchers are
voided/reissued or corrections are posted late.

Findings per quarter:
  - WAGES_MISMATCH: sum(voucher wages) != 941 wages reported.
  - FIT_MISMATCH: voucher federal withholding sum != 941 Line 3.
  - SS_MISMATCH: social security wages × rate != 941 Line 5a × 2.
  - MEDICARE_MISMATCH: medicare wages × 2.9% != 941 Line 5c × 2.
  - ADDL_MEDICARE_MISSING: employee over $200K with no additional
    Medicare withheld.
  - NEGATIVE_TAX_LIABILITY: line calculation comes out negative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

_SS_RATE = Decimal("0.062")  # employee + employer each
_MEDICARE_RATE = Decimal("0.0145")
_ADDITIONAL_MEDICARE_THRESHOLD = Decimal("200000")
_ADDITIONAL_MEDICARE_RATE = Decimal("0.009")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class QuarterRecon:
    quarter: int
    year: int
    voucher_total_wages: Decimal
    form941_total_wages: Decimal
    voucher_fit: Decimal
    form941_fit: Decimal
    voucher_ss_wages: Decimal
    form941_ss_tax: Decimal
    voucher_medicare_wages: Decimal
    form941_medicare_tax: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class Form941Report:
    client_id: str
    year: int
    quarter: int
    as_of: date
    recon: QuarterRecon
    tolerance: Decimal


class PrismHRReader(Protocol):
    async def sum_vouchers_for_quarter(
        self, client_id: str, year: int, quarter: int
    ) -> dict: ...
    async def get_form941(
        self, client_id: str, year: int, quarter: int
    ) -> dict: ...


async def run_form_941_reconciliation(
    reader: PrismHRReader,
    *,
    client_id: str,
    year: int,
    quarter: int,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
) -> Form941Report:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))

    voucher = await reader.sum_vouchers_for_quarter(client_id, year, quarter)
    form941 = await reader.get_form941(client_id, year, quarter)

    v_wages = _dec(voucher.get("totalWages"))
    v_fit = _dec(voucher.get("federalIncomeTax"))
    v_ss_wages = _dec(voucher.get("socialSecurityWages"))
    v_medicare_wages = _dec(voucher.get("medicareWages"))
    v_addl_medicare_wages = _dec(voucher.get("additionalMedicareWages"))

    f_wages = _dec(form941.get("line2_totalWages") or form941.get("totalWages"))
    f_fit = _dec(form941.get("line3_fit") or form941.get("federalIncomeTax"))
    f_ss_tax = _dec(form941.get("line5a_socialSecurityTax") or form941.get("socialSecurityTax"))
    f_medicare_tax = _dec(form941.get("line5c_medicareTax") or form941.get("medicareTax"))

    recon = QuarterRecon(
        quarter=quarter,
        year=year,
        voucher_total_wages=v_wages,
        form941_total_wages=f_wages,
        voucher_fit=v_fit,
        form941_fit=f_fit,
        voucher_ss_wages=v_ss_wages,
        form941_ss_tax=f_ss_tax,
        voucher_medicare_wages=v_medicare_wages,
        form941_medicare_tax=f_medicare_tax,
    )

    if (f_wages - v_wages).copy_abs() > tol:
        recon.findings.append(
            Finding(
                "WAGES_MISMATCH",
                "critical",
                f"941 wages ${f_wages} vs vouchers ${v_wages}; delta ${f_wages - v_wages}.",
            )
        )
    if (f_fit - v_fit).copy_abs() > tol:
        recon.findings.append(
            Finding(
                "FIT_MISMATCH",
                "critical",
                f"941 FIT ${f_fit} vs vouchers ${v_fit}; delta ${f_fit - v_fit}.",
            )
        )

    # SS expected = voucher_ss_wages × 12.4% (ee + er)
    expected_ss = v_ss_wages * _SS_RATE * Decimal("2")
    if (f_ss_tax - expected_ss).copy_abs() > tol:
        recon.findings.append(
            Finding(
                "SS_MISMATCH",
                "critical",
                f"941 SS tax ${f_ss_tax} vs expected ${expected_ss} (wages ${v_ss_wages} × 12.4%).",
            )
        )

    expected_medicare = v_medicare_wages * _MEDICARE_RATE * Decimal("2")
    if (f_medicare_tax - expected_medicare).copy_abs() > tol:
        recon.findings.append(
            Finding(
                "MEDICARE_MISMATCH",
                "critical",
                f"941 Medicare ${f_medicare_tax} vs expected ${expected_medicare} (wages ${v_medicare_wages} × 2.9%).",
            )
        )

    # Additional Medicare: wages above $200K × 0.9% (employee only)
    if v_addl_medicare_wages > 0:
        expected_addl = v_addl_medicare_wages * _ADDITIONAL_MEDICARE_RATE
        f_addl = _dec(form941.get("line5d_additionalMedicareTax") or form941.get("additionalMedicareTax"))
        if (f_addl - expected_addl).copy_abs() > tol:
            recon.findings.append(
                Finding(
                    "ADDL_MEDICARE_MISSING",
                    "critical",
                    f"Additional Medicare: expected ${expected_addl}, reported ${f_addl}.",
                )
            )

    total_liability = f_fit + f_ss_tax + f_medicare_tax
    if total_liability < 0:
        recon.findings.append(
            Finding(
                "NEGATIVE_TAX_LIABILITY",
                "critical",
                f"Total tax liability is ${total_liability} (negative).",
            )
        )

    return Form941Report(
        client_id=client_id,
        year=year,
        quarter=quarter,
        as_of=today,
        recon=recon,
        tolerance=tol,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
