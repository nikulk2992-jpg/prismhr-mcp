"""Probe SystemService.getData + getEmployee with new data-class grants.

Reports on fields now populated now that round-9/10 permissions landed.

getData uses the async download pattern:
  1. initial call returns {downloadId, buildStatus: "INIT"}
  2. poll same endpoint with downloadId until buildStatus="DONE"
  3. fetch dataObject URL for the compiled JSON payload

Usage:
    set DOGFOOD_CLIENT_ID=001202
    .venv/Scripts/python scripts/probe_get_data.py
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


_OUT_DIR = REPO / ".planning" / "verified-responses"


async def _poll_get_data(
    c: httpx.AsyncClient,
    base: str,
    h: dict,
    schema: str,
    class_name: str,
    *,
    client_id: str | None = None,
    employee_id: str | None = None,
    max_polls: int = 40,
) -> dict | None:
    params = {"schemaName": schema, "className": class_name}
    if client_id:
        params["clientId"] = client_id
    if employee_id:
        params["employeeId"] = employee_id
    r = await c.get(f"{base}/system/v1/getData", headers=h, params=params)
    body = r.json()
    status = body.get("buildStatus")
    did = body.get("downloadId")
    if status == "DONE":
        return body
    if not did:
        return body
    for _ in range(max_polls):
        await asyncio.sleep(2)
        params["downloadId"] = did
        r = await c.get(f"{base}/system/v1/getData", headers=h, params=params)
        body = r.json()
        status = body.get("buildStatus")
        if status == "DONE":
            return body
        if status == "ERROR":
            print(f"    ERROR: {body.get('errorMessage') or body}")
            return body
    print(f"    timed out waiting for {schema}|{class_name}")
    return None


async def _fetch_data_object(c: httpx.AsyncClient, h: dict, url: str) -> dict | list | None:
    if not url:
        return None
    try:
        r = await c.get(url, headers={"sessionId": h.get("sessionId", ""),
                                       "Accept": "application/json"})
        # Some dataObjects are latin-1 / windows-1252 not utf-8
        try:
            return r.json()
        except Exception:  # noqa: BLE001
            text = r.content.decode("latin-1", errors="replace")
            import json as _j
            return _j.loads(text)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {str(exc)[:100]}"}


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "001202").strip()

    base = "https://uatapi.prismhr.com/demo/prismhr-api/services/rest"
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{base}/login/v1/createPeoSession", data={
            "peoId": os.environ["PRISMHR_MCP_PEO_ID"],
            "username": os.environ["PRISMHR_MCP_USERNAME"],
            "password": os.environ["PRISMHR_MCP_PASSWORD"],
        })
        sid = r.json()["sessionId"]
        h = {"sessionId": sid, "Accept": "application/json"}

        # ---- find a known employee ----
        r = await c.get(
            f"{base}/payroll/v1/getBatchListByDate",
            headers=h,
            params={"clientId": client_id, "startDate": "2024-01-01",
                    "endDate": "2026-04-20", "dateType": "POST"},
        )
        batches = (r.json() or {}).get("batchList") or []
        eid = ""
        for b in batches[:5]:
            bid = str(b.get("batchId") or "")
            if not bid:
                continue
            vr = await c.get(
                f"{base}/payroll/v1/getPayrollVoucherForBatch",
                headers=h,
                params={"clientId": client_id, "batchId": bid},
            )
            vouchers = (vr.json() or {}).get("payrollVoucher") or []
            if vouchers:
                eid = str(vouchers[0].get("employeeId") or "")
                break
        print(f"Sample employee: {eid}  (client {client_id})")
        print()

        # ---- 1. getEmployee with Compensation option ----
        print("=" * 72)
        print(" getEmployee?options=Compensation — what comes back now")
        print("=" * 72)
        r = await c.get(
            f"{base}/employee/v1/getEmployee",
            headers=h,
            params={"clientId": client_id, "employeeId": eid,
                    "options": "Compensation"},
        )
        body = r.json()
        emp = (body.get("employee") or [{}])[0] if body.get("employee") else body
        comp = emp.get("compensation") or {}
        print(json.dumps(comp, indent=2)[:2500] if comp else "compensation subtree still null/missing")
        print()
        # Save probe
        (_OUT_DIR / "employee_getEmployee_Compensation.json").write_text(
            json.dumps(body, indent=2), encoding="utf-8"
        )

        # ---- 2. SystemService.getData probes ----
        probes = [
            # Employee classes
            ("Employee", "Compensation"),
            ("Employee", "Client"),
            ("Employee", "Person"),
            ("Employee", "Events"),
            ("Employee", "LeaveRequests"),
            ("Employee", "FutureEEChanges"),
            ("Employee", "History"),
            ("Employee", "DirectDeposit"),
            # Benefit classes
            ("Benefit", "BenefitPlan"),
            ("Benefit", "BenefitPlanDetail"),
            ("Benefit", "RetirementPlan"),
            ("Benefit", "Dependent"),
            ("Benefit", "Enrollment"),
            ("Benefit", "AbsenceJournal"),
            ("Benefit", "RetirementLoan"),
            ("Benefit", "SpendingAccounts"),
            ("Benefit", "PaidTimeOff"),
            # Client classes
            ("Client", "Master"),
            ("Client", "Deduction"),
            ("Client", "Pay"),
            ("Client", "Location"),
            ("Client", "Department"),
            ("Client", "Division"),
            ("Client", "Job"),
            # Deduction classes
            ("Deduction", "Garnishment"),
            ("Deduction", "EmployeeArrears"),
            ("Deduction", "EmployeeLoan"),
            ("Deduction", "EmployeeDeductions"),
            ("Deduction", "EmployeeDeductionDetails"),
            ("Deduction", "ScheduledDeductions"),
            # Payroll
            ("Payroll", "BatchControl"),
        ]
        for schema, cls in probes:
            print("=" * 72)
            print(f" SystemService.getData  schema={schema}  class={cls}")
            print("=" * 72)
            result = await _poll_get_data(
                c, base, h, schema, cls,
                client_id=client_id if schema in {"Employee", "Client", "Deduction", "Benefit"} else None,
                employee_id=eid if schema in {"Employee"} else None,
            )
            if not result:
                continue
            if result.get("errorCode") not in (None, "0", 0):
                print(f"ERROR {result.get('errorCode')}: {result.get('errorMessage')}")
                continue
            url = result.get("dataObject") or result.get("dataUrl")
            data = await _fetch_data_object(c, h, url) if url else None
            snippet = json.dumps(data, indent=2)[:1500] if data else "(empty dataObject)"
            print(snippet)
            print()
            # Save
            fname = f"system_getData_{schema}_{cls}.json"
            (_OUT_DIR / fname).write_text(
                json.dumps(data or result, indent=2, default=str),
                encoding="utf-8",
            )

    print()
    print(f"Saved probes under {_OUT_DIR.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
