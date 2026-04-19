# Service: `employee`

**74 methods** in this service.

## `GET /employee/v1/checkForGarnishments`
**Operation:** `checkForGarnishments`

**Summary:** Check for garnishments for employee

**Description:** This method returns whether an employee has active garnishments. It does not return garsnishment details.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `CheckForGarnishmentsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/download1095C`
**Operation:** `download1095C`

**Summary:** Download an employee's 1095C

**Description:** Use this operation to download an employee's 1095C form for the provided year or to batch download a range of employee's 1095Cs. Provide only one employee ID to download a 1095C for a single employee, provide two employee IDs to download 1095Cs for all employees of the provided client within the given range (e.g. providing clientId 123 and employeeIds A00000 and Z99999 will provide all 1095Cs for all employees of client 123). Please note: There is a limit of 200 1095Cs per batch. If there are more than 200 employees working for the provided client, then limit the range of employee IDs to ensur…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier(s); provide only one employee ID to download 1095C for a single employee, provide two employee IDs to download 1095Cs for all employees of the provided client within the given range.
- `year` (query, required) — 1095C year
- `maskSsn` (query, optional) — whether to mask the employee's SSN (true/false; default is false)
- `employerId` (query, optional) — employer ID (optional)

**Responses:**
- `200` — successful operation → `EmployeeFormDownloadResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/downloadW2`
**Operation:** `downloadW2`

**Summary:** Download an employee's W2

**Description:** Use this operation to download an employee's W2 form for the provided year or to batch download a range of employee's W2s. Provide only one employee ID to download a W2 for a single employee, provide two employee IDs to download W2s for all employees of the provided client within the given range (e.g. providing clientId 123 and employeeIds A00000 and Z99999 will provide all W2s for all employees of client 123). Please note: There is a limit of 200 W2s per batch. If there are more than 200 employees working for the provided client, then limit the range of employee IDs to ensure it will match 20…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier(s); provide only one employee ID to download W2 for a single employee, provide two employee IDs to download W2s for all employees of the provided client within the given range.
- `year` (query, required) — W2 year

**Responses:**
- `200` — successful operation → `EmployeeFormDownloadResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/get1095CYears`
**Operation:** `get1095CYears`

**Summary:** Get a list of available Form 1095-C years

**Description:** This operation retrieves a list of Form 1095-C years for a specified employee. This operation only retrieves a 1095-C year when the PrismHR field Show In ESS (located in the Benefits tab of Client Details) is set to "Yes" for that year.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `Employee1095CYearsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/get1099Years`
**Operation:** `get1099Years`

**Summary:** Get a list of available 1099 years

**Description:** This operation returns a list of existing Form 1099 years for a specific independent contractor. Note: This returns only 1099 years that the employer allows to display online for the contractor to view and download.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — ID of the Form 1099 contractor

**Responses:**
- `200` — successful operation → `Employee1099YearsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId- is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getACHDeductions`
**Operation:** `getACHDeductions`

**Summary:** Get Employee ACH Deductions

**Description:** This operation retrieves voluntary employee ACH deduction setup (where accountType = “DED1”, “DED2”, or “DED3”). Note: Voluntary ACH deductions are only supported if the VOLUNTARYDEDACH custom feature code is enabled on the System Parameters form.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `ACHDeductionsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getAddressInfo`
**Operation:** `getAddressInfo`

**Summary:** Get employee address information

**Description:** Use this method to retrieve addresses for a particular employee as employed by the specified client. This includes the employee's residential address, address for Forms W-2, and mailing (alternate) address (if any).

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `EmployeeAddressResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getEmployee`
**Operation:** `getEmployee`

**Summary:** Get employee(s) information by employee ID

**Description:** This operation retrieves between 1 and 20 employees using the specified employee IDs. If the Options parameter is unspecified, the operation will return only the employee data attributes that fall into the Person class. The table lists all of the options. This operation masks certain PII in its response by default, such as employee social security number and date of birth. Please refer to the API documentation article Unmasking PII for instructions on unmasking this data. This operation also supports option-level security, including the ability to remove pay rate information from the Compensat…

