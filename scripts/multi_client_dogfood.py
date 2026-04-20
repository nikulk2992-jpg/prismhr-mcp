"""Multi-client dogfood harness for the voucher_classification_audit
live reader. Runs across every client in the tenant, sums findings,
and emits a cross-client dashboard.

Builds the corpus needed to validate that the live reader + finding
logic behaves consistently across heterogeneous client shapes (big
clients, tiny clients, Ohio locals, multi-state, etc.).

Usage:
  DOGFOOD_LOOKBACK_DAYS=30 .venv/Scripts/python scripts/multi_client_dogfood.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "commercial"))

from prismhr_mcp.auth.credentials import DirectCredentialSource  # noqa: E402
from prismhr_mcp.auth.prismhr_session import SessionManager  # noqa: E402
from prismhr_mcp.clients.prismhr import PrismHRClient  # noqa: E402
from prismhr_mcp.config import Settings  # noqa: E402
from prismhr_mcp.secure_env import load_into_environ  # noqa: E402
from simploy.workflows.adapters import VoucherClassificationReader  # noqa: E402
from simploy.workflows.voucher_classification_audit import (  # noqa: E402
    run_voucher_classification_audit,
)


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    lookback = int(os.environ.get("DOGFOOD_LOOKBACK_DAYS", "30"))
    max_clients = int(os.environ.get("DOGFOOD_MAX_CLIENTS", "999"))
    today = date.today()
    start = today - timedelta(days=lookback)

    s = Settings()
    s.prismhr_peo_id = os.environ["PRISMHR_MCP_PEO_ID"]

    http = httpx.AsyncClient(timeout=120.0)
    creds = DirectCredentialSource(
        s.prismhr_peo_id,
        os.environ["PRISMHR_MCP_USERNAME"],
        os.environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(s, creds, http)
    client = PrismHRClient(s, session, http)
    reader = VoucherClassificationReader(client)

    try:
        list_body = await client.get("/clientMaster/v1/getClientList")
        result = list_body.get("clientListResult") or list_body
        all_clients = result.get("clientList") or []
        print(f"Total clients: {len(all_clients)}. Scanning up to {max_clients}.")
        print(f"Period: {start.isoformat()} .. {today.isoformat()}")
        print()

        findings_by_code: dict[str, int] = defaultdict(int)
        hits_by_client: dict[str, list[str]] = defaultdict(list)
        total_vouchers = 0
        total_flagged = 0
        errored = 0

        for i, cl in enumerate(all_clients[:max_clients], 1):
            cid = str(cl.get("clientId") or "")
            cname = str(cl.get("clientName") or "")[:30]
            if not cid:
                continue
            if i % 10 == 0 or i == 1:
                print(f"  [{i}/{min(len(all_clients), max_clients)}] {cid} {cname}...")
            try:
                report = await run_voucher_classification_audit(
                    reader,
                    client_id=cid,
                    period_start=start,
                    period_end=today,
                )
            except Exception as exc:  # noqa: BLE001
                errored += 1
                continue
            total_vouchers += report.total
            for v in report.vouchers:
                if v.findings or any(l.findings for l in v.lines):
                    total_flagged += 1
                for f in v.findings:
                    findings_by_code[f.code] += 1
                    hits_by_client[cid].append(
                        f"{v.employee_id}:{f.code}"
                    )
                for line in v.lines:
                    for f in line.findings:
                        findings_by_code[f.code] += 1
                        hits_by_client[cid].append(
                            f"{v.employee_id}/{line.pay_code}:{f.code}"
                        )

        print()
        print("=" * 70)
        print(" Cross-Client Dogfood Summary")
        print("=" * 70)
        print(f"Clients scanned:    {min(len(all_clients), max_clients)}")
        print(f"Errored:            {errored}")
        print(f"Vouchers analyzed:  {total_vouchers}")
        print(f"Flagged vouchers:   {total_flagged}")
        print()
        print("Findings by code:")
        for code, count in sorted(findings_by_code.items(), key=lambda kv: -kv[1]):
            print(f"  {code:35s}  {count}")
        print()
        print(f"Clients with hits ({len(hits_by_client)}):")
        for cid, hits in sorted(hits_by_client.items(), key=lambda kv: -len(kv[1]))[:15]:
            print(f"  {cid}  {len(hits)} hits  e.g. {hits[:2]}")
    finally:
        await http.aclose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
