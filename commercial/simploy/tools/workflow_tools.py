"""MCP tool wrappers for every commercial workflow.

Wires the 14 workflows + 5 orchestration packs into FastMCP-callable
tools. Each tool takes structured params (client_id + dates/year),
instantiates the appropriate live reader, runs the workflow, and
returns a Pydantic-friendly dict an agent can reason about.

Usage (in a server composition step):

    from simploy.tools.workflow_tools import register_workflow_tools
    register_workflow_tools(server, registry, prismhr_client, permissions)

Serialization:
  Workflow reports use plain dataclasses with Decimal + date fields.
  `_to_dict()` recursively coerces these to JSON-safe primitives.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.permissions import PermissionManager, Scope
from prismhr_mcp.registry import ToolRegistry

from simploy.workflows.adapters import (
    AbsenceJournalReader,
    BonusGrossUpReader,
    CobraEligibilityReader,
    DependentAgeOutReader,
    FinalPaycheckComplianceReader,
    Form1099NECPreflightReader,
    Form940ReconReader,
    Form941ReconReader,
    GarnishmentHistoryReader,
    OffCycleVoucherReader,
    PayrollBatchHealthReader,
    PTOReconciliationReader,
    ReciprocalWithholdingReader,
    RetirementLoanStatusReader,
    RetirementNDTReader,
    StateFilingsOrchestratorReader,
    StateNewHireReportingReader,
    StateWithholdingReconReader,
    TaxRemittanceReader,
    VoucherClassificationReader,
)
from simploy.workflows.absence_journal_audit import run_absence_journal_audit
from simploy.workflows.bonus_gross_up_audit import run_bonus_gross_up_audit
from simploy.workflows.cobra_eligibility_sweep import run_cobra_sweep
from simploy.workflows.dependent_age_out import run_dependent_age_out
from simploy.workflows.final_paycheck_compliance import run_final_paycheck_compliance
from simploy.workflows.form_1099_nec_preflight import run_form_1099_nec_preflight
from simploy.workflows.garnishment_history import (
    run_garnishment_history_audit as run_garnishment_history,
)
from simploy.workflows.off_cycle_payroll_audit import run_off_cycle_payroll_audit
from simploy.workflows.payroll_batch_health import run_payroll_batch_health
from simploy.workflows.pto_reconciliation import run_pto_reconciliation
from simploy.workflows.reciprocal_withholding import run_reciprocal_withholding_audit
from simploy.workflows.retirement_loan_status import run_retirement_loan_status
from simploy.workflows.retirement_ndt_suite import run_retirement_ndt
from simploy.workflows.state_new_hire_reporting import run_state_new_hire_audit
from simploy.workflows.form_940_reconciliation import run_form_940_reconciliation
from simploy.workflows.form_941_reconciliation import run_form_941_reconciliation
from simploy.workflows.state_filings_orchestrator import run_state_filings_orchestrator
from simploy.workflows.state_withholding_recon import run_state_withholding_recon
from simploy.workflows.tax_remittance_tracking import run_tax_remittance_tracking
from simploy.workflows.voucher_classification_audit import (
    run_voucher_classification_audit,
)


# -----------------------------------------------------------------------------
# Serialization
# -----------------------------------------------------------------------------


def _to_dict(obj: Any) -> Any:
    """Coerce workflow reports to JSON-safe primitives. Handles
    dataclasses, Decimal, date, enums, nested lists/dicts."""
    if obj is None:
        return None
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if is_dataclass(obj):
        return _to_dict(asdict(obj))
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [_to_dict(v) for v in obj]
    if hasattr(obj, "value") and hasattr(obj, "name"):
        # Enum-ish
        return obj.value
    return obj


def _parse_date(raw: str) -> date:
    return date.fromisoformat(raw[:10])


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------


def register_workflow_tools(
    server: FastMCP,
    registry: ToolRegistry,
    prismhr: PrismHRClient,
    permissions: PermissionManager,
) -> None:
    """Register every commercial workflow as an MCP tool.

    All tools require PAYROLL_READ scope; a few also pull benefits
    (BENEFITS_READ) or client-master (CLIENT_READ) data. Permission
    checks are left minimal — the underlying adapters already respect
    PrismHR's Allowed Methods gate."""

    # -------------------- voucher_classification_audit --------------------

    async def commercial_voucher_classification_audit(
        client_id: Annotated[str, Field(description="PrismHR client ID (6-digit).")],
        period_start: Annotated[str, Field(description="YYYY-MM-DD, pay-period start.")],
        period_end: Annotated[str, Field(description="YYYY-MM-DD, pay-period end.")],
    ) -> dict:
        """Audit a client's vouchers for classification errors before journal export.

        Catches FICA exempt misflags (the class of 941-balancing bug where
        an active W-2 employee has the FICA Exempt checkbox ticked),
        contractor-on-W2-pay-code, union code misuse, SS wage-base cap
        handling, additional-Medicare threshold, and state-SUTA mismatch
        for single-state employees.

        Use when: before closing a payroll period, running a 941, or
        onboarding a new client. Returns per-voucher findings with
        severity + remediation hints.
        """
        permissions.check(Scope.PAYROLL_READ)
        reader = VoucherClassificationReader(prismhr)
        report = await run_voucher_classification_audit(
            reader,
            client_id=client_id,
            period_start=_parse_date(period_start),
            period_end=_parse_date(period_end),
        )
        return _to_dict(report)

    registry.register(server, "commercial_voucher_classification_audit",
                      commercial_voucher_classification_audit)

    # -------------------- payroll_batch_health --------------------

    async def commercial_payroll_batch_health(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        max_days_in_init: Annotated[int, Field(description="Days before an INIT batch is stale.", ge=1)] = 3,
        max_days_awaiting_approval: Annotated[int, Field(description="Days before AP.PEND is stuck.", ge=0)] = 1,
    ) -> dict:
        """Sweep open payroll batches at a client for stuck states.

        Flags batches stuck in INIT, stuck awaiting approval, with zero
        vouchers, past pay date but not posted, or containing negative
        net pay. Use when: daily ops review, pre-close readiness.
        """
        permissions.check(Scope.PAYROLL_READ)
        reader = PayrollBatchHealthReader(prismhr)
        report = await run_payroll_batch_health(
            reader, client_id=client_id,
            max_days_in_init=max_days_in_init,
            max_days_awaiting_approval=max_days_awaiting_approval,
        )
        return _to_dict(report)

    registry.register(server, "commercial_payroll_batch_health",
                      commercial_payroll_batch_health)

    # -------------------- garnishment_history --------------------

    async def commercial_garnishment_history(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
    ) -> dict:
        """Per-employee garnishment ledger with CCPA + remit-to-agency tie-out.

        Use when: reviewing garnishment compliance, auditing court-
        ordered deductions, catching orphan garnishments.
        """
        permissions.check(Scope.PAYROLL_READ)
        reader = GarnishmentHistoryReader(prismhr)
        report = await run_garnishment_history(reader, client_id=client_id)
        return _to_dict(report)

    registry.register(server, "commercial_garnishment_history",
                      commercial_garnishment_history)

    # -------------------- absence_journal_audit --------------------

    async def commercial_absence_journal_audit(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        period_start: Annotated[str, Field(description="YYYY-MM-DD.")],
        period_end: Annotated[str, Field(description="YYYY-MM-DD.")],
    ) -> dict:
        """Absence journal audit — orphan entries, balance mismatches, overlap."""
        permissions.check(Scope.PAYROLL_READ)
        reader = AbsenceJournalReader(prismhr)
        report = await run_absence_journal_audit(
            reader, client_id=client_id,
            start=_parse_date(period_start),
            end=_parse_date(period_end),
        )
        return _to_dict(report)

    registry.register(server, "commercial_absence_journal_audit",
                      commercial_absence_journal_audit)

    # -------------------- dependent_age_out --------------------

    async def commercial_dependent_age_out(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
    ) -> dict:
        """Dependents aging out of coverage (typically 26). Flags before premium mis-bills."""
        permissions.check(Scope.PAYROLL_READ)
        reader = DependentAgeOutReader(prismhr)
        report = await run_dependent_age_out(reader, client_id=client_id)
        return _to_dict(report)

    registry.register(server, "commercial_dependent_age_out",
                      commercial_dependent_age_out)

    # -------------------- cobra_eligibility_sweep --------------------

    async def commercial_cobra_eligibility_sweep(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        lookback_days: Annotated[int, Field(description="Days to look back for terminations.", ge=1)] = 60,
    ) -> dict:
        """COBRA eligibility — qualifying events without notice within 14/44 day window."""
        permissions.check(Scope.PAYROLL_READ)
        reader = CobraEligibilityReader(prismhr)
        report = await run_cobra_sweep(
            reader, client_id=client_id, lookback_days=lookback_days,
        )
        return _to_dict(report)

    registry.register(server, "commercial_cobra_eligibility_sweep",
                      commercial_cobra_eligibility_sweep)

    # -------------------- pto_reconciliation --------------------

    async def commercial_pto_reconciliation(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
    ) -> dict:
        """PTO accrual vs used vs balance tie-out per employee."""
        permissions.check(Scope.PAYROLL_READ)
        reader = PTOReconciliationReader(prismhr)
        report = await run_pto_reconciliation(reader, client_id=client_id)
        return _to_dict(report)

    registry.register(server, "commercial_pto_reconciliation",
                      commercial_pto_reconciliation)

    # -------------------- retirement_loan_status --------------------

    async def commercial_retirement_loan_status(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
    ) -> dict:
        """401(k) loan balance + payment schedule adherence + default triggers."""
        permissions.check(Scope.PAYROLL_READ)
        reader = RetirementLoanStatusReader(prismhr)
        report = await run_retirement_loan_status(reader, client_id=client_id)
        return _to_dict(report)

    registry.register(server, "commercial_retirement_loan_status",
                      commercial_retirement_loan_status)

    # -------------------- form_1099_nec_preflight --------------------

    async def commercial_form_1099_nec_preflight(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        tax_year: Annotated[int, Field(description="Tax year, e.g. 2025.", ge=2020, le=2030)],
    ) -> dict:
        """Year-end 1099-NEC readiness. W-9 + TIN + Box 1 tie-out per contractor."""
        permissions.check(Scope.PAYROLL_READ)
        reader = Form1099NECPreflightReader(prismhr)
        report = await run_form_1099_nec_preflight(
            reader, client_id=client_id, tax_year=tax_year,
        )
        return _to_dict(report)

    registry.register(server, "commercial_form_1099_nec_preflight",
                      commercial_form_1099_nec_preflight)

    # -------------------- bonus_gross_up_audit --------------------

    async def commercial_bonus_gross_up_audit(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        period_start: Annotated[str, Field(description="YYYY-MM-DD.")],
        period_end: Annotated[str, Field(description="YYYY-MM-DD.")],
    ) -> dict:
        """Supplemental wage tax calc — FLAT_22, $1M 37% threshold, state supplemental rates."""
        permissions.check(Scope.PAYROLL_READ)
        reader = BonusGrossUpReader(prismhr)
        report = await run_bonus_gross_up_audit(
            reader, client_id=client_id,
            period_start=_parse_date(period_start),
            period_end=_parse_date(period_end),
        )
        return _to_dict(report)

    registry.register(server, "commercial_bonus_gross_up_audit",
                      commercial_bonus_gross_up_audit)

    # -------------------- retirement_ndt_suite --------------------

    async def commercial_retirement_ndt(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        plan_year: Annotated[int, Field(description="Plan year.", ge=2020, le=2030)],
    ) -> dict:
        """401(k) nondiscrimination: ADP + ACP + Section 125 concentration + FSA 55%."""
        permissions.check(Scope.PAYROLL_READ)
        reader = RetirementNDTReader(prismhr)
        report = await run_retirement_ndt(
            reader, client_id=client_id, plan_year=plan_year,
        )
        return _to_dict(report)

    registry.register(server, "commercial_retirement_ndt",
                      commercial_retirement_ndt)

    # -------------------- reciprocal_withholding_audit --------------------

    async def commercial_reciprocal_withholding(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        period_start: Annotated[str, Field(description="YYYY-MM-DD.")],
        period_end: Annotated[str, Field(description="YYYY-MM-DD.")],
    ) -> dict:
        """Multi-state resident vs work-state withholding check.

        41 reciprocity pairs (OH/KY, IL/WI, MD/DC, PA/NJ, etc.).
        Flags wrong-state withholding, missing reciprocity certs,
        double-withholding.
        """
        permissions.check(Scope.PAYROLL_READ)
        reader = ReciprocalWithholdingReader(prismhr)
        report = await run_reciprocal_withholding_audit(
            reader, client_id=client_id,
            period_start=_parse_date(period_start),
            period_end=_parse_date(period_end),
        )
        return _to_dict(report)

    registry.register(server, "commercial_reciprocal_withholding",
                      commercial_reciprocal_withholding)

    # -------------------- state_new_hire_reporting --------------------

    async def commercial_state_new_hire_audit(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        hired_since: Annotated[str, Field(description="YYYY-MM-DD, earliest hire date to scan.")],
    ) -> dict:
        """State new-hire reporting audit. 50-state deadline matrix (20-day federal min,
        tighter in AL/ME/VT/GA/IA/MS/MA/RI/WV)."""
        permissions.check(Scope.PAYROLL_READ)
        reader = StateNewHireReportingReader(prismhr)
        report = await run_state_new_hire_audit(
            reader, client_id=client_id,
            hired_since=_parse_date(hired_since),
        )
        return _to_dict(report)

    registry.register(server, "commercial_state_new_hire_audit",
                      commercial_state_new_hire_audit)

    # -------------------- final_paycheck_compliance --------------------

    async def commercial_final_paycheck_compliance(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        since: Annotated[str, Field(description="YYYY-MM-DD, separations since this date.")],
    ) -> dict:
        """State final-paycheck deadline compliance. CA 72hr, MA day-of,
        NY/NJ separation notice. Flags overdue + PTO payout + commission."""
        permissions.check(Scope.PAYROLL_READ)
        reader = FinalPaycheckComplianceReader(prismhr)
        report = await run_final_paycheck_compliance(
            reader, client_id=client_id,
            since=_parse_date(since),
        )
        return _to_dict(report)

    registry.register(server, "commercial_final_paycheck_compliance",
                      commercial_final_paycheck_compliance)

    # -------------------- off_cycle_payroll_audit --------------------

    async def commercial_off_cycle_payroll_audit(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        period_start: Annotated[str, Field(description="YYYY-MM-DD.")],
        period_end: Annotated[str, Field(description="YYYY-MM-DD.")],
    ) -> dict:
        """Off-cycle (bonus/manual/correction/final) voucher cohort review.
        Catches no-approver, unusual amounts, multiple-bonus loops, missing
        tax method, pre/post-dated vouchers."""
        permissions.check(Scope.PAYROLL_READ)
        reader = OffCycleVoucherReader(prismhr)
        report = await run_off_cycle_payroll_audit(
            reader, client_id=client_id,
            period_start=_parse_date(period_start),
            period_end=_parse_date(period_end),
        )
        return _to_dict(report)

    registry.register(server, "commercial_off_cycle_payroll_audit",
                      commercial_off_cycle_payroll_audit)

    # -------------------- form_941_reconciliation --------------------

    async def commercial_form_941_reconciliation(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        year: Annotated[int, Field(description="Tax year.", ge=2020, le=2030)],
        quarter: Annotated[int, Field(description="Quarter 1-4.", ge=1, le=4)],
    ) -> dict:
        """Federal 941 reconciliation: voucher wages + FIT + SS + Medicare
        tied to filed 941. Catches voucher-vs-form drift from voids, late
        corrections, additional-Medicare misses."""
        permissions.check(Scope.PAYROLL_READ)
        reader = Form941ReconReader(prismhr)
        report = await run_form_941_reconciliation(
            reader, client_id=client_id, year=year, quarter=quarter,
        )
        return _to_dict(report)

    registry.register(server, "commercial_form_941_reconciliation",
                      commercial_form_941_reconciliation)

    # -------------------- form_940_reconciliation --------------------

    async def commercial_form_940_reconciliation(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        year: Annotated[int, Field(description="Tax year.", ge=2020, le=2030)],
    ) -> dict:
        """Annual FUTA 940 reconciliation. $7K per-employee cap handling,
        credit-reduction state detection, tax calc tie-out."""
        permissions.check(Scope.PAYROLL_READ)
        reader = Form940ReconReader(prismhr)
        report = await run_form_940_reconciliation(
            reader, client_id=client_id, year=year,
        )
        return _to_dict(report)

    registry.register(server, "commercial_form_940_reconciliation",
                      commercial_form_940_reconciliation)

    # -------------------- state_withholding_recon --------------------

    async def commercial_state_withholding_recon(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        year: Annotated[int, Field(description="Tax year.", ge=2020, le=2030)],
        quarter: Annotated[int, Field(description="Quarter 1-4.", ge=1, le=4)],
    ) -> dict:
        """Per-state quarterly withholding + SUTA tie-out. NO_FILING,
        WITHHOLDING_MISMATCH, SUTA_WAGES_MISMATCH, EMPLOYEE_COUNT_MISMATCH."""
        permissions.check(Scope.PAYROLL_READ)
        reader = StateWithholdingReconReader(prismhr)
        report = await run_state_withholding_recon(
            reader, client_id=client_id, year=year, quarter=quarter,
        )
        return _to_dict(report)

    registry.register(server, "commercial_state_withholding_recon",
                      commercial_state_withholding_recon)

    # -------------------- tax_remittance_tracking --------------------

    async def commercial_tax_remittance_tracking(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        jurisdiction: Annotated[str, Field(description="federal | state:XX | local:NYC | etc.")],
        tax_code: Annotated[str, Field(description="FIT | SS | MED | SUTA | SWH")],
        year: Annotated[int, Field(description="Tax year.", ge=2020, le=2030)],
    ) -> dict:
        """Liability vs ACH deposit tie-out. DEPOSIT_MISSING, DEPOSIT_LATE,
        DEPOSIT_UNDER, DEPOSIT_OVER. Catches FTD penalty exposure."""
        permissions.check(Scope.PAYROLL_READ)
        reader = TaxRemittanceReader(prismhr)
        report = await run_tax_remittance_tracking(
            reader, client_id=client_id,
            jurisdiction=jurisdiction, tax_code=tax_code, year=year,
        )
        return _to_dict(report)

    registry.register(server, "commercial_tax_remittance_tracking",
                      commercial_tax_remittance_tracking)

    # -------------------- state_filings_orchestrator --------------------

    async def commercial_state_filings_orchestrator(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        year: Annotated[int, Field(description="Tax year.", ge=2020, le=2030)],
        quarter: Annotated[int, Field(description="Quarter 1-4.", ge=1, le=4)],
    ) -> dict:
        """Unified filing-status board across every state the client
        operates in. Shows form name per state, due date, filed status,
        reconciliation-open-issue count. Blocks filing when recon has
        open criticals."""
        permissions.check(Scope.PAYROLL_READ)
        reader = StateFilingsOrchestratorReader(prismhr)
        report = await run_state_filings_orchestrator(
            reader, client_id=client_id, year=year, quarter=quarter,
        )
        return _to_dict(report)

    registry.register(server, "commercial_state_filings_orchestrator",
                      commercial_state_filings_orchestrator)
