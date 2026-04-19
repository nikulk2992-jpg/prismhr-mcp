"""Second-pass probe: retry error endpoints with matched (clientId, employeeId) pairs.

The first calibrated_probe pass uses flat-list fixtures — client_id[0] + employee_id[0]
may belong to different clients, which is why most per-employee endpoints 400/500.

This pass:
  1. Reads the bulk YTD response from .planning/verified-responses/ to build real
     (clientId, employeeId) tuples.
  2. For each method that errored in the first pass, iterates tuples until one
     returns a 200.
  3. For benefit-plan endpoints that need (clientId, employeeId, planId), chains:
        getActiveBenefitPlans → grab planId → retry.
  4. Saves 200 response bodies and updates the local verification matrix.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.errors import PrismHRRequestError
from prismhr_mcp.secure_env import load_into_environ

MATRIX = pathlib.Path(".planning/verification-matrix.json")
RESP_DIR = pathlib.Path(".planning/verified-responses")
BULK_YTD = RESP_DIR / "payroll_getBulkYearToDateValues.json"


async def _load_tuples_fresh(
    client: PrismHRClient, http: httpx.AsyncClient, max_pairs: int = 200
) -> list[tuple[str, str]]:
    """Call getBulkYearToDateValues fresh and parse (clientId, employeeId) pairs.

    Can't trust the cached disk copy — probe harness truncates at 200KB.
    """
    raw = await client.get(
        "/payroll/v1/getBulkYearToDateValues", params={"asOfDate": "2026-04-19"}
    )
    if not isinstance(raw, dict):
        return []
    # Already DONE? Otherwise poll.
    async def _unwrap(env: dict[str, Any]) -> Any:
        url = env.get("dataObject")
        if not url:
            return env
        token = await client._session.token()  # noqa: SLF001
        resp = await http.get(url, headers={"sessionId": token})
        if resp.status_code == 200:
            return resp.json()
        return env

    if raw.get("buildStatus") == "DONE":
        body = await _unwrap(raw)
    else:
        did = raw.get("downloadId")
        for _ in range(20):
            await asyncio.sleep(2)
            polled = await client.get(
                "/payroll/v1/getBulkYearToDateValues",
                params={"downloadId": did, "asOfDate": "2026-04-19"},
            )
            if isinstance(polled, dict) and polled.get("buildStatus") == "DONE":
                body = await _unwrap(polled)
                break
        else:
            return []

    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, list):
        return []
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        cid = row.get("clientId")
        eid = row.get("employeeId")
        if cid and eid:
            key = (str(cid), str(eid))
            if key not in seen:
                seen.add(key)
                pairs.append(key)
        if len(pairs) >= max_pairs:
            break
    return pairs


async def _try_call(
    client: PrismHRClient, path: str, params: dict[str, Any]
) -> tuple[bool, Any, str | None]:
    try:
        raw = await client.get(path, params=params)
    except PrismHRRequestError as exc:
        return False, None, str(exc)[:200]
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)[:200]
    if isinstance(raw, dict):
        err = raw.get("errorCode")
        if err not in (None, "", "0"):
            return False, raw, f"errorCode={err} errorMessage={raw.get('errorMessage')!s:.120s}"
    return True, raw, None


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    s = Settings()
    s.prismhr_peo_id = os.environ["PRISMHR_MCP_PEO_ID"]
    http = httpx.AsyncClient(timeout=60.0)
    creds = DirectCredentialSource(
        s.prismhr_peo_id,
        os.environ["PRISMHR_MCP_USERNAME"],
        os.environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(s, creds, http)
    client = PrismHRClient(s, session, http)

    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    print("fetching fresh bulk YTD for (clientId, employeeId) pairs...")
    pairs = await _load_tuples_fresh(client, http)
    print(f"loaded {len(pairs)} (clientId, employeeId) pairs from bulk YTD")
    if not pairs:
        print("no pairs available — run calibrated_probe.py first")
        return 1

    # Target endpoints that need (clientId, employeeId).
    # Ordered by likelihood + independence.
    per_employee_gets = [
        "/employee/v1/getEmployee",
        "/employee/v1/getAddressInfo",
        "/employee/v1/getACHDeductions",
        "/employee/v1/getScheduledDeductions",
        "/employee/v1/getEverifyStatus",
        "/employee/v1/getEmployersInfo",
        "/employee/v1/get1095CYears",
        "/employee/v1/get1099Years",
        "/benefits/v1/getActiveBenefitPlans",
        "/benefits/v1/getBenefitPlans",
        "/benefits/v1/getDependents",
        "/benefits/v1/getPaidTimeOff",
        "/benefits/v1/getRetirementLoans",
        "/benefits/v1/getRetirementPlan",
        "/deductions/v1/getDeductions",
        "/deductions/v1/getGarnishmentDetails",
        "/deductions/v1/getGarnishmentPaymentHistory",
        "/deductions/v1/getVoluntaryRecurringDeductions",
        "/payroll/v1/getPayrollVouchersForEmployee",
    ]

    # Index existing probe records so we update in place.
    by_path = {p["path"]: p for p in matrix.get("probes", [])}

    new_verified: list[str] = []

    for path in per_employee_gets:
        print(f"\n--- {path} ---")
        won = False
        winning_args = None
        raw_response: Any = None
        # Try up to N pairs; stop on first 200
        for i, (cid, eid) in enumerate(pairs[:40]):
            ok, raw, err = await _try_call(client, path, {"clientId": cid, "employeeId": eid})
            if ok:
                won = True
                winning_args = {"clientId": cid, "employeeId": eid}
                raw_response = raw
                print(f"  [OK ] pair #{i}: client={cid} employee={eid}")
                break
            if i < 3:  # show first few failures for signal
                print(f"  [err] #{i}: client={cid} employee={eid} -> {err[:80] if err else '?'}")
        if won:
            new_verified.append(path)
            # Save response
            out = RESP_DIR / (
                path.strip("/").replace("/", "_").replace("v1_", "") + ".json"
            )
            out.write_text(
                json.dumps(raw_response, indent=2, default=str)[:100000],
                encoding="utf-8",
            )
            # Update matrix record
            keys = []
            def walk(v, pfx=""):
                if isinstance(v, dict):
                    for k, val in v.items():
                        p = f"{pfx}.{k}" if pfx else k
                        keys.append(p)
                        walk(val, p)
                elif isinstance(v, list) and v:
                    walk(v[0], f"{pfx}[]")
            walk(raw_response)
            by_path[path] = {
                "path": path,
                "status": "verified",
                "args_used": winning_args,
                "response_keys": keys[:80],
            }
        else:
            print(f"  [FAIL] no pair worked in {len(pairs[:40])} tries")

    # Chain benefit plan lookup: if getActiveBenefitPlans worked, use its planId
    # for getBenefitPlanDetails + getPaidTimeOff per-plan probes.
    active_bp_path = "/benefits/v1/getActiveBenefitPlans"
    active_bp_file = RESP_DIR / "benefits_v1_getActiveBenefitPlans.json"
    if active_bp_file.exists():
        try:
            bp = json.loads(active_bp_file.read_text(encoding="utf-8"))
            record = by_path.get(active_bp_path, {})
            cid = record.get("args_used", {}).get("clientId")
            eid = record.get("args_used", {}).get("employeeId")
            # Find a planId in the response
            plan_id = None
            def find_plan(v: Any) -> None:
                nonlocal plan_id
                if plan_id:
                    return
                if isinstance(v, dict):
                    pid = v.get("planId") or v.get("planID")
                    if pid and not plan_id:
                        plan_id = str(pid)
                    for val in v.values():
                        find_plan(val)
                elif isinstance(v, list):
                    for item in v:
                        find_plan(item)
            find_plan(bp)
            if cid and eid and plan_id:
                print(f"\n--- chained plan probes (cid={cid} eid={eid} plan={plan_id}) ---")
                for path in [
                    "/benefits/v1/getBenefitPlans",
                    "/benefits/v1/getDisabilityPlanEnrollmentDetails",
                    "/benefits/v1/getBenefitAdjustments",
                ]:
                    ok, raw, err = await _try_call(
                        client, path,
                        {"clientId": cid, "employeeId": eid, "planId": plan_id},
                    )
                    if ok:
                        new_verified.append(path)
                        out = RESP_DIR / (
                            path.strip("/").replace("/", "_").replace("v1_", "") + ".json"
                        )
                        out.write_text(
                            json.dumps(raw, indent=2, default=str)[:100000],
                            encoding="utf-8",
                        )
                        by_path[path] = {
                            "path": path,
                            "status": "verified",
                            "args_used": {"clientId": cid, "employeeId": eid, "planId": plan_id},
                            "response_keys": [],
                        }
                        print(f"  [OK ] {path}")
                    else:
                        print(f"  [err] {path} -> {err[:120] if err else '?'}")
        except Exception as exc:
            print(f"chain failed: {exc}")

    # Write updated matrix
    matrix["probes"] = list(by_path.values())
    MATRIX.write_text(json.dumps(matrix, indent=2, default=str), encoding="utf-8")

    print(f"\n=== SUMMARY ===")
    print(f"new verified this pass: {len(new_verified)}")
    for p in new_verified:
        print(f"  + {p}")

    await http.aclose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
