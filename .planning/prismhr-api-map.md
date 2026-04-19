# PrismHR API Surface — Full Method Map

Source: `prismapi_full_bible_with_index.pdf` (extracted 2026-04-19). Raw JSON at `.planning/prismhr-methods.json`.

**Total: 447 methods across 18 services.**

## Surface summary

| Service | Methods | GET | POST | MCP group | Scopes | PEO domain |
|---|---:|---:|---:|---|---|---|
| `clientMaster` | 81 | 38 | 43 | `client` | `client:read`, `client:write` | Clients & Worksites |
| `benefits` | 77 | 47 | 30 | `benefits` | `benefits:read`, `benefits:write` | Benefits & PTO |
| `employee` | 74 | 31 | 43 | `employee` | `employee:read`, `employee:write` | Employees & HR |
| `payroll` | 56 | 40 | 16 | `payroll` | `payroll:read`, `payroll:write` | Payroll |
| `codeFiles` | 40 | 21 | 19 | `codes` | `codes:read`, `codes:write` | Code Files (Reference Data) |
| `system` | 20 | 15 | 5 | `system` | `system:read`, `system:write` | System |
| `prismSecurity` | 17 | 14 | 3 | `security` | `security:read`, `security:write` | Security & User Admin |
| `generalLedger` | 13 | 10 | 3 | `gl` | `gl:read`, `gl:write` | General Ledger & AR |
| `signOn` | 11 | 3 | 8 | `signon` | `signon:read`, `signon:write` | Sign-On (SSO) |
| `deductions` | 8 | 6 | 2 | `deductions` | `deductions:read`, `deductions:write` | Deductions & Garnishments |
| `newHire` | 8 | 2 | 6 | `onboarding` | `onboarding:read`, `onboarding:write` | New Hire / Onboarding |
| `taxRate` | 8 | 7 | 1 | `tax` | `tax:read`, `tax:write` | Tax Setup & Rates |
| `humanResources` | 7 | 4 | 3 | `hr` | `hr:read`, `hr:write` | HR Operations |
| `subscription` | 7 | 4 | 3 | `subscription` | `subscription:read`, `subscription:write` | API Subscriptions |
| `timesheet` | 7 | 3 | 4 | `timesheet` | `timesheet:read`, `timesheet:write` | Timesheet & Time Entry |
| `login` | 6 | 2 | 4 | `session` | `session:read`, `session:write` | Session / Auth (internal) |
| `documentService` | 4 | 2 | 2 | `documents` | `documents:read`, `documents:write` | Document Management |
| `applicant` | 3 | 2 | 1 | `applicant` | `applicant:read`, `applicant:write` | Applicant Tracking |
| **TOTAL** | **447** | **251** | **196** | — | — | — |

## MCP layout strategy

Three tool tiers stack side by side. The goal: **a PEO ops user says 'reconcile this batch' and Claude picks the right tool.** No one calls `payroll_register_reconcile(client_id=..., batch_id=..., threshold_pct=0.05)` directly.

1. **Workflow tools (hand-written).** The headline moat. Composable PEO ops: `client_list`, `payroll_superbatch_status`, `payroll_register_reconcile`, `benefits_audit_discrepancies`. These combine several raw calls + domain logic.

2. **Raw escape-hatch (single tool).** `prismhr_raw_request(service, operation, params)` — when the workflow tools don't cover a use case, Claude can still hit any PrismHR endpoint the account's upstream permissions allow. Scope-gated on a per-service basis.

3. **Meta tools.** Session, permission, introspection.

Auto-registering all 447 methods as individual tools would flood Claude's tool-picker context. Keep the handful of curated workflow tools sharp; expose the long tail through one discoverable escape-hatch.

## Service catalog

### `clientMaster` — Clients & Worksites (81 methods)

**MCP group:** `client` · **Scopes:** `client:read`, `client:write`

<details><summary>Read methods (GET, 38)</summary>

- `GET /clientMaster/v1/getACALargeEmployer` — Get ACA large Employer
- `GET /clientMaster/v1/getAllPrismClientContacts` — Get all Prism client contacts
- `GET /clientMaster/v1/getBackupAssignments` — Get Backup Assignments
- `GET /clientMaster/v1/getBenefitGroup` — Get a benefit group
- `GET /clientMaster/v1/getBillPending` — Get bill pending record
- `GET /clientMaster/v1/getBundledBillingRule` — Get bundled billing rule(s)
- `GET /clientMaster/v1/getClientBillingBankAccount` — Get client billing bank account
- `GET /clientMaster/v1/getClientCodes` — Get code tables for the specified client
- `GET /clientMaster/v1/getClientEvents` — Get client specific events
- `GET /clientMaster/v1/getClientList` — Get clients list
- `GET /clientMaster/v1/getClientLocationDetails` — Get client location detail
- `GET /clientMaster/v2/getClientLocationDetails` — Get client location detail V2 version
- `GET /clientMaster/v1/getClientMaster` — Get client master data
- `GET /clientMaster/v1/getClientOwnership` — Get client ownership details
- `GET /clientMaster/v1/getDocExpirations` — Return docs that will expire within 'daysOut' days from current date
- `GET /clientMaster/v1/getEmployeeListByEntity` — Get employee list by entity
- `GET /clientMaster/v1/getEmployeesInPayGroup` — Get employees by pay group
- `GET /clientMaster/v1/getGLCutbackCheckPost` — Get GLCutbackCheckPost
- `GET /clientMaster/v1/getGLData` — Get GL data
- `GET /clientMaster/v1/getGLInvoicePost` — Get GL invoice post
- `GET /clientMaster/v1/getGLJournalPost` — Get GL journal post
- `GET /clientMaster/v1/getGeoLocations` — Get GeoLocations matching for the ZIP code
- `GET /clientMaster/v1/getLaborAllocations` — Get list of labor allocation templates
- `GET /clientMaster/v1/getLaborUnionDetails` — Get Labor Union Details
- `GET /clientMaster/v1/getMessageList` — Get message list
- `GET /clientMaster/v1/getMessages` — Get messages
- `GET /clientMaster/v1/getOSHA300Astats` — Get OSHA 300A stats
- `GET /clientMaster/v1/getPayDayRules` — Return pay day rules for the client
- `GET /clientMaster/v1/getPayGroupDetails` — Get pay group details by pay group ID
- `GET /clientMaster/v1/getPayrollSchedule` — Get pay group and pay schedule for the specified client
- `GET /clientMaster/v1/getPrismClientContact` — Get a Prism client contact
- `GET /clientMaster/v1/getRetirementPlanList` — Get Retirement Plan List
- `GET /clientMaster/v1/getSutaBillingRates` — Get SUTA billing rates
- `GET /clientMaster/v2/getSutaBillingRates` — Get SUTA billing rates (v2)
- `GET /clientMaster/v1/getSutaRates` — Get SUTA rates
- `GET /clientMaster/v1/getUnbundledBillingRules` — Get unbundled billing rules
- `GET /clientMaster/v1/getWCAccrualModifiers` — Get client W/C accrual modifiers
- `GET /clientMaster/v1/getWCBillingModifiers` — Get client W/C billing modifiers

