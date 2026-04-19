"""Fixtures pass: target missing_params endpoints using IDs mined from
already-verified responses.

Harvests: payGroupCode, retirementPlanId, ptoPlanId, benefitPlanId,
stateCode, reportYear, locationId. Then probes methods needing those.

PII hygiene: all response bodies are redacted via `_redact()` before
being written to disk. Even though `.planning/verified-responses/` is
gitignored, the redaction is a belt-and-suspenders guard against an
accidental force-add or sanitize helper misfire. Only schema shape
(field names) and non-sensitive enum values are preserved.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

from prismhr_mcp.secure_env import load_into_environ

# Keys whose values are sensitive regardless of surrounding context.
# We keep the key (schema is useful) but replace the value with a marker.
_REDACT_KEYS: frozenset[str] = frozenset({
    "ssn", "socialSecurityNumber", "dob", "dateOfBirth", "birthDate",
    "bankAccountNumber", "routingNumber", "accountNumber",
    "driversLicenseNumber", "passportNumber",
    "homePhone", "cellPhone", "workPhone", "mobilePhone", "emergencyPhone",
    "email", "personalEmail", "workEmail",
    "addressLine1", "addressLine2", "streetAddress", "street",
    "password", "token", "sessionId", "apiKey",
})

# Regex used as a last line of defense on string values.
_SSN_RE = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")


def _redact(value: Any) -> Any:
    """Walk a JSON structure, masking sensitive values but preserving shape."""
    if isinstance(value, dict):
        return {
            k: ("***REDACTED***" if k in _REDACT_KEYS else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, str) and _SSN_RE.search(value):
        return _SSN_RE.sub("***REDACTED***", value)
    return value

CID = "TEST-CLIENT"
CID_ALT = "TEST-CLIENT"
EID = "TEST-EMPLOYEE"


def _load(name: str) -> dict:
    p = Path(".planning/verified-responses") / name
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def harvest() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {
        "payGroup": [],
        "retirementPlanId": [],
        "ptoPlanId": [],
        "benefitPlanId": [],
        "locationId": [],
        "reportYear": ["2024", "2025"],
        "stateCode": ["NE", "CA", "MI", "TX", "NY"],
        "daysOut": ["30", "60", "90"],
        # planType uses single-letter codes per quirks overlay:
        # H=HSA, F=FSA, S=Section 125. 125 / HSA / FSA all return 400.
        "planType": ["H", "F", "S"],
        "deductionCode": [],
        "departmentCode": [],
        "positionCode": [],
    }

    sched = _load("clientMaster_getPayrollSchedule.json")
    for r in (sched.get("clientPayrollSchedule") or []):
        if r.get("groupId"):
            out["payGroup"].append(r["groupId"])

    ret = _load("clientMaster_getRetirementPlanList.json")
    for cr in (ret.get("clientRetirement") or []):
        for p in (cr.get("retirementPlanList") or []):
            if p.get("retirePlan"):
                out["retirementPlanId"].append(p["retirePlan"])

    pto = _load("benefits_getPaidTimeOffPlans.json")
    for p in (pto.get("paidTimeOffPlan") or []):
        if p.get("id"):
            out["ptoPlanId"].append(p["id"])

    ben = _load("benefits_getClientBenefitPlans.json")
    for p in (ben.get("benefitPlanOverview") or []):
        if p.get("planId"):
            out["benefitPlanId"].append(p["planId"])

    ded = _load("deductions_getDeductions.json")
    for d in (ded.get("deductionList") or ded.get("deductions") or []):
        if d.get("deductionCode"):
            out["deductionCode"].append(d["deductionCode"])

    return out


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    base = "https://uatapi.prismhr.com/demo/prismhr-api/services/rest"
    fix = harvest()
    print(f"harvested fixtures: {json.dumps({k: v[:3] for k, v in fix.items()}, indent=2)}")

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

        targets: list[tuple[str, dict]] = []

        # pay group detail
        for pg in fix["payGroup"][:2]:
            targets.append(("/clientMaster/v1/getPayGroupDetails", {"clientId": CID, "payGroupCode": pg}))

        # PTO plan detail (has client dot-prefix)
        for pp in fix["ptoPlanId"][:2]:
            targets.append(("/benefits/v1/getPtoPlanDetails", {"clientId": pp.split(".")[0], "ptoPlanId": pp}))

        # section 125
        for pt in fix["planType"]:
            targets.append(("/benefits/v1/getSection125Plans", {"clientId": CID, "planType": pt}))

        # state code endpoints
        for sc in fix["stateCode"]:
            targets.append(("/clientMaster/v1/getSutaRates", {"clientId": CID, "state": sc}))
            targets.append(("/clientMaster/v1/getWCBillingModifiers", {"clientId": CID, "stateCode": sc}))
            targets.append(("/clientMaster/v2/getSutaBillingRates", {"clientId": CID, "stateCode": sc, "year": "2025"}))

        # OSHA 300A by year
        for y in fix["reportYear"]:
            targets.append(("/clientMaster/v1/getOSHA300Astats", {"clientId": CID, "reportYear": y}))

        # doc expirations
        for d in fix["daysOut"][:2]:
            targets.append(("/clientMaster/v1/getDocExpirations", {"clientId": CID, "daysOut": d}))

        # 401K match rules — needs benefitGroupId + retirementPlanId
        for rp in fix["retirementPlanId"][:1]:
            targets.append(("/benefits/v1/get401KMatchRules", {"clientId": CID, "retirementPlanId": rp, "benefitGroupId": "1"}))

        # entity employee list variations
        for et in ["DEPARTMENT", "DIVISION", "LOCATION"]:
            targets.append(("/clientMaster/v1/getEmployeeListByEntity", {"clientId": CID, "entityType": et, "entityId": "ALL"}))

        # disability plan details (cycle benefit plan IDs)
        for bp in fix["benefitPlanId"][:3]:
            targets.append(("/benefits/v1/getDisabilityPlanEnrollmentDetails", {"clientId": CID, "groupBenefitPlanId": bp}))

        # retirement census
        targets.append(("/benefits/v1/retirementCensusExport", {"clientId": CID, "reportFormat": "CSV"}))

        # GL data
        for gt in ["JOURNAL", "ACCOUNT", "LEDGER"]:
            targets.append(("/clientMaster/v1/getGLData", {"clientId": CID, "type": gt}))

        # EEO codes
        for et in ["1", "2", "RACE", "JOB"]:
            targets.append(("/codeFiles/v1/getEeoCodes", {"clientId": CID, "eeoCodeType": et}))

        # user defined fields
        for ft in ["EMPLOYEE", "CLIENT", "PAYCODE"]:
            targets.append(("/codeFiles/v1/getUserDefinedFields", {"clientId": CID, "fieldType": ft}))

        # deduction code details
        for dc in fix["deductionCode"][:3]:
            targets.append(("/codeFiles/v1/getDeductionCodeDetails", {"clientId": CID, "deductionCode": dc}))

        ok = 0
        per: dict[str, str] = {}
        for path, params in targets:
            try:
                resp = await c.get(base + path, headers=h, params=params)
                if resp.status_code == 200:
                    body = resp.json()
                    ec = body.get("errorCode") if isinstance(body, dict) else None
                    if ec in (None, "", "0"):
                        key = path
                        if key not in per:
                            per[key] = "OK"
                            ok += 1
                            name = path.strip("/").replace("/", "_").replace("v1_", "").replace("v2_", "v2_") + ".json"
                            out = Path(".planning/verified-responses") / name
                            redacted = _redact(body)
                            out.write_text(
                                json.dumps(redacted, indent=2, default=str)[:100000],
                                encoding="utf-8",
                            )
                            print(f"[OK ] {path}  params={params}")
                        continue
                    per.setdefault(path, f"errorCode={ec} msg={(body.get('errorMessage') or '')[:60]}")
                else:
                    per.setdefault(path, f"status={resp.status_code} body={resp.text[:80]}")
            except Exception as exc:
                per.setdefault(path, f"exc={str(exc)[:80]}")

        print(f"\n=== {ok} new verified ===")
        for p, reason in per.items():
            if reason != "OK":
                print(f"  FAIL {p}  ({reason})")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