**Parameters:**
- `sessionId` (header, required) — session token
- `employeeId` (query, required) — list of employee IDs
- `clientId` (query, required) — client identifier
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `EmployeeAndEmployeeBySsnResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[getEmployeeBySSN]] · [[getEmployeeEvents]] · [[getEmployeeList]] · [[getEmployeeSSNList]] · [[getEmployeesReadyForEverify]]

---

## `GET /employee/v1/getEmployeeEvents`
**Operation:** `getEmployeeEvents`

**Summary:** Get events for an employee

**Description:** The EmployeeService.getEmployeeEvents method returns a list of employee events for a single employee. Use the checksum value to update an employee event using API method EmployeeService.updateEmployeeEvents.

**Parameters:**
- `sessionId` (header, required) — session token
- `employeeId` (query, required) — employee ID
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `EmployeeEventsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getEmployeeList`
**Operation:** `getEmployeeList`

**Summary:** Get list of employees for a specified client

**Description:** This operation retrieves the complete list of employees for the specified client. You can filter the results based on employee status class (active, leave, terminated) and type class (part-time or full-time). This list includes only the employee ID, as the list may be quite large. Use the EmployeeService.getEmployee operation to retrieve detailed information about a specific employee.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `statusClass` (query, optional) — filter the method response by employee status class. Enter any combination of the following: (A)ctive, (L)eave, or (T)erminated.
- `typeClass` (query, optional) — filter the method response by employee type class. Enter (F)ull-time or (P)art-time.

**Responses:**
- `200` — successful operation → `EmployeePendingApprovalResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getEmployeeSSNList`
**Operation:** `getEmployeeSSNList`

**Summary:** Get list of employees with their SSN

**Description:** This operation retrieves a list of employees including their employee IDs and Social Security numbers for the specified client.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `EmployeeSsnListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getEmployeesReadyForEverify`
**Operation:** `getEmployeesReadyForEverify`

**Summary:** Get employees who have E-Verify Requested status

**Description:** The EmployeeService.getEmployeesReadyForEverify method returns a list of employees from the clients that have the status E-Verify Requested

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `EmployeesReadyForEverifyResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getEmployersInfo`
**Operation:** `getEmployersInfo`

**Summary:** Get current employer and list of possible employers

**Description:** This operation retrieves an employee's current employer and all potential employers associated with the specified client.

**Parameters:**
- `sessionId` (header, required) — session token
- `employeeId` (query, required) — employeeId
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `EmployerResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getEverifyStatus`
**Operation:** `getEverifyStatus`

**Summary:** Get employee's E-Verify data

**Description:** Use this operation to return an employee's E-Verify data, including status and case number.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `EmployeeEVerifyStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getFutureEeChange`
**Operation:** `getFutureEeChange`

**Summary:** Get employee future event change

**Description:** Use this operation to retrieve future-scheduled changes to an employee job/position, pay rate, or status. In the required eventObjectId parameter, pass the objectId returned by SubscriptionService.getEvents or getNewEvents for subscription Schema Employee and Class FutureEEChanges.

**Parameters:**
- `sessionId` (header, required) — session token
- `eventObjectId` (query, required) — event object identifier

**Responses:**
- `200` — successful operation → `FutureEeChangeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getGarnishmentEmployee`
**Operation:** `getGarnishmentEmployee`

**Summary:** Get employee Id for garnishment

**Description:** Use this operation to retrieve the employee ID associated with a specific client ID and garnishment ID/docket number. This can be used in conjunction to our garnishment events with Schema Deduction and Class Garnishment. Note: A web service user can only call this endpoint if it exists in the Allowed Methods grid for that user. This endpoint also respects any client access security associated with the web service user.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `garnishmentId` (query, required) — garnishment identifier (docket number)

**Responses:**
- `200` — successful operation → `GarnishmentEmployeeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getHistory`
**Operation:** `getHistory`

**Summary:** Get historical events

**Description:** This operation retrieves an array of historical events for an employee: pay rate changes, job/position changes, leave of absence, status changes, and employment termination. You can also use the type option to return the history of any changes made using EmployeeService.updateFutureAssignment, or through PrismHR forms like HR|Action|Department Change and HR|Action|Location Change. Please note that entity history data is associated with the PrismHR features mentioned above, which can update future entity assignments for employees. Because of this relationship, the history only extends back to J…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `type` (query, optional) — history types (specify B for benefit groups, C for locations, D for departments, J for jobs/positions, P for pay, S for status, V for divisions, W for wellness status, or leave blank to retrieve all history types)

**Responses:**
- `200` — successful operation → `EmployeeHistoryResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getI9Data`
**Operation:** `getI9Data`

**Summary:** Get employee I9 data

**Description:** This operation retrieves Form I-9 data for a particular employee as employed by the specified client. This includes all data pertinent to the USCIS Form I-9. By default, this operation masks certain personally identifiable information (PII) in its response, such as SSN, date of birth, numbers of identity documents. Please refer to the API documentation article Unmasking PII to learn how to unmask this data.Option DescriptionAdditionalMetadatareturn additional metadata useful for the E-verify process

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `I9Data`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getLeaveRequests`
**Operation:** `getLeaveRequests`