</details>

<details><summary>Write methods (POST, 43)</summary>

- `POST /clientMaster/v1/addBillPending` — add a bill pending record
- `POST /clientMaster/v1/cloneClient` — Clone a client
- `POST /clientMaster/v1/createClientMaster` — Create a new client master record
- `POST /clientMaster/v1/createNewMessage` — Create new message
- `POST /clientMaster/v1/createPositionCode` — Create position code
- `POST /clientMaster/v1/createPrismClientContact` — Create a new Prism client contact
- `POST /clientMaster/v1/createSutaRates` — Create SUTA Rates
- `POST /clientMaster/v1/deleteBillPending` — delete a bill pending record
- `POST /clientMaster/v1/deletePrismMessage` — delete Prism message
- `POST /clientMaster/v1/flagClientsForEverify` — Flag all clients for everify that are listed in the input
- `POST /clientMaster/v1/flagLocationEverifyOverride` — Flag client's location(s) for everify
- `POST /clientMaster/v1/removePrismClientContact` — Remove a Prism client contact
- `POST /clientMaster/v1/setACALargeEmployer` — Set ACA large Employer
- `POST /clientMaster/v1/setAccountAssignments` — Update the account roles associated with a client
- `POST /clientMaster/v1/setAlternateEmployers` — set alteranate Employers
- `POST /clientMaster/v1/setBackupAssignments` — Set Backup Assignments
- `POST /clientMaster/v1/setBenefitGroup` — Set a benefit group
- `POST /clientMaster/v1/setBillingDetails` — Set billing details
- `POST /clientMaster/v1/setBundledBillingRule` — create or update bundled billing rule
- `POST /clientMaster/v1/setClientBillingBankAccount` — Set client billing bank account
- `POST /clientMaster/v1/setClientControl` — Set client control options
- `POST /clientMaster/v1/setClientEvents` — Create or update a client specific event
- `POST /clientMaster/v1/setClientLocationDetails` — Create new worksite location
- `POST /clientMaster/v1/setClientOwnership` — Set client ownership details
- `POST /clientMaster/v1/setClientPayroll` — Set client payroll options
- `POST /clientMaster/v1/setClientTimeSheetPayCode` — Set client time sheet pay codes and default hours
- `POST /clientMaster/v1/setCodeDescriptionOverride` — Create or update a code description override
- `POST /clientMaster/v1/setControlCodes` — Set Control Codes
- `POST /clientMaster/v1/setLaborAllocations` — Create or update labor allocation template
- `POST /clientMaster/v1/setLaborUnionDetails` — set labor union details
- `POST /clientMaster/v1/setMessageToRead` — Set a message as alreadyRead status
- `POST /clientMaster/v1/setPayDayRules` — sets payday rules for a client
- `POST /clientMaster/v1/setPayGroup` — set pay group details by pay group code
- `POST /clientMaster/v1/setRetirementPlan` — Update the retirement plans associated with a client
- `POST /clientMaster/v1/setWCAccrualModifiers` — Set client W/C accrual modifiers
- `POST /clientMaster/v1/setWCBillingModifiers` — Set client W/C billing modifiers
- `POST /clientMaster/v1/setWorkersCompPolicy` — update or create Workers' Compensation insurance policy
- `POST /clientMaster/v1/updateClientAddress` — Update client address information
- `POST /clientMaster/v1/updateClientMasterFields` — Update client master fields
- `POST /clientMaster/v1/updateClientStatus` — update client status
- `POST /clientMaster/v1/updateClientTaxInfo` — update Client Tax Info
- `POST /clientMaster/v1/updatePrismClientContact` — Update a Prism client contact
- `POST /clientMaster/v1/updateWorksiteLocationAch` — Update worksite location's ACH

</details>

### `benefits` — Benefits & PTO (77 methods)

**MCP group:** `benefits` · **Scopes:** `benefits:read`, `benefits:write`

<details><summary>Read methods (GET, 47)</summary>

