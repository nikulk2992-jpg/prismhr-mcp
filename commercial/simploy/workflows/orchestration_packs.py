"""Orchestration packs — meta-workflows that chain existing findings.

Each pack is a single entry point that runs a curated sequence of
workflow checks and rolls their findings up into one report. Designed
so an agent can say "run month-end close for client <client_id>" and get
back a single structured answer — not orchestrate 10 calls by hand.

Packs:

  MonthEndClosePack
    Pre-close readiness for every payroll run in the month.
    Chain: payroll_batch_health -> voucher_classification_audit ->
           gl_template_integrity -> payroll_journal_preflight
    Exit non-zero if any step flags critical.

  QuarterEndClosePack
    Reconcile + file-ready for the quarter.
    Chain: form_941_reconciliation -> state_withholding_recon ->
           tax_remittance_tracking -> state_filings_orchestrator
    Marks which states are "ready to file" vs "blocked."

  YearEndClosePack
    W-2 + 1095 + 1099 + 401k test readiness.
    Chain: w2_readiness -> form_1095c_consistency -> irs_air_preflight ->
           form_1099_nec_preflight -> retirement_ndt (ADP/ACP/125/FSA55)

  NewClientGoLivePack
    End-to-end onboarding verification for a freshly-converted client.
    Chain: client_golive_readiness -> prior_peo_conversion_recon ->
           state_tax_setup -> gl_template_integrity -> benefit_rate_drift

  PayrollRunPreflightPack
    Two-minute check before running any payroll.
    Chain: voucher_classification_audit -> payroll_batch_health ->
           gl_template_integrity -> payroll_journal_preflight

Each pack yields PackResult with:
  * per-step finding tally (critical / warning / info)
  * ready-to-proceed boolean
  * step-by-step sub-report references for drill-down

The pack never re-implements finding logic — it only chains existing
workflows and aggregates. This keeps the packs thin and stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable


Severity = str


@dataclass
class StepSummary:
    name: str
    critical: int = 0
    warning: int = 0
    info: int = 0
    blocked: bool = False
    sub_report: Any = None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.critical == 0 and not self.blocked and not self.error


@dataclass
class PackResult:
    pack_name: str
    client_id: str
    as_of: date
    steps: list[StepSummary] = field(default_factory=list)

    @property
    def ready_to_proceed(self) -> bool:
        return all(s.ok for s in self.steps)

    @property
    def total_critical(self) -> int:
        return sum(s.critical for s in self.steps)

    @property
    def total_warning(self) -> int:
        return sum(s.warning for s in self.steps)


def _tally(findings_iter) -> tuple[int, int, int]:
    critical = warning = info = 0
    for f in findings_iter:
        sev = (getattr(f, "severity", "") or "").lower()
        if sev == "critical":
            critical += 1
        elif sev == "warning":
            warning += 1
        elif sev == "info":
            info += 1
    return critical, warning, info


def _collect_findings(report: Any) -> list:
    """Flatten every `findings` list attached to a report or its children."""
    out: list = []

    def walk(obj: Any) -> None:
        if obj is None:
            return
        findings = getattr(obj, "findings", None)
        if isinstance(findings, list):
            out.extend(findings)
        # walk through common container attributes
        for attr in (
            "batches", "vouchers", "employees", "bonuses", "separations",
            "hires", "contractors", "lines", "keys", "states", "rows",
            "audits", "lists",
        ):
            coll = getattr(obj, attr, None)
            if isinstance(coll, list):
                for item in coll:
                    walk(item)
        # Aggregate report fields
        for attr in (
            "recon", "adp", "acp", "section_125", "fsa_55", "summary",
        ):
            child = getattr(obj, attr, None)
            if child is not None:
                walk(child)
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)

    walk(report)
    return out


async def _run_step(name: str, coro_factory: Callable[[], Any]) -> StepSummary:
    step = StepSummary(name=name)
    try:
        report = await coro_factory()
    except Exception as exc:  # noqa: BLE001
        step.error = f"{type(exc).__name__}: {str(exc)[:120]}"
        step.blocked = True
        return step
    step.sub_report = report
    c, w, i = _tally(_collect_findings(report))
    step.critical = c
    step.warning = w
    step.info = i
    return step


# -----------------------------------------------------------------------------
# Pack runners — each takes a dict of ready-to-call async callables keyed by
# workflow name. This keeps packs decoupled from adapter bootstrap.
# -----------------------------------------------------------------------------


async def run_month_end_close_pack(
    *, client_id: str, as_of: date | None = None,
    steps: dict[str, Callable[[], Any]],
) -> PackResult:
    today = as_of or date.today()
    result = PackResult(pack_name="MonthEndClosePack", client_id=client_id, as_of=today)
    for name in (
        "payroll_batch_health",
        "voucher_classification_audit",
        "gl_template_integrity",
        "payroll_journal_preflight",
    ):
        if name not in steps:
            continue
        result.steps.append(await _run_step(name, steps[name]))
    return result


async def run_quarter_end_close_pack(
    *, client_id: str, as_of: date | None = None,
    steps: dict[str, Callable[[], Any]],
) -> PackResult:
    today = as_of or date.today()
    result = PackResult(pack_name="QuarterEndClosePack", client_id=client_id, as_of=today)
    for name in (
        "form_941_reconciliation",
        "state_withholding_recon",
        "tax_remittance_tracking",
        "state_filings_orchestrator",
    ):
        if name not in steps:
            continue
        result.steps.append(await _run_step(name, steps[name]))
    return result


async def run_year_end_close_pack(
    *, client_id: str, as_of: date | None = None,
    steps: dict[str, Callable[[], Any]],
) -> PackResult:
    today = as_of or date.today()
    result = PackResult(pack_name="YearEndClosePack", client_id=client_id, as_of=today)
    for name in (
        "w2_readiness",
        "form_1095c_consistency",
        "irs_air_preflight",
        "form_1099_nec_preflight",
        "retirement_ndt",
    ):
        if name not in steps:
            continue
        result.steps.append(await _run_step(name, steps[name]))
    return result


async def run_new_client_golive_pack(
    *, client_id: str, as_of: date | None = None,
    steps: dict[str, Callable[[], Any]],
) -> PackResult:
    today = as_of or date.today()
    result = PackResult(pack_name="NewClientGoLivePack", client_id=client_id, as_of=today)
    for name in (
        "client_golive_readiness",
        "prior_peo_conversion_recon",
        "state_tax_setup",
        "gl_template_integrity",
        "benefit_rate_drift",
    ):
        if name not in steps:
            continue
        result.steps.append(await _run_step(name, steps[name]))
    return result


async def run_payroll_run_preflight_pack(
    *, client_id: str, as_of: date | None = None,
    steps: dict[str, Callable[[], Any]],
) -> PackResult:
    today = as_of or date.today()
    result = PackResult(pack_name="PayrollRunPreflightPack", client_id=client_id, as_of=today)
    for name in (
        "voucher_classification_audit",
        "payroll_batch_health",
        "gl_template_integrity",
        "payroll_journal_preflight",
    ):
        if name not in steps:
            continue
        result.steps.append(await _run_step(name, steps[name]))
    return result
