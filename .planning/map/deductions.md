# Service: `deductions`

**8 methods** in this service.

## `GET /deductions/v1/getDeductionArrears`
**Operation:** `getDeductionArrears`

**Summary:** Get payroll deductions arrear information

**Description:** Use this operation to return information about payroll deductions in arrears for a particular employee. Benefit deductions go into arrears when employee wages are not sufficient to cover a deduction.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — the employee ID used to retrieve the deductions
- `options` (query, optional) — reserved for future use; send empty String

**Responses:**
- `200` — successful operation → `DeductionArrearsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /deductions/v1/getDeductions`
**Operation:** `getDeductions`

**Summary:** Get payroll deductions information

**Description:** This service manages what can most easily be described as the "rules" for employee payroll deductions, rather than precise values (which must be determined by looking at payroll vouchers after payroll is completed). There are three groups of deductions. Voluntary deductions, such as uniforms or movie tickets, are fixed amounts or percentages. These are added immediately to the deductions file when they are added to the system. The first group of non-voluntary deductions, such as garnishments and loans, are immediately added by the respective modules in PrismHR. The final group of deductions ar…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — the employee ID used to retrieve the deductions
- `options` (query, optional) — reserved for future use; send empty String

**Responses:**
- `200` — successful operation → `DeductionResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /deductions/v1/getEmployeeLoans`
**Operation:** `getEmployeeLoans`

**Summary:** Get employee loans information

**Description:** This operation returns all loan information for a specific employee. Use the checksum value to update an existing loan via DeductionService.setEmployeeLoanResponse.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — the employee ID used to retrieve the loans
- `loanId` (query, optional) — the loan ID. Optional parameter that allows to extract loan by Id

**Responses:**
- `200` — successful operation → `EmployeeLoanResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /deductions/v1/getGarnishmentDetails`
**Operation:** `getGarnishmentDetails`

**Summary:** Garnishment Details for the employee

**Description:** This operation returns garnishment details for a particular employee and client. To call this endpoint, it must be explicitly listed in the Allowed Methods table on the Web Service User form in PrismHR. By default, this operation masks certain personally identifiable information (PII) in its response by default, such as Issuing Authority, State Id, Payee, and Annotations. Please refer to the API documentation article Unmasking PII to learn how to unmask this data. See also the article on Option-Level Access Control to learn how to restrict this endpoint to specific garnishment types.

**Parameters:**
- `sessionId` (header, required) — Session Token
- `clientId` (query, required) — Client Identifier
- `employeeId` (query, required) — Employee Identifier
- `docketNumber` (query, optional) — Garnishment Docket Number
- `garnishmentType` (query, optional) — Garnishment Type (C- Child Support, SP- Spousal Support, I- IRS Tax Levy, B- Bankruptcy Order, S- State Tax Levy, FTB- Franchise Tax Board, O- Creditor Wage Garnishment, SL- Student Loan)

**Responses:**
- `200` — successful operation → `GarnishmentDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /deductions/v1/getGarnishmentPaymentHistory`
**Operation:** `getGarnishmentPaymentHistory`

**Summary:** Get gernishment payment history

**Description:** This operation returns an employee's garnishment payment history.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — the employee ID used to retrieve the loans
- `docketNumber` (query, optional) — docket number assigned to this garnishment

**Responses:**
- `200` — successful operation → `GarnishmentPaymentHistoryResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /deductions/v1/getVoluntaryRecurringDeductions`
**Operation:** `getVoluntaryRecurringDeductions`

**Summary:** Get voluntary recurring deductions list

**Description:** This method returns all voluntary recurring deductions for an employee. Use the checksum value to update voluntary recurring deductions via DeductionService.setVoluntaryRecurringDeductions.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — the employee ID used to retrieve the voluntary deductions

**Responses:**
- `200` — successful operation → `VoluntaryDeductionResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /deductions/v1/setEmployeeLoan`
**Operation:** `setEmployeeLoan`

**Summary:** Update or create new loan for an employee

**Description:** This method writes or updates employee loan information. To create a new employee loan, add NEW for the loanId. To update, you must include a loanId. In this case, a checksum is required and returned via DeductionService.getEmployeeLoans. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EmployeeLoanUpdate`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /deductions/v1/setVoluntaryRecurringDeductions`
**Operation:** `setVoluntaryRecurringDeductions`

**Summary:** update, add or remove a voluntary deduction for an employee

**Description:** This method updates voluntary recurring deductions. Use this method to update, add, or remove a voluntary deduction in a record, without affecting any other type of deduction. To obtain the checksum, call the DeductionService.getVoluntaryRecurringDeductions method. Please note all voluntary deductions must be included in the update or they will be deleted. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the da…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `VoluntaryDeductionUpdate`

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
