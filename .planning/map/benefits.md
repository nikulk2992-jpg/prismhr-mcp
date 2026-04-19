# Service: `benefits`

**77 methods** in this service.

## `GET /benefits/v1/benefitEnrollmentStatus`
**Operation:** `benefitEnrollmentStatus`

**Summary:** Benefit Enrollment Status

**Description:** This operation returns web enrollment configuration details for a specified client. You can filter the response to a specific employee ID or enrollment type (Benefit Enrollment, Open Enrollment, Anytime Enrollment, Life Event). This operation also returns paginated results. Use the count and startpage request parameters to navigate through the list of records. count specifies the number of records to return per page, and startpage indicates the starting position in the list of enrollment records. The operation returns these parameters in the response object as well, along with the total number…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, optional) — return only records for the specified employee
- `enrollmentType` (query, optional) — return only records from a specific enrollment type; if empty, all enrollment records are returned; allowed values: "BE" (Benefits Enrollment), "OE" (Open Enrollment), "AE" (Anytime Enrollment), "LE" (Life Event)
- `count` (query, optional) — number of enrollment records returned per page (default: 5000)
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `BenefitEnrollmentStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/get401KMatchRules`
**Operation:** `get401KMatchRules`

**Summary:** Get client's 401(k) match rules

**Description:** This method retrieves a client's 401(k) match rules.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `benefitGroupId` (query, required) — benefit group identifier
- `retirementPlanId` (query, required) — retirement plan identifier
- `effectiveDate` (query, optional) — YYYY-MM-DD formatted string

**Responses:**
- `200` — successful operation → `GetRetirement401KMatchRulesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getACAOfferedEmployees`
**Operation:** `getACAOfferedEmployees`

**Summary:** Get ACAOffered Employees

**Description:** Use this operation to retrieve data about variable hour employees who are set up to be offered benefits. This data can be set up on the ACA Offered Employees form in PrismHR, or by calling BenefitService.setACAOfferedEmployees. This operation returns paginated results. Use the count and startpage query parameters to navigate through the list of employees. count specifies the number of employees to return per page, and startpage indicates the starting position in the employee list. The operation returns these parameters in the response object as well, along with the total number of employees.

**Parameters:**
- `sessionId` (header, required) — Session Token
- `clientId` (query, required) — client identifier
- `employeeId` (query, optional) — employee identifier
- `count` (query, optional) — number of employees returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetACAOfferedEmployeesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getAbsenceJournal`
**Operation:** `getAbsenceJournal`

**Summary:** Get absence journals

**Description:** This operation returns absence journal information for the specified journal(s) and client; specify up to 20 absence journals. Use EmployeeService.getEmployee with the AbsenceJournal option to retrieve journal IDs for specific employees.

**Parameters:**
- `sessionId` (header, required) — session token
- `journalId` (query, required) — absence journal identifier(s)
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `AbsenceJournalResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

**Related:** [[getAbsenceJournalByDate]]

---

## `GET /benefits/v1/getAbsenceJournalByDate`
**Operation:** `getAbsenceJournalByDate`

**Summary:** Get absence journals by Date

**Description:** This operation returns a list of absence journals for a specific date range for a specific client. You can filter the response to a specific employee ID. The maximum date range will be a year (for example 2024-04-01 to 2025-03-31).Both the journalDateStart and journalDateEnd fields are required. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of absence journals.count specifies the number of absence journals to return per page, and startpage indicates the starting position in the absence journal list. The operation return…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, optional) — return only records for the specified employee
- `journalDateStart` (query, required) — absence journals date range starting date (format: YYYY-MM-DD)
- `journalDateEnd` (query, required) — absence journals date range ending date (format: YYYY-MM-DD)
- `count` (query, optional) — number of absence journal records returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `AbsenceJournalResponseWithDate`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getActiveBenefitPlans`
**Operation:** `getActiveBenefitPlans`

**Summary:** Get active plan(s) for an employee

**Description:** This operation return the benefit plan(s) that are currently active for the specified employee. You can specify an effectiveDate to use in this calculation; if it is left empty, then the current date is used. You can also specify a specific planId to return; if left empty, then an array (list) of all the plans is returned.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `planId` (query, optional) — list of benefit plan IDs
- `effectiveDate` (query, optional) — YYYY-MM-DD formatted string

**Responses:**
- `200` — successful operation → `GetBenefitPlansResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getAvailableBenefitPlans`
**Operation:** `getAvailableBenefitPlans`

**Summary:** Get available benefit plans for the specified employee

**Description:** This operation returns available benefit plans for the specified employee, including the employee's status in those plans (eligible, enrolled, and so on).

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `AvailableBenefitPlansResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getBenefitAdjustments`
**Operation:** `getBenefitAdjustments`

**Summary:** Get benefit adjustment information for a specified employee

**Description:** This operation retrieves benefit adjustment information for a specified employee.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier associated with the employee
- `employeeId` (query, required) — employee whose benefits adjustments should be retrieved

**Responses:**
- `200` — successful operation → `GetBenefitAdjustmentsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getBenefitConfirmationData`
**Operation:** `getBenefitConfirmationData`

**Summary:** Downloads benefits confirmation statement

**Description:** Note: Web Service Users cannot call multiple concurrent instances of this method. Please wait until the first instance returns a buildStatus of "DONE," retrieve your download link, and then, if necessary, invoke this method again. If you try to call a second instance before the first one completes, the system will return HTTP response code 429 and you must complete the previous instance using the downloadId provided before initiating a new instance. Use this operation to return detailed benefit confirmation data associated with a particular client, employee, and benefit confirmation number. Yo…

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — identifier used to check status of / download data
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `confirmNum` (query, required) — benefits confirmation code

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getBenefitConfirmationList`
**Operation:** `getBenefitConfirmationList`

