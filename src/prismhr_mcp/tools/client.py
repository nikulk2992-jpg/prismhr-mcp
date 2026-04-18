"""Group 1 — Client & Employee Management tools.

Phase 1d scope per plan:
  * `client_list` — list clients in the current PEO environment.
  * `client_employees` — list employees for a given client.
  * `client_employee` — fetch full detail for one or more employees.
  * `client_employee_search` — cross-client name/email search.

Each tool enforces its permission scope at entry (see
`prismhr_mcp.permissions`). Ungranted calls raise
`PermissionDeniedError` which surfaces through MCP as a structured error,
with a remediation message pointing at `meta_grant_permissions`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..clients.prismhr import PrismHRClient
from ..models.client import (
    ClientListResponse,
    EmployeeDetail,
    EmployeeDetailResponse,
    EmployeeListResponse,
    EmployeeRef,
    EmployeeSearchResponse,
)
from ..permissions import PermissionManager, Scope
from ..registry import ToolRegistry

PATH_CLIENT_LIST = "/clientMaster/v1/getClientList"
PATH_EMPLOYEE_LIST = "/employee/v1/getEmployeeList"
PATH_EMPLOYEE = "/employee/v1/getEmployee"

StatusFilter = Literal["active", "inactive", "all"]


def register(
    server: FastMCP,
    registry: ToolRegistry,
    prismhr: PrismHRClient,
    permissions: PermissionManager,
) -> None:
    async def client_list() -> ClientListResponse:
        """List all clients visible to the current PrismHR PEO account.

        Returns client IDs, names, and status. Use this before any tool
        that needs a `client_id`. Downstream: feeds `client_employees`,
        `client_employee_search`, and most billing/payroll tools.

        Requires scope: client:read.
        """
        permissions.check(Scope.CLIENT_READ)
        raw = await prismhr.get(PATH_CLIENT_LIST)
        return ClientListResponse.from_raw(raw)

    async def client_employees(
        client_id: Annotated[str, Field(description="PrismHR client ID (from client_list).")],
        status: Annotated[
            StatusFilter,
            Field(description="Filter by employment status. 'active' excludes terminated employees."),
        ] = "active",
    ) -> EmployeeListResponse:
        """List employees for a single client.

        Downstream: feeds `client_employee` for batched detail lookup,
        payroll tools, and branded roster exports.

        Requires scope: employee:read.
        """
        permissions.check(Scope.EMPLOYEE_READ)
        params: dict[str, object] = {"clientId": client_id}
        if status != "all":
            params["statusType"] = status
        raw = await prismhr.get(PATH_EMPLOYEE_LIST, params=params)
        return EmployeeListResponse.from_raw(client_id, raw)

    async def client_employee(
        client_id: Annotated[str, Field(description="PrismHR client ID.")],
        employee_ids: Annotated[
            list[str],
            Field(
                description="Employee IDs to fetch. PrismHR accepts batches of 20; this tool chunks automatically.",
                min_length=1,
            ),
        ],
    ) -> EmployeeDetailResponse:
        """Fetch full detail records for one or more employees of a single client.

        Uses PrismHR's batch endpoint (`getEmployee` accepts up to 20 IDs
        per call) and chunks automatically.

        Requires scope: employee:read.
        """
        permissions.check(Scope.EMPLOYEE_READ)
        unique_ids = list(dict.fromkeys(employee_ids))

        async def fetch(chunk: list[str]) -> list[dict]:
            raw = await prismhr.post(
                PATH_EMPLOYEE,
                json={"clientId": client_id, "employeeIds": list(chunk)},
            )
            return _coerce_list(raw)

        rows = await prismhr.batch(unique_ids, fetch, chunk_size=20)
        employees = [EmployeeDetail.model_validate(row) for row in rows]
        found_ids = {e.employee_id for e in employees}
        missing = [eid for eid in unique_ids if eid not in found_ids]
        return EmployeeDetailResponse(employees=employees, missing_ids=missing)

    async def client_employee_search(
        query: Annotated[
            str,
            Field(
                description="Case-insensitive substring to match against first/last name or work email.",
                min_length=1,
            ),
        ],
        status: Annotated[
            StatusFilter,
            Field(description="Limit search to employees with this status."),
        ] = "active",
        client_ids: Annotated[
            list[str] | None,
            Field(description="Restrict to these clients. Omit to search every client in the PEO."),
        ] = None,
    ) -> EmployeeSearchResponse:
        """Search employees across clients by name or work email.

        Slow path: walks the client list and paginates employees. Prefer
        `client_employees` if you already know the `client_id`.

        Requires scopes: employee:read and client:read (client:read is
        auto-included as a prerequisite when you grant employee:read).
        """
        permissions.check(Scope.EMPLOYEE_READ)
        permissions.check(Scope.CLIENT_READ)

        normalized = query.strip().lower()
        if not normalized:
            return EmployeeSearchResponse(query=query, matches=[], searched_clients=0, count=0)

        if client_ids is None:
            raw_clients = await prismhr.get(PATH_CLIENT_LIST)
            client_list_resp = ClientListResponse.from_raw(raw_clients)
            ids_to_search = [c.client_id for c in client_list_resp.clients]
        else:
            ids_to_search = list(client_ids)

        matches: list[EmployeeRef] = []
        for cid in ids_to_search:
            params: dict[str, object] = {"clientId": cid}
            if status != "all":
                params["statusType"] = status
            raw = await prismhr.get(PATH_EMPLOYEE_LIST, params=params)
            resp = EmployeeListResponse.from_raw(cid, raw)
            for emp in resp.employees:
                if _employee_matches(emp, normalized):
                    matches.append(emp)

        return EmployeeSearchResponse(
            query=query,
            matches=matches,
            searched_clients=len(ids_to_search),
            count=len(matches),
        )

    registry.register(server, "client_list", client_list)
    registry.register(server, "client_employees", client_employees)
    registry.register(server, "client_employee", client_employee)
    registry.register(server, "client_employee_search", client_employee_search)


def _employee_matches(emp: EmployeeRef, needle: str) -> bool:
    haystacks = (emp.first_name, emp.last_name, emp.email)
    return any(h and needle in h.lower() for h in haystacks)


def _coerce_list(raw: object) -> list[dict]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw  # type: ignore[return-value]
    if isinstance(raw, dict):
        for value in raw.values():
            if isinstance(value, list):
                return value  # type: ignore[return-value]
        return [raw]
    return []
