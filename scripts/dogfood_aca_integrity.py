"""Dogfood ACA Integrity workflow against UAT."""

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

from simploy.workflows.adapters import ACAIntegrityReader  # noqa: E402
from simploy.workflows.aca_integrity import run_aca_integrity  # noqa: E402


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID")
        return 2
    year = int(os.environ.get("DOGFOOD_YEAR", str(date.today().year - 1)))

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
    reader = ACAIntegrityReader(client)

    print()
    print("=" * 72)
    print(f" ACA Integrity — UAT dogfood  client={client_id}  year={year}")
    print("=" * 72)
    print()

    try:
        report = await run_aca_integrity(reader, client_id=client_id, year=year)
    finally:
        await http.aclose()

    print(f"critical findings: {report.critical_count}")
    print()
    print("Month-level:")
    for m in report.months:
        if m.findings:
            print(f"  month {m:2d}" if False else f"  month {m.month:02d}  MEC={m.mec_indicator or '-'}  FT={m.ft_count}  MEC#={m.mec_count}")
            for f in m.findings:
                print(f"    {f.severity.upper():8s}  {f.code}: {f.message}")

    print()
    print(f"Employee-level findings: {len(report.employees)}")
    for emp in report.employees[:20]:
        if not emp.findings:
            continue
        print(f"  {emp.employee_id}")
        for f in emp.findings:
            print(f"    {f.severity.upper():8s}  {f.code}: {f.message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