**Summary:** Get a list of benefit confirmation

**Description:** This operation returns all Benefit Confirmation numbers for a given client and employee, along with the date of confirmation. You can also filter the response to a specific year. To retrieve specific data about employee Benefit Confirmations, use this in conjunction with BenefitService.getBenefitConfirmationData.

**Parameters:**
- `sessionId` (header, required) — session token
- `employeeId` (query, required) — Employee Identifier
- `clientId` (query, required) — Client Identifier
- `year` (query, optional) — Specify a year (in YYYY format) to only return confirmations from that year, or leave blank to return confirmations from all years

**Responses:**
- `200` — successful operation → `BenefitConfirmationListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getBenefitPlanList`
**Operation:** `getBenefitPlanList`

**Summary:** Get a list of group benefit plans

**Description:** The BenefitService.getBenefitPlanList operation returns a list of system level benefit plans.

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `BenefitPlanListResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getBenefitPlans`
**Operation:** `getBenefitPlans`

**Summary:** Get benefit plans for the specified employee

**Description:** This operation returns benefit plan(s) for the specified employee (regardless of their status). You can specify one or more planIds to return; if left empty, then an array (list) of all the plans is returned.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `planId` (query, optional) — list of benefit plan IDs

**Responses:**
- `200` — successful operation → `GetBenefitPlansResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getBenefitRule`
**Operation:** `getBenefitRule`

**Summary:** Get benefit rule

**Description:** This method returns a client's Benefit Rules information. Benefit rules establish the conditions that a client's employees must satisfy to enroll in a benefit plan: group benefit plans, retirement plans, flexible spending, and so on. To retrieve a list of current client benefit groups, use ClientMasterService.getClientCodes and use BenefitGroup as the option.If you do not specify a groupPlanId, then the method returns benefit rule information for all groups and any employee benefit rule overrides. Note that, for an employee override, the employee ID populates the benefitGroupId field in the re…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `groupPlanId` (query, optional) — identifier for client's benefit group, or employee ID if the rule is an employee-specific override
- `planId` (query, optional) — identifier for the group benefit plan
- `effectiveDate` (query, optional) — (format YYYY-MM-DD)
- `useActualEffectiveDate` (query, optional) — when calculating contributions, whether to use the current effective date (false, default behavior) or the effective date of each individual benefit rule (true) which will be returned in the historicalRule array when there are rates subsequent to the effective date

**Responses:**
- `200` — successful operation → `BenefitRuleResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getBenefitWorkflowGrid`
**Operation:** `getBenefitWorkflowGrid`

**Summary:** Get client benefit work flow grid

**Description:** Use this operation to retrieve the fields in the client benefit workflow grid. Depending on the input, this method can return data for workflows with specific start dates at the client level and/or the system level. Note: Web Service Users cannot call multiple concurrent instances of this method. Please wait until the first instance returns a buildStatus of "DONE," retrieve your download link, and then, if necessary, invoke this method again. If you try to call a second instance before the first one completes, the system will return HTTP response code 429 and you must complete the previous ins…

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — identifier used to check status of / download data
- `clientId` (query, optional) — client identifier
- `workflowEffDate` (query, optional) — YYYY-MM-DD formatted string
- `workflowLevel` (query, optional) — workflow level: system-level (S), client-level (C), or both (B)
- `oeStartDate` (query, optional) — YYYY-MM-DD formatted string
- `oeEndDate` (query, optional) — YYYY-MM-DD formatted string

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getBenefitsEnrollmentTrace`
**Operation:** `getBenefitsEnrollmentTrace`

**Summary:** Get employee's benefit enrollment workflow

**Description:** Use this operation to return the steps in an employee's benefit enrollment workflow. This operation returns up to 5000 lines of trace data

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `BenefitsEnrollmentTrace`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getClientBenefitPlanSetupDetails`
**Operation:** `getClientBenefitPlanSetupDetails`

**Summary:** Get client benefit plan setup details

**Description:** This method returns benefit plan details for the specified client, plan, and plan classification

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `planId` (query, required) — plan identifier
- `planClass` (query, required) — plan classification must be one of: 'G' (Group Benefits), 'R' (Retirement), 'F' (Flex Spending), 'M' (Employer Match), or 'H' (HSA)

**Responses:**
- `200` — successful operation → `BenefitPlanDetailResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getClientBenefitPlans`
**Operation:** `getClientBenefitPlans`

