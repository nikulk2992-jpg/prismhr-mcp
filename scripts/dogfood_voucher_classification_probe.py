"""Probe the PrismHR endpoints needed by voucher_classification_audit.

Not a full workflow run — a field-coverage diagnostic. Hits the UAT
tenant, pulls sample data from each endpoint the workflow would use,
and reports which fields are populated vs empty so we know whether the
UAT tenant has enough data to light up the workflow.

Usage:
    set DOGFOOD_CLIENT_ID=<client-id>
    .venv/Scripts/python scripts/dogfood_voucher_classification_probe.py
"""

from __future__ import annotations

import asyncio
import json
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


def _pct(n: int, d: int) -> str:
    return f"{(100 * n / d):.0f}%" if d else "n/a"


def _fmt(v) -> str:
    if v in (None, ""):
        return "(empty)"
    s = str(v)
    return s if len(s) < 40 else s[:37] + "..."


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    client_id = os.environ.get("DOGFOOD_CLIENT_ID", "").strip()
    if not client_id:
        print("ERROR: set DOGFOOD_CLIENT_ID")
        return 2

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
    c = PrismHRClient(s, session, http)

    print()
    print("=" * 72)
    print(" Voucher Classification Audit — UAT field coverage probe")
    print(f" client: {client_id}")
    print("=" * 72)
    print()

    try:
        # ---- 1. list a batch, get its vouchers ----
        print("[1/5] Finding a recent batch with vouchers...")
        batch_list = await c.get(
            "/payroll/v1/getBatchListByDate",
            params={
                "clientId": client_id,
                "startDate": "2024-01-01",
                "endDate": "2026-04-20",
                "dateType": "POST",
            },
        )
        batches = batch_list.get("batchList") or batch_list.get("availableBatches") or []
        if not batches:
            print("  NO BATCHES. Client has no voucher history in UAT.")
            return 1
        print(f"  Found {len(batches)} batches.")
        target_batch = None
        target_vouchers: list[dict] = []
        for b in batches[:20]:
            bid = str(b.get("batchId") or b.get("id") or "")
            if not bid:
                continue
            try:
                vbody = await c.get(
                    "/payroll/v1/getPayrollVoucherForBatch",
                    params={"clientId": client_id, "batchId": bid},
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  batch {bid}: {type(exc).__name__}")
                continue
            vouchers = vbody.get("payrollVoucher") or []
            if vouchers:
                target_batch = bid
                target_vouchers = vouchers
                break
        if not target_vouchers:
            print("  NO VOUCHERS across checked batches. UAT has empty voucher shells.")
            return 1
        print(f"  Using batch {target_batch} with {len(target_vouchers)} vouchers.")
        print()

        # ---- 2. inspect voucher shape ----
        print("[2/5] Voucher-level fields present...")
        v = target_vouchers[0]
        print(f"  voucherId: {_fmt(v.get('voucherId'))}")
        print(f"  employeeId: {_fmt(v.get('employeeId'))}")
        print(f"  type: {_fmt(v.get('type'))}")
        print(f"  payDate: {_fmt(v.get('payDate'))}")
        print(f"  totalEarnings: {_fmt(v.get('totalEarnings'))}")
        print(f"  wcState: {_fmt(v.get('wcState'))}")
        etaxes = v.get("employeeTax") or []
        earnings = v.get("earning") or []
        print(f"  employeeTax rows: {len(etaxes)}  |  earning rows: {len(earnings)}")
        if etaxes:
            codes = [str(r.get("empTaxDeductCode") or "") for r in etaxes]
            print(f"  tax codes seen: {codes[:6]}...")
        if earnings:
            pc = [str(r.get("payCode") or "") for r in earnings[:5]]
            print(f"  pay codes seen: {pc}")
        print()

        eid = str(v.get("employeeId") or "")

        # ---- 3. employee record ----
        print(f"[3/5] Employee {eid} — tax profile via getEmployee...")
        try:
            ebody = await c.get(
                "/employee/v1/getEmployee",
                params={"clientId": client_id, "employeeId": eid},
            )
            emp = (ebody.get("employee") or [{}])[0] if ebody.get("employee") else ebody
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {type(exc).__name__}: {str(exc)[:80]}")
            emp = {}
        needed = [
            "employmentType", "employeeType", "type",
            "ficaExempt", "medicareExempt", "futaExempt", "sutaExempt",
            "workState", "stateCode", "primaryState",
            "unionId", "unionCode",
        ]
        for k in needed:
            print(f"  {k:20s} = {_fmt(emp.get(k))}")
        print()

        # ---- 4. YTD wages via bulk ----
        print(f"[4/5] YTD wages via getBulkYearToDateValues...")
        try:
            ybody = await c.get(
                "/payroll/v1/getBulkYearToDateValues",
                params={"clientId": client_id, "asOfDate": "2026-04-20"},
            )
            ydata = ybody.get("data") or []
            matching = next((r for r in ydata if str(r.get("employeeId") or "") == eid), None)
            if matching:
                ytd = matching.get("YTD", {})
                tw = ytd.get("taxWithholding", {})
                print(f"  totalEarned:      {_fmt(ytd.get('totalEarned'))}")
                print(f"  SS withheld:      {_fmt(tw.get('socialSecurity'))}")
                print(f"  Medicare withheld:{_fmt(tw.get('medicare'))}")
                print(f"  FIT withheld:     {_fmt(tw.get('federalIncomeTax'))}")
                payCodes = ytd.get("payCodes") or []
                print(f"  payCodes count:   {len(payCodes)}")
            else:
                print(f"  No YTD row for employee {eid}.")
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {type(exc).__name__}: {str(exc)[:80]}")
        print()

        # ---- 5. field coverage summary ----
        print("[5/5] Field coverage verdict...")
        coverage = {
            "voucher.employeeTax": bool(etaxes),
            "voucher.earning": bool(earnings),
            "voucher.type": bool(v.get("type")),
            "employee.employmentType|type": any(emp.get(k) for k in ("employmentType", "employeeType", "type")),
            "employee.ficaExempt flag": emp.get("ficaExempt") is not None,
            "employee.workState": any(emp.get(k) for k in ("workState", "stateCode", "primaryState")),
            "employee.unionId": any(emp.get(k) for k in ("unionId", "unionCode")),
        }
        for name, ok in coverage.items():
            mark = "OK  " if ok else "MISS"
            print(f"  [{mark}] {name}")
        print()
        if not any(
            coverage[k] for k in (
                "employee.employmentType|type",
                "employee.ficaExempt flag",
                "employee.workState",
            )
        ):
            print("DIAGNOSIS: UAT getEmployee returns names-only stubs. Classification")
            print("fields (employment type, FICA/Medicare exempt, work state, union")
            print("id) are empty. That is why the voucher_classification_audit")
            print("reader cannot populate emp.type / fica_exempt / work_state / unionId.")
            print()
            print("Likely next step: probe additional endpoints that actually carry")
            print("these flags — candidates:")
            print("  /employee/v1/getEmployersInfo")
            print("  /payroll/v1/getEmployeeOverrideRates")
            print("  /clientMaster/v1/getEmployeesInPayGroup (has status etc.)")
            print("Or: request new UAT permission for employee compensation / tax-setup")
            print("endpoints from PrismHR support.")
        else:
            print("DIAGNOSIS: classification fields populated. Wire a live reader now.")
        print()
    finally:
        await http.aclose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
