"""Client + employee domain models.

Fields use `validation_alias` (not `alias`) so PrismHR's camelCase inputs
map onto snake_case attributes, while MCP output schemas + serialization
stay snake_case. This matters: FastMCP generates its tool output schema
with `by_alias=True`, so using plain `alias=` here would leak camelCase
into the LLM-visible contract.
"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ClientRef(BaseModel):
    """Lightweight client identifier used in lists."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    client_id: str = Field(validation_alias=AliasChoices("client_id", "clientId"))
    name: str | None = Field(
        default=None, validation_alias=AliasChoices("name", "clientName")
    )
    status: str | None = Field(
        default=None, validation_alias=AliasChoices("status", "statusType")
    )


class ClientListResponse(BaseModel):
    clients: list[ClientRef]
    count: int

    @classmethod
    def from_raw(cls, raw: list[dict] | dict | None) -> "ClientListResponse":
        rows = _ensure_list(raw)
        clients = [ClientRef.model_validate(row) for row in rows]
        return cls(clients=clients, count=len(clients))


class EmployeeRef(BaseModel):
    """Lightweight employee identifier used in list responses."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    employee_id: str = Field(validation_alias=AliasChoices("employee_id", "employeeId"))
    client_id: str | None = Field(
        default=None, validation_alias=AliasChoices("client_id", "clientId")
    )
    first_name: str | None = Field(
        default=None, validation_alias=AliasChoices("first_name", "firstName")
    )
    last_name: str | None = Field(
        default=None, validation_alias=AliasChoices("last_name", "lastName")
    )
    status: str | None = Field(
        default=None, validation_alias=AliasChoices("status", "statusType")
    )
    hire_date: str | None = Field(
        default=None, validation_alias=AliasChoices("hire_date", "hireDate")
    )
    email: str | None = Field(
        default=None, validation_alias=AliasChoices("email", "emailWork")
    )


class EmployeeListResponse(BaseModel):
    client_id: str
    employees: list[EmployeeRef]
    count: int

    @classmethod
    def from_raw(cls, client_id: str, raw: list[dict] | dict | None) -> "EmployeeListResponse":
        rows = _ensure_list(raw)
        for row in rows:
            row.setdefault("clientId", client_id)
        employees = [EmployeeRef.model_validate(row) for row in rows]
        return cls(client_id=client_id, employees=employees, count=len(employees))


class EmployeeDetail(BaseModel):
    """Full employee record — passthrough from PrismHR getEmployee."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    employee_id: str = Field(validation_alias=AliasChoices("employee_id", "employeeId"))
    client_id: str | None = Field(
        default=None, validation_alias=AliasChoices("client_id", "clientId")
    )
    first_name: str | None = Field(
        default=None, validation_alias=AliasChoices("first_name", "firstName")
    )
    last_name: str | None = Field(
        default=None, validation_alias=AliasChoices("last_name", "lastName")
    )
    status: str | None = Field(
        default=None, validation_alias=AliasChoices("status", "statusType")
    )
    hire_date: str | None = Field(
        default=None, validation_alias=AliasChoices("hire_date", "hireDate")
    )
    termination_date: str | None = Field(
        default=None, validation_alias=AliasChoices("termination_date", "terminationDate")
    )
    status_date: str | None = Field(
        default=None, validation_alias=AliasChoices("status_date", "statusDate")
    )
    term_reason_code: str | None = Field(
        default=None, validation_alias=AliasChoices("term_reason_code", "termReasonCode")
    )
    term_explanation: str | None = Field(
        default=None, validation_alias=AliasChoices("term_explanation", "termExplanation")
    )


class EmployeeDetailResponse(BaseModel):
    employees: list[EmployeeDetail]
    missing_ids: list[str] = Field(default_factory=list)


class EmployeeSearchResponse(BaseModel):
    """Results of a cross-client employee search."""

    query: str
    matches: list[EmployeeRef]
    searched_clients: int
    count: int


def _ensure_list(raw: list | dict | None) -> list[dict]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, dict):
        # Some PrismHR endpoints wrap the list under a key like "employeeList".
        for value in raw.values():
            if isinstance(value, list):
                return list(value)
        return [raw]
    return []
