"""Wide-pass probe: try remaining unprobed endpoints across every service.

Not exhaustive — hits the highest-signal reads that weren't reached by
flat or tuple passes. Uses a known-good (clientId, employeeId) pair.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

from prismhr_mcp.secure_env import load_into_environ

# Fixture IDs supplied at runtime via env so this script ships no
# tenant-specific values. Set PROBE_CLIENT_ID / PROBE_EMPLOYEE_ID /
# PROBE_BATCH_ID before running.
CID = os.environ.get("PROBE_CLIENT_ID", "")
EID = os.environ.get("PROBE_EMPLOYEE_ID", "")
BATCH = os.environ.get("PROBE_BATCH_ID", "")


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    base = "https://uatapi.prismhr.com/demo/prismhr-api/services/rest"
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.post(
            f"{base}/login/v1/createPeoSession",
            data={
                "peoId": os.environ["PRISMHR_MCP_PEO_ID"],
                "username": os.environ["PRISMHR_MCP_USERNAME"],
                "password": os.environ["PRISMHR_MCP_PASSWORD"],
            },
        )
        tok = r.json()["sessionId"]
        h = {"sessionId": tok, "Accept": "application/json"}

        targets = [
            ("/applicant/v1/getJobApplicantList", {"clientId": CID}),
            ("/documentService/v1/getRuleset", {"clientId": CID}),
            ("/benefits/v1/getBenefitWorkflowGrid", {"clientId": CID}),
            ("/benefits/v1/getBenefitRule", {"clientId": CID}),
            ("/benefits/v1/getBenefitsEnrollmentTrace", {"clientId": CID, "employeeId": EID}),
            ("/benefits/v1/benefitEnrollmentStatus", {"clientId": CID, "employeeId": EID}),
            ("/clientMaster/v1/getDocExpirations", {"clientId": CID, "daysOut": "30"}),
            ("/clientMaster/v1/getGeoLocations", {"zipCode": "90210"}),
            ("/clientMaster/v1/getMessages", {"clientId": CID}),
            ("/clientMaster/v1/getMessageList", {"clientId": CID}),
            ("/clientMaster/v1/getOSHA300Astats", {"clientId": CID, "year": "2026"}),
            ("/clientMaster/v1/getPrismClientContact", {"clientId": CID}),
            ("/clientMaster/v2/getClientLocationDetails", {"clientId": CID}),
            ("/clientMaster/v2/getSutaBillingRates", {"clientId": CID, "year": "2026"}),
            ("/codeFiles/v1/getPayGrades", {"clientId": CID}),
            ("/codeFiles/v1/getUserDefinedFields", {"clientId": CID, "fieldType": "EMPLOYEE"}),
            ("/employee/v1/getEmployeeSSNList", {"clientId": CID}),
            ("/employee/v1/getEmployeesReadyForEverify", {"clientId": CID}),
            ("/payroll/v1/getEmployeeOverrideRates", {"clientId": CID, "employeeId": EID}),
            ("/payroll/v1/getEmployee401KContributionsByDate", {"clientId": CID, "employeeId": EID, "startDate": "2024-01-01", "endDate": "2026-12-31"}),
            ("/payroll/v1/getEmployeePayrollSummary", {"clientId": CID, "employeeId": EID}),
            ("/payroll/v1/getRetirementAdjVoucherListByDate", {"clientId": CID, "startDate": "2024-01-01", "endDate": "2026-12-31"}),
            ("/payroll/v1/getExternalPtoBalance", {"clientId": CID, "employeeId": EID}),
            ("/payroll/v1/getBillingVouchers", {"clientId": CID, "startDate": "2024-01-01", "endDate": "2026-12-31"}),
            ("/payroll/v1/getBillingCodeTotalsByPayGroup", {"clientId": CID, "batchId": BATCH}),
            ("/payroll/v1/getBillingVouchersByBatch", {"clientId": CID, "batchId": BATCH}),
            ("/payroll/v1/getBatchPayments", {"clientId": CID, "batchId": BATCH, "employeeId": EID}),
            ("/payroll/v1/getProcessSchedule", {"clientId": CID}),
            ("/payroll/v1/getProcessScheduleCodes", {"clientId": CID}),
            ("/payroll/v1/getClientsWithVouchers", {"startDate": "2024-01-01", "endDate": "2026-12-31"}),
            ("/timesheet/v1/getParamData", {}),
        ]

        ok_count = 0
        verified_paths: list[str] = []
        failures: list[tuple[str, str]] = []
        for path, params in targets:
            try:
                resp = await c.get(base + path, headers=h, params=params)
                if resp.status_code == 200:
                    body = resp.json()
                    ec = body.get("errorCode") if isinstance(body, dict) else None
                    if ec in (None, "", "0"):
                        ok_count += 1
                        verified_paths.append(path)
                        out_name = (
                            path.strip("/")
                            .replace("/", "_")
                            .replace("v1_", "")
                            .replace("v2_", "v2_")
                            + ".json"
                        )
                        out = Path(".planning/verified-responses") / out_name
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_text(
                            json.dumps(body, indent=2, default=str)[:100000],
                            encoding="utf-8",
                        )
                        print(f"[OK ] {path}")
                        continue
                    failures.append((path, f"errorCode={ec} msg={(body.get('errorMessage') or '')[:50]}"))
                else:
                    failures.append((path, f"status={resp.status_code}"))
            except Exception as exc:  # noqa: BLE001
                failures.append((path, str(exc)[:80]))

        print(f"\n=== {ok_count}/{len(targets)} verified ===")
        for p, reason in failures:
            print(f"  FAIL {p}  ({reason})")

        # Append verified entries to local matrix
        matrix_path = Path(".planning/verification-matrix.json")
        if matrix_path.exists():
            matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
            existing = {p["path"]: p for p in matrix["probes"]}
            for v in verified_paths:
                existing[v] = {"path": v, "status": "verified", "response_keys": []}
            matrix["probes"] = list(existing.values())
            matrix_path.write_text(
                json.dumps(matrix, indent=2, default=str), encoding="utf-8"
            )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
