"""Probe SystemService.getData with date-range + per-employee filters
to map how each Schema|Class responds to subset queries.

The getData doc lists which classes accept "Filter by Employee" and
"Filter by Date Range" — but exact param names aren't documented. This
script tries candidate params and reports which combinations PrismHR
actually honors. Output feeds adapter design.

Usage:
  DOGFOOD_CLIENT_ID=YOUR_CLIENT_ID .venv/Scripts/python scripts/probe_getdata_dimensions.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from prismhr_mcp.secure_env import load_into_environ  # noqa: E402

# Classes that per docs should accept date range filtering.
DATE_PROBES = [
    ("Employee", "Compensation", "effective"),
    ("Employee", "Person", "peoStartDate"),
    ("Employee", "Client", "hireDate"),
    ("Employee", "History", "effectiveDate"),
    ("Benefit", "Enrollment", "effectiveDate"),
    ("Benefit", "AbsenceJournal", "startDate"),
    ("Benefit", "RetirementLoan", "loanDate"),
    ("Deduction", "Garnishment", "startDate"),
    ("Deduction", "ScheduledDeductions", "startDate"),
]

# Classes that per docs accept per-employee filtering.
EMPLOYEE_PROBES = [
    "Employee", "Benefit", "Deduction",
]

DATE_PARAM_CANDIDATES = [
    "startDate", "fromDate", "effectiveStartDate", "dateFrom",
]
END_PARAM_CANDIDATES = [
    "endDate", "toDate", "effectiveEndDate", "dateTo",
]


async def _get(c: httpx.AsyncClient, url: str, h: dict, params: dict) -> tuple[int, dict | list]:
    try:
        r = await c.get(url, headers=h, params=params)
        return r.status_code, r.json() if r.content else {}
    except Exception as exc:  # noqa: BLE001
        return -1, {"error": str(exc)[:80]}


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID in env.")
        return 2
    base = "https://uatapi.prismhr.com/demo/prismhr-api/services/rest"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{base}/login/v1/createPeoSession", data={
            "peoId": os.environ["PRISMHR_MCP_PEO_ID"],
            "username": os.environ["PRISMHR_MCP_USERNAME"],
            "password": os.environ["PRISMHR_MCP_PASSWORD"],
        })
        sid = r.json()["sessionId"]
        h = {"sessionId": sid, "Accept": "application/json"}

        print("=" * 74)
        print(f"getData dimension probe  (client {client_id})")
        print("=" * 74)

        # --- Date-range tests ---
        for schema, cls, date_note in DATE_PROBES:
            print(f"\n[date] {schema}|{cls}  (docs say filter by: {date_note})")
            for start_key in DATE_PARAM_CANDIDATES:
                for end_key in END_PARAM_CANDIDATES:
                    params = {
                        "schemaName": schema,
                        "className": cls,
                        "clientId": client_id,
                        start_key: "2025-01-01",
                        end_key: "2025-12-31",
                    }
                    status, body = await _get(c, f"{base}/system/v1/getData", h, params)
                    if status == 200 and isinstance(body, dict):
                        bs = body.get("buildStatus")
                        did = body.get("downloadId", "")[:10]
                        err = body.get("errorMessage", "")
                        print(f"  {start_key}/{end_key:22s}  status=INIT  err={err[:40]}")
                        # Successful INIT = keys are accepted. Stop at first win.
                        if bs == "INIT":
                            print(f"    -> {start_key}/{end_key} accepted")
                            break
                    else:
                        err = body.get("errorMessage", "") if isinstance(body, dict) else str(body)[:40]
                        print(f"  {start_key}/{end_key:22s}  status={status}  err={err[:40]}")
                else:
                    continue
                break

        # --- Per-employee tests ---
        # Find a valid employee
        r2 = await c.get(
            f"{base}/employee/v1/getEmployeeList", headers=h,
            params={"clientId": client_id}
        )
        ids = ((r2.json() or {}).get("employeeList") or {}).get("employeeId") or []
        eid = ids[0] if ids else ""
        if not eid:
            print("No employee to test per-employee probes.")
            return 0

        print(f"\n[emp filter] using eid={eid}")
        for schema in EMPLOYEE_PROBES:
            for cls in ("Person", "Compensation", "Client", "Garnishment",
                        "EmployeeDeductions", "Enrollment", "BenefitPlan"):
                params = {
                    "schemaName": schema,
                    "className": cls,
                    "clientId": client_id,
                    "employeeId": eid,
                }
                status, body = await _get(c, f"{base}/system/v1/getData", h, params)
                err = body.get("errorMessage", "") if isinstance(body, dict) else ""
                bs = body.get("buildStatus", "") if isinstance(body, dict) else ""
                if status == 200 and bs == "INIT":
                    mark = "OK"
                elif status == 200 and err:
                    mark = f"ERR ({err[:30]})"
                else:
                    mark = f"status={status}"
                print(f"  {schema:10s}|{cls:22s}  {mark}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
