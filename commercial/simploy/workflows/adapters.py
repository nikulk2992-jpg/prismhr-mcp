"""Adapters bridging the OSS core's PrismHRClient to workflow readers.

Workflows declare narrow reader protocols; adapters translate each
protocol method into one or more PrismHR endpoint calls. Keeping this
split means workflows remain testable with in-memory fakes while still
talking to real PrismHR in production.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from prismhr_mcp.clients.prismhr import PrismHRClient


class PrismHRClientReader:
    """Implements `new_hire_audit.PrismHRReader` against a live PrismHRClient.

    `get_employee_list` is a two-pass call because PrismHR's
    getEmployeeList returns only IDs (no hire date) and has no
    server-side hire-date filter. We fetch IDs, then getEmployee in
    batches of up to 20, then filter client-side. The
    `max_detail_fetch` cap bounds the total number of detail calls so
    a large roster does not produce hundreds of requests.
    """

    # PrismHR's getEmployee accepts up to 20 comma-separated IDs per call.
    _DETAIL_BATCH_SIZE = 20
    # Default cap on how many employee detail records we will fetch
    # during a list-level probe; callers can override by wrapping.
    _DEFAULT_DETAIL_CAP = 200

    def __init__(
        self,
        client: PrismHRClient,
        *,
        max_detail_fetch: int = _DEFAULT_DETAIL_CAP,
    ) -> None:
        self._c = client
        self._cap = max_detail_fetch

    async def get_employee_list(self, client_id: str, hired_since: date) -> list[dict]:
        # Step 1: fetch all active employee IDs for the client.
        list_body = await self._c.get(
            "/employee/v1/getEmployeeList",
            params={"clientId": client_id, "employmentStatus": "A"},
        )
        ids = _extract_ids(list_body)
        if not ids:
            return []
        # Step 2: detail-fetch in bounded batches. PrismHR wants repeated
        # `employeeId` query params (NOT comma-separated). `options=Client`
        # pulls in hireDate + status; Person pulls in ssn via getEmployee.
        ids_to_probe = sorted(ids, reverse=True)[: self._cap]
        details: list[dict] = []
        for i in range(0, len(ids_to_probe), self._DETAIL_BATCH_SIZE):
            chunk = ids_to_probe[i : i + self._DETAIL_BATCH_SIZE]
            params: list[tuple[str, str]] = [
                ("clientId", client_id),
                ("options", "Person,Client"),
            ]
            params.extend(("employeeId", eid) for eid in chunk)
            body = await self._c.get("/employee/v1/getEmployee", params=params)
            rows = _rows(body, "employee") or []
            details.extend(rows)
        # Step 3: filter client-side by hire date >= hired_since. The
        # relevant field is client.lastHireDate (most recent rehire) and
        # falls back to firstHireDate for employees who were never rehired.
        results: list[dict] = []
        for r in details:
            client_block = r.get("client") or {}
            raw_hire = (
                client_block.get("lastHireDate")
                or client_block.get("firstHireDate")
                or client_block.get("statusDate")
                or ""
            )
            parsed = _parse_iso_prefix(raw_hire)
            if parsed is None or parsed < hired_since:
                continue
            results.append(
                {
                    "employeeId": r.get("id") or r.get("employeeId") or "",
                    "firstName": r.get("firstName", ""),
                    "lastName": r.get("lastName", ""),
                    "hireDate": raw_hire,
                }
            )
        return results

    async def get_employee(self, client_id: str, employee_id: str) -> dict:
        body = await self._c.get(
            "/employee/v1/getEmployee",
            params=[
                ("clientId", client_id),
                ("options", "Person"),
                ("employeeId", employee_id),
            ],
        )
        row = _first(body, "employee") or {}
        person = row.get("person") or {}
        return {
            "employeeId": row.get("id") or row.get("employeeId") or employee_id,
            "ssn": person.get("ssn") or "",
        }

    async def get_address(self, client_id: str, employee_id: str) -> dict:
        # Address lives on the Person option under contactInformation, not a
        # separate endpoint on our verified surface.
        body = await self._c.get(
            "/employee/v1/getEmployee",
            params=[
                ("clientId", client_id),
                ("options", "Person"),
                ("employeeId", employee_id),
            ],
        )
        row = _first(body, "employee") or {}
        contact = row.get("contactInformation") or {}
        home = contact.get("homeAddress") or contact.get("primaryAddress") or {}
        return {
            "line1": home.get("addressLine1")
            or home.get("line1")
            or home.get("street")
            or "",
            "city": home.get("city", ""),
            "state": home.get("state", ""),
            "zip": home.get("postalCode") or home.get("zip") or "",
        }

    async def get_everify(self, client_id: str, employee_id: str) -> dict:
        body = await self._c.get(
            "/employee/v1/getEverifyStatus",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        row = _first(body, "everifyStatus") or body or {}
        return {"everifyStatus": row.get("everifyStatus") or row.get("status") or ""}

    async def get_scheduled_deductions(self, client_id: str, employee_id: str) -> dict:
        body = await self._c.get(
            "/employee/v1/getScheduledDeductions",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        rows = _rows(body, "scheduledDeductions") or _rows(body, "deductions") or []
        return {"scheduledDeductions": rows}

    async def check_garnishments(self, client_id: str, employee_id: str) -> dict:
        body = await self._c.get(
            "/employee/v1/checkForGarnishments",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        row = body or {}
        has = bool(row.get("hasGarnishments") or row.get("garnishmentCount", 0))
        return {
            "hasGarnishments": has,
            "setupComplete": bool(row.get("setupComplete", has)),
        }


def _rows(body: Any, key: str) -> list[dict]:
    if not isinstance(body, dict):
        return []
    val = body.get(key)
    if isinstance(val, list):
        return val
    return []


def _parse_iso_prefix(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


class _IDExtractor:
    pass


def _extract_ids(body: Any) -> list[str]:
    """PrismHR's getEmployeeList returns {employeeList: {employeeId: [ids]}}."""
    if not isinstance(body, dict):
        return []
    bucket = body.get("employeeList")
    if isinstance(bucket, dict):
        ids = bucket.get("employeeId") or bucket.get("employeeIds")
        if isinstance(ids, list):
            return [str(x) for x in ids if x]
    if isinstance(bucket, list):
        return [
            str(r.get("employeeId") or r.get("empId"))
            for r in bucket
            if isinstance(r, dict) and (r.get("employeeId") or r.get("empId"))
        ]
    return []


def _first(body: Any, key: str) -> dict | None:
    if not isinstance(body, dict):
        return None
    val = body.get(key)
    if isinstance(val, list) and val:
        return val[0] if isinstance(val[0], dict) else None
    if isinstance(val, dict):
        return val
    return None
