"""Bonus gross-up audit — verifies supplemental wage tax calcs.

IRS allows two methods for withholding on supplemental wages (bonuses,
commissions, severance, back pay):
  FLAT_22    22% flat federal rate (25% still used by some old systems)
  AGGREGATE  add to regular wages and compute combined rate

For amounts over $1M in a year, 37% mandatory on the excess.

Gross-up: to guarantee an employee nets $X, employer computes gross
such that gross - taxes = net. Formula differs by method and employee
state/locality.

This workflow checks:
  * Bonus vouchers used the correct method
  * Aggregate-method vouchers correctly annualized
  * Over-$1M employees got 37% on the excess
  * Gross-up math ties to target-net when gross-up is requested
  * State supplemental rates applied correctly

Finding codes:
  WRONG_SUPPLEMENTAL_RATE   applied rate != expected for method/amount
  OVER_1M_NO_37PCT          over-$1M excess not taxed at 37%
  GROSS_UP_MISMATCH         gross-up result ≠ declared target net
  STATE_SUPP_RATE_WRONG     state supplemental rate not applied or wrong
  MIXED_METHODS             same voucher mixes methods
  AGGREGATE_NOT_ANNUALIZED  aggregate method but no regular-wage context
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

_FLAT_FED_RATE = Decimal("0.22")
_OVER_1M_RATE = Decimal("0.37")
_OVER_1M_THRESHOLD = Decimal("1000000")


# Selected state supplemental rates (as of 2026). States with no income
# tax or no separate supp rate not listed.
_STATE_SUPP_RATES: dict[str, Decimal] = {
    "CA": Decimal("0.1023"),   # varies by bonus vs stock
    "CO": Decimal("0.044"),
    "CT": Decimal("0.0699"),
    "GA": Decimal("0.0539"),
    "IL": Decimal("0.0495"),
    "IN": Decimal("0.0315"),
    "KY": Decimal("0.045"),
    "MA": Decimal("0.05"),
    "MD": Decimal("0.055"),
    "MI": Decimal("0.0425"),
    "MN": Decimal("0.068"),
    "MO": Decimal("0.0480"),
    "NC": Decimal("0.0450"),
    "NJ": Decimal("0.0637"),
    "NM": Decimal("0.059"),
    "NY": Decimal("0.1123"),
    "OH": Decimal("0.035"),
    "OR": Decimal("0.08"),
    "PA": Decimal("0.0307"),
    "VA": Decimal("0.0575"),
    "VT": Decimal("0.06"),
    "WI": Decimal("0.0753"),
}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class BonusAudit:
    voucher_id: str
    employee_id: str
    method: str
    amount: Decimal
    federal_withheld: Decimal
    state_withheld: Decimal
    target_net: Decimal
    actual_net: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class BonusReport:
    client_id: str
    as_of: date
    bonuses: list[BonusAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for b in self.bonuses if b.findings)


class PrismHRReader(Protocol):
    async def list_bonus_vouchers(
        self, client_id: str, period_start: date, period_end: date
    ) -> list[dict]:
        """Rows: {voucherId, employeeId, supplementalMethod (FLAT_22|AGGREGATE),
        supplementalAmount, federalWithheld, stateWithheld, workState,
        ytdSupplementalWages, netPay, targetNetRequested, isGrossUp}"""
        ...


async def run_bonus_gross_up_audit(
    reader: PrismHRReader,
    *,
    client_id: str,
    period_start: date,
    period_end: date,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
) -> BonusReport:
    today = as_of or date.today()
    tol = Decimal(str(tolerance))
    rows = await reader.list_bonus_vouchers(client_id, period_start, period_end)

    audits: list[BonusAudit] = []
    for row in rows:
        vid = str(row.get("voucherId") or "")
        eid = str(row.get("employeeId") or "")
        method = str(row.get("supplementalMethod") or "").upper()
        amount = _dec(row.get("supplementalAmount"))
        fed = _dec(row.get("federalWithheld"))
        st = _dec(row.get("stateWithheld"))
        state = str(row.get("workState") or "").upper()
        ytd = _dec(row.get("ytdSupplementalWages"))
        target_net = _dec(row.get("targetNetRequested"))
        actual_net = _dec(row.get("netPay"))
        is_gu = bool(row.get("isGrossUp"))

        audit = BonusAudit(
            voucher_id=vid,
            employee_id=eid,
            method=method,
            amount=amount,
            federal_withheld=fed,
            state_withheld=st,
            target_net=target_net,
            actual_net=actual_net,
        )

        if method not in {"FLAT_22", "AGGREGATE"}:
            audit.findings.append(
                Finding(
                    "MIXED_METHODS",
                    "critical",
                    f"Supplemental method '{method}' is not FLAT_22 or AGGREGATE.",
                )
            )

        # Federal rate check
        if method == "FLAT_22":
            ytd_after = ytd + amount
            if ytd < _OVER_1M_THRESHOLD and ytd_after > _OVER_1M_THRESHOLD:
                # Split: portion under threshold at 22%, portion over at 37%
                under = _OVER_1M_THRESHOLD - ytd
                over = ytd_after - _OVER_1M_THRESHOLD
                expected_fed = (under * _FLAT_FED_RATE + over * _OVER_1M_RATE
                                ).quantize(Decimal("0.01"))
            elif ytd >= _OVER_1M_THRESHOLD:
                expected_fed = (amount * _OVER_1M_RATE).quantize(Decimal("0.01"))
                if fed + tol < expected_fed:
                    audit.findings.append(
                        Finding(
                            "OVER_1M_NO_37PCT",
                            "critical",
                            f"Employee has YTD supp wages ${ytd} > $1M; "
                            f"expected 37% = ${expected_fed}, withheld ${fed}.",
                        )
                    )
                    audits.append(audit)
                    continue
            else:
                expected_fed = (amount * _FLAT_FED_RATE).quantize(Decimal("0.01"))

            if (fed - expected_fed).copy_abs() > tol:
                audit.findings.append(
                    Finding(
                        "WRONG_SUPPLEMENTAL_RATE",
                        "critical",
                        f"FLAT_22 method: expected fed withholding ${expected_fed} "
                        f"on ${amount}, actual ${fed}.",
                    )
                )

        # State supplemental rate check
        if state and state in _STATE_SUPP_RATES:
            expected_st = (amount * _STATE_SUPP_RATES[state]).quantize(Decimal("0.01"))
            if (st - expected_st).copy_abs() > tol:
                audit.findings.append(
                    Finding(
                        "STATE_SUPP_RATE_WRONG",
                        "warning",
                        f"{state} supplemental rate {_STATE_SUPP_RATES[state]} — "
                        f"expected ${expected_st}, actual ${st}.",
                    )
                )

        # Gross-up tie-out
        if is_gu and target_net > 0:
            if (actual_net - target_net).copy_abs() > tol:
                audit.findings.append(
                    Finding(
                        "GROSS_UP_MISMATCH",
                        "critical",
                        f"Gross-up targeted net ${target_net}, actual net ${actual_net} "
                        f"(delta ${actual_net - target_net}).",
                    )
                )

        # Aggregate sanity
        if method == "AGGREGATE" and not row.get("regularWageContext"):
            audit.findings.append(
                Finding(
                    "AGGREGATE_NOT_ANNUALIZED",
                    "warning",
                    "AGGREGATE method used but no regular-wage context on "
                    "voucher — annualization math can't be verified.",
                )
            )

        audits.append(audit)

    return BonusReport(client_id=client_id, as_of=today, bonuses=audits)


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
