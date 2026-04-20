"""Diff workflow: reference tax engine vs PrismHR voucher withholding.

For each voucher in a period:
  1. Compute what our reference engine would withhold (federal + MO + IL)
  2. Extract what the voucher actually withheld
  3. Flag deltas > tolerance
  4. Run multi_state voucher validator for cross-state correctness

Most valuable output: the MULTI_STATE findings. Vertex/Symmetry do
the math right; PrismHR feeds them inputs. This workflow checks
whether those inputs produced the right outputs given the employee's
home/work-state profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from simploy.tax_engine.engine import StateCalcInput, compute_state
from simploy.tax_engine.federal import FederalCalcInput, compute_federal
from simploy.tax_engine.multi_state import analyze_voucher as analyze_multi_state


Severity = str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class VoucherDiff:
    voucher_id: str
    employee_id: str
    home_state: str
    work_state: str
    reference_fit: Decimal
    actual_fit: Decimal
    reference_ss: Decimal
    actual_ss: Decimal
    reference_medicare: Decimal
    actual_medicare: Decimal
    reference_state_tax: Decimal = Decimal("0")
    actual_state_tax: Decimal = Decimal("0")
    state_engine_confidence: str = "NONE"
    findings: list[Finding] = field(default_factory=list)


@dataclass
class TaxEngineDiffReport:
    client_id: str
    period_start: date
    period_end: date
    as_of: date
    vouchers: list[VoucherDiff]

    @property
    def flagged(self) -> int:
        return sum(1 for v in self.vouchers if v.findings)


class PrismHRReader(Protocol):
    async def list_vouchers_for_period(
        self, client_id: str, start: date, end: date
    ) -> list[dict]: ...
    async def get_employee_profile(
        self, client_id: str, employee_id: str
    ) -> dict:
        """{ homeState, filingStatus, payPeriodsPerYear, hasNRCert,
             ytdSSWages, ytdMedicareWages, ytdFutaWages, isResident*,
             basicAllowances, additionalAllowances }"""
        ...

    async def get_location_state_map(
        self, client_id: str
    ) -> dict[str, str]:
        """Return { locationName -> stateAbbrev } for all WSL of a
        client. Enables per-line state allocation. Implementations
        may return {} if unavailable; the validator degrades gracefully."""
        ...


def _dec(raw) -> Decimal:
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _extract_actuals(voucher: dict) -> dict:
    """Pull what PrismHR actually withheld from the voucher tax rows."""
    out = {
        "fit": Decimal("0"),
        "ss": Decimal("0"),
        "medicare": Decimal("0"),
        "state_by_code": {},
    }
    for t in (voucher.get("employeeTax") or []):
        code = str(t.get("empTaxDeductCode") or "")
        amt = _dec(t.get("empTaxAmount"))
        if code.startswith("00-10"):
            out["fit"] += amt
        elif code.startswith("00-11"):
            out["medicare"] += amt
        elif code.startswith("00-12"):
            out["ss"] += amt
    return out


async def run_tax_engine_diff(
    reader: PrismHRReader,
    *,
    client_id: str,
    period_start: date,
    period_end: date,
    as_of: date | None = None,
    fit_tolerance: Decimal | str = "2.00",
    fica_tolerance: Decimal | str = "0.05",
) -> TaxEngineDiffReport:
    today = as_of or date.today()
    fit_tol = Decimal(str(fit_tolerance))
    fica_tol = Decimal(str(fica_tolerance))

    vouchers = await reader.list_vouchers_for_period(
        client_id, period_start, period_end
    )

    # Pull the WSL location -> state map once per client
    try:
        location_state_map = await reader.get_location_state_map(client_id)
    except Exception:  # noqa: BLE001
        location_state_map = {}

    profile_cache: dict[str, dict] = {}

    async def profile(eid: str) -> dict:
        if eid not in profile_cache:
            try:
                profile_cache[eid] = await reader.get_employee_profile(
                    client_id, eid
                ) or {}
            except Exception:  # noqa: BLE001
                profile_cache[eid] = {}
        return profile_cache[eid]

    diffs: list[VoucherDiff] = []
    for v in vouchers:
        eid = str(v.get("employeeId") or "")
        vid = str(v.get("voucherId") or "")
        if not eid or not vid:
            continue
        prof = await profile(eid)
        wages = _dec(v.get("totalEarnings"))
        periods = int(prof.get("payPeriodsPerYear") or 52)

        # Reference federal
        ref = compute_federal(FederalCalcInput(
            gross_wages_period=wages,
            pay_periods_per_year=periods,
            filing_status=prof.get("filingStatus") or "S",
            ytd_ss_wages=_dec(prof.get("ytdSSWages")),
            ytd_medicare_wages=_dec(prof.get("ytdMedicareWages")),
            ytd_futa_wages=_dec(prof.get("ytdFutaWages")),
        ))

        actuals = _extract_actuals(v)
        work_state = str(v.get("wcState") or "").upper()
        home_state = str(prof.get("homeState") or "").upper()

        d = VoucherDiff(
            voucher_id=vid,
            employee_id=eid,
            home_state=home_state,
            work_state=work_state,
            reference_fit=ref.fit_period,
            actual_fit=actuals["fit"],
            reference_ss=ref.ss_ee_period,
            actual_ss=actuals["ss"],
            reference_medicare=ref.medicare_ee_period,
            actual_medicare=actuals["medicare"],
        )

        # Compare — FIT has looser tolerance (annualization vs cumulative)
        if (ref.fit_period - actuals["fit"]).copy_abs() > fit_tol:
            d.findings.append(Finding(
                "FIT_DELTA",
                "warning",
                f"Reference FIT ${ref.fit_period} vs actual ${actuals['fit']} "
                f"(delta ${ref.fit_period - actuals['fit']}).",
            ))
        if (ref.ss_ee_period - actuals["ss"]).copy_abs() > fica_tol:
            d.findings.append(Finding(
                "SS_DELTA",
                "critical",
                f"Reference SS ${ref.ss_ee_period} vs actual ${actuals['ss']}.",
            ))
        if (ref.medicare_ee_period - actuals["medicare"]).copy_abs() > fica_tol:
            d.findings.append(Finding(
                "MEDICARE_DELTA",
                "critical",
                f"Reference Medicare ${ref.medicare_ee_period} vs actual "
                f"${actuals['medicare']}.",
            ))

        # Multi-state voucher validation — the HIGH value check.
        # Passes in the WSL location -> state map so per-line work
        # allocation is checked against tax-withholding distribution.
        if home_state:
            ms = analyze_multi_state(
                v, home_state=home_state,
                has_nr_cert=bool(prof.get("hasNRCert")),
                location_state_map=location_state_map,
            )
            for f in ms.findings:
                d.findings.append(Finding(f.code, f.severity, f.message))

        # State-engine diff (per-state reference calc vs actual)
        if work_state:
            # Actual state tax pulled from voucher: first -20 line whose
            # desc contains the work-state abbrev
            actual_state = Decimal("0")
            for t in (v.get("employeeTax") or []):
                code = str(t.get("empTaxDeductCode") or "")
                desc = str(t.get("empTaxDeductCodeDesc") or "").upper()
                if "-20" in code and work_state in desc:
                    actual_state += _dec(t.get("empTaxAmount"))
            d.actual_state_tax = actual_state

            state_inp = StateCalcInput(
                work_state=work_state,
                home_state=home_state or work_state,
                gross_wages_period=wages,
                pay_periods_per_year=periods,
                filing_status=prof.get("filingStatus") or "S",
                allowances=int(prof.get("stateAllowances") or 0),
                has_nr_cert=bool(prof.get("hasNRCert")),
                work_state_withholding_period=actual_state,
            )
            try:
                state_out = compute_state(state_inp)
            except Exception:  # noqa: BLE001
                state_out = None
            if state_out is not None:
                d.reference_state_tax = state_out.expected_withholding_period
                d.state_engine_confidence = state_out.confidence
                # Only flag HIGH-confidence states to avoid false positives
                # from CA/NY approximations.
                if state_out.confidence == "HIGH":
                    delta = (state_out.expected_withholding_period - actual_state)
                    if delta.copy_abs() > Decimal("1.00"):
                        d.findings.append(Finding(
                            "STATE_TAX_DELTA",
                            "warning",
                            f"{work_state} reference ${state_out.expected_withholding_period} "
                            f"vs actual ${actual_state} (delta ${delta}). "
                            f"Confidence HIGH.",
                        ))

        diffs.append(d)

    return TaxEngineDiffReport(
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        as_of=today,
        vouchers=diffs,
    )
