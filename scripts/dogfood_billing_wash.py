"""Dogfood Billing-vs-Payroll Wash Audit against UAT."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.secure_env import load_into_environ

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.adapters import BillingWashAuditLiveReader  # noqa: E402
from simploy.workflows.billing_wash_audit import run_billing_wash_audit  # noqa: E402


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID")
        return 2
    today = date.today()
    year = int(os.environ.get("DOGFOOD_YEAR", str(today.year)))
    month = int(os.environ.get("DOGFOOD_MONTH", str(max(1, today.month - 1))))

    s = Settings()
    if s.environment != "uat":
        print(f"ERROR: UAT-only. environment={s.environment}")
        return 2
    s.prismhr_peo_id = os.environ["PRISMHR_MCP_PEO_ID"]

    http = httpx.AsyncClient(timeout=120.0)
    creds = DirectCredentialSource(
        s.prismhr_peo_id,
        os.environ["PRISMHR_MCP_USERNAME"],
        os.environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(s, creds, http)
    client = PrismHRClient(s, session, http)
    reader = BillingWashAuditLiveReader(client)

    print()
    print("=" * 72)
    print(f" Billing-Wash Audit — UAT  client={client_id}  year={year}  month={month:02d}")
    print("=" * 72)
    print()

    try:
        report = await run_billing_wash_audit(
            reader, client_id=client_id, year=year, month=month
        )
    finally:
        await http.aclose()

    print(f"rows audited: {report.total}  flagged: {report.flagged}")
    print()

    shown = 0
    for row in report.rows:
        if not row.findings:
            continue
        shown += 1
        print(
            f"  {row.employee_id}  plan={row.plan_id}  "
            f"billed=${row.premium_billed}  deducted=${row.employee_deduction}"
        )
        for f in row.findings:
            print(f"    {f.severity.upper():8s}  {f.code}: {f.message}")
        if shown >= 20:
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
