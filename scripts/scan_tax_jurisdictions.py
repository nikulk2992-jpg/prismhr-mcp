"""Enumerate every tax jurisdiction Simploy actually remits to.

Pulls voucher-level employeeTax[] + companyTax[] across every client,
aggregates unique empTaxDeductCode values, and maps to
federal/state/local/county/SD buckets. Output feeds the state-tax-
filing-orchestrator scope doc.

PrismHR tax code convention (verified empirically from voucher probes):
  00-10  FIT
  00-11  FICA Medicare
  00-12  FICA OASDI
  00-15  Medicare employer
  00-16  OASDI employer
  00-17  FUTA
  XX-20  state income tax  (XX = state 2-digit)
  XX-24  state unemployment  (XX = state)
  XXXXXXXXX-31  local (city) income tax  (code = FIPS/geocode)
  XXXXXXXXX-32  county tax
  XXXXXXXXX-33  school district
  XXXXXXXXX-34  transit / occupational

Usage:
  DOGFOOD_LOOKBACK_DAYS=365 .venv/Scripts/python scripts/scan_tax_jurisdictions.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from prismhr_mcp.secure_env import load_into_environ  # noqa: E402

OUT_PATH = REPO / ".planning" / "tax-jurisdictions.json"


import re

# PrismHR uses its own state-code scheme (NOT FIPS). Real mapping is
# derived from empTaxDeductCodeDesc which contains the state abbrev.
# Keep the FIPS map around only as a last-resort fallback.
_FIPS_FALLBACK = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "72": "PR",
}

_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY", "PR",
}


def _state_from_desc(desc: str) -> str | None:
    """Pull a US state abbreviation from the description string.
    e.g. 'MO INCOME TAX' -> 'MO'
         'SAINT LOUIS,MO CIWT' -> 'MO'
         'FAIRLAWN,SUMMIT COUNTY,OH CIWT' -> 'OH'
    """
    if not desc:
        return None
    # Explicit ", XX " or "XX INCOME" patterns
    tokens = re.findall(r"\b([A-Z]{2})\b", desc.upper())
    for tok in tokens:
        if tok in _US_STATES:
            return tok
    return None


def _classify(code: str, desc: str) -> dict:
    """Map empTaxDeductCode -> {level, state, jurisdiction, kind}."""
    c = (code or "").strip()
    d = (desc or "").strip()
    if c.startswith("00-"):
        suffix = c[3:]
        tag = {
            "10": ("federal", "FIT"),
            "11": ("federal", "FICA_MEDICARE_EE"),
            "12": ("federal", "FICA_OASDI_EE"),
            "15": ("federal", "FICA_MEDICARE_ER"),
            "16": ("federal", "FICA_OASDI_ER"),
            "17": ("federal", "FUTA"),
        }.get(suffix, ("federal", "OTHER_FEDERAL"))
        return {"level": tag[0], "kind": tag[1]}
    # 2-digit state code prefix
    if "-" in c:
        head, tail = c.split("-", 1)
        if len(head) == 2 and head.isdigit():
            # Prefer state from desc; fall back to FIPS guess
            state = _state_from_desc(d) or _FIPS_FALLBACK.get(head, f"?{head}")
            kind_map = {
                "20": "STATE_INCOME_TAX",
                "24": "STATE_UI",
                "21": "STATE_DISABILITY",
                "22": "STATE_PFML",
                "25": "STATE_WORKFORCE",
            }
            return {"level": "state", "state": state, "kind": kind_map.get(tail, f"STATE_OTHER_{tail}")}
        # Long head = geocode; treat as local
        if len(head) >= 8 and head.isdigit():
            state = _state_from_desc(d) or _FIPS_FALLBACK.get(head[:2], f"?{head[:2]}")
            kind_map = {
                "31": "LOCAL_CITY_INCOME",
                "32": "COUNTY",
                "33": "SCHOOL_DISTRICT",
                "34": "TRANSIT_OCCUP",
            }
            kind = kind_map.get(tail, f"LOCAL_OTHER_{tail}")
            return {
                "level": "local",
                "state": state,
                "geocode": head,
                "kind": kind,
                "jurisdiction": d,
            }
    return {"level": "unknown", "raw_code": c, "desc": d}


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    lookback = int(os.environ.get("DOGFOOD_LOOKBACK_DAYS", "365"))
    today = date.today()
    start = today - timedelta(days=lookback)

    base = "https://uatapi.prismhr.com/demo/prismhr-api/services/rest"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{base}/login/v1/createPeoSession", data={
            "peoId": os.environ["PRISMHR_MCP_PEO_ID"],
            "username": os.environ["PRISMHR_MCP_USERNAME"],
            "password": os.environ["PRISMHR_MCP_PASSWORD"],
        })
        sid = r.json()["sessionId"]
        h = {"sessionId": sid, "Accept": "application/json"}

        print(f"Lookback: {start.isoformat()} .. {today.isoformat()}")

        r = await c.get(f"{base}/clientMaster/v1/getClientList", headers=h)
        clist = (r.json() or {}).get("clientListResult", {}).get("clientList", [])
        print(f"Clients: {len(clist)}")

        codes_seen: Counter[tuple[str, str]] = Counter()
        amount_by_jurisdiction: defaultdict[str, float] = defaultdict(float)
        clients_per_jurisdiction: defaultdict[str, set[str]] = defaultdict(set)

        for i, cl in enumerate(clist, 1):
            cid = str(cl.get("clientId") or "")
            if not cid:
                continue
            if i % 20 == 0 or i == 1:
                print(f"  [{i}/{len(clist)}] scanning {cid}...")
            try:
                br = await c.get(
                    f"{base}/payroll/v1/getBatchListByDate",
                    headers=h,
                    params={"clientId": cid, "startDate": start.isoformat(),
                            "endDate": today.isoformat(), "dateType": "POST"},
                )
                body = br.json()
                batches = body.get("batchList") if isinstance(body, dict) else body
                if not isinstance(batches, list):
                    continue
            except Exception:  # noqa: BLE001
                continue

            # Sample 3 batches per client for speed
            for b in batches[:3]:
                bid = str(b.get("batchId") or "")
                if not bid:
                    continue
                try:
                    vr = await c.get(
                        f"{base}/payroll/v1/getPayrollVoucherForBatch",
                        headers=h,
                        params={"clientId": cid, "batchId": bid},
                    )
                    vbody = vr.json()
                    vouchers = vbody.get("payrollVoucher") if isinstance(vbody, dict) else vbody
                    if not isinstance(vouchers, list):
                        continue
                except Exception:  # noqa: BLE001
                    continue
                for v in vouchers:
                    for t in v.get("employeeTax") or []:
                        code = str(t.get("empTaxDeductCode") or "")
                        desc = str(t.get("empTaxDeductCodeDesc") or "")
                        amt = float(t.get("empTaxAmount") or 0) or 0.0
                        if not code:
                            continue
                        codes_seen[(code, desc)] += 1
                        bucket = _classify(code, desc)
                        key = json.dumps(bucket, sort_keys=True)
                        amount_by_jurisdiction[key] += amt
                        clients_per_jurisdiction[key].add(cid)

        print()
        print(f"Unique tax codes: {len(codes_seen)}")
        # Build JSON summary
        jurisdictions = []
        for key, total in amount_by_jurisdiction.items():
            bucket = json.loads(key)
            bucket["total_amount_ytd"] = round(total, 2)
            bucket["clients_affected"] = len(clients_per_jurisdiction[key])
            jurisdictions.append(bucket)
        jurisdictions.sort(key=lambda j: -j["total_amount_ytd"])

        summary = {
            "scanned": str(today),
            "lookback_days": lookback,
            "total_clients": len(clist),
            "unique_tax_codes": len(codes_seen),
            "jurisdictions": jurisdictions,
            "raw_codes": [
                {"code": c, "desc": d, "vouchers_seen": n}
                for (c, d), n in codes_seen.most_common(200)
            ],
        }
        OUT_PATH.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        print(f"Wrote {OUT_PATH.relative_to(REPO)}")

        # Print top buckets by level
        by_level: defaultdict[str, list] = defaultdict(list)
        for j in jurisdictions:
            by_level[j.get("level", "unknown")].append(j)

        for lvl in ("federal", "state", "local", "unknown"):
            lst = by_level[lvl]
            if not lst:
                continue
            print()
            print(f"=== {lvl.upper()} ({len(lst)} buckets) ===")
            for j in lst[:25]:
                loc = j.get("state", "")
                jurisdiction = j.get("jurisdiction") or j.get("geocode") or ""
                kind = j.get("kind", "")
                print(f"  {loc:3s}  {kind:22s}  {jurisdiction[:40]:40s}  "
                      f"${j['total_amount_ytd']:>12,.2f}  clients={j['clients_affected']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