**Summary:** Get leave requests by clientId and leaveId

**Description:** Use this method to retrieve employee PTO request information.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `leaveId` (query, required) — PTO (leave request) identifier

**Responses:**
- `200` — successful operation → `LeaveRequestResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getLifeEvent`
**Operation:** `getLifeEvent`

**Summary:** Retrieve an employee life event

**Description:** This operation retrieves a single employee life event for the provided client and employee.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `EmployeeLifeEventResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getOSHA`
**Operation:** `getOSHA`

**Summary:** Get OSHA case

**Description:** This operation retrieves an OHSA case file from PrismHR.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `caseNumber` (query, required) — OSHA case file number

**Responses:**
- `200` — successful operation → `OSHAResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getPayCardEmployees`
**Operation:** `getPayCardEmployees`

**Summary:** Get list of employees associated with a specified direct deposit transit/routing number.

**Description:** Use this operation to retrieve a list of employees associated with a specified direct deposit transit/routing number.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `transitNumber` (query, required) — direct deposit routing number
- `employeeId` (query, optional) — optional employeeId filter

**Responses:**
- `200` — successful operation → `PayCardResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getPayRateHistory`
**Operation:** `getPayRateHistory`

**Summary:** Get historical pay rate attributes

**Description:** This operation will retrieve an array (list) of historical pay rate attributes.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `EmployeePayRateHistoryResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getPendingApproval`
**Operation:** `getPendingApproval`

**Summary:** Get list of pending approvals by employeeID

**Description:** This operation retrieves an array (list) of employeeIDs with pending approvals for status/type changes or terminations. (Note that this does not include leaves of absence.)

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `type` (query, optional) — pending approval type (specify 'T' for terminated, 'A' for Active, or leave blank to retrieve both status change types)
- `employeeId` (query, optional) — employee identifier

**Responses:**
- `200` — successful operation → `EmployeePendingApprovalResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getPositionRate`
**Operation:** `getPositionRate`

**Summary:** Get list of position rates

**Description:** This operation retrieves an array (list) of position rate objects that contain standard rate, pay code, and billing rate attributes.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `EmployeeJobRateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getScheduledDeductions`
**Operation:** `getScheduledDeductions`

**Summary:** Get an employee's scheduled deductions

**Description:** Use this method to get a list of an employee's scheduled deductions. These are one-time or temporary deductions and do not include standard deductions or garnishments.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client ID
- `employeeId` (query, required) — employee ID

**Responses:**
- `200` — successful operation → `ScheduledDeductionResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getStatusHistoryForAdjustment`
**Operation:** `getStatusHistoryForAdjustment`

**Summary:** Retrieve status history for employee

**Description:** This operation provides all the information necessary to make a status/type history date adjustment for an employee in a specified client. To make this date change, use EmployeeService.adjustStatusHistory. The allowUpdates field will return true If hire dates can be adjusted. Otherwise, you can only change the effectiveDate of the status or type.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `StatusTypeHistoryResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getTerminationDateRange`
**Operation:** `getTerminationDateRange`

**Summary:** Get termination date range for employees

**Description:** This operation retrieves a valid date range for employee terminations.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `EmployeeTerminationResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/getW2Years`
**Operation:** `getW2Years`

**Summary:** Get a list of available W2 years

**Description:** Use this method to return a list of Form W-2 years available for a specified employee.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `EmployeeW2YearsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/reprint1099`
**Operation:** `reprint1099`

**Summary:** Download an employee's 1099

**Description:** This operation downloads an independent contractor's Form 1099 for the specified year. Use EmployeeService.get1099Years to retrieve a list of allowed year values for a specific employeeId.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — ID of the independent contractor
- `year` (query, required) — Form 1099 year, returned by EmployeeService.get1099Years

**Responses:**
- `200` — successful operation → `EmployeeFormDownloadResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /employee/v1/reprintW2C`
**Operation:** `reprintW2C`

**Summary:** Download an employee's W2C

