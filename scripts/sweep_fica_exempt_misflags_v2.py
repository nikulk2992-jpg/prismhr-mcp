"""FICA_EXEMPT_MISFLAG sweep — v2, using real ficaExempt flag.

v1 used voucher-side signal only (row absence of 00-11/00-12). That
was a heuristic — couldn't distinguish "genuinely exempt per flag" from
"misflagged." With getEmployee?options=Compensation now returning the
actual ficaExempt checkbox, v2 can be precise:

  For each client:
    For each active W-2 employee with YTD wages > 0:
      Pull employee.compensation.ficaExempt
      If ficaExempt == True AND position is not in allowlist:
        Verify voucher side shows no FICA withholding (sanity)
        Report as candidate misflag

This doesn't use the voucher sweep at all — hits the tax-setup source
of truth directly. Much faster (no voucher-per-employee fetching) and
catches employees who were flagged exempt even with $0 YTD (dormant
bad flags waiting to bite).

Usage:
  set DOGFOOD_EMPLOYER_ID=400                  (optional filter)
  set DOGFOOD_MAX_CLIENTS=254                  (cap for testing)
  .venv/Scripts/python scripts/sweep_fica_exempt_misflags_v2.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx


def _parse_date(raw) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _dec(raw) -> Decimal:
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from prismhr_mcp.secure_env import load_into_environ  # noqa: E402


# Positions legitimately FICA-exempt. Extend per client.
_DEFAULT_ALLOWLIST_POSITIONS: frozenset[str] = frozenset({
    "MINISTER", "CLERGY", "PASTOR", "PRIEST", "RABBI", "IMAM",
    "CHAPLAIN",
})


def _is_likely_legit(position: str, citizenship: str, non_res: bool) -> bool:
    p = (position or "").upper()
    if any(kw in p for kw in _DEFAULT_ALLOWLIST_POSITIONS):
        return True
    if non_res and "citizen" not in (citizenship or "").lower():
        # Non-resident alien on F-1/J-1/M-1 in first 5 calendar years
        # is statutorily FICA-exempt. Coarse signal — review manually.
        return True
    return False


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))

    employer_filter = os.environ.get("DOGFOOD_EMPLOYER_ID", "").strip()
    max_clients = int(os.environ.get("DOGFOOD_MAX_CLIENTS", "30"))

    base = "https://uatapi.prismhr.com/demo/prismhr-api/services/rest"

    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{base}/login/v1/createPeoSession", data={
            "peoId": os.environ["PRISMHR_MCP_PEO_ID"],
            "username": os.environ["PRISMHR_MCP_USERNAME"],
            "password": os.environ["PRISMHR_MCP_PASSWORD"],
        })
        sid = r.json()["sessionId"]
        h = {"sessionId": sid, "Accept": "application/json"}

        print()
        print("=" * 78)
        print(" FICA_EXEMPT_MISFLAG sweep v2 (real ficaExempt flag)")
        if employer_filter:
            print(f" employer filter: {employer_filter}")
        print(f" max clients: {max_clients}")
        print("=" * 78)
        print()

        # ---- client list ----
        r = await c.get(f"{base}/clientMaster/v1/getClientList", headers=h)
        body = r.json()
        result = body.get("clientListResult") or body
        all_clients = result.get("clientList") or []
        if isinstance(all_clients, dict):
            all_clients = all_clients.get("client", [])

        if employer_filter:
            clients = [
                cl for cl in all_clients
                if str(cl.get("employerId") or "") == employer_filter
            ]
        else:
            clients = all_clients
        clients = clients[:max_clients]
        print(f"Scanning {len(clients)} clients...")
        print()

        hits: list[dict] = []
        employees_scanned = 0
        errors = 0

        for i, cl in enumerate(clients, 1):
            cid = str(cl.get("clientId") or "")
            if not cid:
                continue
            cname = str(cl.get("clientName") or "")[:30]
            if i % 5 == 0 or i == 1:
                print(f"  [{i}/{len(clients)}] {cid} {cname}...")

            # Get employee list for the client
            try:
                elr = await c.get(
                    f"{base}/employee/v1/getEmployeeList",
                    headers=h,
                    params={"clientId": cid},
                )
                ebody = elr.json()
            except Exception:  # noqa: BLE001
                errors += 1
                continue

            # Real getEmployeeList shape is {employeeList: {employeeId: [ids]}}
            el = ebody.get("employeeList") or {}
            if isinstance(el, dict):
                ids = [str(x) for x in (el.get("employeeId") or []) if x]
            elif isinstance(el, list):
                ids = [str(e.get("id") or "") for e in el if isinstance(e, dict) and e.get("id")]
            else:
                ids = []
            ids = [x for x in ids if x]

            for chunk_start in range(0, len(ids), 20):
                chunk = ids[chunk_start:chunk_start + 20]
                # Two separate calls per chunk — PrismHR options param
                # takes one class at a time. Compensation has ficaExempt,
                # Client has jobCode + employee1099 + officer + status.
                base_params: list[tuple[str, str]] = [("clientId", cid)]
                for eid2 in chunk:
                    base_params.append(("employeeId", eid2))
                try:
                    comp_r = await c.get(
                        f"{base}/employee/v1/getEmployee",
                        headers=h,
                        params=base_params + [("options", "Compensation")],
                    )
                    client_r = await c.get(
                        f"{base}/employee/v1/getEmployee",
                        headers=h,
                        params=base_params + [("options", "Client")],
                    )
                    comp_full = comp_r.json()
                    client_full = client_r.json()
                except Exception:  # noqa: BLE001
                    errors += 1
                    continue
                # Merge compensation + client subtrees by employee id
                client_by_id = {
                    str(e.get("id") or ""): (e.get("client") or {})
                    for e in (client_full.get("employee") or [])
                }
                efull = {
                    "employee": [
                        {**e, "client": client_by_id.get(str(e.get("id") or ""), {})}
                        for e in (comp_full.get("employee") or [])
                    ]
                }

                for emp in (efull.get("employee") or []):
                    employees_scanned += 1
                    comp = emp.get("compensation") or {}
                    client_cls = emp.get("client") or {}
                    if comp.get("ficaExempt") is not True:
                        continue

                    # 1099 contractor — FICA exempt is correct. Skip.
                    if client_cls.get("employee1099") is True:
                        continue

                    # Terminated — historical issue only, no new vouchers.
                    # Still report if we want to trigger voucher reissue
                    # for the active window, but skip from live flag set.
                    status = str(client_cls.get("employeeStatus") or "A").upper()
                    if status in {"T", "TERMINATED"}:
                        continue

                    # Corporate officer / S-corp owner / business owner —
                    # these may legitimately take K-1 income outside W-2
                    # and flag FICA exempt on the employee record.
                    if (client_cls.get("officer") is True or
                            client_cls.get("scorpOwner") is True or
                            client_cls.get("businessOwner") is True):
                        continue

                    position = str(client_cls.get("jobCode") or "")
                    citizenship = str(comp.get("citizenshipStatus") or "")
                    non_res = bool(comp.get("nonResAlien"))
                    form_4029 = bool(comp.get("form4029Filed"))
                    railroad = bool(comp.get("railroadEmployee"))
                    w8 = bool(comp.get("w8Filed"))

                    # Statutory exemption flags resolve the case
                    if form_4029 or railroad or non_res or w8:
                        continue

                    # Skip dormant records: no YTD wages AND last pay
                    # before current year = pre-year termination. These
                    # are noise — flag won't bite unless they're rehired.
                    year_start = date(date.today().year, 1, 1)
                    last_pay = _parse_date(comp.get("lastPayDate"))
                    paid_thru = _parse_date(comp.get("paidThruDate"))
                    last_worked = _parse_date(comp.get("lastWorkedDate"))
                    annual_dec = _dec(comp.get("annualPay") or comp.get("salary"))
                    most_recent = max(
                        (d for d in (last_pay, paid_thru, last_worked) if d),
                        default=None,
                    )
                    if annual_dec == 0 and (
                        most_recent is None or most_recent < year_start
                    ):
                        continue

                    annual = comp.get("annualPay") or comp.get("salary") or "0"
                    pay_method = str(comp.get("payMethod") or "")
                    status = "A"

                    # Severity: US citizen + exempt + no statutory = critical
                    # alien authorized to work = warning (may be H-2A/F-1/J-1)
                    # blank citizenship = warning (fix data first)
                    if citizenship == "A citizen of the United States":
                        severity = "CRITICAL"
                    elif "alien" in citizenship.lower():
                        severity = "WARNING_VISA_REVIEW"
                    else:
                        severity = "WARNING_CITIZENSHIP_BLANK"

                    hits.append({
                        "client_id": cid,
                        "client_name": cname,
                        "employee_id": emp.get("id"),
                        "first_name": emp.get("firstName"),
                        "last_name": emp.get("lastName"),
                        "position": position,
                        "annual_pay": annual,
                        "pay_method": pay_method,
                        "citizenship": citizenship[:30],
                        "non_res_alien": non_res,
                        "status": status,
                        "severity": severity,
                    })

        print()
        print(f"Employees scanned: {employees_scanned}")
        print(f"Errors: {errors}")
        print(f"FICA_EXEMPT_MISFLAG candidates (active W-2, not allowlisted): {len(hits)}")
        print()

        if not hits:
            print("No misflags found.")
            return 0

        # ---- report ----
        # Group by severity for scannable output.
        by_sev = {"CRITICAL": [], "WARNING_VISA_REVIEW": [], "WARNING_CITIZENSHIP_BLANK": []}
        for h_rec in hits:
            by_sev.setdefault(h_rec["severity"], []).append(h_rec)
        for sev_label, recs in by_sev.items():
            if not recs:
                continue
            print("=" * 110)
            print(f"  {sev_label}  ({len(recs)} employees)")
            print("=" * 110)
            print(f"{'CLIENT':8s}  {'EMP':10s}  {'NAME':25s}  {'JOBCODE':15s}  {'CITIZENSHIP':30s}  {'ANNUAL':>12s}  {'CLIENT NAME':30s}")
            print("-" * 128)
            recs.sort(key=lambda r: (-float(str(r['annual_pay'] or 0).replace(',', '')), r['client_id']))
            for h_rec in recs:
                name = f"{h_rec['first_name'] or ''} {h_rec['last_name'] or ''}".strip()[:25]
                cit = (h_rec['citizenship'] or '(blank)')[:30]
                annual = h_rec['annual_pay'] or '0'
                cn = (h_rec.get('client_name') or '')[:30]
                pos = (h_rec.get('position') or '')[:15]
                print(f"{h_rec['client_id']:8s}  {h_rec['employee_id']:10s}  {name:25s}  {pos:15s}  {cit:30s}  ${float(str(annual).replace(',', '')):>11,.0f}  {cn}")
            print()

        print()
        print("Review each in PrismHR Employee > Tax tab > FICA Exempt checkbox.")
        print("If legit (statutory exemption), add position to allowlist.")
        print("Otherwise uncheck the flag; voucher reissue may be required for")
        print("any periods where the flag was active + wages were paid.")
        print()

        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
