# Service: `taxRate`

**8 methods** in this service.

## `GET /taxRate/v1/getStateW4Params`
**Operation:** `getStateW4Params`

**Summary:** Get W4 parameters for a given state

**Description:** Use this method to retrieve the Form W-4 parameters required in the specified state. This also includes the values that are allowed, if any, such as valid filing statuses defined by the state. Use this method with EmployeeService.updateW4 to ensure that you have all of the necessary information.

**Parameters:**
- `stateCode` (query, required) — two-character state code
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `W4StateParamsResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /taxRate/v1/getSutaInformation`
**Operation:** `getSutaInformation`

**Summary:** Retrieve Employee SUTA Reporting Information

**Description:** Use this method to determine an employee's state unemployment tax (SUTA) reporting basis. Depending on the reporting basis, the operation returns the SUTA information relevant to that basis for the employee.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `effectiveDate` (query, optional) — date for which to calculate SUTA basis (YYYY-MM-DD format; default is today's date)

**Responses:**
- `200` — successful operation → `SutaInformationResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /taxRate/v1/getTaxAuthorities`
**Operation:** `getTaxAuthorities`

**Summary:** Get tax authorities

**Description:** This operation returns a list of local tax authorities for the specified state.

**Parameters:**
- `stateCode` (query, optional) — two-character state code
- `authorityId` (query, optional) — authority id
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `TaxAuthoritiesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /taxRate/v1/getTaxRate`
**Operation:** `getTaxRate`

**Summary:** Get tax rates

**Description:** This operation returns an object containing the federal and state tax rates and limits, including OASDI, FUTA, MediCare, and SUTA, as well as the workers' compensation gross rate, multiplier, and discount. If there are state- or client-level overrides of the FUTA rates, the operation returns those values in place of the system-level values. This is designed to get specific information, which might be used to write an initial quote for a potential client company.

**Parameters:**
- `workersCompPolicyId` (query, required) — policy ID retrieved by getWorkersCompPolicyList
- `workersCompClass` (query, required) — classification retrieved by getWorkersCompClasses
- `employerId` (query, required) — _(no description)_
- `effectiveDate` (query, required) — the policy effective date (YYYY-MM-DD format)
- `clientId` (query, optional) — For future development. Client overrides are not currently supported. Leave blank.
- `stateCode` (query, required) — the two-character state code for this transaction
- `mode` (query, optional) — Currently, only PEO (cost) is supported. Always pass P. Other modes will be supported in some future release.
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `TaxRatesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /taxRate/v1/getWorkersCompClasses`
**Operation:** `getWorkersCompClasses`

**Summary:** Get workers' compensation classes

**Description:** This operation returns a list of workers' comp classification codes and descriptions for the specified state.

**Parameters:**
- `stateCode` (query, required) — two-character state code
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `WorkersCompClassesResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /taxRate/v1/getWorkersCompPolicyDetails`
**Operation:** `getWorkersCompPolicyDetails`

**Summary:** Get workers' compensation policy with details

**Description:** This operation returns information about a specified workers' compensation policy.

**Parameters:**
- `sessionId` (header, required) — session token
- `policyId` (query, required) — workers' compensation policy identifier

**Responses:**
- `200` — successful operation → `WorkersCompPoliciesDetailResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /taxRate/v1/getWorkersCompPolicyList`
**Operation:** `getWorkersCompPolicyList`

**Summary:** Get workers' compensation policy list

**Description:** This operation returns a list of all system-level workers' compensation policies, along with some descriptive information about each policy.

**Parameters:**
- `effectiveDate` (query, optional) — date when coverage begins under this policy (this is the beginning of the policy year)
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `WorkersCompPoliciesResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /taxRate/v1/setWorkersCompPolicyDetails`
**Operation:** `setWorkersCompPolicyDetails`

**Summary:** update or create Workers' Compensation insurance policy details

**Description:** Use this operation to set or update Workers' Compensation policy data. Use the checksum value returned by TaxRateService.getWorkersCompPolicyDetails. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `WorkersCompPoliciesDetailUpdate`

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