**Description:** Use this operation to download an employee's W2C form for the provided year. Provide employee ID and clientId to download a W2C for an employee

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier. Provide employee ID to download W2C for an employee
- `year` (query, required) — W2C year

**Responses:**
- `200` — successful operation → `EmployeeFormDownloadResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/addEmployeeEvents`
**Operation:** `addEmployeeEvents`

**Summary:** add new employee events

**Description:** This method adds employee events without affecting existing events. A checksum value is required and can be obtained by calling EmployeeService.getEmployeeEvents.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeEventsChangeRequest`

**Responses:**
- `200` — successful operation → `EmployeeEventChangeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/adjustStatusHistory`
**Operation:** `adjustStatusHistory`

**Summary:** adjusts an employee's status/type change history date.

**Description:** Use this operation to update an employee's status/type change history date. Please note that newEffectiveDate cannot match an existing status date, but can come before any existing date. Use the checksum value returned by EmployeeService.getStatusHistoryForAdjustment when calling this method.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `AdjustStatusHistoryRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /employee/v1/approveOrDenyPTORequest`
**Operation:** `approveOrDenyPTORequest`

**Summary:** Approve or Deny employee PTO request

**Description:** Use this method to (A)pprove, (D)eny or (C)ancel an employee PTO request. A checksum attribute is required, to avoid a conflict with other transactions that might be in flight. To obtain an existing employee PTO request and the checksum, call the BenefitService.getPTORequestsList operation. If you are performing this operation on an employee for a client managed in PrismHR, you must also have a PrismHR user account with the exact same user ID as your web services user account. See Using the API > Setting Up PrismHR and Web Services User Accounts in the documentation.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ApproveDenyCancelPTORequest`

**Responses:**
- `200` — successful operation → `ApproveDenyCancelPTOResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/benefitPlanSetEligible`
**Operation:** `benefitPlanSetEligible`

**Summary:** Set an employee benefit plan status to eligible

**Description:** Use this method to change the enrollment status of a benefit plan for an employee from Not Eligible (ineligible) to Eligible.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitPlanStatus`

**Responses:**
- `200` — successful operation → `BenefitPlanStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/benefitPlanSetInEligible`
**Operation:** `benefitPlanSetInEligible`

**Summary:** Set an employee benefit plan status to ineligible

**Description:** Use this method to change the enrollment status of a benefit plan for an employee from Eligible to Not Eligible (ineligible).

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitPlanStatus`

**Responses:**
- `200` — successful operation → `BenefitPlanStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/benefitPlanSetTerminate`
**Operation:** `benefitPlanSetTerminate`

**Summary:** Set an employee benefit plan status to terminate

**Description:** Use this method to change the enrollment status of a benefit plan for an employee from Active to Terminated.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitPlanTerminateStatus`

**Responses:**
- `200` — successful operation → `BenefitPlanStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/benefitPlanSetWaive`
**Operation:** `benefitPlanSetWaive`

**Summary:** Set an employee benefit plan status to waived

**Description:** Use this method to change the enrollment status of a benefit plan for an employee from Eligible to Waived (unenrolled).

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitPlanWaiveStatus`

**Responses:**
- `200` — successful operation → `BenefitPlanStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/cancelPTORequest`
**Operation:** `cancelPTORequest`

**Summary:** Cancel PTO Request

**Description:** This operation allows an employee to cancel a leave request, mirroring an Employee Portal feature. Employees can only cancel a leave request if the request has not been approved, denied, or paid.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `leaveId` (query, required) — PTO (leave request) identifier

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /employee/v1/getEmployeeBySSN`
**Operation:** `getEmployeeBySSN`

**Summary:** Get employee(s) information by Social Security number

**Description:** This operation retrieves between 1 and 20 employees using the specified employee IDs. If the Options parameter is unspecified, the operation will return only the employee data attributes that fall into the Person class. The table lists all of the options. This operation masks certain PII in its response by default, such as employee social security number and date of birth. Please refer to the API documentation article Unmasking PII for instructions on unmasking this data. This operation also supports option-level security, including the ability to remove pay rate information from the Compensat…

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`, `ssn`

**Responses:**
- `200` — successful operation → `EmployeeAndEmployeeBySsnResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/lookupBySsn`
**Operation:** `lookupBySsn`

**Summary:** Get employee information by Social Security number

**Description:** Use this method to retrieve information associated with the specified Social Security number: name, client ID, employee ID, and current status.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `ssn`