- `GET /benefits/v1/benefitEnrollmentStatus` — Benefit Enrollment Status
- `GET /benefits/v1/get401KMatchRules` — Get client's 401(k) match rules
- `GET /benefits/v1/getACAOfferedEmployees` — Get ACAOffered Employees
- `GET /benefits/v1/getAbsenceJournal` — Get absence journals
- `GET /benefits/v1/getAbsenceJournalByDate` — Get absence journals by Date
- `GET /benefits/v1/getActiveBenefitPlans` — Get active plan(s) for an employee
- `GET /benefits/v1/getAvailableBenefitPlans` — Get available benefit plans for the specified employee
- `GET /benefits/v1/getBenefitAdjustments` — Get benefit adjustment information for a specified employee
- `GET /benefits/v1/getBenefitConfirmationData` — Downloads benefits confirmation statement
- `GET /benefits/v1/getBenefitConfirmationList` — Get a list of benefit confirmation
- `GET /benefits/v1/getBenefitPlanList` — Get a list of group benefit plans
- `GET /benefits/v1/getBenefitPlans` — Get benefit plans for the specified employee
- `GET /benefits/v1/getBenefitRule` — Get benefit rule
- `GET /benefits/v1/getBenefitWorkflowGrid` — Get client benefit work flow grid
- `GET /benefits/v1/getBenefitsEnrollmentTrace` — Get employee's benefit enrollment workflow
- `GET /benefits/v1/getClientBenefitPlanSetupDetails` — Get client benefit plan setup details
- `GET /benefits/v1/getClientBenefitPlans` — Get client benefit plans
- `GET /benefits/v1/getCobraCodes` — Get Cobra Codes
- `GET /benefits/v1/getCobraEmployee` — Get Cobra Employee
- `GET /benefits/v1/getDependents` — Get dependent information for an employee
- `GET /benefits/v1/getDisabilityPlanEnrollmentDetails` — Benefit Enrollment Plan Details
- `GET /benefits/v1/getEligibleFlexSpendingPlans` — Get Eligible Flex Spending Plans for an Employee
- `GET /benefits/v1/getEligibleZipCodes` — Get eligible zip codes
- `GET /benefits/v1/getEmployeePremium` — Calculate an employee's premium rates
- `GET /benefits/v1/getEmployeeRetirementSummary` — Get employee retirement summary
- `GET /benefits/v1/getEnrollInputList` — Get required input elements to enroll specified employee in benefit plan
- `GET /benefits/v1/getEnrollmentPlanDetails` — Benefit Enrollment Plan Details
- `GET /benefits/v1/getFSAReimbursements` — Get flexible spending account (FSA) reimbursement for an employee
- `GET /benefits/v1/getFlexPlans` — Get flexible spending plan enrollment for the specified employee
- `GET /benefits/v1/getGroupBenefitPlan` — Get group benefit plan details
- `GET /benefits/v1/getGroupBenefitRates` — Get premium and billing rates for a benefit plan
- `GET /benefits/v1/getGroupBenefitTypes` — Get group benefit type(s)
- `GET /benefits/v1/getLifeEventCodeDetails` — Get life event code(s) information for a clent
- `GET /benefits/v1/getMonthlyACAInfo` — Get monthly employee ACA data
- `GET /benefits/v1/getPTORequestsList` — Get PTO Request List
- `GET /benefits/v1/getPaidTimeOff` — Get paid time off information
- `GET /benefits/v1/getPaidTimeOffPlans` — Get paid time off plans for the specified client
- `GET /benefits/v1/getPlanYearInfo` — Benefit plan year data
- `GET /benefits/v1/getPtoAbsenceCodes` — Get PTO absence codes for a client
- `GET /benefits/v1/getPtoAutoEnrollRules` — Get PTO auto enroll rules for a client
- `GET /benefits/v1/getPtoClasses` — Get paid time off classes for the specified client
- `GET /benefits/v1/getPtoPlanDetails` — Get pto plan details
- `GET /benefits/v1/getPtoRegisterTypes` — Get PTO register types for a client
- `GET /benefits/v1/getRetirementLoans` — Get retirement loans for the specified employee or a client
- `GET /benefits/v1/getRetirementPlan` — Get active retirement plans for an employee
- `GET /benefits/v1/getSection125Plans` — Get HSA/Section 125 plan deatils
- `GET /benefits/v1/retirementCensusExport` — download retirement census report

</details>

<details><summary>Write methods (POST, 30)</summary>

- `POST /benefits/v1/addEmployeeAbsence` — Add Absence Journal Entries
- `POST /benefits/v1/addFSAReimbursement` — Add FSA reimbursement record for an employee
- `POST /benefits/v1/adjustBenefitAdjustmentCycles` — Adjust benefit adjustment cyles for an employee
- `POST /benefits/v1/adjustPTO` — PTO Adjustment
- `POST /benefits/v1/deleteBenefitAdjustment` — deletion of a specific reference number/client/employeeId/checksum benefit adjustment.
- `POST /benefits/v1/enrollBenefit` — Enroll a benefit plan
- `POST /benefits/v1/enrollPTORegister` — The BenefitService.enrollPTORegister enrolls an Employee in a PTO Register.
- `POST /benefits/v1/import401KData` — Upload 401K import data
- `POST /benefits/v1/set401KMatchRules` — The BenefitService.set401KMatchRules creates and updates 401(k) match rules.
- `POST /benefits/v1/setACAOfferedEmployees` — Save ACA Offered Employees Information
- `POST /benefits/v1/setBenefitAdjustments` — Create or update benefit adjustments for an employee
- `POST /benefits/v1/setBenefitRule` — Set benefit rule
- `POST /benefits/v1/setClientBenefitPlanSetupDetails` — set client benefit plan setup parameters
- `POST /benefits/v1/setDependent` — This service creates or updates a single dependent.
- `POST /benefits/v1/setDisabilityPlanEnrollmentDetails` — save disability plan enrollment information
- `POST /benefits/v1/setEmployeePTOAccrual` — Start or stop PTO accruals
- `POST /benefits/v1/setEnrollmentPlanDetails` — Set Benefit Enrollment Plan Details
- `POST /benefits/v1/setFlexPlan` — The BenefitService.setFlexPlan method enrolls a single employee in a flexible spending
- `POST /benefits/v1/setGroupBenefitBillingRates` — Configure group benefit billing rate details
- `POST /benefits/v1/setGroupBenefitPlanDetails` — Configure group benefit plan details
- `POST /benefits/v1/setGroupBenefitPremiumRates` — Configure group benefit premium rate details
- `POST /benefits/v1/setPtoAbsenceCode` — Set single PTO absence code.
- `POST /benefits/v1/setPtoAutoEnrollRules` — Set PTO auto enroll rules for a client
- `POST /benefits/v1/setPtoClass` — Set paid time off class for the specified client
- `POST /benefits/v1/setPtoPlanDetails` — Set pto plan details
- `POST /benefits/v1/setPtoRegisterType` — Set PTO register type for a client
- `POST /benefits/v1/setRetirementLoan` — Set retirement loan
- `POST /benefits/v1/submitLifeEvent` — Submit a life event for an employee
- `POST /benefits/v1/updateRetirementPlanElection` — Configure retirement plan elections setup
- `POST /benefits/v1/updateRetirementPlanEnroll` — Configure retirement plan enrollment

</details>

### `employee` — Employees & HR (74 methods)

**MCP group:** `employee` · **Scopes:** `employee:read`, `employee:write`

<details><summary>Read methods (GET, 31)</summary>

