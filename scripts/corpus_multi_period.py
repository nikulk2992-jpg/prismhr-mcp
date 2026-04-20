"""Multi-period classification-audit corpus builder.

Runs the voucher_classification_audit + sweep-level counts across
every calendar quarter in a year. Produces:
  * .planning/corpus-{year}-Q{n}.json — per-quarter findings snapshot
  * .planning/corpus-summary.md        — per-quarter aggregate table

Purpose: regression corpus. If we change a workflow later, we can
re-run the same quarters and diff findings to ensure nothing silently
drifted.

Usage:
  DOGFOOD_MAX_CLIENTS=254 .venv/Scripts/python scripts/corpus_multi_period.py 2025
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import date
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


QUARTERS = [
    (1, date(2025, 1, 1), date(2025, 3, 31)),
    (2, date(2025, 4, 1), date(2025, 6, 30)),
    (3, date(2025, 7, 1), date(2025, 9, 30)),
    (4, date(2025, 10, 1), date(2025, 12, 31)),
]


async def scan_quarter(
    client: PrismHRClient,
    reader: VoucherClassificationReader,
    clients: list[dict],
    start: date,
    end: date,
) -> dict:
    findings_by_code: dict[str, int] = defaultdict(int)
    hits_by_client: dict[str, int] = defaultdict(int)
    total_vouchers = 0
    total_flagged = 0
    errored = 0

    for cl in clients:
        cid = str(cl.get("clientId") or "")
        if not cid:
            continue
        try:
            report = await run_voucher_classification_audit(
                reader, client_id=cid,
                period_start=start, period_end=end,
            )
        except Exception:  # noqa: BLE001
            errored += 1
            continue
        total_vouchers += report.total
        for v in report.vouchers:
            if v.findings or any(line.findings for line in v.lines):
                total_flagged += 1
                hits_by_client[cid] += 1
            for f in v.findings:
                findings_by_code[f.code] += 1
            for line in v.lines:
                for f in line.findings:
                    findings_by_code[f.code] += 1

    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "clients_scanned": len(clients),
        "errored": errored,
        "total_vouchers": total_vouchers,
        "total_flagged": total_flagged,
        "findings_by_code": dict(findings_by_code),
        "clients_with_hits": len(hits_by_client),
    }


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    max_clients = int(os.environ.get("DOGFOOD_MAX_CLIENTS", "254"))
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025

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
    reader = VoucherClassificationReader(c)

    try:
        r = await c.get("/clientMaster/v1/getClientList")
        result = r.get("clientListResult") or r
        clients = result.get("clientList") or []
        clients = clients[:max_clients]
        print(f"Scanning {len(clients)} clients across {year} quarters.\n")

        results = []
        for q, start, end in QUARTERS:
            if start.year != year:
                continue
            print(f"Q{q} {year}: {start.isoformat()} .. {end.isoformat()}")
            snapshot = await scan_quarter(c, reader, clients, start, end)
            snapshot["quarter"] = q
            snapshot["year"] = year
            results.append(snapshot)
            out_path = REPO / ".planning" / f"corpus-{year}-Q{q}.json"
            out_path.write_text(
                json.dumps(snapshot, indent=2, default=str),
                encoding="utf-8",
            )
            print(f"  -> {out_path.relative_to(REPO)}  "
                  f"({snapshot['total_vouchers']} vouchers, "
                  f"{snapshot['total_flagged']} flagged)")

        # Summary markdown
        summary = [
            f"# Corpus summary — {year}",
            "",
            "| Quarter | Vouchers | Flagged | Clients w/hits | Top finding |",
            "|---|---:|---:|---:|---|",
        ]
        for s_ in results:
            top_code = max(s_["findings_by_code"].items(),
                           key=lambda kv: kv[1], default=("—", 0))
            summary.append(
                f"| Q{s_['quarter']} {s_['year']} | "
                f"{s_['total_vouchers']} | {s_['total_flagged']} | "
                f"{s_['clients_with_hits']} | "
                f"{top_code[0]} ({top_code[1]}) |"
            )
        summary.append("")
        summary.append("## Findings by code (all quarters combined)")
        summary.append("")
        all_codes: dict[str, int] = defaultdict(int)
        for s_ in results:
            for code, n in s_["findings_by_code"].items():
                all_codes[code] += n
        summary.append("| Code | Total |")
        summary.append("|---|---:|")
        for code, n in sorted(all_codes.items(), key=lambda kv: -kv[1]):
            summary.append(f"| {code} | {n} |")
        (REPO / ".planning" / f"corpus-summary-{year}.md").write_text(
            "\n".join(summary) + "\n", encoding="utf-8"
        )
        print(f"\nWrote .planning/corpus-summary-{year}.md")
    finally:
        await http.aclose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
