# Service: `newHire`

**8 methods** in this service.

## `GET /newHire/v1/getNewHireQuestions`
**Operation:** `getNewHireQuestions`

**Summary:** Get new hire questions associated with state code

**Description:** Use this operation to return new hire and state default questions associated with a particular state code. This information is set up on the New Hire Questions form and assigned on the State Rules form in PrismHR.

**Parameters:**
- `sessionId` (header, required) — session token
- `stateCode` (query, required) — Enter a two-character state code to return new hire questions for that state.

**Responses:**
- `200` — successful operation → `NewHireQuestionsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /newHire/v1/getNewHireRequiredFields`
**Operation:** `getNewHireRequiredFields`

**Summary:** Get list of required fields for new hires

**Description:** This operation retrieves a list of required fields for a new hire for the specified client. The required fields are listed for both the PrismHR New Hire form and electronic onboarding, and they include either the global required fields or the list of fields particular to the client. (In PrismHR, the global-level required fields are defined in the Global New Hire Fields form, and client fields are defined in the New Hire Optional Fields form as well as the Control tab of Client Details.)

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `NewHireRequiredFieldsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /newHire/v1/EPHire`
**Operation:** `EPHire`

**Summary:** Enroll an employee in the Employee Portal new hire process

**Description:** Use this operation to enroll an employee in the Employee Portal new hire process. After a successful call, the operation automatically sends a confirmation email to collect the employee's personal information including ssn and date of birth. To override the automatic email, set manualEmailRequest to true. Requirements: The client must use the PrismHR onboarding module and must be set up for the Employee Portal new hire process. To use this method, you must have an existing PrismHR user account with the same User ID as your Web Service User. For more information, please see Using the API > Pris…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EPHireRequest`

**Responses:**
- `200` — successful operation → `CreateEpHireResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /newHire/v1/cancelImport`
**Operation:** `cancelImport`

**Summary:** Cancel import operation

**Description:** The cancelImport operation will remove all uncommitted employees from the temporary file that are tagged with the specified batch number and client ID. It also cleans up the batch ID number and recycles it for reuse. Note: Be sure you cancel any import batches where all of the employees are not hired (committed). If you do not cancel them, they will remain in "limbo" within the import file indefinitely.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `importBatchId` (query, required) — the batch ID produced by the importEmployees operation

**Responses:**
- `200` — successful operation → `CancelledHiresResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /newHire/v1/commitEmployees`
**Operation:** `commitEmployees`

**Summary:** Commit employees operation

**Description:** The commitEmployees operation performs a final check on a few attributes, for example the SSN, to ensure that each employee has not already been hired (through a different session) and then actually hires the employee, reporting any failures. Note: Be sure you cancel any import batches where all of the employees are not hired (committed). If you do not cancel them, they will remain in "limbo" within the import file indefinitely.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `importBatchId` (query, required) — the batch ID produced by the importEmployees operation

**Responses:**
- `200` — successful operation → `CommitEmployeesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /newHire/v1/getPrehireDetails`
**Operation:** `getPrehireDetails`

**Summary:** Get prehire record details

**Description:** This operation retrieves record details for prehire(s) for the specified client. Prehires are created when the company uses PrismHR Onboarding (NextGen-OBBE) and new hire information is entered. Retrieve the prehire record using the prehire id or a combination of ssn and last name.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`

**Responses:**
- `200` — successful operation → `PrehireDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /newHire/v1/importEmployees`
**Operation:** `importEmployees`

**Summary:** Import a batch of employee records

**Description:** The PrismHR API employee import is a file-based utility similar to the PrismHR expanded employee Import. Please note that the "errorCode" parameter will only be non-zero if there is a problem with the entire employee import operation. If there are errors pertaining to an individual employee in the import, the "validFlag" parameter in the "importedHire" array for that employee will be set to false. It is possible that all employees in the import might have errors, in which case the "validFlag" for each employee would be false, but the "errorCode" would still be zero. Detailed error and/or warni…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `NewHire`

**Responses:**
- `200` — successful operation → `ImportEmployeesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[importEmployeesAllowingCrossHire]]

---

## `POST /newHire/v1/importEmployeesAllowingCrossHire`
**Operation:** `importEmployeesAllowingCrossHire`

**Summary:** Import a batch allowing a cross hire

**Description:** The PrismHR API employee import is a file-based utility similar to the PrismHR expanded employee Import.The NewHireService.importEmployeesAllowingCrossHire operation is very similar to the importEmployees operation, with the additional option to hire an existing employee into an additional company. Your organization should consider restricting its use, instead of using it in place of the importEmployees operation. | Note: It is recommended that you restrict the use to service providers only. Typically, client companies would not import employees using this method because service providers must…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `NewHire`

**Responses:**
- `200` — successful operation → `ImportEmployeesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---