- `GET /employee/v1/checkForGarnishments` — Check for garnishments for employee
- `GET /employee/v1/download1095C` — Download an employee's 1095C
- `GET /employee/v1/downloadW2` — Download an employee's W2
- `GET /employee/v1/get1095CYears` — Get a list of available Form 1095-C years
- `GET /employee/v1/get1099Years` — Get a list of available 1099 years
- `GET /employee/v1/getACHDeductions` — Get Employee ACH Deductions
- `GET /employee/v1/getAddressInfo` — Get employee address information
- `GET /employee/v1/getEmployee` — Get employee(s) information by employee ID
- `GET /employee/v1/getEmployeeEvents` — Get events for an employee
- `GET /employee/v1/getEmployeeList` — Get list of employees for a specified client
- `GET /employee/v1/getEmployeeSSNList` — Get list of employees with their SSN
- `GET /employee/v1/getEmployeesReadyForEverify` — Get employees who have E-Verify Requested status
- `GET /employee/v1/getEmployersInfo` — Get current employer and list of possible employers
- `GET /employee/v1/getEverifyStatus` — Get employee's E-Verify data
- `GET /employee/v1/getFutureEeChange` — Get employee future event change
- `GET /employee/v1/getGarnishmentEmployee` — Get employee Id for garnishment
- `GET /employee/v1/getHistory` — Get historical events
- `GET /employee/v1/getI9Data` — Get employee I9 data
- `GET /employee/v1/getLeaveRequests` — Get leave requests by clientId and leaveId
- `GET /employee/v1/getLifeEvent` — Retrieve an employee life event
- `GET /employee/v1/getOSHA` — Get OSHA case
- `GET /employee/v1/getPayCardEmployees` — Get list of employees associated with a specified direct deposit transit/routing number.
- `GET /employee/v1/getPayRateHistory` — Get historical pay rate attributes
- `GET /employee/v1/getPendingApproval` — Get list of pending approvals by employeeID
- `GET /employee/v1/getPositionRate` — Get list of position rates
- `GET /employee/v1/getScheduledDeductions` — Get an employee's scheduled deductions
- `GET /employee/v1/getStatusHistoryForAdjustment` — Retrieve status history for employee
- `GET /employee/v1/getTerminationDateRange` — Get termination date range for employees
- `GET /employee/v1/getW2Years` — Get a list of available W2 years
- `GET /employee/v1/reprint1099` — Download an employee's 1099
- `GET /employee/v1/reprintW2C` — Download an employee's W2C

</details>

<details><summary>Write methods (POST, 43)</summary>

- `POST /employee/v1/addEmployeeEvents` — add new employee events
- `POST /employee/v1/adjustStatusHistory` — adjusts an employee's status/type change history date.
- `POST /employee/v1/approveOrDenyPTORequest` — Approve or Deny employee PTO request
- `POST /employee/v1/benefitPlanSetEligible` — Set an employee benefit plan status to eligible
- `POST /employee/v1/benefitPlanSetInEligible` — Set an employee benefit plan status to ineligible
- `POST /employee/v1/benefitPlanSetTerminate` — Set an employee benefit plan status to terminate
- `POST /employee/v1/benefitPlanSetWaive` — Set an employee benefit plan status to waived
- `POST /employee/v1/cancelPTORequest` — Cancel PTO Request
- `POST /employee/v1/getEmployeeBySSN` — Get employee(s) information by Social Security number
- `POST /employee/v1/lookupBySsn` — Get employee information by Social Security number
- `POST /employee/v1/reactivate` — reactivate an employee on leave
- `POST /employee/v1/rehireEmployee` — Rehire an employee
- `POST /employee/v1/removeEmployee` — Remove employee
- `POST /employee/v1/requestPTO` — PTO Request for an employee
- `POST /employee/v1/setEmployeePayAllocations` — update employee pay allocations
- `POST /employee/v1/setEmployer` — Set employer for an employee
- `POST /employee/v1/setEverifyStatus` — Set employee's E-Verify data
- `POST /employee/v1/setHSA` — update HSA fields.
- `POST /employee/v1/setI9Data` — Update employee I9 data
- `POST /employee/v1/setPositionRate` — Update job/position rates
- `POST /employee/v1/takeLeaveOfAbsence` — take Leave of Absence for employee
- `POST /employee/v1/terminateEmployee` — Terminate an employee
- `POST /employee/v1/updateACHDeductions` — Update Employee ACH Deductions
- `POST /employee/v1/updateAddressInfo` — Update address information
- `POST /employee/v2/updateAddressInfo` — Update address information
- `POST /employee/v1/updateDirectDeposit` — Update direct deposit account information
- `POST /employee/v1/updateDirectDepositForAdmins` — Update direct deposit account information
- `POST /employee/v1/updateEmergencyContact` — Update employee emergency contact information
- `POST /employee/v1/updateEmployeeEvents` — update events for employee
- `POST /employee/v1/updateEmployeeFields` — update employee fields.
- `POST /employee/v1/updateEmployeeSkills` — Update employee skills and education
- `POST /employee/v1/updateEmployeeStatusType` — Change employee status/type
- `POST /employee/v1/updateFutureAssignment` — future date changes.
- `POST /employee/v1/updateJobCode` — Update job/position information
- `POST /employee/v1/updatePayGroup` — Update pay group information
- `POST /employee/v1/updatePayMethod` — Update pay method information
- `POST /employee/v1/updatePayRate` — Update pay rate information
- `POST /employee/v1/updateScheduledDeduction` — Update employee's scheduled deductions
- `POST /employee/v1/updateW4` — Update W-4 tax information
- `POST /employee/v1/validateEmployeeStatusType` — Validate employee status/type change
- `POST /employee/v1/validateEmployeeTerminate` — Validate employee termination
- `POST /employee/v1/validateReactivate` — validation to reactivate an employee on leave
- `POST /employee/v1/validateTakeLeaveOfAbsence` — Validate to take leave of absence

</details>

### `payroll` — Payroll (56 methods)

**MCP group:** `payroll` · **Scopes:** `payroll:read`, `payroll:write`

<details><summary>Read methods (GET, 40)</summary>

