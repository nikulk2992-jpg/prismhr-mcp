"""Dogfood the Benefits-Deduction Audit against a live UAT tenant.

Usage:
    set DOGFOOD_CLIENT_ID=<client-id>
    uv run python scripts/dogfood_benefits_deduction_audit.py
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

from simploy.workflows.adapters import BenefitsDeductionAuditReader  # noqa: E402
from simploy.workflows.benefits_deduction_audit import (  # noqa: E402
    run_benefits_deduction_audit,
)


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID in env.")
        return 2

    s = Settings()
    if s.environment != "uat":
        print(f"ERROR: UAT-only. environment={s.environment}.")
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
    reader = BenefitsDeductionAuditReader(client)

    print()
    print("=" * 72)
    print(" Benefits-Deduction Audit — UAT dogfood")
    print(f" client: {client_id}")
    print("=" * 72)
    print()

    try:
        report = await run_benefits_deduction_audit(reader, client_id=client_id)
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
        print("No enrollment confirmations returned.")
        return 0

    shown = 0
    for emp in report.employees:
        if not emp.findings:
            continue
        shown += 1
        status = "PASS" if emp.passed else "FAIL"
        print(f"[{status}] {emp.last_name}, {emp.first_name} ({emp.employee_id})")
        print(f"        enrolled: {emp.enrolled_plans}")
        print(f"        deductions: {emp.deduction_codes}")
        for f in emp.findings:
            sev = f.severity.upper().rjust(8)
            print(f"        {sev}  {f.code}: {f.message}")
        print()
        if shown >= 20:
            break

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
