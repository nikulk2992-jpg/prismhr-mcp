"""Run the commercial_tax_engine_diff against a real UAT client.

Exercises: federal Pub 15-T calc, FICA/FUTA, MO+IL+PA+OH+MA+NJ+CA+NY
state engines, multi_state validator (incl. WSL per-line allocation).

Usage:
  set DOGFOOD_CLIENT_ID=<client>
  .venv/Scripts/python scripts/dogfood_tax_engine.py
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
from simploy.workflows.adapters import TaxEngineDiffReader  # noqa: E402
from simploy.workflows.tax_engine_diff import run_tax_engine_diff  # noqa: E402


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    cid = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not cid:
        print("ERROR: set DOGFOOD_CLIENT_ID")
        return 2
    lookback = int(os.environ.get("DOGFOOD_LOOKBACK_DAYS", "30"))
    today = date.today()
    start = today - timedelta(days=lookback)

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
    reader = TaxEngineDiffReader(client)

    print()
    print("=" * 74)
    print(f" Tax engine diff — live dogfood")
    print(f" client:  {cid}")
    print(f" period:  {start.isoformat()} .. {today.isoformat()}")
    print("=" * 74)

    try:
        report = await run_tax_engine_diff(
            reader, client_id=cid,
            period_start=start, period_end=today,
        )
    finally:
        await http.aclose()

    print()
    print(f"Vouchers analyzed: {len(report.vouchers)}")
    print(f"Flagged: {report.flagged}")
    print()

    if not report.flagged:
        print("No findings.")
        return 0

    # Group findings by code
    from collections import defaultdict
    by_code: dict[str, list] = defaultdict(list)
    for v in report.vouchers:
        for f in v.findings:
            by_code[f.code].append((v.voucher_id, v.employee_id, f))

    print("Findings by code:")
    for code, rows in sorted(by_code.items(), key=lambda kv: -len(kv[1])):
        print(f"  {code:40s}  {len(rows)}")
    print()

    # Show first 3 of each interesting code
    for code in (
        "STATE_TAX_DELTA",
        "WRONG_STATE_WITHHELD",
        "DOUBLE_WITHHELD_NON_RECIPROCAL",
        "PER_LINE_STATE_WAGES_NO_WITHHOLDING",
        "MULTI_STATE_TAX_ON_VOUCHER",
        "RECIPROCAL_WORK_WITHHELD_NO_CERT",
        "SS_DELTA",
        "MEDICARE_DELTA",
        "FIT_DELTA",
    ):
        if code not in by_code:
            continue
        print(f"--- {code} (showing 3 of {len(by_code[code])}) ---")
        for vid, eid, f in by_code[code][:3]:
            print(f"  voucher {vid}  emp {eid}  {f.severity.upper()}: {f.message[:100]}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
