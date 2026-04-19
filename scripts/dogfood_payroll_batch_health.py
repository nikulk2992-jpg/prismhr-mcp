"""Dogfood the Payroll Batch Health workflow against a live UAT tenant.

Usage:
    set DOGFOOD_CLIENT_ID=<client-id>
    uv run python scripts/dogfood_payroll_batch_health.py

Refuses to run against production. No files written.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.secure_env import load_into_environ

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.adapters import PayrollBatchHealthReader  # noqa: E402
from simploy.workflows.payroll_batch_health import (  # noqa: E402
    run_payroll_batch_health,
)


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))

    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID in env.")
        return 2

    s = Settings()
    if s.environment != "uat":
        print(f"ERROR: dogfood is UAT-only. environment={s.environment}.")
        return 2
    s.prismhr_peo_id = os.environ["PRISMHR_MCP_PEO_ID"]

    http = httpx.AsyncClient(timeout=60.0)
    creds = DirectCredentialSource(
        s.prismhr_peo_id,
        os.environ["PRISMHR_MCP_USERNAME"],
        os.environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(s, creds, http)
    client = PrismHRClient(s, session, http)
    reader = PayrollBatchHealthReader(client)

    print()
    print("=" * 72)
    print(" Payroll Batch Health Check — UAT dogfood")
    print(f" client: {client_id}")
    print("=" * 72)
    print()

    try:
        report = await run_payroll_batch_health(reader, client_id=client_id)
    finally:
        await http.aclose()

    print(
        f"As of {report.as_of.isoformat()}  |  "
        f"open batches: {report.total}  |  "
        f"clean: {report.clean}  |  "
        f"flagged: {report.flagged}"
    )
    print()

    if not report.batches:
        print("No open batches for this client.")
        return 0

    for b in report.batches:
        marker = "OK" if b.passed and not b.findings else "FLAG"
        print(f"[{marker}] Batch {b.batch_id}  status={b.status}  vouchers={b.voucher_count}")
        if b.status_description:
            print(f"        {b.status_description}")
        if b.pay_date:
            print(f"        pay date: {b.pay_date.isoformat()}")
        if b.period_end:
            print(f"        period end: {b.period_end.isoformat()}")
        for f in b.findings:
            sev = f.severity.upper().rjust(8)
            print(f"        {sev}  {f.code}: {f.message}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