**Responses:**
- `200` — successful operation → `LookupBySsnResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/reactivate`
**Operation:** `reactivate`

**Summary:** reactivate an employee on leave

**Description:** Use this method to reactivate an employee on leave. This requires that the user has a PrismHR user account; see Set Up a PrismHR Web Services User Account in the documenation. The reactivate operation also fires the validateReactivate operation, which first makes sure there are no issues; see validateReactivate for a list of error messages that operation might return. If there are no issues, the employee's employment status at the specified client is changed. It does not prevent the change if there are only warnings, however, even if those issues might cause problems later. It is strongly reco…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeReactivation`

**Responses:**
- `200` — successful operation → `EmployeeReactivationResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[validateReactivate]]

---

## `POST /employee/v1/rehireEmployee`
**Operation:** `rehireEmployee`

**Summary:** Rehire an employee

**Description:** Use this operation to rehire an employee. If you are rehiring this employee for a client managed in PrismHR, you must also have a PrismHR user account with the exact same user ID as your web services user account. See Using the API > Setting Up PrismHR and Web Services User Accounts in the documentation. Note 1: If the onboarding flag is set to true, and once the onboarding process has started, changes to the employee's data are not allowed. Therefore, all changes to the employee's information should be done prior to calling or during the call to rehireEmployee. The onboarding flag will have n…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `Rehire`

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/removeEmployee`
**Operation:** `removeEmployee`

**Summary:** Remove employee

**Description:** Use this operation to remove up to twenty employee records.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — list of employee identifiers (one or more)

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/requestPTO`
**Operation:** `requestPTO`

**Summary:** PTO Request for an employee

**Description:** This operation creates a PTO request for an employee. Note: For a successful operation, you must meet several requirements. First, to use this method, you must have an existing PrismHR user account with the same User ID as your Web Service User. For more information, please see "Setting up PrismHR and Web Service User accounts" on the API documentation website. In addition, you must either have a client-level or global approval policy for Leave Request, OR the employee must have a reportsTo value set up (PTO Approver field in the Work tab of Employee Details).

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `RequestPTO`

**Responses:**
- `200` — successful operation → `EmployeePTOResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/setEmployeePayAllocations`
**Operation:** `setEmployeePayAllocations`

**Summary:** update employee pay allocations

**Description:** This method creates and updates employee pay allocations. Use EmployeeService.getEmployee() call with Compensation option to obtain the compensationChecksum. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PayAllocationUpdate`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/setEmployer`
**Operation:** `setEmployer`

**Summary:** Set employer for an employee

**Description:** This operation updates an employee's employer assignment. Note that a checksum attribute is required, which is used to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call EmployeeService.getEmployersInfo.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployerUpdate`

**Responses:**
- `200` — successful operation → `EmployerResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/setEverifyStatus`
**Operation:** `setEverifyStatus`

**Summary:** Set employee's E-Verify data

**Description:** Use this operation to set an employee's E-Verify data, including E-Verify flag, status, and case number. To flag an employee to go through the e-verify process, set the everifyFlag to "Y" and the everifyStatus to "E-Verify Requested on mm/dd/yyyy."

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeEVerifyStatusRequest`

**Responses:**
- `200` — successful operation → `EmployeeEVerifyStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /employee/v1/setHSA`
**Operation:** `setHSA`

**Summary:** update HSA fields.

**Description:** This operation creates and updates employee direct deposit details related to health savings accounts (HSA). Note: EmployeeService.setHSA replaces the entire record, specifically client and employee HSA account information, therefore you must ensure that you include any existing accounts that are not changing as well as any new accounts.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetHSARequest`

**Responses:**
- `200` — successful operation → `GenericUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /employee/v1/setI9Data`
**Operation:** `setI9Data`

**Summary:** Update employee I9 data

**Description:** The EmployeeService.setI9Data method updates an employee's form I-9 information. Note that a checksum attribute is required and is used to avoid a conflict with other transactions that may be in flight. To obtain the checksum, call the EmployeeService.getI9Data method. The I9Filed flag when set to "true", indicates that the employee's I-9 form has been filed. However, this value may not be set from "true" to "false" using the API. When the I9Filed flag is "true," section 1 of the form I-9 can no longer be updated unless the overrideI9FiledFlag is set to true. The phrI9Version and phrFromOB par…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateI9Data`

**Responses:**
- `200` — successful operation → `UpdateI9DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/setPositionRate`
**Operation:** `setPositionRate`

**Summary:** Update job/position rates

**Description:** This operation sets the employee position rate. Note that a checksum attribute is required, which is used to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call the EmployeeService.getPositionRate operation. 0 is used when there are no position rates for the employee. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date wh…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetPositionRate`

