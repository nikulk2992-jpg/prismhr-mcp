"""Quick end-to-end dogfood of every live reader against one client.

Exercises the readers that got added this session: garnishment, PTO,
dependent age-out, COBRA, retirement loan, 1099-NEC, new-hire reporting,
final paycheck, off-cycle.

Usage:
  set DOGFOOD_CLIENT_ID=<client>
  .venv/Scripts/python scripts/dogfood_all_readers.py
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
from simploy.workflows.adapters import (  # noqa: E402
    CobraEligibilityReader,
    DependentAgeOutReader,
    Form1099NECPreflightReader,
    GarnishmentHistoryReader,
    PTOReconciliationReader,
    RetirementLoanStatusReader,
    StateNewHireReportingReader,
    FinalPaycheckComplianceReader,
    OffCycleVoucherReader,
)


async def _try(label: str, coro):
    print(f"[{label}]...")
    try:
        rows = await coro
        print(f"  OK  rows={len(rows) if hasattr(rows, '__len__') else 'n/a'}")
        if rows and hasattr(rows, '__len__') and len(rows):
            first = rows[0]
            keys = list(first.keys())[:6] if isinstance(first, dict) else []
            print(f"  first-row keys sample: {keys}")
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR  {type(exc).__name__}: {str(exc)[:80]}")


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    cid = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not cid:
        print("ERROR: set DOGFOOD_CLIENT_ID")
        return 2

    s = Settings()
    s.prismhr_peo_id = os.environ["PRISMHR_MCP_PEO_ID"]
    http = httpx.AsyncClient(timeout=120.0)
    creds = DirectCredentialSource(
        s.prismhr_peo_id,
        os.environ["PRISMHR_MCP_USERNAME"],
        os.environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(s, creds, http)
    c = PrismHRClient(s, session, http)

    today = date.today()
    start = today - timedelta(days=90)

    print(f"\nDogfooding all readers for client {cid}")
    print(f"Period: {start.isoformat()} .. {today.isoformat()}\n")

    try:
        await _try("garnishment_holders",
                   GarnishmentHistoryReader(c).list_garnishment_holders(cid))
        await _try("cobra_terminations",
                   CobraEligibilityReader(c).get_terminations(cid, 60))
        await _try("cobra_enrollees",
                   CobraEligibilityReader(c).get_cobra_enrollees(cid))
        await _try("dependents_covered",
                   DependentAgeOutReader(c).list_covered_dependents(cid))
        await _try("pto_classes",
                   PTOReconciliationReader(c).get_pto_classes(cid))
        await _try("pto_plans",
                   PTOReconciliationReader(c).get_pto_plans(cid))
        await _try("pto_employee_rows",
                   PTOReconciliationReader(c).get_employee_pto_rows(cid))
        await _try("retirement_loans",
                   RetirementLoanStatusReader(c).get_retirement_loans(cid))
        await _try("contractors_paid_this_year",
                   Form1099NECPreflightReader(c).list_contractors_paid_in_year(cid, today.year))
        await _try("new_hires_since_90d",
                   StateNewHireReportingReader(c).list_new_hires(cid, start))
        await _try("recent_separations",
                   FinalPaycheckComplianceReader(c).list_recent_separations(cid, start))
        await _try("off_cycle_vouchers",
                   OffCycleVoucherReader(c).list_off_cycle_vouchers(cid, start, today))
    finally:
        await http.aclose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