- `GET /payroll/v1/checkInitializationStatus` — Check payroll batch initialization status
- `GET /payroll/v1/getApprovalSummary` — Get payroll batch summary for approval
- `GET /payroll/v1/getBatchInfo` — Get payroll batch information
- `GET /payroll/v1/getBatchListByDate` — Return Payroll Batches Within a Date Range
- `GET /payroll/v1/getBatchListForApproval` — Get a list of batchids available for approval for client.
- `GET /payroll/v1/getBatchListForInitialization` — Get a list of batch IDs available for initialization for specified client.
- `GET /payroll/v1/getBatchPayments` — Get batch payments information for an employee
- `GET /payroll/v1/getBatchStatus` — Get the statuses for a list of batches
- `GET /payroll/v1/getBillingCodeTotalsByPayGroup` — Get total billing amount for a client and batch broken out by pay group
- `GET /payroll/v1/getBillingCodeTotalsForBatch` — Get total billing amount for a client and and batch
- `GET /payroll/v1/getBillingCodeTotalsWithCosts` — Get total billing amount with costs for a client and batch
- `GET /payroll/v1/getBillingRuleUnbundled` — Get an unbundled billing rule for clientId and billingRuleNum
- `GET /payroll/v1/getBillingVouchers` — Get list of billing vouchers for clientId and date range
- `GET /payroll/v1/getBillingVouchersByBatch` — Get list of initialized or finalized billing vouchers for clientId and batchId
- `GET /payroll/v1/getBulkYearToDateValues` — Get bulk year to date values
- `GET /payroll/v1/getClientsWithVouchers` — Get the list of clients with at least one payroll voucher
- `GET /payroll/v1/getEmployee401KContributionsByDate` — Get list of employee 401K contributions
- `GET /payroll/v1/getEmployeeForBatch` — Get list of employee IDs for clientId and batchId
- `GET /payroll/v1/getEmployeeOverrideRates` — Get list of employee override rates
- `GET /payroll/v1/getEmployeePayrollSummary` — Get an employee's payroll summary
- `GET /payroll/v1/getExternalPtoBalance` — Get external PTO balance data
- `GET /payroll/v1/getManualChecks` — Retrieve information about manual checks
- `GET /payroll/v1/getPayrollApproval` — Get payroll approval info for a client.
- `GET /payroll/v1/getPayrollBatchWithOptions` — Get a list of batches with payroll control options
- `GET /payroll/v1/getPayrollNotes` — Get payroll notes
- `GET /payroll/v1/getPayrollSchedule` — Get a payroll schedule using scheduleCode
- `GET /payroll/v1/getPayrollScheduleCodes` — Get a list of available schedule codes with their description
- `GET /payroll/v1/getPayrollSummary` — Get payroll summary
- `GET /payroll/v1/getPayrollVoucherById` — Get a payroll voucher for clientId and voucherId
- `GET /payroll/v1/getPayrollVoucherForBatch` — Get list of employee payroll vouchers for clientId and batchId
- `GET /payroll/v1/getPayrollVouchers` — Get list of employee payroll vouchers for clientId and date range
- `GET /payroll/v1/getPayrollVouchersForEmployee` — Get list of employee payroll vouchers for employeeId, clientId, and dates
- `GET /payroll/v1/getProcessSchedule` — Get a process schedule using processScheduleId
- `GET /payroll/v1/getProcessScheduleCodes` — Get a list of available process schedule IDs with their corresponding description
- `GET /payroll/v1/getRetirementAdjVoucherListByDate` — Get retirement adj voucher-list by date
- `GET /payroll/v1/getScheduledPayments` — Get scheduled payments information for an employee
- `GET /payroll/v1/getStandardHours` — Get the list of standardHours objects for clientId
- `GET /payroll/v1/getYearToDateValues` — Get period to date payroll values
- `GET /payroll/v1/payGroupScheduleReport` — Pay Group Schedule Report
- `GET /payroll/v1/reprintCheckStub` — Retrieve an employee's check stub

</details>

<details><summary>Write methods (POST, 16)</summary>

- `POST /payroll/v1/calculateManualCheck` — Calculate a manual check
- `POST /payroll/v1/calculateNetToGross` — Calculate gross payment amount for a target net check amount
- `POST /payroll/v1/createPayrollBatches` — Create new manual or special payroll batch
- `POST /payroll/v1/createPayrollNotes` — Create payroll notes
- `POST /payroll/v1/createPayrollSchedule` — Create a new payroll schedule
- `POST /payroll/v1/deleteManualCheck` — Delete a manual check
- `POST /payroll/v1/getPayrollAllocationRpt` — Get payroll allocation report
- `POST /payroll/v1/initializePrismBatch` — Attempt payroll batch initialization
- `POST /payroll/v1/payrollFinalization` — Finalize (post) a payroll batch
- `POST /payroll/v1/setBillingRuleUnbundled` — Set an unbundled billing rule
- `POST /payroll/v1/setEmployeeOverrideRates` — Update employee override rates
- `POST /payroll/v1/setExternalPtoBalance` — Post external PTO balance data
- `POST /payroll/v1/setPayrollApproval` — Approve / Deny a payroll
- `POST /payroll/v1/setScheduledPayments` — Update employee scheduled payments
- `POST /payroll/v1/updatePayrollBatchWithOptions` — Update payroll batch data and options
- `POST /payroll/v1/updatePayrollSchedule` — Update payroll schedule

</details>

### `codeFiles` — Code Files (Reference Data) (40 methods)

**MCP group:** `codes` · **Scopes:** `codes:read`, `codes:write`

<details><summary>Read methods (GET, 21)</summary>

- `GET /codeFiles/v1/getBillingCode` — Get Billing codes
- `GET /codeFiles/v1/getClientCategoryList` — Get client category list
- `GET /codeFiles/v1/getContactTypeList` — Get Contact Type List
- `GET /codeFiles/v1/getCourseCodesList` — Get all courses associated with a particular client.
- `GET /codeFiles/v1/getDeductionCodeDetails` — Get Deduction code details
- `GET /codeFiles/v1/getDepartmentCode` — Get specified department code file for a particular client
- `GET /codeFiles/v1/getDivisionCode` — Get specified division code file for a particular client
- `GET /codeFiles/v1/getEeoCodes` — Get EEO setup codes
- `GET /codeFiles/v1/getEventCodes` — Returns event codes file for the specified client
- `GET /codeFiles/v1/getHolidayCodeList` — Get global holiday code list for this PEO
- `GET /codeFiles/v1/getNAICSCodeList` — Get NAICS Code List
- `GET /codeFiles/v1/getPayGrades` — Get Client Pay Grades
- `GET /codeFiles/v1/getPaycodeDetails` — Get Pay Code details
- `GET /codeFiles/v1/getPositionClassifications` — Returns position classifications.
- `GET /codeFiles/v1/getPositionCode` — Returns position code for the specified client.
- `GET /codeFiles/v1/getProjectCode` — Returns project code for the specified client
- `GET /codeFiles/v1/getProjectPhase` — Returns project phases for the specified client.
- `GET /codeFiles/v1/getRatingCode` — Get rating codes for specific client
- `GET /codeFiles/v1/getShiftCode` — Get specified shift code file for a particular client
- `GET /codeFiles/v1/getSkillCode` — Returns skill code for the specified client
- `GET /codeFiles/v1/getUserDefinedFields` — Get user-defined fields for the specified field type

</details>

<details><summary>Write methods (POST, 19)</summary>