**Responses:**
- `200` — successful operation → `EmployeeJobRateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/takeLeaveOfAbsence`
**Operation:** `takeLeaveOfAbsence`

**Summary:** take Leave of Absence for employee

**Description:** Use this method to take leave of absence for an employee. This requires that the user has a PrismHR user account; see Set Up a PrismHR Web Services User Account in the documenation. The takeLeaveOfAbsence operation also fires the validateTakeLeaveOfAbsence operation, which first makes sure there are no issues; see validateTakeLeaveOfAbsence for a list of error messages that operation might return. If there are no issues, the employee's employment status at the specified client is changed. It does not prevent the change if there are only warnings, however, even if those issues might cause probl…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeLeaveOfAbsence`

**Responses:**
- `200` — successful operation → `EmployeeLeaveOfAbsenceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[validateTakeLeaveOfAbsence]]

---

## `POST /employee/v1/terminateEmployee`
**Operation:** `terminateEmployee`

**Summary:** Terminate an employee

**Description:** Use this operation to terminate the employment of a single employee at a single client. You can also create a COBRA record, if appropriate. The terminateEmployee operation also fires the validateEmployeeTerminate operation to check for fatal errors; see validateEmployeeTerminate for a list of error messages that operation might return and stop the termination. It does not prevent the termination if there are only warnings, however, even if those issues might cause problems later. It is strongly recommended that you use validateEmployeeTerminate before terminateEmployee to check for warnings an…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeTerminate`

**Responses:**
- `200` — successful operation → `EmployeeTerminateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updateACHDeductions`
**Operation:** `updateACHDeductions`

**Summary:** Update Employee ACH Deductions

**Description:** This operation updates voluntary employee ACH deductions. For these deductions, the method is always "F" (Fixed) and the amount is always 0. Any other value passed in these fields will be ignored. Note: For this endpoint, accountType supports three values: "DED1", "DED2", and "DED3". Each of these can only be assigned once per employee. In order to use these options, the VOLUNTARYDEDACH custom feature code must be enabled on the System Parameters form. Note: EmployeeService.updateACHDeductions replaces the entire record, specifically employee ACH setup information. Therefore, you must ensure t…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ACHDeductionsRequest`

**Responses:**
- `200` — successful operation → `GenericUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /employee/v1/updateAddressInfo`
**Operation:** `updateAddressInfo`

**Summary:** Update address information

**Description:** This operation updates employee address information. Note that a checksum attribute is required, which is used to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call the EmployeeService.getAddressInfo operation. Important note: If the zipCode, city, or county has changed for the home address, the API will attempt to adjust the GeoCode automatically; however, if there is a conflict or ambiguity in the geo location information, then an error will be returned. Refer to 'clientMaster/getGeoLocations' for a list of possible GeoCodes and repeat the API requ…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateAddress`

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v2/updateAddressInfo`
**Operation:** `updateAddressInfo`

**Summary:** Update address information

**Description:** This operation updates employee address information. Note that a checksum attribute is required, which is used to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call the EmployeeService.getAddressInfo operation. Important note: If the zipCode, city, or county has changed for the home address and the API can determine a single matching geolocation code, it will update the geolocation code automatically. The endpoint will return an update message with a warning regarding any other address details that were changed as part of the geolocation match. If mu…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateAddress`

**Responses:**
- `200` — successful operation → `EmployeeUpdateAddressV2Response`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updateDirectDeposit`
**Operation:** `updateDirectDeposit`

**Summary:** Update direct deposit account information

**Description:** This operation updates direct deposit account information for checking and savings accounts as well as pay cards. This will not modify other ACH types such as FSA (flexible spending accounts). Changes to those other direct deposit settings must be made in the PrismHR product. Note that pay card accounts must be specially configured (in either product) as a pay card in Bank Routing and then set up as a checking account. The updateDirectDeposit operation replaces the entire record, specifically checking and saving account information, therefore you must ensure that you include any existing accou…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateAch`

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[updateDirectDepositForAdmins]]

---

## `POST /employee/v1/updateDirectDepositForAdmins`
**Operation:** `updateDirectDepositForAdmins`

**Summary:** Update direct deposit account information

