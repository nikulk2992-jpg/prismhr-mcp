"""Dogfood the YTD Reconciliation workflow against a live UAT tenant.

Usage:
    set DOGFOOD_CLIENT_ID=<client-id>
    set DOGFOOD_YEAR=2026            (optional, defaults to current year)
    set DOGFOOD_TOLERANCE=0.02       (optional, default 2 cents)
    uv run python scripts/dogfood_ytd_reconciliation.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.secure_env import load_into_environ

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.adapters import YTDReconciliationReader  # noqa: E402
from simploy.workflows.ytd_reconciliation import (  # noqa: E402
    run_ytd_reconciliation,
)


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID in env.")
        return 2

    year = int(os.environ.get("DOGFOOD_YEAR", str(date.today().year)))
    tolerance = Decimal(os.environ.get("DOGFOOD_TOLERANCE", "0.02"))

    s = Settings()
    if s.environment != "uat":
        print(f"ERROR: UAT-only. environment={s.environment}.")
        return 2
    s.prismhr_peo_id = os.environ["PRISMHR_MCP_PEO_ID"]

    http = httpx.AsyncClient(timeout=120.0)  # bulk YTD is async + slow
    creds = DirectCredentialSource(
        s.prismhr_peo_id,
        os.environ["PRISMHR_MCP_USERNAME"],
        os.environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(s, creds, http)
    client = PrismHRClient(s, session, http)
    reader = YTDReconciliationReader(client)

    print()
    print("=" * 72)
    print(" YTD Payroll Reconciliation — UAT dogfood")
    print(f" client: {client_id}  year: {year}  tolerance: {tolerance}")
    print("=" * 72)
    print()

    try:
        report = await run_ytd_reconciliation(
            reader,
            client_id=client_id,
            year=year,
            tolerance=tolerance,
        )
    finally:
        await http.aclose()

    print(
        f"As of {report.as_of.isoformat()}  |  "
        f"employees: {report.total}  |  "
        f"passed: {report.passed}  |  "
        f"failed: {report.failed}"
    )
    print()

    if not report.employees:
        print("No YTD or voucher records returned.")
        return 0

    shown = 0
    for emp in report.employees:
        if not emp.findings:
            continue
        shown += 1
        status = "PASS" if emp.passed else "FAIL"
        print(f"[{status}] {emp.employee_id}   vouchers={emp.voucher_count}")
        print(f"        YTD: gross={emp.ytd_gross} net={emp.ytd_net} tax={emp.ytd_tax}")
        print(f"        SUM: gross={emp.voucher_gross} net={emp.voucher_net} tax={emp.voucher_tax}")
        for f in emp.findings:
            sev = f.severity.upper().rjust(8)
            print(f"        {sev}  {f.code}: {f.message}")
        print()
        if shown >= 20:
            break

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