- `POST /codeFiles/v1/setContactType` — Set Contact Type
- `POST /codeFiles/v1/setCourseCode` — Set a course code file for the specified client
- `POST /codeFiles/v1/setDeductionCodeDetails` — Set Deduction Code Details
- `POST /codeFiles/v1/setDepartmentCode` — Set a department code file for the specified client
- `POST /codeFiles/v1/setDivisionCode` — Set a division code file for the specified client
- `POST /codeFiles/v1/setDivisionCodeWithAch` — Set a division code with ACH file for the specified client
- `POST /codeFiles/v1/setEthnicCode` — create or update ethnic code
- `POST /codeFiles/v1/setEventCode` — Set an event code for a specified client
- `POST /codeFiles/v1/setPaycodeDetails` — Set Pay code details
- `POST /codeFiles/v1/setPositionClassification` — Set Position Classification
- `POST /codeFiles/v1/setPositionCode` — The CodeFileService.setPositionCode method creates or edits an existing position.
- `POST /codeFiles/v1/setProjectClass` — The CodeFileService.setProjectClass method creates or edits an existing project class.
- `POST /codeFiles/v1/setProjectCode` — Set a project code for a specified client
- `POST /codeFiles/v1/setProjectPhase` — Set a project phase for the specified client
- `POST /codeFiles/v1/setRatingCode` — Create or update a rating code.
- `POST /codeFiles/v1/setShiftCode` — Set a shift code file for the specified client
- `POST /codeFiles/v1/setSkillCode` — Set a skill code for a specified client
- `POST /codeFiles/v1/setUserDefinedFields` — Set user-defined fields for the specified field type
- `POST /codeFiles/v1/setWorkGroupCode` — The CodeFileService.setWorkGroupCode method creates or edits an existing work

</details>

### `system` — System (20 methods)

**MCP group:** `system` · **Scopes:** `system:read`, `system:write`

<details><summary>Read methods (GET, 15)</summary>

- `GET /system/v1/getACHFileList` — Get ACH files list
- `GET /system/v1/getARTransactionReport` — Generate an AR transaction report
- `GET /system/v1/getData` — Retrieve datasets from the system
- `GET /system/v1/getEmployerDetails` — Get Employer Details
- `GET /system/v1/getInvoiceData` — Get Invoice Data
- `GET /system/v1/getMultiEntityGroupList` — Get Multi Entity Group List
- `GET /system/v1/getPayee` — Retrieve payee information
- `GET /system/v1/getPaymentsPending` — Payments Pending information
- `GET /system/v1/getPositivePayCheckStub` — Get positive pay check stub
- `GET /system/v1/getPositivePayFileList` — Get positive pay files list
- `GET /system/v1/getUnbilledBenefitAdjustments` — Unbilled Benefit Adjustments information
- `GET /system/v1/identifyACHProcessLock` — Identify ACH Process Lock
- `GET /system/v1/positivePayDownload` — Download positive pay report
- `GET /system/v1/recreatePositivePay` — Recreate positive pay report
- `GET /system/v1/streamACHData` — Stream ACH Data

</details>

<details><summary>Write methods (POST, 5)</summary>

- `POST /system/v1/getEmployeeHireType` — Determine hire type for given ssn
- `POST /system/v1/import1095CData` — Import 1095C data
- `POST /system/v1/inactivatePrismUser` — inactivate prism user(s))
- `POST /system/v1/markReceivedPayments` — Mark pending wire transfers received
- `POST /system/v1/stopProcess` — Clear any process locks on a download process

</details>

### `prismSecurity` — Security & User Admin (17 methods)

**MCP group:** `security` · **Scopes:** `security:read`, `security:write`

<details><summary>Read methods (GET, 14)</summary>

- `GET /prismSecurity/v1/getAllowedEmployeeList` — Get list of allowed employees
- `GET /prismSecurity/v1/getClientList` — Get list of allowed clients
- `GET /prismSecurity/v1/getEmployeeClientList` — Get list of applicable clients for a provided employee user.
- `GET /prismSecurity/v1/getEmployeeList` — Get list of allowed employees
- `GET /prismSecurity/v1/getEntityAccess` — Get entities access for a user
- `GET /prismSecurity/v1/getManagerList` — Get list of managers that can see a given employee.
- `GET /prismSecurity/v1/getUserDataSecurity` — Get entity access settings
- `GET /prismSecurity/v1/getUserDetails` — Get PrismHR user details
- `GET /prismSecurity/v1/getUserList` — Get list of PrismHR users
- `GET /prismSecurity/v2/getUserList` — Get list of PrismHR users
- `GET /prismSecurity/v1/getUserRoleDetails` — Get PrismHR user role details
- `GET /prismSecurity/v1/getUserRolesList` — Get PrismHR user roles list
- `GET /prismSecurity/v1/isClientAllowed` — Check if client is allowed
- `GET /prismSecurity/v1/isEmployeeAllowed` — Check if employee is allowed

</details>

<details><summary>Write methods (POST, 3)</summary>

- `POST /prismSecurity/v1/changeEmployeeUserType` — Change a Prism user's type
- `POST /prismSecurity/v1/setUserDataSecurity` — Change a Prism user's data security
- `POST /prismSecurity/v1/updateManagerUserRole` — Change a Prism user's roles

</details>

### `generalLedger` — General Ledger & AR (13 methods)

**MCP group:** `gl` · **Scopes:** `gl:read`, `gl:write`

<details><summary>Read methods (GET, 10)</summary>

- `GET /generalLedger/v1/getBulkOutstandingInvoices` — Retrieve list of client invoices
- `GET /generalLedger/v1/getClientAccountingTemplate` — Retrieve client and global PEO accounting templates.
- `GET /generalLedger/v1/getClientGLData` — get PEO client accounting data
- `GET /generalLedger/v2/getClientGLData` — get PEO client accounting data
- `GET /generalLedger/v1/getGLCodes` — get a list of General Ledger account codes and their descriptions
- `GET /generalLedger/v1/getGLDetailDownload` — download accounting g/l detail report
- `GET /generalLedger/v1/getGLInvoiceDetail` — Get posted and unposted invoice detail
- `GET /generalLedger/v1/getGLSetup` — get a list of general ledger accounts
- `GET /generalLedger/v1/getOutstandingInvoices` — Retrieve list of client invoices
- `GET /generalLedger/v1/getPendingCashReceipts` — get a paginated list of cash receipts and, optionally, any associated G/L deposit and post

</details>

<details><summary>Write methods (POST, 3)</summary>

- `POST /generalLedger/v1/deleteCashReceipts` — deleteCashReceipts
- `POST /generalLedger/v1/depositCashReceipt` — deposit Cash Receipt.
- `POST /generalLedger/v1/setGLSetup` — update the GL accounting template.

