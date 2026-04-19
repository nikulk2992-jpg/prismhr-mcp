"""Live UAT dogfood driver.

Exercises every prismhr-mcp tool against PrismHR UAT without requiring
Claude Code. Surfaces schema surprises, auth edge cases, and session
behavior before we ship Phase 3. NOT meant for prod.

Usage:
    # Creds come from env vars set by the caller (see /scripts/run.sh).
    uv run python scripts/uat_dogfood.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.permissions import ConsentStore, PermissionManager, Scope
from prismhr_mcp.runtime import Runtime
from prismhr_mcp.server import build


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
DIM = "\033[2m"
RESET = "\033[0m"


def step(n: int, label: str) -> None:
    print(f"\n{BLUE}=== {n:02d}. {label} ==={RESET}", flush=True)


def ok(msg: str) -> None:
    print(f"  {GREEN}[OK]{RESET} {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"  {YELLOW}[WARN]{RESET} {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}", flush=True)


def dim(msg: str) -> None:
    print(f"  {DIM}{msg}{RESET}", flush=True)


def trunc(value: Any, n: int = 400) -> str:
    s = json.dumps(value, default=str) if not isinstance(value, str) else value
    return s if len(s) <= n else s[:n] + f"... (+{len(s)-n} chars)"


def extract_structured(result: Any) -> dict:
    if isinstance(result, tuple) and len(result) == 2 and result[1] is not None:
        return result[1]
    blocks = result[0] if isinstance(result, tuple) else result
    if blocks:
        text = getattr(blocks[0], "text", None)
        if text:
            return json.loads(text)
    return {}


async def call(server: Any, name: str, args: dict[str, Any]) -> tuple[bool, dict]:
    start = time.monotonic()
    try:
        raw = await server.call_tool(name, args)
    except Exception as exc:  # noqa: BLE001
        elapsed = time.monotonic() - start
        fail(f"tool {name!r} raised after {elapsed*1000:.0f}ms: {exc!s}")
        if os.environ.get("DOGFOOD_TRACE"):
            traceback.print_exc()
        return False, {}
    elapsed = time.monotonic() - start
    data = extract_structured(raw)
    ok(f"{name} in {elapsed*1000:.0f}ms")
    return True, data


async def main() -> int:
    # Prefer an encrypted local env file if present. Falls through to any
    # env vars already set by the caller.
    enc_path = Path(".env.local.enc")
    if enc_path.exists():
        from prismhr_mcp.secure_env import load_into_environ

        loaded = load_into_environ(enc_path)
        dim(f"loaded {len(loaded)} keys from {enc_path}: {loaded}")

    try:
        username = os.environ["PRISMHR_MCP_USERNAME"]
        password = os.environ["PRISMHR_MCP_PASSWORD"]
    except KeyError as missing:
        fail(
            f"missing env var {missing.args[0]}. Either set PRISMHR_MCP_USERNAME + "
            "PRISMHR_MCP_PASSWORD in your shell, or run "
            "`scripts/encrypt_env.py` to create .env.local.enc."
        )
        return 2
    peo_id = os.environ["PRISMHR_MCP_PEO_ID"]

    settings = Settings()  # default uat + scrypt cache dir
    http = httpx.AsyncClient(timeout=60.0)
    session = SessionManager(settings, DirectCredentialSource(peo_id, username, password), http)
    prismhr = PrismHRClient(settings, session, http)
    store = ConsentStore(
        cache_dir=settings.cache_dir,
        peo_id=settings.prismhr_peo_id,
        environment=settings.environment,
    )
    perms = PermissionManager(store)
    # Fresh slate for each dogfood.
    perms.replace([])

    runtime = Runtime(
        settings=settings,
        http=http,
        session=session,
        prismhr=prismhr,
        permissions=perms,
    )
    built = build(runtime=runtime)
    server = built.server

    # Track any data needed across tools (client_id, employee_id, batch_id).
    chosen_client: str | None = None
    chosen_employee: str | None = None
    chosen_batch: str | None = None

    try:
        step(0, "PrismHR getAPIPermissions — what can this account actually call?")
        authorized_services: set[str] = set()
        try:
            raw = await prismhr.get("/login/v1/getAPIPermissions")
        except Exception as exc:  # noqa: BLE001
            fail(f"getAPIPermissions failed: {exc}")
            raw = None
        if isinstance(raw, dict):
            # Shape: {"currentPermissions": {"allowedMethods": [{"service": "..."}]}}
            cp = raw.get("currentPermissions") or {}
            allowed = cp.get("allowedMethods") if isinstance(cp, dict) else None
            if isinstance(allowed, list):
                for item in allowed:
                    if isinstance(item, dict) and item.get("service"):
                        authorized_services.add(str(item["service"]))
            if authorized_services:
                groups: dict[str, int] = {}
                for s in authorized_services:
                    prefix = s.split(".", 1)[0]
                    groups[prefix] = groups.get(prefix, 0) + 1
                ok(f"account authorized for {len(authorized_services)} methods")
                dim(f"by service: {dict(sorted(groups.items(), key=lambda kv: -kv[1]))}")
            else:
                warn("no allowedMethods found — account has zero upstream privileges")
        elif raw is None:
            warn("could not fetch permissions; continuing anyway")

        def _missing(*candidates: str) -> bool:
            """True if NONE of the given PrismHR service names are authorized."""
            if not authorized_services:
                return False  # can't tell; let the call proceed
            return not any(c in authorized_services for c in candidates)

        step(1, "meta_ping — liveness")
        ok_flag, data = await call(server, "meta_ping", {})
        if ok_flag:
            dim(f"server={data.get('server')} v={data.get('version')} utc={data.get('utc')}")

        step(2, "meta_about — public info + commercial")
        ok_flag, data = await call(server, "meta_about", {})
        if ok_flag:
            dim(f"license={data.get('license')} live_groups={data.get('tool_groups_live')}")
            dim(f"commercial tiers={[t['name'] for t in data.get('commercial_support', [])]}")

        step(3, "meta_request_permissions (expect 0 granted)")
        ok_flag, data = await call(server, "meta_request_permissions", {})
        if ok_flag:
            dim(f"total_scopes={data.get('total_scopes')} granted={data.get('granted_count')}")
            dim(f"recommended={data.get('recommended_defaults')}")

        step(4, "meta_grant_permissions — accept recommended defaults (reads only)")
        ok_flag, data = await call(
            server,
            "meta_grant_permissions",
            {"accept_recommended_defaults": True},
        )
        if ok_flag:
            dim(f"granted now: {data.get('granted')}")

        step(5, "client_list — expect ~the client roster in UAT")
        if _missing("ClientMasterService.getClientList"):
            warn(
                "SKIP: account lacks ClientMasterService.getClientList. "
                "Ask PrismHR admin to grant ClientMasterService + EmployeeService."
            )
            ok_flag, data = False, {}
        else:
            ok_flag, data = await call(server, "client_list", {})
            if not ok_flag:
                dim("client_list failed — payroll steps still run with fallback client id")
        clients = data.get("clients") or []
        if clients:
            dim(f"count={data.get('count')}")
            sample = clients[:3]
            dim(f"sample: {[(c.get('client_id'), c.get('name'), c.get('status')) for c in sample]}")
            chosen_client = clients[0].get("client_id")
        elif ok_flag:
            warn("no clients returned — UAT may be empty or endpoint shape changed")

        if chosen_client and not _missing("EmployeeService.getEmployeeList"):
            step(6, f"client_employees — active at {chosen_client}")
            ok_flag, data = await call(
                server,
                "client_employees",
                {"client_id": chosen_client, "status": "active"},
            )
            employees = data.get("employees") or []
            dim(f"count={data.get('count')}")
            if employees:
                dim(f"sample: {[(e.get('employee_id'), e.get('first_name'), e.get('last_name')) for e in employees[:3]]}")
                chosen_employee = employees[0].get("employee_id")

        if chosen_client and chosen_employee and not _missing("EmployeeService.getEmployee"):
            step(7, f"client_employee — detail for {chosen_employee}")
            ok_flag, data = await call(
                server,
                "client_employee",
                {"client_id": chosen_client, "employee_ids": [chosen_employee]},
            )
            if ok_flag:
                emps = data.get("employees") or []
                dim(f"count={len(emps)} missing_ids={data.get('missing_ids')}")
                if emps:
                    keys = sorted(emps[0].keys())
                    dim(f"fields present: {keys}")

        step(8, "client_employee_search — query=claude")
        if _missing("EmployeeService.getEmployeeList", "ClientMasterService.getClientList"):
            warn("SKIP: needs EmployeeService + ClientMasterService privileges")
            ok_flag, data = False, {}
        else:
            ok_flag, data = await call(
                server,
                "client_employee_search",
                {"query": "claude"},
            )
        if ok_flag:
            dim(f"searched={data.get('searched_clients')} matches={data.get('count')}")

        # Payroll tools only need a client_id; if we lack ClientMasterService,
        # seed from a known UAT client instead. Pick the first ACME-like guess.
        if not chosen_client:
            fallback_client = os.environ.get("PRISMHR_MCP_FALLBACK_CLIENT")
            if fallback_client:
                chosen_client = fallback_client
                dim(f"using fallback client_id from env: {chosen_client}")

        if chosen_client and not _missing("PayrollService.getBatchListByDate"):
            step(9, f"payroll_batch_status — Q1 2026 at {chosen_client}")
            ok_flag, data = await call(
                server,
                "payroll_batch_status",
                {
                    "client_id": chosen_client,
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
                },
            )
            batches = data.get("batches") or []
            dim(f"count={data.get('count')}")
            if batches:
                chosen_batch = batches[0].get("batch_id")
                dim(f"sample: {[(b.get('batch_id'), b.get('pay_date'), b.get('status')) for b in batches[:3]]}")

        if chosen_client and chosen_employee:
            step(10, f"payroll_pay_history — Q1 2026 for {chosen_employee}")
            ok_flag, data = await call(
                server,
                "payroll_pay_history",
                {
                    "client_id": chosen_client,
                    "employee_id": chosen_employee,
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
                },
            )
            dim(f"vouchers={data.get('count')} ytd_present={data.get('ytd') is not None}")

            step(11, "payroll_pay_group_check")
            ok_flag, data = await call(
                server,
                "payroll_pay_group_check",
                {"client_id": chosen_client, "employee_id": chosen_employee},
            )
            dim(f"assigned={data.get('assigned')} group={data.get('pay_group_id')} warning={data.get('warning')}")

            step(12, "payroll_deduction_conflicts")
            ok_flag, data = await call(
                server,
                "payroll_deduction_conflicts",
                {"client_id": chosen_client, "employee_id": chosen_employee},
            )
            dim(f"scanned={data.get('scanned_count')} conflicts={len(data.get('conflicts') or [])}")

            step(13, "payroll_overtime_anomalies — Q1 2026")
            ok_flag, data = await call(
                server,
                "payroll_overtime_anomalies",
                {
                    "client_id": chosen_client,
                    "employee_id": chosen_employee,
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
                },
            )
            dim(f"scanned={data.get('scanned_vouchers')} anomalies={len(data.get('anomalies') or [])}")

        if chosen_client:
            step(14, "payroll_superbatch_status — Q1 2026")
            ok_flag, data = await call(
                server,
                "payroll_superbatch_status",
                {
                    "client_id": chosen_client,
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
                },
            )
            if ok_flag:
                dim(
                    f"batches={data.get('batch_count')} "
                    f"gross={data.get('total_gross')} "
                    f"open={data.get('open_batch_count')} "
                    f"posted={data.get('posted_batch_count')}"
                )

        if chosen_client and chosen_batch:
            step(15, f"payroll_register_reconcile — batch {chosen_batch}")
            ok_flag, data = await call(
                server,
                "payroll_register_reconcile",
                {"client_id": chosen_client, "batch_id": chosen_batch},
            )
            if ok_flag:
                dim(
                    f"reconciled={data.get('reconciled')} "
                    f"voucher={data.get('voucher_gross_total')} "
                    f"billing={data.get('billing_code_total')} "
                    f"delta={data.get('delta')}"
                )
        else:
            warn("skipped payroll_register_reconcile (no batch available)")

        step(16, "payroll_void_workflow — expect PermissionDeniedError")
        ok_flag, data = await call(
            server,
            "payroll_void_workflow",
            {"client_id": chosen_client or "ACME", "voucher_id": "TEST", "reason": "dogfood"},
        )
        if ok_flag:
            warn("void workflow ran — write scope was granted unexpectedly")
            dim(trunc(data))

        step(17, "grant payroll:write then retry void")
        perms.grant([Scope.PAYROLL_WRITE])
        ok_flag, data = await call(
            server,
            "payroll_void_workflow",
            {"client_id": chosen_client or "ACME", "voucher_id": "TEST", "reason": "dogfood"},
        )
        if ok_flag:
            dim(f"code={data.get('code')} planned_for={data.get('planned_for')}")

        step(18, "meta_list_permissions — final state")
        ok_flag, data = await call(server, "meta_list_permissions", {})
        if ok_flag:
            dim(f"granted ({data.get('granted_count')}): {data.get('granted')}")

        print(f"\n{GREEN}Dogfood complete.{RESET}")
        return 0
    finally:
        await http.aclose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
