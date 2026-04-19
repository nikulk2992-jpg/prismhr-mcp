"""Submit a PrismHR web-service-user permissions update request.

The correct request body shape (reverse-engineered from the Simploy
consolidated-payroll-reporter app) is NOT documented in the bible PDF:

    POST /login/v1/requestAPIPermissions
    Content-Type: application/json
    {
      "sessionId": "<same as header>",
      "webServiceUser": "<username>",
      "overwritePendingRequest": true,
      "newPermissions": {
        "appVersion": "<free text>",
        "description": "<free text>",
        "minApiVersion": "ALL",      // or '1.30' or 'prismhr-api'
        "contactInfo": "<email>",
        "allowedIps": [...],
        "allowedMethods": [
          {"service": "ServiceName.methodName", "options": [], "fromTime": "", "toTime": ""},
          ...
        ]
      }
    }

Key details:
  - The inner `newPermissions` wrapper is mandatory — top-level
    `allowedMethods` without it returns 400 "Please provide the version
    to which your application is updating" (the error text is misleading;
    it really means the request was not shaped as an ApiPermissionsRequest).
  - `sessionId` + `webServiceUser` appear BOTH in the header (sessionId)
    and in the body (both). Some PrismHR endpoints want the session as
    a body param too.
  - PrismHR 200s regardless of approval — the request is saved pending
    an admin review in the PEO's PrismHR admin UI. Use
    `GET /login/v1/checkPermissionsRequestStatus` to poll.

Usage: lists requested additions, prints new grants vs existing, POSTs,
and prints the response. Manual-only. NEVER exposed as an MCP tool.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

from prismhr_mcp.secure_env import load_into_environ

# Edit this list as your coverage needs grow. Keep the additions focused
# on read methods the OSS core + commercial assistants actually call.
DESIRED_SERVICES: list[str] = [
    # ClientMasterService — client directory + payroll setup
    "ClientMasterService.getClientList",
    "ClientMasterService.getClientMaster",
    "ClientMasterService.getClientCodes",
    "ClientMasterService.getPayGroupDetails",
    "ClientMasterService.getPayrollSchedule",
    "ClientMasterService.getClientEvents",
    "ClientMasterService.getClientLocationDetails",
    "ClientMasterService.getEmployeeListByEntity",
    "ClientMasterService.getEmployeesInPayGroup",
    "ClientMasterService.getClientOwnership",
    # EmployeeService — employee roster + detail
    "EmployeeService.getEmployeeList",
    "EmployeeService.getEmployee",
    "EmployeeService.getScheduledDeductions",
    "EmployeeService.getAddressInfo",
    "EmployeeService.getEmployeeEvents",
    "EmployeeService.getACHDeductions",
    "EmployeeService.checkForGarnishments",
    "EmployeeService.getEmployersInfo",
    "EmployeeService.getEverifyStatus",
    "EmployeeService.get1095CYears",
    "EmployeeService.get1099Years",
    # BenefitService — enrollment, PTO, ACA
    "BenefitService.getActiveBenefitPlans",
    "BenefitService.getBenefitPlans",
    "BenefitService.getClientBenefitPlans",
    "BenefitService.getBenefitPlanList",
    "BenefitService.getPaidTimeOff",
    "BenefitService.getMonthlyACAInfo",
    "BenefitService.getDependents",
    "BenefitService.getRetirementLoans",
    "BenefitService.getRetirementPlan",
    "BenefitService.getCobraCodes",
    "BenefitService.getCobraEmployee",
    "BenefitService.getBenefitConfirmationList",
    "BenefitService.getPaidTimeOffPlans",
    "BenefitService.getAbsenceJournal",
    "BenefitService.getPtoClasses",
    # DeductionService — garnishments, voluntary deductions
    "DeductionService.getGarnishmentDetails",
    "DeductionService.getGarnishmentPaymentHistory",
    "DeductionService.getVoluntaryRecurringDeductions",
    # CodeFileService — reference data. Initial grant covered some but
    # several return 403 even after approval; re-requesting explicitly.
    "CodeFileService.getBillingCode",
    "CodeFileService.getDeductionCodeDetails",
    "CodeFileService.getPaycodeDetails",
    "CodeFileService.getDepartmentCode",
    "CodeFileService.getDivisionCode",
    "CodeFileService.getNAICSCodeList",
    "CodeFileService.getEeoCodes",
    "CodeFileService.getPayGrades",
    "CodeFileService.getHolidayCodeList",
    "CodeFileService.getEventCodes",
    "CodeFileService.getShiftCode",
    "CodeFileService.getPositionCode",
    "CodeFileService.getProjectCode",
    "CodeFileService.getClientCategoryList",
    "CodeFileService.getContactTypeList",
    "CodeFileService.getCourseCodesList",
    "CodeFileService.getSkillCode",
    "CodeFileService.getRatingCode",
    "CodeFileService.getProjectPhase",
    "CodeFileService.getPositionClassifications",
    "CodeFileService.getUserDefinedFields",
    # Additional authorized-tier expansion candidates
    "ClientMasterService.getClientLocationDetails",
    "ClientMasterService.getLaborAllocations",
    "ClientMasterService.getLaborUnionDetails",
    "ClientMasterService.getSutaBillingRates",
    "ClientMasterService.getSutaRates",
    "ClientMasterService.getWCAccrualModifiers",
    "ClientMasterService.getWCBillingModifiers",
    "ClientMasterService.getMessageList",
    "ClientMasterService.getMessages",
    "ClientMasterService.getGLData",
    "ClientMasterService.getPayDayRules",
    "ClientMasterService.getRetirementPlanList",
    "ClientMasterService.getUnbundledBillingRules",
    "TaxRateService.getFutaTaxRates",
    "TaxRateService.getSutaTaxRates",
    "HumanResourcesService.getEEO1SurveyData",
    "GeneralLedgerService.getGLInvoicePost",
    "GeneralLedgerService.getGLJournalPost",
    "GeneralLedgerService.getGLCutbackCheckPost",
    "BenefitService.getAbsenceJournal",
    "BenefitService.getBenefitAdjustments",
    "BenefitService.get401KMatchRules",
    "BenefitService.getACAOfferedEmployees",
    "BenefitService.getAvailableBenefitPlans",
    "BenefitService.getBenefitRule",
    "BenefitService.getDisabilityPlanEnrollmentDetails",
    "BenefitService.getSection125Plans",
    "BenefitService.getPtoPlanDetails",
    "BenefitService.getPtoAbsenceCodes",
    "BenefitService.getPtoAutoEnrollRules",
    "BenefitService.getPtoRegisterTypes",
    "BenefitService.getEligibleFlexSpendingPlans",
    "BenefitService.getPlanYearInfo",
    "BenefitService.retirementCensusExport",
    # TaxRateService — tax setup
    "TaxRateService.getFutaTaxRates",
    "TaxRateService.getSutaTaxRates",
    # GeneralLedgerService — invoicing + AR
    "GeneralLedgerService.getBulkOutstandingInvoices",
    "GeneralLedgerService.getClientAccountingTemplate",
    "GeneralLedgerService.getClientGLData",
    "GeneralLedgerService.getGLCutbackCheckPost",
    "GeneralLedgerService.getGLInvoicePost",
    "GeneralLedgerService.getGLJournalPost",
    # HumanResourcesService
    "HumanResourcesService.getEEO1SurveyData",
    # NewHireService — onboarding
    "NewHireService.getImportStatus",
    # ApplicantService
    "ApplicantService.getJobApplicantList",
    "ApplicantService.getJobApplicants",
    # DocumentService
    "DocumentService.getDocumentTypes",
    "DocumentService.getRuleset",
    # Round 4: additional payroll/benefits/client/employee coverage
    "PayrollService.getBillingVouchers",
    "PayrollService.getBillingCodeTotalsByPayGroup",
    "PayrollService.getBillingVouchersByBatch",
    "PayrollService.getBatchPayments",
    "PayrollService.getProcessSchedule",
    "PayrollService.getProcessScheduleCodes",
    "PayrollService.getClientsWithVouchers",
    "PayrollService.getEmployeeOverrideRates",
    "PayrollService.getEmployee401KContributionsByDate",
    "PayrollService.getEmployeePayrollSummary",
    "PayrollService.getRetirementAdjVoucherListByDate",
    "PayrollService.getExternalPtoBalance",
    "BenefitService.getBenefitWorkflowGrid",
    "BenefitService.getBenefitsEnrollmentTrace",
    "BenefitService.benefitEnrollmentStatus",
    "ClientMasterService.getDocExpirations",
    "ClientMasterService.getGeoLocations",
    "ClientMasterService.getOSHA300Astats",
    "EmployeeService.getEmployeeSSNList",
    "EmployeeService.getEmployeesReadyForEverify",
]


async def main() -> int:
    load_into_environ(Path(".env.local.enc"))
    peo_id = os.environ["PRISMHR_MCP_PEO_ID"]
    username = os.environ["PRISMHR_MCP_USERNAME"]
    password = os.environ["PRISMHR_MCP_PASSWORD"]
    base = "https://uatapi.prismhr.com/demo/prismhr-api/services/rest"

    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.post(
            f"{base}/login/v1/createPeoSession",
            data={"peoId": peo_id, "username": username, "password": password},
        )
        sid = r.json()["sessionId"]
        h = {"sessionId": sid, "Accept": "application/json", "Content-Type": "application/json"}

        cur = (await c.get(f"{base}/login/v1/getAPIPermissions", headers=h)).json()[
            "currentPermissions"
        ]
        existing = {m["service"] for m in cur["allowedMethods"]}
        additions = [s for s in DESIRED_SERVICES if s not in existing]
        if not additions:
            print("no new services needed; nothing to request.")
            return 0

        merged = list(cur["allowedMethods"])
        for s in additions:
            merged.append({"service": s, "options": [], "fromTime": "", "toTime": ""})

        payload = {
            "sessionId": sid,
            "webServiceUser": username,
            "overwritePendingRequest": True,
            "newPermissions": {
                "appVersion": "prismhr-mcp/0.1.0-dev10",
                "description": (
                    "prismhr-mcp OSS MCP server — read access for catalog + "
                    "workflow tool verification"
                ),
                "minApiVersion": "ALL",
                "contactInfo": "nihar@simploy.com",
                "allowedIps": cur.get("allowedIps", []),
                "allowedMethods": merged,
            },
        }
        print(f"requesting {len(additions)} new services:")
        for s in additions:
            print(f"  + {s}")
        resp = await c.post(
            f"{base}/login/v1/requestAPIPermissions",
            headers=h,
            content=json.dumps(payload),
        )
        print(f"\nresponse: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

        # Poll request status so the user sees what's pending.
        status = await c.get(
            f"{base}/login/v1/checkPermissionsRequestStatus",
            headers=h,
            params={"webServiceUser": username},
        )
        print("\npending-request status:")
        print(json.dumps(status.json(), indent=2)[:2000])

        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
