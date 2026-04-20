"""Prior-PEO YTD conversion reconciliation.

Scenario: a client switches to Simploy mid-year from another PEO (ADP
TotalSource, TriNet, Insperity, Paychex PEO, etc). The prior PEO's
YTD wages + YTD taxes for every employee must be loaded into PrismHR
at conversion so that:
  * FICA wage-base caps apply correctly (SS $168,600 / $176,100)
  * 401(k) 402(g) annual limits are respected
  * Supplemental wage $1M threshold tracks correctly
  * W-2 at year end aggregates both PEO periods

Drift between the prior-PEO YTD statement and what got loaded is the
single biggest source of year-end W-2 reissues.

Findings per employee:
  YTD_NOT_LOADED            prior-PEO statement shows wages, PrismHR YTD = 0
  WAGE_MISMATCH             loaded YTD != prior-PEO YTD (over tolerance)
  FIT_MISMATCH              FIT withholding differs
  SS_WAGE_CAP_EXCEEDED      combined SS wages exceed SS wage base
  MEDICARE_WAGE_MISMATCH    Medicare wage side drift
  401K_YTD_MISSING          YTD deferrals not loaded — will violate 402(g)
  STATE_WAGE_MISMATCH       state-level YTD not carried over
  NO_PRIOR_STATEMENT        employee active at conversion but no prior
                             statement on file — likely missing load
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str
_SS_WAGE_BASE_2025 = Decimal("168600")
_SS_WAGE_BASE_2026 = Decimal("176100")
_402G_LIMIT = Decimal("23500")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class EmployeeConversionAudit:
    employee_id: str
    prior_peo_ytd_wages: Decimal
    loaded_ytd_wages: Decimal
    prior_peo_ytd_fit: Decimal
    loaded_ytd_fit: Decimal
    prior_peo_ytd_ss_wages: Decimal
    loaded_ytd_ss_wages: Decimal
    prior_peo_ytd_401k: Decimal
    loaded_ytd_401k: Decimal
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ConversionReport:
    client_id: str
    conversion_date: date
    tax_year: int
    as_of: date
    employees: list[EmployeeConversionAudit]

    @property
    def flagged(self) -> int:
        return sum(1 for e in self.employees if e.findings)

    @property
    def clean(self) -> int:
        return sum(1 for e in self.employees if not e.findings)


class PrismHRReader(Protocol):
    async def list_prior_peo_statements(
        self, client_id: str, conversion_date: date
    ) -> list[dict]:
        """Rows: {employeeId, priorYtdWages, priorYtdFit,
        priorYtdSSWages, priorYtdMedicareWages, priorYtd401k,
        priorStateYtd: {state: wages}}"""
        ...

    async def list_current_ytd(
        self, client_id: str, tax_year: int
    ) -> list[dict]:
        """Rows: {employeeId, ytdGross, ytdFit, ytdSSWages,
        ytdMedicareWages, ytd401kDeferrals, ytdStateWages: {state: wages}}"""
        ...

    async def list_active_employees_at(
        self, client_id: str, at_date: date
    ) -> list[str]:
        ...


async def run_prior_peo_conversion_recon(
    reader: PrismHRReader,
    *,
    client_id: str,
    conversion_date: date,
    tax_year: int | None = None,
    as_of: date | None = None,
    tolerance: Decimal | str = "1.00",
) -> ConversionReport:
    today = as_of or date.today()
    year = tax_year or conversion_date.year
    tol = Decimal(str(tolerance))
    ss_cap = _SS_WAGE_BASE_2026 if year >= 2026 else _SS_WAGE_BASE_2025

    statements = await reader.list_prior_peo_statements(client_id, conversion_date)
    current = await reader.list_current_ytd(client_id, year)
    active = await reader.list_active_employees_at(client_id, conversion_date)

    prior_by_id = {str(s.get("employeeId") or ""): s for s in statements}
    curr_by_id = {str(c.get("employeeId") or ""): c for c in current}
    all_ids = set(prior_by_id) | set(curr_by_id) | {str(a) for a in active}

    audits: list[EmployeeConversionAudit] = []
    for eid in sorted(all_ids):
        if not eid:
            continue
        prior = prior_by_id.get(eid, {})
        curr = curr_by_id.get(eid, {})

        pr_wages = _dec(prior.get("priorYtdWages"))
        pr_fit = _dec(prior.get("priorYtdFit"))
        pr_ss = _dec(prior.get("priorYtdSSWages"))
        pr_mc = _dec(prior.get("priorYtdMedicareWages"))
        pr_401k = _dec(prior.get("priorYtd401k"))

        ld_wages = _dec(curr.get("ytdGross"))
        ld_fit = _dec(curr.get("ytdFit"))
        ld_ss = _dec(curr.get("ytdSSWages"))
        ld_mc = _dec(curr.get("ytdMedicareWages"))
        ld_401k = _dec(curr.get("ytd401kDeferrals"))

        audit = EmployeeConversionAudit(
            employee_id=eid,
            prior_peo_ytd_wages=pr_wages,
            loaded_ytd_wages=ld_wages,
            prior_peo_ytd_fit=pr_fit,
            loaded_ytd_fit=ld_fit,
            prior_peo_ytd_ss_wages=pr_ss,
            loaded_ytd_ss_wages=ld_ss,
            prior_peo_ytd_401k=pr_401k,
            loaded_ytd_401k=ld_401k,
        )

        has_prior = bool(prior)
        is_active = eid in {str(a) for a in active}

        if is_active and not has_prior and pr_wages == 0:
            audit.findings.append(
                Finding(
                    "NO_PRIOR_STATEMENT",
                    "critical",
                    f"Employee {eid} active at conversion but no prior-PEO "
                    f"YTD statement on file. Load statement before first "
                    f"Simploy payroll.",
                )
            )

        if has_prior:
            if pr_wages > 0 and ld_wages <= tol:
                audit.findings.append(
                    Finding(
                        "YTD_NOT_LOADED",
                        "critical",
                        f"Prior-PEO YTD wages ${pr_wages} not loaded "
                        f"(PrismHR YTD = $0).",
                    )
                )
            else:
                if (pr_wages - ld_wages).copy_abs() > tol:
                    audit.findings.append(
                        Finding(
                            "WAGE_MISMATCH",
                            "critical",
                            f"Prior YTD wages ${pr_wages}, loaded ${ld_wages}, "
                            f"delta ${pr_wages - ld_wages}.",
                        )
                    )
                if (pr_fit - ld_fit).copy_abs() > tol:
                    audit.findings.append(
                        Finding(
                            "FIT_MISMATCH",
                            "critical",
                            f"Prior FIT ${pr_fit}, loaded ${ld_fit}, "
                            f"delta ${pr_fit - ld_fit}.",
                        )
                    )
                if (pr_ss - ld_ss).copy_abs() > tol:
                    audit.findings.append(
                        Finding(
                            "SS_WAGE_MISMATCH",
                            "critical",
                            f"Prior SS wages ${pr_ss}, loaded ${ld_ss}.",
                        )
                    )
                if (pr_mc - ld_mc).copy_abs() > tol:
                    audit.findings.append(
                        Finding(
                            "MEDICARE_WAGE_MISMATCH",
                            "warning",
                            f"Prior Medicare wages ${pr_mc}, loaded ${ld_mc}.",
                        )
                    )
                if pr_401k > 0 and ld_401k <= tol:
                    audit.findings.append(
                        Finding(
                            "401K_YTD_MISSING",
                            "critical",
                            f"Prior 401(k) YTD ${pr_401k} not loaded. Will "
                            f"violate 402(g) $23,500 annual limit by year-end.",
                        )
                    )

            # Combined SS wages vs cap
            combined_ss = ld_ss if ld_ss > 0 else pr_ss
            if combined_ss > ss_cap + tol:
                audit.findings.append(
                    Finding(
                        "SS_WAGE_CAP_EXCEEDED",
                        "warning",
                        f"Combined SS wages ${combined_ss} exceed ${year} cap "
                        f"${ss_cap}. Verify overcontribution returned to employee.",
                    )
                )

            # State YTD
            pr_state = prior.get("priorStateYtd") or {}
            ld_state = curr.get("ytdStateWages") or {}
            for state, pr_amt in pr_state.items():
                pr_dec = _dec(pr_amt)
                ld_dec = _dec(ld_state.get(state))
                if (pr_dec - ld_dec).copy_abs() > tol:
                    audit.findings.append(
                        Finding(
                            "STATE_WAGE_MISMATCH",
                            "critical",
                            f"{state}: prior ${pr_dec}, loaded ${ld_dec}.",
                        )
                    )

        audits.append(audit)

    return ConversionReport(
        client_id=client_id,
        conversion_date=conversion_date,
        tax_year=year,
        as_of=today,
        employees=audits,
    )


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
