"""Commercial MCP tools: local (PA + OH) tax withholding validation.

Wired as `commercial_tax_local_pa_eit_validate` and
`commercial_tax_local_oh_muni_validate`. Read-only; require
Scope.COMPLIANCE_READ.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from prismhr_mcp.clients.prismhr import PrismHRClient  # noqa: F401
from prismhr_mcp.permissions import PermissionManager, Scope
from prismhr_mcp.registry import ToolRegistry


def register_tax_locals_tools(
    server: FastMCP,
    registry: ToolRegistry,
    prismhr: PrismHRClient,
    permissions: PermissionManager,
) -> None:
    from simploy.tax_engine.locals.oh_muni import validate_oh_muni_withholding
    from simploy.tax_engine.locals.pa_eit import validate_pa_eit_withholding

    async def commercial_tax_local_pa_eit_validate(
        gross_wages_period: Annotated[str, Field(description="Gross wages for the pay period (decimal, e.g. '2000.00').")],
        home_psd: Annotated[str, Field(description="Employee's home PSD code (6 digits).")],
        work_psd: Annotated[str, Field(description="Employee's work-location PSD code (6 digits).")],
        actual_withholding_period: Annotated[str, Field(description="What PrismHR actually withheld this period (decimal).")],
        tolerance: Annotated[str, Field(description="Dollar tolerance for match vs mismatch.")] = "0.50",
    ) -> dict[str, Any]:
        """Validate a PA EIT withholding against Act 32 rules.

        Compares PrismHR's actual withholding against the greater-of
        resident-home-rate vs nonresident-work-rate. Philadelphia is
        handled separately (outside Act 32). Returns rate applied,
        computed expected amount, delta, and match/mismatch status.
        """
        permissions.check(Scope.COMPLIANCE_READ)
        return validate_pa_eit_withholding(
            gross_wages_period=Decimal(gross_wages_period),
            home_psd=home_psd, work_psd=work_psd,
            actual_withholding_period=Decimal(actual_withholding_period),
            tolerance=Decimal(tolerance),
        )

    async def commercial_tax_local_oh_muni_validate(
        gross_wages_period: Annotated[str, Field(description="Gross wages for the pay period (decimal).")],
        home_muni: Annotated[str, Field(description="Home municipality name (e.g. 'CLEVELAND').")],
        work_muni: Annotated[str, Field(description="Work municipality name (e.g. 'COLUMBUS').")],
        actual_total_withholding_period: Annotated[str, Field(description="Total OH local withholding (work + resident) actually taken.")],
        days_worked_in_work_muni: Annotated[int, Field(description="Days worked in the work muni this year (for 20-day rule).")] = 365,
        is_principal_place_of_work: Annotated[bool, Field(description="If True, bypass the 20-day threshold.")] = True,
        tolerance: Annotated[str, Field(description="Dollar tolerance.")] = "0.50",
    ) -> dict[str, Any]:
        """Validate OH municipal withholding using HB 5 credit rules.

        Computes expected work-city tax + resident-city tax (minus
        resident-credit for work-city tax paid, capped by credit_rate
        and credit_limit). Applies the 20-day threshold rule.
        """
        permissions.check(Scope.COMPLIANCE_READ)
        return validate_oh_muni_withholding(
            gross_wages_period=Decimal(gross_wages_period),
            home_muni=home_muni, work_muni=work_muni,
            actual_total_withholding_period=Decimal(actual_total_withholding_period),
            tolerance=Decimal(tolerance),
            days_worked_in_work_muni=days_worked_in_work_muni,
            is_principal_place_of_work=is_principal_place_of_work,
        )

    registry.register(
        server, "commercial_tax_local_pa_eit_validate",
        commercial_tax_local_pa_eit_validate,
    )
    registry.register(
        server, "commercial_tax_local_oh_muni_validate",
        commercial_tax_local_oh_muni_validate,
    )
