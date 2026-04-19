"""Dogfood the New Hire Onboarding Audit workflow against a live UAT tenant.

Usage:
    # 1. Encrypt creds into .env.local.enc via scripts/encrypt_env.py
    # 2. Pick a client ID you have access to in UAT:
    #      set DOGFOOD_CLIENT_ID=<client-id>
    #      set DOGFOOD_LOOKBACK_DAYS=90        (optional, default 30)
    #      set DOGFOOD_MAX_EMPLOYEES=10        (optional, default 5)
    # 3. Run:
    #      uv run python scripts/dogfood_new_hire_audit.py

Refuses to run against production. Caps employee count so an accidental
invocation does not pull thousands of records. Prints a human-readable
report, nothing else — no files written, nothing logged to disk.
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

# commercial/ is a sibling package; add it to path for this local script
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.workflows.adapters import PrismHRClientReader  # noqa: E402
from simploy.workflows.new_hire_audit import run_new_hire_audit  # noqa: E402


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))

    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID in env before running.")
        return 2

    lookback = int(os.environ.get("DOGFOOD_LOOKBACK_DAYS", "30"))
    max_employees = int(os.environ.get("DOGFOOD_MAX_EMPLOYEES", "5"))

    s = Settings()
    if s.environment != "uat":
        print(f"ERROR: dogfood is UAT-only. Current environment={s.environment}.")
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
    reader = PrismHRClientReader(client)

    # Wrap the reader so we never audit more than DOGFOOD_MAX_EMPLOYEES.
    orig_list = reader.get_employee_list

    async def capped_list(cid: str, since):  # type: ignore[no-untyped-def]
        roster = await orig_list(cid, since)
        if len(roster) > max_employees:
            print(
                f"[cap] roster has {len(roster)}; capping audit at "
                f"{max_employees} per DOGFOOD_MAX_EMPLOYEES."
            )
        return roster[:max_employees]

    reader.get_employee_list = capped_list  # type: ignore[method-assign]

    print()
    print("=" * 72)
    print(f" New Hire Onboarding Audit — UAT dogfood")
    print(f" client: {client_id}")
    print(f" lookback: {lookback} days   cap: {max_employees} employees")
    print("=" * 72)
    print()

    try:
        report = await run_new_hire_audit(
            reader,
            client_id=client_id,
            lookback_days=lookback,
        )
    finally:
        await http.aclose()

    print(
        f"As of {report.as_of.isoformat()}  |  "
        f"audited: {report.total}  |  "
        f"passed: {report.passed}  |  "
        f"failed: {report.failed}"
    )
    print()

    if not report.employees:
        print("No new hires in the lookback window. Nothing to audit.")
        return 0

    for emp in report.employees:
        status = "PASS" if emp.passed else "FAIL"
        print(f"[{status}] {emp.last_name}, {emp.first_name} ({emp.employee_id})")
        if emp.hire_date:
            print(f"        hired: {emp.hire_date.isoformat()}")
        if not emp.findings:
            print("        (no issues)")
        for f in emp.findings:
            sev = f.severity.upper().rjust(8)
            print(f"        {sev}  {f.code}: {f.message}")
        print()

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
