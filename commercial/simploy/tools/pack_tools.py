"""MCP tool wrappers for orchestration packs.

Each pack bundles multiple workflow calls. Auto-resolves the needed
live readers from a PrismHRClient + lets an agent run
`commercial_month_end_close_pack(client_id)` end-to-end.

Registration requires the same surface as workflow_tools.register_workflow_tools.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Any, Callable

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.permissions import PermissionManager, Scope
from prismhr_mcp.registry import ToolRegistry

from simploy.tools.workflow_tools import _parse_date, _to_dict
from simploy.workflows.adapters import (
    BonusGrossUpReader,
    CobraEligibilityReader,
    DependentAgeOutReader,
    FinalPaycheckComplianceReader,
    Form1099NECPreflightReader,
    GarnishmentHistoryReader,
    OffCycleVoucherReader,
    PayrollBatchHealthReader,
    PTOReconciliationReader,
    ReciprocalWithholdingReader,
    RetirementLoanStatusReader,
    RetirementNDTReader,
    StateNewHireReportingReader,
    VoucherClassificationReader,
)
from simploy.workflows.bonus_gross_up_audit import run_bonus_gross_up_audit
from simploy.workflows.cobra_eligibility_sweep import run_cobra_sweep
from simploy.workflows.dependent_age_out import run_dependent_age_out
from simploy.workflows.final_paycheck_compliance import run_final_paycheck_compliance
from simploy.workflows.form_1099_nec_preflight import run_form_1099_nec_preflight
from simploy.workflows.orchestration_packs import (
    run_month_end_close_pack,
    run_new_client_golive_pack,
    run_payroll_run_preflight_pack,
    run_quarter_end_close_pack,
    run_year_end_close_pack,
)
from simploy.workflows.payroll_batch_health import run_payroll_batch_health
from simploy.workflows.pto_reconciliation import run_pto_reconciliation
from simploy.workflows.reciprocal_withholding import run_reciprocal_withholding_audit
from simploy.workflows.retirement_loan_status import run_retirement_loan_status
from simploy.workflows.retirement_ndt_suite import run_retirement_ndt
from simploy.workflows.state_new_hire_reporting import run_state_new_hire_audit
from simploy.workflows.voucher_classification_audit import (
    run_voucher_classification_audit,
)


def _build_step_registry(
    prismhr: PrismHRClient,
    client_id: str,
    period_start: date,
    period_end: date,
) -> dict[str, Callable[[], Any]]:
    """One-shot lookup from pack-step-name to a no-arg coroutine factory.

    The orchestration packs call these by name and aggregate findings.
    Extend here when a new workflow earns a pack slot.
    """
    return {
        # Payroll / classification / journal
        "payroll_batch_health": lambda: run_payroll_batch_health(
            PayrollBatchHealthReader(prismhr), client_id=client_id,
        ),
        "voucher_classification_audit": lambda: run_voucher_classification_audit(
            VoucherClassificationReader(prismhr),
            client_id=client_id,
            period_start=period_start,
            period_end=period_end,
        ),

        # Tax-adjacent
        "form_1099_nec_preflight": lambda: run_form_1099_nec_preflight(
            Form1099NECPreflightReader(prismhr),
            client_id=client_id, tax_year=period_end.year,
        ),
        "bonus_gross_up_audit": lambda: run_bonus_gross_up_audit(
            BonusGrossUpReader(prismhr),
            client_id=client_id,
            period_start=period_start, period_end=period_end,
        ),
        "retirement_ndt": lambda: run_retirement_ndt(
            RetirementNDTReader(prismhr),
            client_id=client_id, plan_year=period_end.year,
        ),
        "reciprocal_withholding_audit": lambda: run_reciprocal_withholding_audit(
            ReciprocalWithholdingReader(prismhr),
            client_id=client_id,
            period_start=period_start, period_end=period_end,
        ),

        # Lifecycle
        "state_new_hire_audit": lambda: run_state_new_hire_audit(
            StateNewHireReportingReader(prismhr),
            client_id=client_id,
            hired_since=period_start,
        ),
        "final_paycheck_compliance": lambda: run_final_paycheck_compliance(
            FinalPaycheckComplianceReader(prismhr),
            client_id=client_id, since=period_start,
        ),
        "off_cycle_payroll_audit": lambda: run_off_cycle_payroll_audit_stub(
            prismhr, client_id, period_start, period_end,
        ),

        # Benefits / retirement
        "dependent_age_out": lambda: run_dependent_age_out(
            DependentAgeOutReader(prismhr), client_id=client_id,
        ),
        "cobra_eligibility_sweep": lambda: run_cobra_sweep(
            CobraEligibilityReader(prismhr),
            client_id=client_id, lookback_days=60,
        ),
        "pto_reconciliation": lambda: run_pto_reconciliation(
            PTOReconciliationReader(prismhr), client_id=client_id,
        ),
        "retirement_loan_status": lambda: run_retirement_loan_status(
            RetirementLoanStatusReader(prismhr), client_id=client_id,
        ),
    }


async def run_off_cycle_payroll_audit_stub(
    prismhr: PrismHRClient, client_id: str,
    period_start: date, period_end: date,
):
    # Thin wrapper keeps the registry factory expression uniform.
    from simploy.workflows.off_cycle_payroll_audit import run_off_cycle_payroll_audit
    return await run_off_cycle_payroll_audit(
        OffCycleVoucherReader(prismhr),
        client_id=client_id,
        period_start=period_start, period_end=period_end,
    )


def register_pack_tools(
    server: FastMCP,
    registry: ToolRegistry,
    prismhr: PrismHRClient,
    permissions: PermissionManager,
) -> None:
    """Register the five orchestration packs as MCP tools."""

    async def commercial_month_end_close_pack(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        period_start: Annotated[str, Field(description="Month start, YYYY-MM-DD.")],
        period_end: Annotated[str, Field(description="Month end, YYYY-MM-DD.")],
    ) -> dict:
        """Month-end close pack — batch health + classification + GL
        template + journal preflight. Returns per-step critical/warning
        tally + ready_to_proceed flag."""
        permissions.check(Scope.PAYROLL_READ)
        steps = _build_step_registry(
            prismhr, client_id, _parse_date(period_start), _parse_date(period_end)
        )
        report = await run_month_end_close_pack(
            client_id=client_id, steps=steps,
        )
        return _to_dict(report)

    registry.register(server, "commercial_month_end_close_pack",
                      commercial_month_end_close_pack)

    async def commercial_quarter_end_close_pack(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        quarter_end: Annotated[str, Field(description="Last day of quarter, YYYY-MM-DD.")],
    ) -> dict:
        """Quarter-end close pack — 941 + state WH + tax remittance +
        state filings orchestrator."""
        permissions.check(Scope.PAYROLL_READ)
        end = _parse_date(quarter_end)
        start = date(end.year, ((end.month - 1) // 3) * 3 + 1, 1)
        steps = _build_step_registry(prismhr, client_id, start, end)
        report = await run_quarter_end_close_pack(
            client_id=client_id, steps=steps,
        )
        return _to_dict(report)

    registry.register(server, "commercial_quarter_end_close_pack",
                      commercial_quarter_end_close_pack)

    async def commercial_year_end_close_pack(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        tax_year: Annotated[int, Field(description="Tax year.", ge=2020, le=2030)],
    ) -> dict:
        """Year-end close pack — W-2 readiness + 1095-C + AIR +
        1099-NEC + retirement NDT."""
        permissions.check(Scope.PAYROLL_READ)
        start = date(tax_year, 1, 1)
        end = date(tax_year, 12, 31)
        steps = _build_step_registry(prismhr, client_id, start, end)
        report = await run_year_end_close_pack(
            client_id=client_id, steps=steps,
        )
        return _to_dict(report)

    registry.register(server, "commercial_year_end_close_pack",
                      commercial_year_end_close_pack)

    async def commercial_new_client_golive_pack(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        golive_date: Annotated[str, Field(description="Go-live date, YYYY-MM-DD.")],
    ) -> dict:
        """New-client go-live readiness pack."""
        permissions.check(Scope.PAYROLL_READ)
        start = _parse_date(golive_date)
        end = date.today()
        steps = _build_step_registry(prismhr, client_id, start, end)
        report = await run_new_client_golive_pack(
            client_id=client_id, steps=steps,
        )
        return _to_dict(report)

    registry.register(server, "commercial_new_client_golive_pack",
                      commercial_new_client_golive_pack)

    async def commercial_payroll_run_preflight_pack(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        period_start: Annotated[str, Field(description="Pay period start, YYYY-MM-DD.")],
        period_end: Annotated[str, Field(description="Pay period end, YYYY-MM-DD.")],
    ) -> dict:
        """Pre-payroll sanity — classification + batch health + GL +
        journal preflight. Run before hitting 'Process' on a payroll."""
        permissions.check(Scope.PAYROLL_READ)
        steps = _build_step_registry(
            prismhr, client_id, _parse_date(period_start), _parse_date(period_end)
        )
        report = await run_payroll_run_preflight_pack(
            client_id=client_id, steps=steps,
        )
        return _to_dict(report)

    registry.register(server, "commercial_payroll_run_preflight_pack",
                      commercial_payroll_run_preflight_pack)
