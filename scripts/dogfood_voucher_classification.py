"""Dogfood voucher_classification_audit against live UAT via the
new VoucherClassificationReader adapter.

Picks a client, runs the workflow against a recent pay period, and
prints any findings. Surfaces HARDIN-class misflags end-to-end through
the actual MCP-facing reader (not the ad-hoc sweep script).

Usage:
  set DOGFOOD_CLIENT_ID=001315
  .venv/Scripts/python scripts/dogfood_voucher_classification.py
"""

from __future__ import annotations

import asyncio
import os
import sys
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

    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "001315").strip()
    lookback = int(os.environ.get("DOGFOOD_LOOKBACK_DAYS", "90"))
    today = date.today()
    start = today - timedelta(days=lookback)

    s = Settings()
    if s.environment != "uat":
        print(f"ERROR: UAT-only. environment={s.environment}")
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
    reader = VoucherClassificationReader(client)

    print()
    print("=" * 74)
    print(" Voucher Classification Audit — live reader dogfood")
    print(f" client:  {client_id}")
    print(f" period:  {start.isoformat()} .. {today.isoformat()}")
    print("=" * 74)
    print()

    try:
        report = await run_voucher_classification_audit(
            reader,
            client_id=client_id,
            period_start=start,
            period_end=today,
        )
    finally:
        await http.aclose()

    print(f"Vouchers analyzed: {report.total}")
    print(f"Clean:             {report.clean}")
    print(f"Flagged:           {report.flagged}")
    print()

    if not report.flagged:
        print("No findings.")
        return 0

    for v in report.vouchers:
        if not v.findings and not any(l.findings for l in v.lines):
            continue
        print(f"[voucher {v.voucher_id}]  employee {v.employee_id}  "
              f"pay_date {v.pay_date.isoformat() if v.pay_date else '?'}  "
              f"earnings ${v.total_earnings}")
        for f in v.findings:
            print(f"   {f.severity.upper():8s}  {f.code}: {f.message}")
        for line in v.lines:
            for f in line.findings:
                print(f"   line {line.pay_code}  {f.severity.upper():8s}  "
                      f"{f.code}: {f.message}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
