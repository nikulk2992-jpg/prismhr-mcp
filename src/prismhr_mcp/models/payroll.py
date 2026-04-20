"""Payroll domain models (OSS basic reads).

camelCase from PrismHR is mapped via `validation_alias=AliasChoices(...)` so
tool outputs stay snake_case regardless of FastMCP's `by_alias` default.

Commercial-tier models (DeductionConflict, OvertimeAnomaly,
RegisterReconciliation, WorkflowDeferred) live in
`simploy.models.payroll_compliance`.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

# ----- Batch listing -----


class BatchEntry(BaseModel):
    """One payroll batch summary from `getBatchListByDate`."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    batch_id: str = Field(validation_alias=AliasChoices("batch_id", "batchId"))
    client_id: str | None = Field(
        default=None, validation_alias=AliasChoices("client_id", "clientId")
    )
    pay_date: str | None = Field(
        default=None, validation_alias=AliasChoices("pay_date", "payDate")
    )
    check_date: str | None = Field(
        default=None, validation_alias=AliasChoices("check_date", "checkDate")
    )
    period_start: str | None = Field(
        default=None, validation_alias=AliasChoices("period_start", "periodStartDate")
    )
    period_end: str | None = Field(
        default=None, validation_alias=AliasChoices("period_end", "periodEndDate")
    )
    status: str | None = Field(
        default=None, validation_alias=AliasChoices("status", "batchStatus", "statusType")
    )
    voucher_count: int | None = Field(
        default=None, validation_alias=AliasChoices("voucher_count", "voucherCount")
    )
    gross_total: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("gross_total", "grossTotal", "grossAmount")
    )


class BatchStatusResponse(BaseModel):
    client_id: str
    start_date: str
    end_date: str
    batches: list[BatchEntry]
    count: int


# ----- Voucher / pay history -----


class PayVoucher(BaseModel):
    """One paycheck / pay voucher (`getPayrollVouchersForEmployee`).

    Shared data contract — used by both OSS pay_history reader and
    commercial overtime-anomaly detector."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    voucher_id: str | None = Field(
        default=None, validation_alias=AliasChoices("voucher_id", "voucherId", "checkNumber")
    )
    batch_id: str | None = Field(
        default=None, validation_alias=AliasChoices("batch_id", "batchId")
    )
    pay_date: str | None = Field(
        default=None, validation_alias=AliasChoices("pay_date", "payDate", "checkDate")
    )
    period_start: str | None = Field(
        default=None, validation_alias=AliasChoices("period_start", "periodStartDate")
    )
    period_end: str | None = Field(
        default=None, validation_alias=AliasChoices("period_end", "periodEndDate")
    )
    gross: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("gross", "grossAmount", "grossPay")
    )
    net: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("net", "netAmount", "netPay")
    )
    regular_hours: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("regular_hours", "regularHours")
    )
    overtime_hours: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("overtime_hours", "overtimeHours")
    )
    regular_pay: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("regular_pay", "regularAmount")
    )
    overtime_pay: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("overtime_pay", "overtimeAmount")
    )
    voided: bool | None = Field(
        default=None, validation_alias=AliasChoices("voided", "isVoid")
    )


class YTDValues(BaseModel):
    """Year-to-date aggregates for an employee (`getYearToDateValues`)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    as_of_date: str | None = Field(
        default=None, validation_alias=AliasChoices("as_of_date", "asOfDate")
    )
    gross_ytd: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("gross_ytd", "grossYTD")
    )
    net_ytd: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("net_ytd", "netYTD")
    )
    federal_tax_ytd: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("federal_tax_ytd", "federalTaxYTD")
    )
    ss_ytd: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("ss_ytd", "socialSecurityYTD")
    )
    medicare_ytd: Decimal | None = Field(
        default=None, validation_alias=AliasChoices("medicare_ytd", "medicareYTD")
    )


class PayHistoryResponse(BaseModel):
    client_id: str
    employee_id: str
    start_date: str
    end_date: str
    vouchers: list[PayVoucher]
    ytd: YTDValues | None = None
    count: int


# ----- Pay group assignment -----


class PayGroupAssignment(BaseModel):
    client_id: str
    employee_id: str
    pay_group_id: str | None
    pay_group_name: str | None
    pay_frequency: str | None = Field(
        default=None, description="e.g. 'weekly', 'biweekly', 'semimonthly', 'monthly'."
    )
    assigned: bool
    warning: str | None = None


# ----- SuperBatch status -----


class SuperBatchSummary(BaseModel):
    """Aggregated view across a date range — mirrors PrismHR's SuperBatch UI."""

    client_id: str
    start_date: str
    end_date: str
    batch_count: int
    total_vouchers: int
    total_gross: Decimal
    open_batch_count: int
    pending_batch_count: int
    posted_batch_count: int
    voided_batch_count: int
    batches: list[BatchEntry]
