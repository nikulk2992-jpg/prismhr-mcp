"""401(k) Nondiscrimination Testing + Section 125 + FSA 55% tests.

Annual tests required to keep qualified plans compliant:

  ADP (Actual Deferral Percentage) — 401(k) salary deferrals
    HCE average deferral rate cannot exceed NHCE avg by more than:
      NHCE ADP <= 2%       -> HCE ADP <= 2 * NHCE
      NHCE ADP 2-8%        -> HCE ADP <= NHCE + 2
      NHCE ADP >= 8%       -> HCE ADP <= 1.25 * NHCE

  ACP (Actual Contribution Percentage) — employer matches + after-tax
    Same statutory limits as ADP, applied to combined ER match + EE
    after-tax contributions.

  Section 125 Cafeteria Plan Nondiscrimination
    25% concentration test: sum(key-employee pre-tax) / sum(all pre-tax)
    must be <= 25%.
    Key employees = officers w/ comp > $220K (2025), >5% owners, >1%
    owners with comp > $150K.

  FSA 55% Average Benefits Test (Dependent Care FSA)
    Average NHCE benefit must be >= 55% of average HCE benefit, or the
    entire plan becomes taxable.

Finding codes:
  ADP_TEST_FAILED
  ACP_TEST_FAILED
  HCE_DETERMINATION_NEEDED      plan has no HCE classification on file
  SECTION_125_CONCENTRATION     key employees > 25% of cafeteria plan
  FSA_55_PERCENT_FAILED
  INSUFFICIENT_DATA             not enough participants to run test
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol


Severity = str

# IRS limits — 2025/2026
_HCE_COMP_THRESHOLD = Decimal("155000")   # 2025 = $155K; 2026 ~ $160K
_KEY_OFFICER_THRESHOLD = Decimal("220000")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


@dataclass
class ADPACPResult:
    hce_rate_pct: Decimal
    nhce_rate_pct: Decimal
    allowed_hce_rate_pct: Decimal
    passed: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass
class Section125Result:
    key_pretax_total: Decimal
    all_pretax_total: Decimal
    concentration_pct: Decimal
    passed: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass
class FSA55Result:
    hce_avg_benefit: Decimal
    nhce_avg_benefit: Decimal
    ratio_pct: Decimal
    passed: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass
class NDTReport:
    client_id: str
    plan_year: int
    as_of: date
    adp: ADPACPResult | None
    acp: ADPACPResult | None
    section_125: Section125Result | None
    fsa_55: FSA55Result | None

    @property
    def all_passed(self) -> bool:
        return all(
            (r is None) or r.passed
            for r in (self.adp, self.acp, self.section_125, self.fsa_55)
        )


class PrismHRReader(Protocol):
    async def list_401k_participants(
        self, client_id: str, plan_year: int
    ) -> list[dict]:
        """Rows per employee: {employeeId, ytdGross, ytdDeferral,
        ytdEmployerMatch, ytdAfterTax, isHCE, isKeyEmployee, ownerPct}"""
        ...

    async def list_section_125_participants(
        self, client_id: str, plan_year: int
    ) -> list[dict]:
        """Rows per employee: {employeeId, ytdPretaxBenefits, isKeyEmployee}"""
        ...

    async def list_dependent_care_fsa(
        self, client_id: str, plan_year: int
    ) -> list[dict]:
        """Rows per employee: {employeeId, fsaBenefit, isHCE}"""
        ...


def _allowed_hce_rate(nhce_rate: Decimal) -> Decimal:
    """Compute the ceiling HCE ADP/ACP rate given NHCE rate."""
    if nhce_rate <= Decimal("0"):
        return Decimal("0")
    if nhce_rate <= Decimal("2"):
        return nhce_rate * Decimal("2")
    if nhce_rate < Decimal("8"):
        return nhce_rate + Decimal("2")
    return nhce_rate * Decimal("1.25")


def _rate_pct(contribution: Decimal, comp: Decimal) -> Decimal:
    if comp <= 0:
        return Decimal("0")
    return (contribution / comp * Decimal("100")).quantize(Decimal("0.01"))


async def run_retirement_ndt(
    reader: PrismHRReader,
    *,
    client_id: str,
    plan_year: int,
    as_of: date | None = None,
) -> NDTReport:
    today = as_of or date.today()

    # --- ADP + ACP ---
    participants = await reader.list_401k_participants(client_id, plan_year)
    adp = _run_adp_or_acp(participants, contribution_key="ytdDeferral", test_name="ADP")
    acp = _run_adp_or_acp(
        participants,
        contribution_key="ytdEmployerMatch",
        secondary_key="ytdAfterTax",
        test_name="ACP",
    )

    # --- Section 125 concentration ---
    s125_rows = await reader.list_section_125_participants(client_id, plan_year)
    section_125 = _run_section_125(s125_rows)

    # --- FSA 55% ---
    fsa_rows = await reader.list_dependent_care_fsa(client_id, plan_year)
    fsa_55 = _run_fsa_55(fsa_rows)

    return NDTReport(
        client_id=client_id,
        plan_year=plan_year,
        as_of=today,
        adp=adp,
        acp=acp,
        section_125=section_125,
        fsa_55=fsa_55,
    )


def _run_adp_or_acp(
    participants: list[dict],
    *,
    contribution_key: str,
    secondary_key: str | None = None,
    test_name: str,
) -> ADPACPResult:
    findings: list[Finding] = []
    if not participants:
        findings.append(
            Finding(
                "INSUFFICIENT_DATA",
                "warning",
                f"{test_name} test skipped — no participants in plan year.",
            )
        )
        return ADPACPResult(
            hce_rate_pct=Decimal("0"),
            nhce_rate_pct=Decimal("0"),
            allowed_hce_rate_pct=Decimal("0"),
            passed=True,
            findings=findings,
        )

    hce_rates: list[Decimal] = []
    nhce_rates: list[Decimal] = []
    hce_missing_flag = False

    for p in participants:
        comp = _dec(p.get("ytdGross"))
        contrib = _dec(p.get(contribution_key))
        if secondary_key:
            contrib += _dec(p.get(secondary_key))
        rate = _rate_pct(contrib, comp)
        is_hce = p.get("isHCE")
        if is_hce is None:
            # Fall back to comp-threshold heuristic
            is_hce = comp >= _HCE_COMP_THRESHOLD
            hce_missing_flag = True
        if is_hce:
            hce_rates.append(rate)
        else:
            nhce_rates.append(rate)

    hce_avg = _avg(hce_rates)
    nhce_avg = _avg(nhce_rates)
    allowed = _allowed_hce_rate(nhce_avg)
    passed = hce_avg <= allowed

    if hce_missing_flag:
        findings.append(
            Finding(
                "HCE_DETERMINATION_NEEDED",
                "warning",
                f"{test_name}: HCE flag missing on some participants; "
                f"used comp > ${_HCE_COMP_THRESHOLD} heuristic. Confirm HCE "
                f"classification with plan TPA.",
            )
        )
    if not passed:
        code = f"{test_name}_TEST_FAILED"
        findings.append(
            Finding(
                code,
                "critical",
                f"{test_name} HCE rate {hce_avg}% exceeds allowed {allowed}% "
                f"(NHCE avg {nhce_avg}%). Plan requires corrective action — "
                f"return excess contributions or QNEC.",
            )
        )

    return ADPACPResult(
        hce_rate_pct=hce_avg,
        nhce_rate_pct=nhce_avg,
        allowed_hce_rate_pct=allowed,
        passed=passed,
        findings=findings,
    )


def _run_section_125(rows: list[dict]) -> Section125Result:
    findings: list[Finding] = []
    if not rows:
        return Section125Result(
            key_pretax_total=Decimal("0"),
            all_pretax_total=Decimal("0"),
            concentration_pct=Decimal("0"),
            passed=True,
            findings=[Finding("INSUFFICIENT_DATA", "warning", "No §125 participants.")],
        )
    key_total = Decimal("0")
    all_total = Decimal("0")
    for r in rows:
        pretax = _dec(r.get("ytdPretaxBenefits"))
        all_total += pretax
        if r.get("isKeyEmployee"):
            key_total += pretax
    if all_total <= 0:
        return Section125Result(
            key_pretax_total=Decimal("0"),
            all_pretax_total=Decimal("0"),
            concentration_pct=Decimal("0"),
            passed=True,
            findings=[Finding("INSUFFICIENT_DATA", "info", "No pre-tax benefits elected.")],
        )
    concentration = (key_total / all_total * Decimal("100")).quantize(Decimal("0.01"))
    passed = concentration <= Decimal("25")
    if not passed:
        findings.append(
            Finding(
                "SECTION_125_CONCENTRATION",
                "critical",
                f"Key employees hold {concentration}% of cafeteria-plan "
                f"pre-tax benefits (${key_total} of ${all_total}); "
                f"statutory ceiling is 25%. Plan becomes discriminatory — "
                f"key employees lose pre-tax treatment.",
            )
        )
    return Section125Result(
        key_pretax_total=key_total,
        all_pretax_total=all_total,
        concentration_pct=concentration,
        passed=passed,
        findings=findings,
    )


def _run_fsa_55(rows: list[dict]) -> FSA55Result:
    findings: list[Finding] = []
    if not rows:
        return FSA55Result(
            hce_avg_benefit=Decimal("0"),
            nhce_avg_benefit=Decimal("0"),
            ratio_pct=Decimal("0"),
            passed=True,
            findings=[Finding("INSUFFICIENT_DATA", "info", "No DCFSA participants.")],
        )
    hce_benefits: list[Decimal] = []
    nhce_benefits: list[Decimal] = []
    for r in rows:
        b = _dec(r.get("fsaBenefit"))
        if r.get("isHCE"):
            hce_benefits.append(b)
        else:
            nhce_benefits.append(b)
    hce_avg = _avg(hce_benefits)
    nhce_avg = _avg(nhce_benefits)
    if hce_avg <= 0:
        return FSA55Result(
            hce_avg_benefit=Decimal("0"),
            nhce_avg_benefit=nhce_avg,
            ratio_pct=Decimal("0"),
            passed=True,
            findings=[Finding("INSUFFICIENT_DATA", "info", "No HCE DCFSA elections.")],
        )
    ratio = (nhce_avg / hce_avg * Decimal("100")).quantize(Decimal("0.01"))
    passed = ratio >= Decimal("55")
    if not passed:
        findings.append(
            Finding(
                "FSA_55_PERCENT_FAILED",
                "critical",
                f"NHCE avg DCFSA benefit ${nhce_avg} is {ratio}% of HCE avg "
                f"${hce_avg}; statutory floor 55%. Entire plan becomes taxable.",
            )
        )
    return FSA55Result(
        hce_avg_benefit=hce_avg,
        nhce_avg_benefit=nhce_avg,
        ratio_pct=ratio,
        passed=passed,
        findings=findings,
    )


def _avg(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    total = sum(values, Decimal("0"))
    return (total / Decimal(len(values))).quantize(Decimal("0.01"))


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")
