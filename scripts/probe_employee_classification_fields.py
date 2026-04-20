"""Hunt for classification fields (emp type / FICA exempt / work state /
union) across candidate PrismHR endpoints. Reports which endpoint has
what.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.secure_env import load_into_environ


CANDIDATES = [
    ("/employee/v1/getEmployersInfo", {}),
    ("/employee/v1/getEmployee", {}),
    ("/employee/v1/getEmployee", {"class": "Compensation"}),
    ("/employee/v1/getEmployee", {"class": "Person"}),
    ("/employee/v1/getEmployee", {"class": "ContactInformation"}),
    ("/employee/v1/getEmployee", {"class": "Client"}),
    ("/employee/v1/getEmployee", {"class": "Health"}),
    ("/payroll/v1/getEmployeeOverrideRates", {}),
    ("/clientMaster/v1/getEmployeesInPayGroup", {}),
    ("/employee/v1/getAddressInfo", {}),
]

KEYWORDS = (
    "fica", "exempt", "employ", "type", "status", "union", "contract",
    "1099", "w2", "state", "class",
)


def _recursive_keys(obj, prefix=""):
    for k, v in (obj.items() if isinstance(obj, dict) else []):
        path = f"{prefix}.{k}" if prefix else k
        yield (path, v)
        if isinstance(v, dict):
            yield from _recursive_keys(v, path)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            yield from _recursive_keys(v[0], path + "[]")


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID")
        return 2

    s = Settings()
    s.prismhr_peo_id = os.environ["PRISMHR_MCP_PEO_ID"]
    http = httpx.AsyncClient(timeout=60.0)
    creds = DirectCredentialSource(
        s.prismhr_peo_id,
        os.environ["PRISMHR_MCP_USERNAME"],
        os.environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(s, creds, http)
    c = PrismHRClient(s, session, http)

    try:
        batch_list = await c.get(
            "/payroll/v1/getBatchListByDate",
            params={
                "clientId": client_id,
                "startDate": "2024-01-01",
                "endDate": "2026-04-20",
                "dateType": "POST",
            },
        )
        bid = ""
        eid = ""
        for b in (batch_list.get("batchList") or []):
            bid = str(b.get("batchId") or "")
            if not bid:
                continue
            try:
                vbody = await c.get(
                    "/payroll/v1/getPayrollVoucherForBatch",
                    params={"clientId": client_id, "batchId": bid},
                )
            except Exception:  # noqa: BLE001
                continue
            vs = vbody.get("payrollVoucher") or []
            if vs:
                eid = str(vs[0].get("employeeId") or "")
                break

        if not eid:
            print("No employee found for probing.")
            return 1

        print(f"Employee: {eid}  (client {client_id})\n")

        for path, extra in CANDIDATES:
            params = {"clientId": client_id, "employeeId": eid}
            if "PayGroup" in path:
                params = {"clientId": client_id}
            params.update(extra)
            label = path + ("?" + "&".join(f"{k}={v}" for k, v in extra.items()) if extra else "")
            try:
                body = await c.get(path, params=params)
            except Exception as exc:  # noqa: BLE001
                print(f"[{label}] ERROR {type(exc).__name__}: {str(exc)[:80]}")
                continue
            print(f"[{label}]")
            hits = []
            for fpath, val in _recursive_keys(body):
                fname = fpath.lower()
                if any(kw in fname for kw in KEYWORDS):
                    if val not in (None, "", [], {}):
                        hits.append((fpath, val))
            if hits:
                for fp, val in hits[:25]:
                    vs = json.dumps(val) if not isinstance(val, str) else val
                    if len(vs) > 60:
                        vs = vs[:57] + "..."
                    print(f"    {fp:50s} = {vs}")
            else:
                print("    (no non-empty matches)")
            print()
    finally:
        await http.aclose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
