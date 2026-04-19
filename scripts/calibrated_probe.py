"""Calibrated probe harness — no-guesswork version.

Runs against the live PrismHR API to:
  1. Build a fixture registry from methods that work with no params (seeds).
  2. Iteratively unlock more methods whose required params are now satisfiable.
  3. Harvest response JSON from every 200, record both shape and sample.
  4. Emit `.planning/verified-responses/<service>_<op>.json` per method.
  5. Emit `.planning/verification-matrix.json` summarizing coverage.

Guesswork is forbidden:
  - Methods are only called when EVERY required parameter has a fixture value.
  - Bogus fake IDs are never invented. If no fixture fits, skip.
  - Responses with non-zero errorCode are recorded as errors, not shapes.

The fixture registry learns over time:
  - Client IDs from `getBulkYearToDateValues` download payload
  - Employee IDs from the same payload
  - Batch IDs, voucher IDs, pay dates from payroll vouchers
  - Pay group codes, schedule codes from reference endpoints

Requires .env.local.enc with valid credentials.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx

from prismhr_mcp.auth.credentials import DirectCredentialSource
from prismhr_mcp.auth.prismhr_session import SessionManager
from prismhr_mcp.clients.prismhr import PrismHRClient
from prismhr_mcp.config import Settings
from prismhr_mcp.errors import PrismHRRequestError
from prismhr_mcp.secure_env import load_into_environ

ROOT = pathlib.Path(".planning")
RESP_DIR = ROOT / "verified-responses"
SUMMARY_PATH = ROOT / "verification-matrix.json"
SKIP_OPS = {"downloadPayrollReports", "reprintCheckStub", "positivePayDownload", "streamACHData"}


class FixtureRegistry:
    """Learns values (client_id, employee_id, etc.) from successful probes."""

    def __init__(self) -> None:
        # Known good fixtures keyed by canonical param name.
        # Lists are append-only; later probes may expand them.
        self._values: dict[str, list[str]] = defaultdict(list)
        # Common param-name aliases that map to the same logical fixture.
        self._aliases: dict[str, str] = {
            "clientId": "client_id",
            "employeeId": "employee_id",
            "applicantId": "applicant_id",
            "batchId": "batch_id",
            "voucherId": "voucher_id",
            "journalId": "journal_id",
            "planId": "plan_id",
            "payGroupId": "pay_group_id",
            "scheduleCode": "schedule_code",
            "billingCode": "billing_code",
            "deductionCode": "deduction_code",
            "paycode": "paycode",
            "sessionId": "session_id",  # auth-handled, not a fixture
            "webServiceUser": "web_service_user",
            "downloadId": "download_id",
            "startDate": "start_date",
            "endDate": "end_date",
            "payDateStart": "pay_date_start",
            "payDateEnd": "pay_date_end",
            "asOfDate": "as_of_date",
            "year": "year",
            "quarter": "quarter",
        }
        # Seed with date-type fixtures that are always available.
        self._values["start_date"] = ["2026-01-01"]
        self._values["end_date"] = ["2026-04-19"]
        self._values["pay_date_start"] = ["2026-01-01"]
        self._values["pay_date_end"] = ["2026-04-19"]
        self._values["as_of_date"] = ["2026-04-19"]
        self._values["year"] = ["2026"]
        self._values["quarter"] = ["1"]

    def canonical(self, name: str) -> str:
        return self._aliases.get(name, name)

    def add(self, name: str, value: str) -> None:
        if not value:
            return
        key = self.canonical(name)
        if value not in self._values[key]:
            self._values[key].append(value)

    def first(self, name: str) -> str | None:
        key = self.canonical(name)
        vals = self._values.get(key)
        return vals[0] if vals else None

    def has(self, name: str) -> bool:
        key = self.canonical(name)
        return bool(self._values.get(key))

    def snapshot(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self._values.items()}


def _flatten_keys(value: Any, prefix: str = "", out: list[str] | None = None) -> list[str]:
    """Return a flat list of dotted keys present in the response."""
    if out is None:
        out = []
    if isinstance(value, dict):
        for k, v in value.items():
            new = f"{prefix}.{k}" if prefix else k
            out.append(new)
            _flatten_keys(v, new, out)
    elif isinstance(value, list) and value:
        _flatten_keys(value[0], f"{prefix}[]", out)
    return out


def _harvest_ids_from_response(reg: FixtureRegistry, payload: Any) -> int:
    """Walk a JSON payload and drop any client/employee/batch IDs into the registry.

    Returns count of new values learned.
    """
    count_before = sum(len(v) for v in reg._values.values())  # noqa: SLF001
    harvest_keys = {
        "clientId": "client_id",
        "employeeId": "employee_id",
        "batchId": "batch_id",
        "voucherId": "voucher_id",
        "payGroupId": "pay_group_id",
        "planId": "plan_id",
        "scheduleCode": "schedule_code",
        "deductionCode": "deduction_code",
        "billingCode": "billing_code",
        "payCode": "paycode",
        "departmentCode": "department_code",
        "divisionCode": "division_code",
        "jobCode": "job_code",
        "positionCode": "position_code",
        "locationId": "location_id",
        "benefitPlanId": "benefit_plan_id",
        "benefitPlanCode": "benefit_plan_code",
        "eventCode": "event_code",
        "checkNumber": "check_number",
        "refNumber": "ref_number",
        "refId": "ref_id",
        "uploadId": "upload_id",
        "userId": "user_id",
        "taskId": "task_id",
        "templateId": "template_id",
        "journalId": "journal_id",
        "planClass": "plan_class",
        "payrollRunId": "payroll_run_id",
        "loanId": "loan_id",
        "garnishmentId": "garnishment_id",
        "courseCode": "course_code",
        "skillCode": "skill_code",
        "shiftCode": "shift_code",
        "projectCode": "project_code",
        "ratingCode": "rating_code",
        "eeoCode": "eeo_code",
        "holidayCode": "holiday_code",
        "cobraCode": "cobra_code",
        "absenceCode": "absence_code",
        "ptoClassCode": "pto_class_code",
        "ptoRegisterType": "pto_register_type",
        "naicsCode": "naics_code",
        "contactType": "contact_type",
        "clientCategoryCode": "client_category_code",
    }

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for k, val in v.items():
                if k in harvest_keys and isinstance(val, (str, int)):
                    reg.add(harvest_keys[k], str(val))
                walk(val)
        elif isinstance(v, list):
            for item in v:
                walk(item)

    walk(payload)
    after = sum(len(v) for v in reg._values.values())  # noqa: SLF001
    return after - count_before


def _satisfiable(params: list[dict[str, Any]], reg: FixtureRegistry) -> tuple[bool, dict[str, str]]:
    """True iff every required non-session param has a fixture value."""
    args: dict[str, str] = {}
    for p in params:
        name = p["name"]
        required = p.get("required", False)
        loc = p.get("location", "")
        # sessionId is handled by the client transparently.
        if name == "sessionId":
            continue
        # Skip path params (we don't substitute them in /payroll/v1/foo).
        if loc == "path":
            continue
        if required:
            val = reg.first(name)
            if val is None:
                return False, {}
            args[name] = val
        else:
            val = reg.first(name)
            if val is not None:
                args[name] = val
    return True, args


async def _follow_async_download(
    client: PrismHRClient,
    path: str,
    initial: dict[str, Any],
    http: httpx.AsyncClient,
) -> Any:
    """Poll a PrismHR async-download job until DONE; fetch the dataObject URL."""
    if not isinstance(initial, dict):
        return initial
    download_id = initial.get("downloadId")
    if not download_id:
        return initial

    async def _unwrap(envelope: dict[str, Any]) -> Any:
        url = envelope.get("dataObject")
        if not url:
            return envelope
        token = await client._session.token()  # noqa: SLF001
        resp = await http.get(url, headers={"sessionId": token})
        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError:
                return resp.text
        return envelope

    # If the very first call already returned DONE, unwrap immediately.
    if initial.get("buildStatus") == "DONE":
        return await _unwrap(initial)

    for _ in range(20):
        await asyncio.sleep(2)
        try:
            polled = await client.get(path, params={"downloadId": download_id})
        except Exception:
            return initial
        if not isinstance(polled, dict):
            return polled
        status = polled.get("buildStatus")
        if status == "DONE":
            return await _unwrap(polled)
        if status == "ERROR":
            return polled
    return initial


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    settings = Settings()
    settings.prismhr_peo_id = os.environ["PRISMHR_MCP_PEO_ID"]
    http = httpx.AsyncClient(timeout=60.0)
    creds = DirectCredentialSource(
        settings.prismhr_peo_id,
        os.environ["PRISMHR_MCP_USERNAME"],
        os.environ["PRISMHR_MCP_PASSWORD"],
    )
    session = SessionManager(settings, creds, http)
    client = PrismHRClient(settings, session, http)

    methods = json.loads(pathlib.Path(".planning/prismhr-methods-v2.json").read_text())

    # Discover authorized services upfront — no point probing unauthorized ones.
    perms = await client.get("/login/v1/getAPIPermissions")
    authorized_services = set()
    if isinstance(perms, dict):
        cp = perms.get("currentPermissions") or {}
        for m in cp.get("allowedMethods", []) or []:
            if isinstance(m, dict) and m.get("service"):
                authorized_services.add(str(m["service"]))

    print(f"authorized services: {len(authorized_services)}")

    # Build service -> prefix map (e.g., 'PayrollService' -> 'payroll')
    def service_authorized(rec: dict[str, Any]) -> bool:
        svc = rec["service"]
        # Map path segment (lowercase) to prismhr-service (PascalCase)
        prefix_map = {
            "clientMaster": "ClientMasterService",
            "employee": "EmployeeService",
            "payroll": "PayrollService",
            "benefits": "BenefitService",
            "deductions": "DeductionService",
            "codeFiles": "CodeFilesService",
            "humanResources": "HumanResourcesService",
            "taxRate": "TaxRateService",
            "timesheet": "TimesheetService",
            "newHire": "NewHireService",
            "generalLedger": "GeneralLedgerService",
            "documentService": "DocumentService",
            "applicant": "ApplicantService",
            "prismSecurity": "PrismSecurityService",
            "system": "SystemService",
            "subscription": "SubscriptionService",
            "signOn": "SignOnService",
            "login": "LoginService",
        }
        pr_service = prefix_map.get(svc)
        if not pr_service:
            return False
        full = f"{pr_service}.{rec['operation']}"
        return full in authorized_services

    reg = FixtureRegistry()
    RESP_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, Any]] = []

    # ----- Seed round: call GETs with no required non-session params -----
    print("\n--- SEED ROUND (no-arg GETs) ---")
    for rec in [r for r in methods if r["method"] == "GET"]:
        if rec["operation"] in SKIP_OPS:
            continue
        if not service_authorized(rec):
            continue
        params = rec["parameters"]
        required_non_session = [p for p in params if p["required"] and p["name"] != "sessionId" and p.get("location") != "path"]
        if required_non_session:
            continue
        # Call the endpoint
        try:
            start = time.monotonic()
            raw = await client.get(rec["path"])
            elapsed = int((time.monotonic() - start) * 1000)
        except Exception as exc:  # noqa: BLE001
            summary.append({
                "path": rec["path"],
                "status": "error",
                "error": str(exc)[:200],
            })
            print(f"  [ERR] {rec['path']} ({str(exc)[:80]})")
            continue

        # PrismHR may return 200 with errorCode != 0. Check.
        if isinstance(raw, dict):
            err = raw.get("errorCode")
            if err not in (None, "", "0"):
                summary.append({
                    "path": rec["path"],
                    "status": "prismhr_error",
                    "errorCode": err,
                    "errorMessage": raw.get("errorMessage"),
                    "elapsed_ms": elapsed,
                })
                print(f"  [PHR] {rec['path']} errorCode={err}")
                continue

        # If this is the async download, follow it to get real data
        follow = None
        if rec["operation"] == "getBulkYearToDateValues":
            follow = await _follow_async_download(client, rec["path"], raw, http)
            if follow is not None:
                raw = follow
        elif isinstance(raw, dict) and raw.get("buildStatus") == "INIT":
            raw = await _follow_async_download(client, rec["path"], raw, http)

        # Harvest IDs
        learned = _harvest_ids_from_response(reg, raw)
        keys = _flatten_keys(raw)

        out_path = RESP_DIR / f"{rec['service']}_{rec['operation']}.json"
        try:
            out_path.write_text(json.dumps(raw, indent=2, default=str)[:200000], encoding="utf-8")
        except Exception:
            pass

        summary.append({
            "path": rec["path"],
            "status": "verified",
            "elapsed_ms": elapsed,
            "response_keys": keys[:80],
            "fields_discovered": learned,
        })
        print(f"  [OK ] {rec['path']}  ({elapsed}ms, +{learned} fixtures)")

    # ----- Iterative rounds: keep going while new methods become satisfiable -----
    for round_no in range(1, 10):
        print(f"\n--- ITER {round_no} (using learned fixtures) ---")
        print(f"  fixtures now: {sum(len(v) for v in reg._values.values())} values across "  # noqa: SLF001
              f"{len(reg._values)} keys")  # noqa: SLF001
        new_calls = 0
        for rec in [r for r in methods if r["method"] == "GET"]:
            if rec["operation"] in SKIP_OPS:
                continue
            if not service_authorized(rec):
                continue
            key = rec["path"]
            # skip if already verified or errored
            if any(s["path"] == key for s in summary):
                continue
            ok, args = _satisfiable(rec["parameters"], reg)
            if not ok:
                continue
            # Call it
            try:
                start = time.monotonic()
                raw = await client.get(rec["path"], params=args)
                elapsed = int((time.monotonic() - start) * 1000)
            except PrismHRRequestError as exc:
                summary.append({
                    "path": key,
                    "status": "error",
                    "args_used": args,
                    "error": str(exc)[:200],
                })
                print(f"  [ERR] {key} ({str(exc)[:80]})")
                new_calls += 1
                continue
            except Exception as exc:  # noqa: BLE001
                summary.append({"path": key, "status": "transport_error", "error": str(exc)[:200]})
                print(f"  [ERR] {key}: {str(exc)[:80]}")
                new_calls += 1
                continue

            if isinstance(raw, dict):
                err = raw.get("errorCode")
                if err not in (None, "", "0"):
                    summary.append({
                        "path": key,
                        "status": "prismhr_error",
                        "args_used": args,
                        "errorCode": err,
                        "errorMessage": raw.get("errorMessage"),
                        "elapsed_ms": elapsed,
                    })
                    new_calls += 1
                    print(f"  [PHR] {key} errorCode={err}")
                    continue

            learned = _harvest_ids_from_response(reg, raw)
            keys = _flatten_keys(raw)
            out_path = RESP_DIR / f"{rec['service']}_{rec['operation']}.json"
            try:
                out_path.write_text(
                    json.dumps(raw, indent=2, default=str)[:200000], encoding="utf-8"
                )
            except Exception:
                pass
            summary.append({
                "path": key,
                "status": "verified",
                "args_used": args,
                "elapsed_ms": elapsed,
                "response_keys": keys[:80],
                "fields_discovered": learned,
            })
            print(f"  [OK ] {key}  ({elapsed}ms, +{learned} fixtures)")
            new_calls += 1

        if new_calls == 0:
            print(f"  no new satisfiable methods — stopping iteration")
            break

    verified = sum(1 for s in summary if s["status"] == "verified")
    phr_err = sum(1 for s in summary if s["status"] == "prismhr_error")
    other_err = sum(1 for s in summary if s["status"] in ("error", "transport_error"))
    print(
        f"\nCOVERAGE: {verified} verified, {phr_err} prismhr-errors, "
        f"{other_err} transport/http errors. fixtures learned: "
        f"{sum(len(v) for v in reg._values.values())} values."  # noqa: SLF001
    )

    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "authorized_services": sorted(authorized_services),
                "fixtures": reg.snapshot(),
                "probes": summary,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"summary: {SUMMARY_PATH}")
    print(f"verified responses: {RESP_DIR}/")

    await http.aclose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