**Description:** This operation updates direct deposit account information for checking and savings accounts as well as pay cards. This will not modify other ACH types such as FSA (flexible spending accounts). Changes to those other direct deposit settings must be made in the PrismHR product. Note that pay card accounts must be specially configured (in either product) as a pay card in Bank Routing and then set up as a checking account. The updateDirectDeposit operation replaces the entire record, specifically checking and saving account information, therefore you must ensure that you include any existing accou…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateAch`

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updateEmergencyContact`
**Operation:** `updateEmergencyContact`

**Summary:** Update employee emergency contact information

**Description:** This operation updates employee emergency contact information (Employee Details Personal tab in PrismHR product). Note that a checksum attribute is required, which is used to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call the EmployeeService.getEmployee operation with the Person option to collect the personChecksum. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateEmergencyContact`

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updateEmployeeEvents`
**Operation:** `updateEmployeeEvents`

**Summary:** update events for employee

**Description:** This method updates existing employee events for an employee and requires a checksum value. Use EmployeeService.getEmployeeEvents to collect the checksum. Please note all events must be included in the update or they will be deleted.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeEventsChangeRequest`

**Responses:**
- `200` — successful operation → `EmployeeEventChangeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updateEmployeeFields`
**Operation:** `updateEmployeeFields`

**Summary:** update employee fields.

**Description:** Use this operation to update individual employee fields without the requirement of providing a checksum. The API will ignore any fields excluded from the input, as well as any fields set to null. Sub-Objects like vehicleDetails, autoPolicy and localTax must include all fields and their values when updating any field within that object.The operation returns checksums for any employee record files that were updated. For example, it returns a compensationChecksum value for any changes to fields in the Employee Pay record.SecurityThis operation supports field-level security: for any web service us…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateEmployeeFieldsRequest`

**Responses:**
- `200` — successful operation → `UpdateEmployeeFieldsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /employee/v1/updateEmployeeSkills`
**Operation:** `updateEmployeeSkills`

**Summary:** Update employee skills and education

**Description:** This endpoint updates an employee's skills and education. To obtain the checksum for this endpoint, call EmployeeService.getEmployee with the Skills option and collect the skillChecksum value. Note: You must include all existing skills and education information, or they will be deleted.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateEmployeeSkills`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /employee/v1/updateEmployeeStatusType`
**Operation:** `updateEmployeeStatusType`

**Summary:** Change employee status/type

**Description:** Use this method to change an employee's employment status or type. Statuses indicate whether the employee is active, on leave, or terminated. Types indicate things such as full- or part-time employment. This requires that the user has a PrismHR user account; see Set Up a PrismHR Web Services User Account in the documenation. The updateEmployeeStatusType operation also fires the validateEmployeeStatusType operation, which first makes sure there are no issues; see validateEmployeeStatusType for a list of error messages that operation might return. If there are no issues, the employee's employmen…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeStatusType`

**Responses:**
- `200` — successful operation → `EmployeeStatusTypeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updateFutureAssignment`
**Operation:** `updateFutureAssignment`

**Summary:** future date changes.

**Description:** Use this method to make future date changes for Division, Department, Location or Benefit group.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `changeType`, `clientId`, `employeeId`, `futureDate`, `newAssignment`

**Responses:**
- `200` — successful operation → `UpdateFutureAssignmentResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /employee/v1/updateJobCode`
**Operation:** `updateJobCode`

**Summary:** Update job/position information

**Description:** This operation updates employee job/position information. To get the values for jobCode and reasonCode, call ClientMasterService.getClientCodes with the options Job and Reason.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateJobCode`

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updatePayGroup`
**Operation:** `updatePayGroup`

**Summary:** Update pay group information

**Description:** This operation updates employee pay group information.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`, `employeeId`, `payGroup`

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updatePayMethod`
**Operation:** `updatePayMethod`

**Summary:** Update pay method information

**Description:** This operation updates employee pay method information. You can use this in conjunction with updatePayRate in order to update an employee's pay information. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record. Collect the checksum for this operation from EmployeeService.getEmployee with the Compensation option.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdatePayMethod`

**Responses:**
- `200` — successful operation → `ServiceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updatePayRate`
**Operation:** `updatePayRate`

**Summary:** Update pay rate information