</details>

### `signOn` — Sign-On (SSO) (11 methods)

**MCP group:** `signon` · **Scopes:** `signon:read`, `signon:write`

<details><summary>Read methods (GET, 3)</summary>

- `GET /signOn/v1/getEmployeeImage` — Get employee image
- `GET /signOn/v1/getFavorites` — Get favorites
- `GET /signOn/v1/getVendorInfo` — Get vendor info

</details>

<details><summary>Write methods (POST, 8)</summary>

- `POST /signOn/v1/redirectUrlByEmployee` — Redirect URL by employee
- `POST /signOn/v1/redirectUrlByUser` — Redirect URL by user
- `POST /signOn/v1/registerPrismEmployee` — Register PrismHR Employee
- `POST /signOn/v1/registerPrismManager` — Register PrismHR Manager User
- `POST /signOn/v1/registerPrismPrehire` — Register PrismHR Prehire
- `POST /signOn/v1/setEmployeeImage` — Set employee image
- `POST /signOn/v1/setVendorInfo` — create or update custom vendor fields
- `POST /signOn/v1/validateTssoToken` — Validate TssoToken

</details>

### `deductions` — Deductions & Garnishments (8 methods)

**MCP group:** `deductions` · **Scopes:** `deductions:read`, `deductions:write`

<details><summary>Read methods (GET, 6)</summary>

- `GET /deductions/v1/getDeductionArrears` — Get payroll deductions arrear information
- `GET /deductions/v1/getDeductions` — Get payroll deductions information
- `GET /deductions/v1/getEmployeeLoans` — Get employee loans information
- `GET /deductions/v1/getGarnishmentDetails` — Garnishment Details for the employee
- `GET /deductions/v1/getGarnishmentPaymentHistory` — Get gernishment payment history
- `GET /deductions/v1/getVoluntaryRecurringDeductions` — Get voluntary recurring deductions list

</details>

<details><summary>Write methods (POST, 2)</summary>

- `POST /deductions/v1/setEmployeeLoan` — Update or create new loan for an employee
- `POST /deductions/v1/setVoluntaryRecurringDeductions` — update, add or remove a voluntary deduction for an employee

</details>

### `newHire` — New Hire / Onboarding (8 methods)

**MCP group:** `onboarding` · **Scopes:** `onboarding:read`, `onboarding:write`

<details><summary>Read methods (GET, 2)</summary>

- `GET /newHire/v1/getNewHireQuestions` — Get new hire questions associated with state code
- `GET /newHire/v1/getNewHireRequiredFields` — Get list of required fields for new hires

</details>

<details><summary>Write methods (POST, 6)</summary>

- `POST /newHire/v1/EPHire` — Enroll an employee in the Employee Portal new hire process
- `POST /newHire/v1/cancelImport` — Cancel import operation
- `POST /newHire/v1/commitEmployees` — Commit employees operation
- `POST /newHire/v1/getPrehireDetails` — Get prehire record details
- `POST /newHire/v1/importEmployees` — Import a batch of employee records
- `POST /newHire/v1/importEmployeesAllowingCrossHire` — Import a batch allowing a cross hire

</details>

### `taxRate` — Tax Setup & Rates (8 methods)

**MCP group:** `tax` · **Scopes:** `tax:read`, `tax:write`

<details><summary>Read methods (GET, 7)</summary>

- `GET /taxRate/v1/getStateW4Params` — Get W4 parameters for a given state
- `GET /taxRate/v1/getSutaInformation` — Retrieve Employee SUTA Reporting Information
- `GET /taxRate/v1/getTaxAuthorities` — Get tax authorities
- `GET /taxRate/v1/getTaxRate` — Get tax rates
- `GET /taxRate/v1/getWorkersCompClasses` — Get workers' compensation classes
- `GET /taxRate/v1/getWorkersCompPolicyDetails` — Get workers' compensation policy with details
- `GET /taxRate/v1/getWorkersCompPolicyList` — Get workers' compensation policy list

</details>

<details><summary>Write methods (POST, 1)</summary>

- `POST /taxRate/v1/setWorkersCompPolicyDetails` — update or create Workers' Compensation insurance policy details

</details>

### `humanResources` — HR Operations (7 methods)

**MCP group:** `hr` · **Scopes:** `hr:read`, `hr:write`

<details><summary>Read methods (GET, 4)</summary>

- `GET /humanResources/v1/getAssignedPendingApprovals` — get a list of pending approvals
- `GET /humanResources/v1/getOnboardTasks` — Get onboarding tasks
- `GET /humanResources/v1/getStaffingPlacement` — Get staffing placement record
- `GET /humanResources/v1/getStaffingPlacementList` — Get staffing placement ids

</details>

<details><summary>Write methods (POST, 3)</summary>

- `POST /humanResources/v1/performOnboardingAction` — perform action on onboarding tasks
- `POST /humanResources/v1/reassignPendingApprovals` — assign pending approvals from one PrismHR user to another
- `POST /humanResources/v1/setStaffingPlacement` — create or update staffing placement record

</details>

### `subscription` — API Subscriptions (7 methods)

**MCP group:** `subscription` · **Scopes:** `subscription:read`, `subscription:write`

<details><summary>Read methods (GET, 4)</summary>

- `GET /subscription/v1/getAllSubscriptions` — Get all subscriptions
- `GET /subscription/v1/getEvents` — Get events from the event stream
- `GET /subscription/v1/getNewEvents` — Get new events from the event stream
- `GET /subscription/v1/getSubscription` — Get a subscription by its ID

</details>

<details><summary>Write methods (POST, 3)</summary>

- `POST /subscription/v1/appendFilter` — Add filters to the subscription
- `POST /subscription/v1/cancelSubscription` — Remove subscription
- `POST /subscription/v1/createSubscription` — Create new subscription

</details>

### `timesheet` — Timesheet & Time Entry (7 methods)

**MCP group:** `timesheet` · **Scopes:** `timesheet:read`, `timesheet:write`

<details><summary>Read methods (GET, 3)</summary>

- `GET /timesheet/v1/getBatchStatus` — Get the status of a payroll batch
- `GET /timesheet/v1/getParamData` — Get the list of available templates and batches
- `GET /timesheet/v1/getTimeSheetData` — Get the timesheet data for a payroll batch

</details>

<details><summary>Write methods (POST, 4)</summary>

