"""Dogfood W-2 Distribution workflow against UAT.

Local-only: writes PDFs + a manifest to a temp dir under
`./tmp/w2-dogfood/`. NEVER calls a real mail or email provider. Ship
path only light up when real Lob / Graph adapters are wired in the
commercial deployment.
"""

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

from simploy.workflows.adapters import PrismHRW2Source  # noqa: E402
from simploy.workflows.w2_distribution import (  # noqa: E402
    DeliveryMode,
    LocalDryRunArchiver,
    LocalDryRunEmailSender,
    LocalDryRunMailSender,
    run_w2_distribution,
)


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID.")
        return 2
    year = os.environ.get("DOGFOOD_YEAR", "2023")
    max_emp = int(os.environ.get("DOGFOOD_MAX_EMPLOYEES", "3"))

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
    source = PrismHRW2Source(client, max_employees=max_emp)

    out_dir = Path(os.environ.get("DOGFOOD_OUT_DIR", "tmp/w2-dogfood"))
    out_dir.mkdir(parents=True, exist_ok=True)

    mail = LocalDryRunMailSender(out_dir=out_dir)
    email = LocalDryRunEmailSender(out_dir=out_dir)
    archiver = LocalDryRunArchiver(out_dir=out_dir)

    print()
    print("=" * 72)
    print(" W-2 Distribution — UAT dogfood (LOCAL DRY RUN)")
    print(f" client={client_id}  year={year}  max_emp={max_emp}")
    print(f" output dir: {out_dir.resolve()}")
    print("=" * 72)
    print()

    try:
        report = await run_w2_distribution(
            source=source,
            mail_sender=mail,
            email_sender=email,
            archiver=archiver,
            client_id=client_id,
            year=year,
            modes=[DeliveryMode.MAIL, DeliveryMode.EMAIL, DeliveryMode.ARCHIVE],
            max_employees=max_emp,
            certified_mail=True,
        )
    finally:
        await http.aclose()

    print(f"roster with W-2 for {year}: {report.total}  delivered: {report.delivered}  failed: {report.failed}")
    print()

    for emp in report.employees:
        print(f"  {emp.last_name}, {emp.first_name} ({emp.employee_id})  pdf={emp.pdf_size_bytes}B")
        if emp.mail_tracking_id:
            addr_tag = f" [addr={emp.mail_address_source}]" if emp.mail_address_source else ""
            print(f"    MAIL     -> {emp.mail_tracking_id}{addr_tag}")
        if emp.email_message_id:
            print(f"    EMAIL    -> {emp.email_message_id}")
        if emp.archive_url:
            print(f"    ARCHIVE  -> {emp.archive_url}")
        for f in emp.findings:
            print(f"    {f.severity.upper():8s}  {f.code}: {f.message}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