**Description:** This operation updates employee pay rate information. You can use this in conjunction with updatePayMethod in order to update an employee's pay information.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdatePayRate`

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updateScheduledDeduction`
**Operation:** `updateScheduledDeduction`

**Summary:** Update employee's scheduled deductions

**Description:** Use this method to update one or more of an employee's scheduled deductions. These are one-time or temporary deductions and do not include standard deductions or garnishments. The updateScheduledDeduction operation replaces the entire record, therefore you must ensure that you include any existing scheduled deductions that are not changing along with the new deductions. The checksum required to update an employee's scheduled deductions, along with the list of existing scheduled deductions, may be obtained by calling employee/getScheduledDeductions. To update voluntary recurring deductions see …

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateScheduledDeduction`

**Responses:**
- `200` — successful operation → `ServiceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/updateW4`
**Operation:** `updateW4`

**Summary:** Update W-4 tax information

**Description:** This operation updates tax information for the Form W-4. The system validates the updated fields against those required by the state; call the TaxRateService.getStateW4Params method to ensure that you have all of the necessary information. Note that a checksum attribute is required, which is used to avoid a conflict with other transactions that might be in flight. To obtain the compensationChecksum, call the EmployeeService.getEmployee operation, and specify the class 'Compensation' for the Options parameter. This API requires that all data retrieved from the corresponding get operation be sup…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateW4`

**Responses:**
- `200` — successful operation → `EmployeeUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/validateEmployeeStatusType`
**Operation:** `validateEmployeeStatusType`

**Summary:** Validate employee status/type change

**Description:** This operation checks for any issues with employee status/type change. If there are issues, it returns one or more of the error or warning messages listed below.Error Type Error MessageE0004REASON_CODE is not a valid Reason Code.E0005This person is a COBRA participant who is a dependent of an employee. Cannot Change Type or Status.E0006This employee currently has an ACTIVE status for COBRA. Their COBRA coverage should be terminated. Cannot Change Type or Status.E0007REASON_CODE is not a valid Status/Type change reason.E0008REASON_CODE is flagged as obsolete.E0009EMPLOYEE_STATUS_CODE has a Stat…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeStatusType`

**Responses:**
- `200` — successful operation → `EmployeeStatusTypeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/validateEmployeeTerminate`
**Operation:** `validateEmployeeTerminate`

**Summary:** Validate employee termination

**Description:** This operation checks for issues with terminating the employee's employment with the specified client. If there are issues, it returns one or more of the error or warning messages listed below.Error TypeError MessageE0001This employee EMPLOYEE_ID is already terminated!E0002You may not perform a DESC on employee with a type of TYPE.CODE.REC<1>E0003You may not perform a DESC on employee with a status of STATUS.CODE.REC<1>E0004Cannot find SSN for this employeeE0005This person is a COBRA participant who is a dependent of an employee. Cannot TerminateE0006This employee currently has an ACTIVE statu…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ValidateTerminateRequest`

**Responses:**
- `200` — successful operation → `ValidateEmployeeTerminateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/validateReactivate`
**Operation:** `validateReactivate`

**Summary:** validation to reactivate an employee on leave

**Description:** This operation checks for any issues with reactivating an employee on leave. If there are issues, it returns one or more of the error or warning messages listed below.Error Type Error MessageE0004REASON_CODE is not a valid Reason Code.E0005This person is a COBRA participant who is a dependent of an employee. Cannot change type or status.E0007REASON_CODE is not a valid reactivation reason.E0008REASON_CODE is flagged as obsolete.E0010EMPLOYEE_STATUS_CODE does not have correct Status classification for reactivation.E0011EMPLOYEE_STATUS_CODE is flagged as obsolete.E0012EMPLOYEE_TYPE_CODE is not va…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeReactivation`

**Responses:**
- `200` — successful operation → `EmployeeReactivationResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /employee/v1/validateTakeLeaveOfAbsence`
**Operation:** `validateTakeLeaveOfAbsence`

**Summary:** Validate to take leave of absence

**Description:** This operation checks for any issues with taking a leave of absence for an employee. If there are issues, it returns one or more of the error or warning messages listed below.Error Type Error MessageE0004REASON_CODE is not a valid Reason Code.E0005This person is a COBRA participant who is a dependent of an employee. Cannot take leave of absence.E0007REASON_CODE is not a valid Leave of Absence reason.E0008REASON_CODE is flagged as obsolete.E0010EMPLOYEE_STATUS_CODE does not have correct status classification for leave of absence.E0011EMPLOYEE_STATUS_CODE is flagged as obsolete.E0012EMPLOYEE_TYP…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeLeaveOfAbsence`

**Responses:**
- `200` — successful operation → `EmployeeLeaveOfAbsenceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---
