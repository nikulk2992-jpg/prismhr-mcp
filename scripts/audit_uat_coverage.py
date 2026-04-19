"""Audit UAT method coverage: for every authorized method, report status.

Output `.planning/uat-coverage-audit.md` (local-only; gitignored — tenant
metadata) and a terminal summary. Helps us see which authorized methods
are still not verified and WHY.

Categories:
  - verified        — probe succeeded, response shape captured
  - prismhr_error   — probe hit PrismHR but got errorCode != 0
  - transport_error — probe hit HTTP 400/403/500 from PrismHR
  - missing_params  — authorized but probe never tried: required params
                      not in fixture registry
  - unauthorized    — method not in allowedMethods list
"""

from __future__ import annotations

import json
import os
import pathlib
from pathlib import Path
from typing import Any

from prismhr_mcp.catalog import load_catalog
from prismhr_mcp.secure_env import load_into_environ


SERVICE_PREFIX_MAP = {
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


def _service_method(path_service: str, op: str) -> str:
    return f"{SERVICE_PREFIX_MAP.get(path_service, path_service)}.{op}"


def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    catalog = load_catalog()

    # Read verification matrix (local — has real IDs) + authorized services
    matrix_path = pathlib.Path(".planning/verification-matrix.json")
    if not matrix_path.exists():
        print("run scripts/calibrated_probe.py first")
        return 2
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    authorized = set(matrix.get("authorized_services", []))
    probes_by_path = {p["path"]: p for p in matrix.get("probes", [])}
    fixtures = matrix.get("fixtures", {})
    # Canonical param-name -> fixture key (duplicate of harness mapping)
    alias = {
        "clientId": "client_id", "employeeId": "employee_id", "batchId": "batch_id",
        "voucherId": "voucher_id", "planId": "plan_id", "payGroupId": "pay_group_id",
        "scheduleCode": "schedule_code", "deductionCode": "deduction_code",
        "billingCode": "billing_code", "payCode": "paycode",
        "departmentCode": "department_code", "divisionCode": "division_code",
        "jobCode": "job_code", "positionCode": "position_code",
        "locationId": "location_id", "benefitPlanId": "benefit_plan_id",
        "benefitPlanCode": "benefit_plan_code", "eventCode": "event_code",
        "checkNumber": "check_number", "refNumber": "ref_number",
        "refId": "ref_id", "uploadId": "upload_id", "userId": "user_id",
        "journalId": "journal_id", "planClass": "plan_class",
        "startDate": "start_date", "endDate": "end_date",
        "payDateStart": "pay_date_start", "payDateEnd": "pay_date_end",
        "asOfDate": "as_of_date", "year": "year", "quarter": "quarter",
    }

    # For each endpoint in the catalog, categorize
    categories: dict[str, list[dict[str, Any]]] = {
        "verified": [],
        "prismhr_error": [],
        "transport_error": [],
        "missing_params": [],
        "unauthorized": [],
        "admin_blocked": [],
    }

    for contract in catalog.all():
        rec = {
            "method_id": contract.method_id,
            "path": contract.path,
            "http": contract.http_method,
            "summary": contract.summary[:80],
        }
        if contract.is_admin:
            categories["admin_blocked"].append(rec)
            continue

        svc_method = _service_method(contract.service, contract.operation)
        if svc_method not in authorized:
            categories["unauthorized"].append(rec)
            continue

        probe = probes_by_path.get(contract.path)
        if probe:
            if probe["status"] == "verified":
                categories["verified"].append(rec)
            elif probe["status"] == "prismhr_error":
                rec["prismhr_error"] = probe.get("errorCode")
                categories["prismhr_error"].append(rec)
            else:
                rec["error"] = (probe.get("error") or "")[:150]
                categories["transport_error"].append(rec)
            continue

        # Never probed — check why
        required = [p for p in contract.parameters
                    if p.get("required") and p["name"] != "sessionId"
                    and p.get("location") != "path"]
        missing = []
        for p in required:
            key = alias.get(p["name"], p["name"])
            if not fixtures.get(key):
                missing.append(p["name"])
        rec["missing_params"] = missing
        categories["missing_params"].append(rec)

    # Print summary
    print(f"Audit of {len(catalog)} catalog methods:")
    print(f"  admin_blocked:   {len(categories['admin_blocked']):3d}")
    print(f"  unauthorized:    {len(categories['unauthorized']):3d}")
    print(f"  verified:        {len(categories['verified']):3d}")
    print(f"  prismhr_error:   {len(categories['prismhr_error']):3d}")
    print(f"  transport_error: {len(categories['transport_error']):3d}")
    print(f"  missing_params:  {len(categories['missing_params']):3d}")

    # Write markdown
    out = pathlib.Path(".planning/uat-coverage-audit.md")
    lines = ["# UAT Coverage Audit", ""]
    lines.append(f"**Catalog:** {len(catalog)} methods · **Authorized services:** "
                 f"{len(authorized)} · **Fixture keys learned:** {len(fixtures)}")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|---|---:|")
    for cat in ["verified", "prismhr_error", "transport_error", "missing_params",
                 "unauthorized", "admin_blocked"]:
        lines.append(f"| `{cat}` | {len(categories[cat])} |")
    lines.append("")

    # Detail missing_params with which fields block them — most useful section
    lines.append("## `missing_params` — authorized but not probeable yet")
    lines.append("")
    lines.append("Methods whose required params we don't have fixtures for.")
    lines.append("")
    lines.append("| Method | HTTP | Missing params | Summary |")
    lines.append("|---|---|---|---|")
    for rec in sorted(categories["missing_params"], key=lambda r: r["method_id"]):
        missing = ", ".join(f"`{p}`" for p in rec["missing_params"])
        lines.append(f"| `{rec['method_id']}` | {rec['http']} | {missing} | {rec['summary']} |")
    lines.append("")

    # prismhr_error breakdown
    lines.append("## `prismhr_error` — probe hit the wire but PrismHR returned errorCode")
    lines.append("")
    lines.append("| Method | HTTP | errorCode | Summary |")
    lines.append("|---|---|---|---|")
    for rec in sorted(categories["prismhr_error"], key=lambda r: r["method_id"]):
        lines.append(f"| `{rec['method_id']}` | {rec['http']} | {rec.get('prismhr_error')} | {rec['summary']} |")
    lines.append("")

    # transport_error breakdown
    lines.append("## `transport_error` — HTTP 4xx/5xx from PrismHR")
    lines.append("")
    lines.append("| Method | Error |")
    lines.append("|---|---|")
    for rec in sorted(categories["transport_error"], key=lambda r: r["method_id"]):
        lines.append(f"| `{rec['method_id']}` | {rec.get('error', '')[:120]} |")
    lines.append("")

    # unauthorized — just aggregate by service
    unauth_by_svc: dict[str, int] = {}
    for r in categories["unauthorized"]:
        svc = r["method_id"].split(".", 1)[0]
        unauth_by_svc[svc] = unauth_by_svc.get(svc, 0) + 1
    lines.append("## `unauthorized` — service.method not in account's allowedMethods")
    lines.append("")
    lines.append("Ask PrismHR admin to grant these services to expand coverage.")
    lines.append("")
    lines.append("| Service | Unauthorized count |")
    lines.append("|---|---:|")
    for svc, cnt in sorted(unauth_by_svc.items(), key=lambda kv: -kv[1]):
        lines.append(f"| `{svc}` | {cnt} |")
    lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
