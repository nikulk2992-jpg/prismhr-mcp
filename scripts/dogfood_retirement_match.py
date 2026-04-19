"""Dogfood 401(k) Match Compliance workflow against UAT."""

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

from simploy.workflows.adapters import RetirementMatchReader  # noqa: E402
from simploy.workflows.retirement_match_compliance import (  # noqa: E402
    run_retirement_match_compliance,
)


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID.")
        return 2
    year = int(os.environ.get("DOGFOOD_YEAR", str(date.today().year)))

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
    reader = RetirementMatchReader(client)

    print()
    print("=" * 72)
    print(" 401(k) Match Compliance — UAT dogfood")
    print(f" client: {client_id}  year: {year}")
    print("=" * 72)
    print()

    try:
        report = await run_retirement_match_compliance(
            reader, client_id=client_id, year=year
        )
    finally:
        await http.aclose()

    print(
        f"plan: {report.plan_id}  |  employees: {len(report.employees)}  |  "
        f"flagged: {report.flagged}"
    )
    print()

    shown = 0
    for emp in report.employees:
        if not emp.findings:
            continue
        shown += 1
        age = f"age={emp.age}" if emp.age is not None else "age=?"
        print(f"[FAIL] {emp.employee_id}  {age}")
        print(f"        EE contrib: ${emp.ytd_employee_contribution}")
        print(f"        ER match:   ${emp.ytd_employer_match}  (expected ${emp.expected_match})")
        for f in emp.findings:
            sev = f.severity.upper().rjust(8)
            print(f"        {sev}  {f.code}: {f.message}")
        print()
        if shown >= 20:
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
