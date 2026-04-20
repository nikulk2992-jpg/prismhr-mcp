"""Sweep every client for potential FICA_EXEMPT_MISFLAG hits.

Pure voucher-side analysis — doesn't need the employee classification
fields (which UAT doesn't populate). Logic:

  For each client:
    For each recent batch (past N days):
      For each voucher in the batch:
        If voucher has wages > 0 AND no SS tax (code starts 00-12)
        AND no Medicare tax (code starts 00-11)
        AND voucher type is R (regular, not correction/void):
          → this employee's payroll skipped FICA.
          → aggregate per (client, employee).

Output: per employee, count of FICA-less vouchers + total wages skipped.
High counts = high-confidence FICA exempt flag is set (and may be wrong).

UAT-safe; read-only. Does NOT require prod. Run with:

    set DOGFOOD_LOOKBACK_DAYS=90
    .venv/Scripts/python scripts/sweep_fica_exempt_misflags.py

Or limit to one employer by setting DOGFOOD_EMPLOYER_ID.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.secure_env import load_into_environ


def _dec(raw) -> Decimal:
    if raw in (None, "", 0):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def _has_fica(voucher: dict) -> tuple[bool, bool]:
    """Return (has_ss_row, has_medicare_row).

    Key: row PRESENCE, not amount > 0. A high earner over the SS wage
    base cap ($168,600 for 2025) legitimately has $0 OASDI withheld with
    `empOverLimitAmount` populated — the 00-12 row is still present.
    Only row-absence means FICA was skipped entirely (the misflag case).
    """
    has_ss = False
    has_med = False
    for t in voucher.get("employeeTax") or []:
        code = str(t.get("empTaxDeductCode") or "")
        if code.startswith("00-12"):
            has_ss = True
        elif code.startswith("00-11"):
            has_med = True
    return has_ss, has_med


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))

    lookback_days = int(os.environ.get("DOGFOOD_LOOKBACK_DAYS", "90"))
    employer_filter = os.environ.get("DOGFOOD_EMPLOYER_ID", "").strip()
    max_clients = int(os.environ.get("DOGFOOD_MAX_CLIENTS", "9999"))
    today = date.today()
    start = today - timedelta(days=lookback_days)

    s = Settings()
    s.prismhr_peo_id = os.environ["PRISMHR_MCP_PEO_ID"]
    http = httpx.AsyncClient(timeout=60.0)
    creds = DirectCredentialSource(
        s.prismhr_peo_id,
        os.environ["PRISMHR_MCP_USERNAME"],
        os.environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(s, creds, http)
    c = PrismHRClient(s, session, http)

    print()
    print("=" * 78)
    print(" FICA_EXEMPT_MISFLAG sweep")
    print(f" environment: {s.environment}")
    print(f" lookback:    {lookback_days} days  ({start.isoformat()} .. {today.isoformat()})")
    if employer_filter:
        print(f" employer:    {employer_filter}  (filtered)")
    print("=" * 78)
    print()

    try:
        # ---- get client list ----
        client_list_body = await c.get("/clientMaster/v1/getClientList")
        # Real shape: { clientListResult: { clientList: [ {clientId,...} ] } }
        result = client_list_body.get("clientListResult") or client_list_body
        all_clients = (
            result.get("clientList")
            or result.get("clients")
            or []
        )
        if isinstance(all_clients, dict):
            all_clients = all_clients.get("client", [])
        print(f"Total clients in tenant: {len(all_clients)}")

        if employer_filter:
            clients = [
                cl for cl in all_clients
                if str(cl.get("employerId") or "") == employer_filter
            ]
            print(f"After employer filter '{employer_filter}': {len(clients)} clients")
        else:
            clients = all_clients

        clients = clients[:max_clients]
        print()

        # ---- aggregate hits ----
        hits: dict[tuple[str, str], dict] = defaultdict(
            lambda: {
                "voucher_count": 0,
                "total_wages_skipped": Decimal("0"),
                "batches_seen": set(),
                "voucher_ids": [],
                "pay_date_range": [None, None],
            }
        )
        clients_with_data = 0
        clients_errored = 0

        for i, cl in enumerate(clients, 1):
            cid = str(cl.get("clientId") or cl.get("id") or "")
            cname = str(cl.get("clientName") or cl.get("name") or "")[:30]
            if not cid:
                continue
            if i % 10 == 0 or i == 1:
                print(f"  [{i}/{len(clients)}] scanning {cid} {cname}...")

            try:
                batches_body = await c.get(
                    "/payroll/v1/getBatchListByDate",
                    params={
                        "clientId": cid,
                        "startDate": start.isoformat(),
                        "endDate": today.isoformat(),
                        "dateType": "POST",
                    },
                )
            except Exception:  # noqa: BLE001
                clients_errored += 1
                continue

            # Some tenants return [] or a bare list for empty clients.
            if isinstance(batches_body, list):
                batches = batches_body
            elif isinstance(batches_body, dict):
                batches = batches_body.get("batchList") or batches_body.get("availableBatches") or []
            else:
                batches = []
            if not batches:
                continue
            clients_with_data += 1

            for b in batches:
                bid = str(b.get("batchId") or b.get("id") or "")
                if not bid:
                    continue
                try:
                    vbody = await c.get(
                        "/payroll/v1/getPayrollVoucherForBatch",
                        params={"clientId": cid, "batchId": bid},
                    )
                except Exception:  # noqa: BLE001
                    continue
                if isinstance(vbody, list):
                    vouchers = vbody
                elif isinstance(vbody, dict):
                    vouchers = vbody.get("payrollVoucher") or []
                else:
                    vouchers = []
                for v in vouchers:
                    vtype = str(v.get("type") or "").upper()
                    # skip corrections/voids
                    if vtype in {"C", "V"}:
                        continue
                    total_earn = _dec(v.get("totalEarnings"))
                    if total_earn <= 0:
                        continue
                    has_ss, has_med = _has_fica(v)
                    if has_ss and has_med:
                        continue  # normal voucher
                    # FICA missing on positive-wage regular voucher
                    eid = str(v.get("employeeId") or "")
                    vid = str(v.get("voucherId") or "")
                    pd = str(v.get("payDate") or "")
                    key = (cid, eid)
                    rec = hits[key]
                    rec["voucher_count"] += 1
                    rec["total_wages_skipped"] += total_earn
                    rec["batches_seen"].add(bid)
                    rec["voucher_ids"].append(vid)
                    # Track earliest+latest pay date
                    if pd:
                        if rec["pay_date_range"][0] is None or pd < rec["pay_date_range"][0]:
                            rec["pay_date_range"][0] = pd
                        if rec["pay_date_range"][1] is None or pd > rec["pay_date_range"][1]:
                            rec["pay_date_range"][1] = pd

        print()
        print(f"Clients scanned: {len(clients)}   with voucher data: {clients_with_data}   errors: {clients_errored}")
        print(f"Unique (client, employee) hits: {len(hits)}")
        print()

        if not hits:
            print("No potential FICA_EXEMPT_MISFLAG hits in scanned window.")
            return 0

        # ---- report ----
        print("=" * 78)
        print(" Potential FICA_EXEMPT_MISFLAG candidates")
        print(" (active voucher with wages > 0 but no SS + Medicare withheld)")
        print("=" * 78)
        print()
        print(
            f"{'CLIENT':8s}  {'EMP ID':10s}  {'# VOUCHERS':>10s}  "
            f"{'WAGES SKIPPED':>15s}  {'PERIOD':22s}  {'BATCHES':8s}"
        )
        print("-" * 78)
        sorted_hits = sorted(
            hits.items(),
            key=lambda kv: (-kv[1]["voucher_count"], -float(kv[1]["total_wages_skipped"])),
        )
        for (cid, eid), rec in sorted_hits[:100]:
            period = f"{rec['pay_date_range'][0] or '?'}..{rec['pay_date_range'][1] or '?'}"
            print(
                f"{cid:8s}  {eid:10s}  {rec['voucher_count']:>10d}  "
                f"${rec['total_wages_skipped']:>13,.2f}   {period:22s}  "
                f"{len(rec['batches_seen'])}"
            )

        if len(sorted_hits) > 100:
            print(f"\n... {len(sorted_hits) - 100} more (suppressed). Set DOGFOOD_EMPLOYER_ID to narrow.")

        print()
        print("Next step: for each hit, verify in PrismHR Employee > Tax tab whether")
        print("the FICA Exempt checkbox is intentional. Legitimate cases (clergy,")
        print("student workers, F-1/J-1 visa holders, railroad workers) add to the")
        print("allowlist. Rest are data errors — uncheck the flag and reissue the")
        print("affected vouchers.")
        print()

        return 0
    finally:
        await http.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