**Summary:** Get client benefit plans

**Description:** This method returns all benefit plans available to a client, (regardless of their status).

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `ClientBenefitPlanOverview`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

**Related:** [[getClientBenefitPlanSetupDetails]]

---

## `GET /benefits/v1/getCobraCodes`
**Operation:** `getCobraCodes`

**Summary:** Get Cobra Codes

**Description:** Use this operation to return list of qualifying events and termination reasons found in the Cobra processing parameters.

**Parameters:**
- `sessionId` (header, required) — Session Token

**Responses:**
- `200` — successful operation → `CobraCodesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getCobraEmployee`
**Operation:** `getCobraEmployee`

**Summary:** Get Cobra Employee

**Description:** Use this operation to return COBRA benefit plan enrollment information about qualified employees.

**Parameters:**
- `sessionId` (header, required) — Session Token
- `employeeId` (query, required) — Employee Identifier

**Responses:**
- `200` — successful operation → `CobraEmployeeDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getDependents`
**Operation:** `getDependents`

**Summary:** Get dependent information for an employee

**Description:** This operation returns information about the specified employee's dependents. By default, this operation masks certain personally identifiable information (PII) in its response, such as Social Security Numbers and birth dates. Please refer to the API documentation article Unmasking PII to learn how to unmask this data.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `dependentId` (query, optional) — dependent identifier
- `onlyActive` (query, optional) — Indicates whether the operation should return only active dependents. Valid values are true, false, or empty. If true, this operation returns only active dependents; if false or empty (default), this operation returns all dependents regardless of status.

**Responses:**
- `200` — successful operation → `GetDependentResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getDisabilityPlanEnrollmentDetails`
**Operation:** `getDisabilityPlanEnrollmentDetails`

**Summary:** Benefit Enrollment Plan Details

