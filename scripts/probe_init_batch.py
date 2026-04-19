"""Targeted probe: initialize a TS.READY batch, verify approval-flow endpoints.

UAT snapshot has no batches sitting in INIT status — everything is COMP
(completed) or TS.READY (timesheet done, payroll not started). To verify
the approval-flow endpoints, this script:

  1. Finds a TS.READY batch via getBatchListByDate.
  2. Calls initializePrismBatch (form-urlencoded, NOT JSON — PrismHR 415s
     if you send application/json).
  3. Polls checkInitializationStatus until initStatus == COMPLETE.
  4. Calls getApprovalSummary with clientId + batchId, optionally with
     options=ITEMIZEDDEDUCTIONS.
  5. Saves the response under .planning/verified-responses/.

Confirmed response shape for getApprovalSummary (verified against
a UAT tenant):
    batchId, batchDescription, periodStart, periodEnd, payDate,
    approvalStatus, approvalStatusMessage, netPay, deduction,
    taxWithholding, employerContribution, employerTaxes, providerFee,
    total, itemizedDeduction

Important: this script mutates UAT state — it initializes a payroll
batch. Safe in a UAT sandbox; NEVER run against production.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys
from pathlib import Path

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.secure_env import load_into_environ


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

    matrix = json.loads(pathlib.Path(".planning/verification-matrix.json").read_text())
    client_ids = matrix.get("fixtures", {}).get("client_id", [])
    if not client_ids:
        print("no client_id fixtures; run calibrated_probe.py first")
        return 1

    print(f"scanning {len(client_ids)} clients for INIT-status batches...")
    found_batch: str | None = None
    found_client: str | None = None
    for i, cid in enumerate(client_ids[:50]):  # cap scan to keep it fast
        try:
            resp = await client.get(
                "/payroll/v1/getBatchListForInitialization",
                params={"clientId": cid},
            )
        except Exception as exc:  # noqa: BLE001
            continue
        if not isinstance(resp, dict):
            continue
        # Typical shape: { "batchList": [...], "errorCode": "0", ... }
        batches = resp.get("batchList") or resp.get("batches") or []
        if not isinstance(batches, list):
            continue
        for b in batches:
            if isinstance(b, dict) and b.get("batchId"):
                found_batch = str(b["batchId"])
                found_client = cid
                print(f"  client {cid}: found batch {found_batch}")
                break
        if found_batch:
            break
        if (i + 1) % 10 == 0:
            print(f"  ...scanned {i+1} clients, still looking")
    if not found_batch:
        print("no INIT-status batches found in first 50 clients")
        await http.aclose()
        return 1

    # Probe getApprovalSummary
    print(f"\nprobing getApprovalSummary with client={found_client}, batch={found_batch}")
    for options in [None, "ITEMIZEDDEDUCTIONS"]:
        params = {"clientId": found_client, "batchId": found_batch}
        if options:
            params["options"] = options
        try:
            resp = await client.get("/payroll/v1/getApprovalSummary", params=params)
            status = "ok" if isinstance(resp, dict) and resp.get("errorCode") in (None, "", "0") else "errorCode=" + str(resp.get("errorCode") if isinstance(resp, dict) else "?")
            keys = list(resp.keys())[:20] if isinstance(resp, dict) else []
            print(f"  options={options!r} -> {status}  keys={keys}")
            # Save body for analysis
            out = pathlib.Path(".planning/verified-responses/payroll_getApprovalSummary.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(resp, indent=2, default=str)[:100000], encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            print(f"  options={options!r} -> ERR {str(exc)[:150]}")

    await http.aclose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