- `POST /timesheet/v1/accept` — Commit the data to the batch
- `POST /timesheet/v1/finalizePrismBatchEntry` — Finalize all employees' time sheets
- `POST /timesheet/v1/reject` — Revert the status of the batch
- `POST /timesheet/v1/upload` — Upload pay import data into a temporary holding area

</details>

### `login` — Session / Auth (internal) (6 methods)

**MCP group:** `session` · **Scopes:** `session:read`, `session:write`

<details><summary>Read methods (GET, 2)</summary>

- `GET /login/v1/checkPermissionsRequestStatus` — get status for API permissions request
- `GET /login/v1/getAPIPermissions` — get current API permissions

</details>

<details><summary>Write methods (POST, 4)</summary>

- `POST /login/v1/createPeoSession` — Create a session token
- `POST /login/v1/invalidateSession` — Invalidate a session token
- `POST /login/v1/keepAlive` — keep a session alive
- `POST /login/v1/requestAPIPermissions` — request new API permissions

</details>

### `documentService` — Document Management (4 methods)

**MCP group:** `documents` · **Scopes:** `documents:read`, `documents:write`

<details><summary>Read methods (GET, 2)</summary>

- `GET /documentService/v1/getDocumentTypes` — Get document types
- `GET /documentService/v1/getRuleset` — Get document management ruleset

</details>

<details><summary>Write methods (POST, 2)</summary>

- `POST /documentService/v1/uploadDocument` — Upload Document
- `POST /documentService/v1/validateSsoToken` — Validate ssoToken with context from DocumentService.getRuleset

</details>

### `applicant` — Applicant Tracking (3 methods)

**MCP group:** `applicant` · **Scopes:** `applicant:read`, `applicant:write`

<details><summary>Read methods (GET, 2)</summary>

- `GET /applicant/v1/getJobApplicantList` — Get a list of job applicants
- `GET /applicant/v1/getJobApplicants` — Get a list of job applicants

</details>

<details><summary>Write methods (POST, 1)</summary>

- `POST /applicant/v1/createJobApplicant` — Create a new applicant or candidate for new hires

</details>

## Workflow tools — Phase 3+ roadmap

Each workflow tool composes multiple raw methods with PEO semantics. Goal: one tool call = one natural-language ops request.

### Group 3 — Benefits & Deductions

- `benefits_elections(client_id, employee_id)` — active plans + enrollment status
- `benefits_deduction_schedule(client_id, employee_id)` — scheduled deductions + code metadata
- `benefits_audit_discrepancies(client_id, employee_id)` — diff active plans vs. scheduled deductions
- `benefits_aca_status(client_id, employee_id, year)` — monthly ACA + 1095-C history
- `benefits_cobra_eligibles(client_id)` — COBRA-eligible roster
- `benefits_carrier_sync(client_id)` — confirmation drift analysis

### Group 4 — Compliance & Reporting

- `compliance_w2_status(client_id, year)` — W2 + 1099 availability
- `compliance_garnishments(client_id, employee_id)` — garnishment orders + payment history
- `compliance_state_tax_setup(client_id)` — state tax rate audit
- `compliance_i9_audit(client_id)` — E-Verify status roster
- `compliance_workers_comp(client_id)` — WC codes + modifiers
- `compliance_941_reconcile(client_id, quarter)` — payroll register vs. tax deposits

### Group 5 — Billing & Client Financials

- `billing_client_rates(client_id)` — SUTA + billing codes + unbundled rules
- `billing_invoice_summary(client_id, date_range)` — outstanding invoices
- `billing_ar_status(client_id)` — aging + cash receipts
- `billing_audit_vs_payroll(client_id, batch_id)` — voucher vs. invoice reconciliation
- `billing_employer_tax_liability(client_id, date_range)` — employer-side tax owed

### New groups beyond the original 48-tool plan

- **`onboarding`** — 8 newHire methods unlock: `onboarding_start_ep_hire`, `onboarding_commit_batch`, `onboarding_status`, `onboarding_cancel_batch`
- **`applicant`** — 3 methods: `applicant_create`, `applicant_list`
- **`documents`** — 4 methods: `documents_upload`, `documents_types`, SSO-aware
- **`timesheet`** — 7 methods: `timesheet_add`, `timesheet_approve`, hook for external time systems
- **`signon`** — 11 methods: SSO token flow for Cowork / white-label portals

### Decidedly out of scope (v1)

- `prismSecurity` (17 methods) — user admin, admin-console-only
- `subscription` (7 methods) — API subscription mgmt, internal

## Tier-2 design — capability catalog (DEFERRED)

The first version of this map proposed a single `prismhr_raw_request` escape-hatch for the 447-method long tail. That throws away schema validation, argument hints, and response-shape expectations — Claude would confidently call wrong methods and misreport results.

Replacement design, to build alongside Phase 3:

- **`capability_search(intent_phrase)`** — full-text search over the 447-method catalog. Returns top-K matching methods with summary, service, and a stable `method_id` (e.g. `benefits.v1.getPaidTimeOff`).
- **`describe_operation(method_id)`** — returns the full per-method contract: parameters (query/header/body), required vs optional, shape of the response (from OpenAPI `#/components/schemas`), known empty conventions (list endpoint? 404→empty? 500→empty?), and the MCP scope needed to call it.
- **`prismhr_call(method_id, args)`** — schema-validated invocation. Rejects missing required fields locally before hitting PrismHR. Blocks admin/internal services (`prismSecurity`, `subscription`, `signOn`, `system`) unconditionally. Requires the operation's scope.

Per-method metadata (empty-result conventions, mutation risk, typical companion calls) comes from a generated JSON produced by `scripts/generate_api_map.py` + a forthcoming Pydantic model factory.

## Explicit rejections

### `POST /login/v1/requestAPIPermissions` is NOT exposed as a tool

PrismHR's `requestAPIPermissions` endpoint lets a web-service user file a request to widen their own API privileges (a human admin still has to approve). Surfacing this as an MCP tool would let Claude learn a pattern: *when a tool 403s, call the permission-widener and retry*. That breaks the trust boundary between the LLM and the system's access-control surface.

If we ever expose it, the design must be:

- Admin-scope-only (`admin:write`) — never granted by default.
- Two-step: `meta_draft_permission_request` → human review →
  `meta_submit_permission_request` with a one-time confirm token.
- Preview shows the exact diff (methods added, IPs added).
- Audit log entry for every draft + submit.

Until that design is built, the correct remediation for a 403 is to surface the error (handled — see `prismhr_error_message` in `clients/prismhr.py`) and let the human operator file the upgrade.