**Description:** Use this operation to retrieve coverage amounts and other enrollment details for group benefit plans of Offer Types "STD" (short-term disability) or "LTD" (long-term disability"). This includes settings that determine when an employee is required to submit an Evidence of Insurability (EOI) form. Use the request parameters to return all enrollment details for a specific plan (planId with no filters), all enrollment details for effective dates on or after a particular fromDate, or all details for a specific plan and effectiveDate.

**Parameters:**
- `sessionId` (header, required) — Session Token
- `groupBenefitPlanId` (query, required) — benefit plan ID; must be a disability plan, with offerType="LTD" or "STD"
- `effectiveDate` (query, optional) — specify a plan effective date (format: YYYY-MM-DD) to return only plans for that date; leave empty to return plan details for all effective dates
- `fromDate` (query, optional) — specify a date (format: YYYY-MM-DD) to return benefit plan enrollment records with effective dates on or after this date

**Responses:**
- `200` — successful operation → `DisabilityEnrollmentPlanDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getEligibleFlexSpendingPlans`
**Operation:** `getEligibleFlexSpendingPlans`

**Summary:** Get Eligible Flex Spending Plans for an Employee

**Description:** Use this operation to return a list of FSA and HSA plans for which an employee is eligible

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `asOfDate` (query, optional) — date to use when calculating an employee's eligibility. Defaults to today's date

**Responses:**
- `200` — successful operation → `GetEligibleFlexSpendingPlansResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getEligibleZipCodes`
**Operation:** `getEligibleZipCodes`

**Summary:** Get eligible zip codes

**Description:** Use this operation to return a list of eligible zip codes for a Group Benefit Plan that is not set up to collect network information. This endpoint also returns a checksum, which may be used when calling BenefitService.setEligibleZipCodes

**Parameters:**
- `sessionId` (header, required) — session token
- `planId` (query, required) — group benefit plan identifier

**Responses:**
- `200` — successful operation → `GetEligibleZipCodesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getEmployeePremium`
**Operation:** `getEmployeePremium`

**Summary:** Calculate an employee's premium rates

**Description:** This operation calculates the billing rates (and optionally the premium and contribution rates) for the specified employee and benefit plan. The following table lists all possible options that may be included in the options parameter. Option Description PremiumRates Include calculated insurance benefit premium rates in the response ContributionRates Include calculated employer contribution rates in the response

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `effectiveDate` (query, required) — date to use when calculating the employee's premium
- `planId` (query, required) — benefit plan identifier
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `EmployeePremiumResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getEmployeeRetirementSummary`
**Operation:** `getEmployeeRetirementSummary`

**Summary:** Get employee retirement summary

**Description:** This operation retrieves the details of the retirement benefits for an employee. Use /benefits/getRetirementPlan to return all retirement plan(s) for the specified employee.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `planId` (query, required) — plan identifier
- `planYear` (query, required) — plan year
- `planYearPeriod` (query, optional) — plan year period. You can leave it empty for year-to-date (default) or enter valid values (e.g. 1)

**Responses:**
- `200` — successful operation → `EmployeeRetirementSummaryResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getEnrollInputList`
**Operation:** `getEnrollInputList`

**Summary:** Get required input elements to enroll specified employee in benefit plan

**Description:** This operation returns the elements that are required to enroll the employee in the specified group benefit plan (medical, vision, dental, life insurance, and so on). Different plans have different requirements.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `planId` (query, required) — group benefit plan identifier

**Responses:**
- `200` — successful operation → `EnrollInputResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getEnrollmentPlanDetails`
**Operation:** `getEnrollmentPlanDetails`

**Summary:** Benefit Enrollment Plan Details

**Description:** Use this operation to return benefit plan information from the benefit carrier, including deductibles, copay amounts, and visit types.

**Parameters:**
- `sessionId` (header, required) — Session Token
- `planId` (query, required) — benefit plan identifier
- `offerType` (query, required) — group benefit plan offer type (Examples: MED, DEN, VIS, LIF)
- `effectiveDate` (query, optional) — enter a date to return only plans associated with that effective date or dates following it, or leave blank to return all plans

**Responses:**
- `200` — successful operation → `EnrollmentPlanDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getFSAReimbursements`
**Operation:** `getFSAReimbursements`

**Summary:** Get flexible spending account (FSA) reimbursement for an employee

**Description:** Use this operation to retrieve information about FSA plan reimbursements for specific employees and clients. You can filter the response by plan year, account type, and the reimbursement reference number.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `planYear` (query, optional) — enter an FSA plan year to only return data associated with that plan year
- `accountType` (query, optional) — enter a flexible spending account type to only return data associated with accounts of that type
- `refNumber` (query, optional) — enter a reference number to only return information about the reimbursement associated with that number

**Responses:**
- `200` — successful operation → `GetFSAReimbursementsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getFlexPlans`
**Operation:** `getFlexPlans`

**Summary:** Get flexible spending plan enrollment for the specified employee

**Description:** This operation returns flexible spending plan enrollment information for the specified employee.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `FlexPlansResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getGroupBenefitPlan`
**Operation:** `getGroupBenefitPlan`

**Summary:** Get group benefit plan details

**Description:** This method retrieves the details of the specified group benefit plan.

**Parameters:**
- `sessionId` (header, required) — session token
- `planId` (query, required) — plan identifier

**Responses:**
- `200` — successful operation → `GroupBenefitPlanResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getGroupBenefitRates`
**Operation:** `getGroupBenefitRates`

**Summary:** Get premium and billing rates for a benefit plan

**Description:** This operation returns the premium and billing rates for a specific benefit plan. You can call this method with the BILLING or PREMIUM options to return the associated billing and premium rates for the specified plan. You can also use method restrictions to limit Web Service User access to these options. If you do not provide any method restrictions, the Web Service User can call the method with either option. For more information, please see Using the API > API Methods with Option-Level Access Control on the API documentation site.

**Parameters:**
- `sessionId` (header, required) — session token
- `planId` (query, required) — group benefit plan id
- `date` (query, optional) — effective date
- `rateGroup` (query, optional) — rate group
- `networkId` (query, optional) — network id
- `planType` (query, optional) — plan type
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `GetGroupBenefitRatesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getGroupBenefitTypes`
**Operation:** `getGroupBenefitTypes`

**Summary:** Get group benefit type(s)

**Description:** Use this operation to retrieve a list of system-level group benefit plan type codes, along with their associated data. You can use this information during your group benefit plan setup process. To filter the response to a particular code, provide a typeCode in the input parameters.

**Parameters:**
- `sessionId` (header, required) — session token
- `typeCode` (query, optional) — group benefit plan type code

**Responses:**
- `200` — successful operation → `GroupBenefitTypeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getLifeEventCodeDetails`
**Operation:** `getLifeEventCodeDetails`

**Summary:** Get life event code(s) information for a clent

**Description:** Use this operation to return information about life event codes or a specified life event code. The response is limited by client and Web Service User security settings. For detailed information about life event setup, please see the PrismHR Benefits Enrollment User Guide.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `lifeEventCode` (query, optional) — enter a life event code if you want to return information about only that code. Otherwise, the method returns information about all life event codes available to the client and Web Service User.

**Responses:**
- `200` — successful operation → `LifeEventResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getMonthlyACAInfo`
**Operation:** `getMonthlyACAInfo`

**Summary:** Get monthly employee ACA data

**Description:** Use this operation to return monthly employee ACA data, as calculated by the system for the current year. This method does not return official Form 1095-C data. Note that the coveredSsn and coveredDob fields contain Personally Identifiable Information and are masked by default. To unmask the values in this field, use the NOMASKSSN and NOMASKDOB permissions, respectively. For definitions of these terms and information about ACA processing in general, please see the ACA User Guide. In order to activate this data in Prism you need to run Rebuild ACA Data and add the following Custom Feature Code …

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier or identifiers

**Responses:**
- `200` — successful operation → `GetMonthlyACAInfoResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getPTORequestsList`
**Operation:** `getPTORequestsList`

**Summary:** Get PTO Request List

**Description:** The BenefitService.getPTORequestsList method returns a listing of all employee's leave requests for a client. Use the optional filters to limit the results. Enter 'D' (Denied) under statuses to see denied requests. These will not be returned by default.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, optional) — list of employee IDs
- `statuses` (query, optional) — Optional. Filter by PTO request status. Enter one or more of the following, with no spaces: N (Pending), A (Approved), C (Cancelled), P (Paid), D (Denied)
- `leaveType` (query, optional) — Optional. Filter by this PTO type code
- `ptoStartsAfterDate` (query, optional) — Optional. Filter by PTO date range. Include only time off that starts after this date, in YYYY-MM-DD format.

**Responses:**
- `200` — successful operation → `PTOAutoRequestListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getPaidTimeOff`
**Operation:** `getPaidTimeOff`

**Summary:** Get paid time off information

**Description:** This operation returns paid time off register information for the current year, and an array (list) of basic summary information for prior years. It also identifies which paid time off plan the employee is enrolled in. This information is up-to-date as of the latest payroll, plus adjustments.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `PaidTimeOffResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

**Related:** [[getPaidTimeOffPlans]]

---

## `GET /benefits/v1/getPaidTimeOffPlans`
**Operation:** `getPaidTimeOffPlans`

**Summary:** Get paid time off plans for the specified client

**Description:** This operation returns an array (list) of all available paid time off plans for the specified client. Note that this does NOT include employee enrollment or register information. For paid time off register and enrollment, use the BenefitService.getPaidTimeOff operation.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `PtoPlanResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getPlanYearInfo`
**Operation:** `getPlanYearInfo`

**Summary:** Benefit plan year data

**Description:** Use this operation to retrieve benefit plan year data for retirement, HSA, and Section 125 plans. You can use the optional input parameters to filter the method response by benefit plan year, ID, or type.

**Parameters:**
- `sessionId` (header, required) — session token
- `planType` (query, optional) — provide a plan type to return only information for that type of plan. Valid types are F (retirement), H (HSA), and C (Section 125)
- `planYear` (query, optional) — provide a four-digit year to return only information for that year
- `planId` (query, optional) — provide a plan ID to return only information for that benefit plan

**Responses:**
- `200` — successful operation → `GetPlanYearInfoResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /benefits/v1/getPtoAbsenceCodes`
**Operation:** `getPtoAbsenceCodes`

**Summary:** Get PTO absence codes for a client

**Description:** This method returns all PTO absence codes for a client. Specify an absenceCode to return a single PTO absence code.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `absenceCode` (query, optional) — absence code identifier to get a single absence code

**Responses:**
- `200` — successful operation → `PtoAbsenceCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getPtoAutoEnrollRules`
**Operation:** `getPtoAutoEnrollRules`

**Summary:** Get PTO auto enroll rules for a client

**Description:** The BenefitService.getPtoAutoEnrollRules method returns a list of PTO auto enroll rules for a client.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `PTOAutoEnrollRulesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getPtoClasses`
**Operation:** `getPtoClasses`

**Summary:** Get paid time off classes for the specified client

**Description:** You can use the new BenefitService.getPtoClasses method to return all PTO classes.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `GetPTOClassesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getPtoPlanDetails`
**Operation:** `getPtoPlanDetails`

**Summary:** Get pto plan details

**Description:** The BenefitService.getPtoPlanDetails method returns information about a single PTO Benefit Plan.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `ptoPlanId` (query, required) — ptoPlanId

**Responses:**
- `200` — successful operation → `BenefitPtoPlanDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getPtoRegisterTypes`
**Operation:** `getPtoRegisterTypes`

**Summary:** Get PTO register types for a client

**Description:** The BenefitService.getPtoRegisterTypes method returns a list of PTO register types for a client.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `ptoTypeCode` (query, optional) — single PTO type code to return

**Responses:**
- `200` — successful operation → `PTORegisterTypeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getRetirementLoans`
**Operation:** `getRetirementLoans`

**Summary:** Get retirement loans for the specified employee or a client

**Description:** This operation returns retirement loan information for the specified employee, including payback information and payback adjustments, or for a client.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, optional) — employee identifier to retrieve loans for that employee

**Responses:**
- `200` — successful operation → `RetirementLoanResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getRetirementPlan`
**Operation:** `getRetirementPlan`

**Summary:** Get active retirement plans for an employee

**Description:** This operation returns the retirement plan(s) that are currently active for the specified employee. You can specify an effectiveDate to use in this calculation; if left empty, then the current date is used.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — PrismHR employee id
- `effectiveDate` (query, optional) — YYYY-MM-DD formatted string
- `isActive` (query, optional) — If isActive is set to true, we will only return retirement plan details that are active from today’s date or the effective date entered. Default is false which will return all detail information.

**Responses:**
- `200` — successful operation → `RetirementPlanResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/getSection125Plans`
**Operation:** `getSection125Plans`

**Summary:** Get HSA/Section 125 plan deatils

**Description:** This operation returns data about Health Savings Account (HSA) benefit plans and Section 125 plans (which are both associated with Flexible Spending Accounts, or FSAs). You must specify the plan type to return: type codes are H = HSA, C = Section 125. This operation also returns paginated results. Pagination is required when more than 500 records exist. Use the count and startpage query parameters to navigate through the list of plans. count specifies the number of plans to return per page, and startpage indicates the starting position in the plan list. The operation returns these parameters i…

**Parameters:**
- `sessionId` (header, required) — session token
- `planType` (query, required) — type of plan to return; valid values are H (HSA) and C (Section 125)
- `planId` (query, optional) — specify a plan ID to return only data about that plan
- `count` (query, optional) — number of plans returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetSection125PlansResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /benefits/v1/retirementCensusExport`
**Operation:** `retirementCensusExport`

**Summary:** download retirement census report

**Description:** Note: Web Service Users cannot call multiple concurrent instances of this method. Please wait until the first instance returns a buildStatus of "DONE," retrieve your download link, and then, if necessary, invoke this method again. If you try to call a second instance before the first one completes, the system will return HTTP response code 429 and you must complete the previous instance using the downloadId provided before initiating a new instance. This operation is used to generate and download a retirement census report. To use this API, provide a report format (Census, Participants, or Eli…

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — identifier used to check status of / download data
- `reportFormat` (query, required) — report format: Census, Participants, or Eligibility
- `planId` (query, required) — retirement plan identifier; enter a single retirement plan ID or ALL for all plans
- `clientId` (query, optional) — client identifier
- `startDate` (query, required) — pay date range starting date (formatted YYYY-MM-DD)
- `endDate` (query, required) — pay date range ending date (formatted YYYY-MM-DD)
- `include1099` (query, optional) — Include 1099 employees (true/false)
- `includeLoans` (query, optional) — Include retirement loan payments even if client no longer offers retirement plan (true/false)
- `includeHoursPaid` (query, optional) — Include hours paid (true/false)
- `includeRetirementPlan` (query, optional) — Include retirement plan (true/false)

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /benefits/v1/addEmployeeAbsence`
**Operation:** `addEmployeeAbsence`

**Summary:** Add Absence Journal Entries

**Description:** Use this operation to add absence journal entries to an employee PTO register.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeAbsenceDetailsRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/addFSAReimbursement`
**Operation:** `addFSAReimbursement`

**Summary:** Add FSA reimbursement record for an employee

**Description:** Use this operation to create a new flexible spending account reimbursement for an employee. Be sure to enter NEW in the refNumber input field. This operation does not modify existing FSA reimbursements.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `AddFSAReimbursementRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/adjustBenefitAdjustmentCycles`
**Operation:** `adjustBenefitAdjustmentCycles`

**Summary:** Adjust benefit adjustment cyles for an employee

**Description:** Use this operation to calculate benefit plan adjustments related to changes in the benefit adjustment cycle. The writeAdjustment parameter determines whether the system will write the recalculated values to the adjustment record. If this parameter is false (default value), the method returns calculation data without writing it to the adjustment record. To obtain the checksum for this method, call the BenefitService.getBenefitAdjustments method.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `checksum`, `clientId`, `cycles`, `employeeId`, `refId`, `writeAdjustment`

**Responses:**
- `200` — successful operation → `AdjustBenefitAdjustmentCyclesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/adjustPTO`
**Operation:** `adjustPTO`

**Summary:** PTO Adjustment

**Description:** Use this method to adjust Employee PTO.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `AdjustPTO`

**Responses:**
- `200` — successful operation → `AdjustPTOResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/deleteBenefitAdjustment`
**Operation:** `deleteBenefitAdjustment`

**Summary:** deletion of a specific reference number/client/employeeId/checksum benefit adjustment.

**Description:** deletion of a specific reference number/client/employeeId/checksum benefit adjustment. To obtain the checksum for this method, call the BenefitService.getBenefitAdjustments method

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `checksum`, `clientId`, `employeeId`, `refNumber`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/enrollBenefit`
**Operation:** `enrollBenefit`

**Summary:** Enroll a benefit plan

**Description:** Use this method to enroll an employee in a benefit plan.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitPlanEnroll`

**Responses:**
- `200` — successful operation → `EnrollBenefitResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/enrollPTORegister`
**Operation:** `enrollPTORegister`

**Summary:** The BenefitService.enrollPTORegister enrolls an Employee in a PTO Register.

**Description:** You can use the new BenefitService.enrollPTORegister method to enroll an employee in a paid time off register. Please review the PTO Register Enrollment section of the PrismHR Online Help/PTO User Guide before using this feature, as this section contains important information about PTO register fields (specifically, the benefitStart and calculateThruDate fields).

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EnrollPTORegisterRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/import401KData`
**Operation:** `import401KData`

**Summary:** Upload 401K import data

**Description:** The benefits/import401KData method uploads 401K import data, performs validations against the data, and then writes the new data to PrismHR. The response identifies those lines in the import data that did not pass validation, with error messages for each line. Rows that do pass validation are imported even if some rows contain errors. This method can be called repeatedly, and overwrites the previous upload. This allows the client application to review the response, correct problems, and then upload the method again without duplicating records; note employees not included in subsequent uploads …

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `importData`, `loanPaymentCycle`

**Responses:**
- `200` — successful operation → `Import401KResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/set401KMatchRules`
**Operation:** `set401KMatchRules`

**Summary:** The BenefitService.set401KMatchRules creates and updates 401(k) match rules.

**Description:** Use this method to create and update 401(k) match rules. Use the checksum value from BenefitService.get401KMatchRules to update an existing match rule. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `Set401KMatchRulesRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/setACAOfferedEmployees`
**Operation:** `setACAOfferedEmployees`

**Summary:** Save ACA Offered Employees Information

**Description:** Use this operation to update the ACA Offered Employees grid for up to 20 employees under the same client. By default, the endpoint only appends data to the grid. If you want to update acaOfferOfCoverage to an existing line on the grid, set updateOfferOfCoverage to true. In this case, the endpoint returns an error if you try to pass data for multiple lines.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetACAOfferedEmployeesRequest`

**Responses:**
- `200` — successful operation → `SetACAOfferedEmployeesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/setBenefitAdjustments`
**Operation:** `setBenefitAdjustments`

**Summary:** Create or update benefit adjustments for an employee

**Description:** Use this method to create or update benefit adjustments for an employee. The checksum is required when updating benefit adjustments for an employee. To obtain the checksum for this method, call the BenefitService.getBenefitAdjustments method. To create a new benefit adjustment enter NEW in the refNumber field. To delete a benefit adjustment call BenefitService.deleteBenefitAdjustment. This method will only update or create those benefit adjustments input. We will not clear or change benefit adjustments not in the input.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitAdjustmentsRequest`

**Responses:**
- `200` — successful operation → `SetBenefitAdjustmentsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/setBenefitRule`
**Operation:** `setBenefitRule`

**Summary:** Set benefit rule

**Description:** Use this method to set Benefit Rules conditions that the client's employees must satisfy to enroll in a benefit plan. This only applies to rules for group benefit plans; users cannot set benefit rules for retirement, flexible spending, employer match, or HSA match plans. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the recor…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitRuleSetup`

**Responses:**
- `200` — successful operation → `BenefitResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/setClientBenefitPlanSetupDetails`
**Operation:** `setClientBenefitPlanSetupDetails`

**Summary:** set client benefit plan setup parameters

**Description:** Use this method to set a client's Benefit Plan Setup parameters for group benefit, retirement plans, flexible spending, employer match, or HSA match plans. The checksum is required when updating a benefit plan setup. To obtain the checksum for this method, call the BenefitService.getClientBenefitPlanSetupDetails method. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record. When using this method to update an existing benefit plan setup, the API will ignore any fields excluded from the input, as well as any fields set…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitPlanSetup`

**Responses:**
- `200` — successful operation → `SetClientBenefitPlanSetupDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/setDependent`
**Operation:** `setDependent`

**Summary:** This service creates or updates a single dependent.

**Description:** To create a new dependent, add NEW for the dependentId. To update, you must include a dependentId. In this case, a checksum is required and returned via BenefitService.getDependent. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateDependent`

**Responses:**
- `200` — successful operation → `SetDependentResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/setDisabilityPlanEnrollmentDetails`
**Operation:** `setDisabilityPlanEnrollmentDetails`

**Summary:** save disability plan enrollment information

**Description:** Use this operation to create or update coverage amounts and other enrollment details for group benefit plans of Offer Types "STD" “STA”(short-term disability) or "LTD" “LTA” (long-term disability"). This includes settings that determine when an employee is required to submit an Evidence of Insurability (EOI) form. Use the checksum value returned by BenefitService.getDisabilityPlanEnrollmentDetails when making updates.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetDisabilityPlanEnrollmentDetailsRequest`

**Responses:**
- `200` — successful operation → `SetDisabilityPlanEnrollmentDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/setEmployeePTOAccrual`
**Operation:** `setEmployeePTOAccrual`

**Summary:** Start or stop PTO accruals

**Description:** Use this operation to start or stop PTO accruals for PTO registers associated with a particular employee. Use the action attribute to specify whether to "start" or "stop" accruals. You can apply the change to all PTO registers associated with the employee or to specific registers. If you want to specify the affected registers, set allAccruals to false.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetEmployeePTOAccrualRequest`

**Responses:**
- `200` — successful operation → `SetEmployeePTOAccrualUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/setEnrollmentPlanDetails`
**Operation:** `setEnrollmentPlanDetails`

**Summary:** Set Benefit Enrollment Plan Details

**Description:** Use this operation to update benefit plan information from the benefit carrier, including deductibles, copay amounts, and visit types. Use the checksum value returned by BenefitService.getEnrollmentPlanDetails when making updates. Please note: The key and field values returned in BenefitService.getEnrollmentPlanDetails cannot be updated or changed by this method. In addition if an invalid key value is entered all fields in the array will be ignored.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EnrollmentPlanDetailsRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/setFlexPlan`
**Operation:** `setFlexPlan`

**Summary:** The BenefitService.setFlexPlan method enrolls a single employee in a flexible spending

**Description:** Use this method to enroll a single employee in a flexible spending plan. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetFlexPlanRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/setGroupBenefitBillingRates`
**Operation:** `setGroupBenefitBillingRates`

**Summary:** Configure group benefit billing rate details

**Description:** Use this method to create or update group benefit billing rate details. The checksum is required when updating a group benefit billing rate. To obtain the checksum for this method, call the BenefitService.getGroupBenefitRates method .

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `GroupBenefitRateRequest`

**Responses:**
- `200` — successful operation → `SetGroupBenefitRatesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/setGroupBenefitPlanDetails`
**Operation:** `setGroupBenefitPlanDetails`

**Summary:** Configure group benefit plan details

**Description:** Use this method to create or update group benefit plan details. The checksum is required when updating a group benefit plan. To obtain the checksum for this method, call the BenefitService.getGroupBenefitPlan method .

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `GroupBenefitPlanRequest`

**Responses:**
- `200` — successful operation → `SetBenefitPlanDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/setGroupBenefitPremiumRates`
**Operation:** `setGroupBenefitPremiumRates`

**Summary:** Configure group benefit premium rate details

**Description:** Use this method to create or update group benefit premium rate details. The checksum is required when updating a group benefit premium rate. To obtain the checksum for this method, call the BenefitService.getGroupBenefitRates method .

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `GroupBenefitRateRequest`

**Responses:**
- `200` — successful operation → `SetGroupBenefitRatesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/setPtoAbsenceCode`
**Operation:** `setPtoAbsenceCode`

**Summary:** Set single PTO absence code.

**Description:** This method creates or updates a single PTO absence code. To obtain the checksum for this method, call the The BenefitService.getPtoAbsenceCodes method. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PtoAbsenceCodeUpdate`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/setPtoAutoEnrollRules`
**Operation:** `setPtoAutoEnrollRules`

**Summary:** Set PTO auto enroll rules for a client

**Description:** The BenefitService.setPtoAutoEnrollRules method updates or creates PTO Auto Enroll Rules. To obtain the checksum for this method, call the BenefitService.getPtoAutoEnrollRules method. Each rule object in the array contains a "line" parameter which must be in sequential order starting with line 1, depending on the order in which auto enroll rules should be applied. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure tha…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetPTOAutoEnrollRule`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/setPtoClass`
**Operation:** `setPtoClass`

**Summary:** Set paid time off class for the specified client

**Description:** You can use the new BenefitService.setPtoClass method to create a PTO class.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetPTOClass`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/setPtoPlanDetails`
**Operation:** `setPtoPlanDetails`

**Summary:** Set pto plan details

**Description:** The BenefitService.setPtoPlandetails creates a new or updates an existing PTO Benefit Plan. To obtain the checksum for this method, call the BenefitService.getPtoPlanDetails method. Calculation BasisArray Values Flat (F) flatAmountMonths Worked (M) monthsWorkedHours Worked (by Hours) (HH) payCodesHourlyAccrual, payPeriodAccrualThresholds, hoursWorkedByHoursHours Worked (by Month) (HM) payCodesHourlyAccrual, payPeriodAccrualThresholds, hoursWorkedByMonthsHours Worked (by Position) (HHP) payCodesHourlyAccrual, payPeriodAccrualThresholds, hoursWorkedByPositionFlat Amount By Hours Worked (FH) payC…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitPtoPlanDetailsSetRequest`

**Responses:**
- `200` — successful operation → `BenefitPtoPlanDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/setPtoRegisterType`
**Operation:** `setPtoRegisterType`

**Summary:** Set PTO register type for a client

**Description:** The BenefitService.setPtoRegisterType method updates or creates a single PTO register type. To obtain the checksum for this method, call the BenefitService.getPtoRegisterTypes method. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetPTORegisterType`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /benefits/v1/setRetirementLoan`
**Operation:** `setRetirementLoan`

**Summary:** Set retirement loan

**Description:** Use this method to create or update retirement loan information. When creating a new loan, leave the loanId and checksum blank; if updating an existing loan, those values are required. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `RetirementLoanSetup`

**Responses:**
- `200` — successful operation → `BenefitResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/submitLifeEvent`
**Operation:** `submitLifeEvent`

**Summary:** Submit a life event for an employee

**Description:** Use this operation to assign life event workflows to employees. Note: This operation is designed to work specifically with PrismHR Benefits Enrollment. Do not use for third-party benefits enrollment applications.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SubmitLifeEvent`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/updateRetirementPlanElection`
**Operation:** `updateRetirementPlanElection`

**Summary:** Configure retirement plan elections setup

**Description:** This operation configures an employee's retirement plan election details. The checksum is required when updating a retirement benefit plan. To obtain the checksum, call BenefitService.getRetirementPlan and use the value returned under planDetailsChecksum. This endpoint requires that all data retrieved from the corresponding GET operation be supplied in the request object, along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up to date when writing the updates back to the record. This en…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `RetirementPlanElectionDetail`

**Responses:**
- `200` — successful operation → `BenefitResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /benefits/v1/updateRetirementPlanEnroll`
**Operation:** `updateRetirementPlanEnroll`

**Summary:** Configure retirement plan enrollment

**Description:** Use this method to configure the details of an employee's retirement plan enrollment information. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `RetirementPlanEnroll`

**Responses:**
- `200` — successful operation → `BenefitResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---
