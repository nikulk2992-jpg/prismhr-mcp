# Service: `applicant`

**3 methods** in this service.

## `GET /applicant/v1/getJobApplicantList`
**Operation:** `getJobApplicantList`

**Summary:** Get a list of job applicants

**Description:** This operation returns an array of all the job applicants/candidates for the specified client or clients. To retrieve applicants from multiple clients, pass a comma-separated list of values for the clientId. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of applicants. count specifies the number of applicants to return per page, and startpage indicates the starting position in the applicant list. The operation returns these parameters in the response object as well, along with the total number of applicants.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier--up to 20 IDs can be passed, separated by commas
- `applicantId` (query, optional) — applicant Id
- `applyDate` (query, optional) — application date (YYYY-MM-DD format)
- `lastName` (query, optional) — applicant last name
- `count` (query, optional) — number of records returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')
- `listName` (header, optional) — unique list name required when multiple client ids are passed

**Responses:**
- `200` — successful operation → `JobApplicantListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /applicant/v1/getJobApplicants`
**Operation:** `getJobApplicants`

**Summary:** Get a list of job applicants

**Description:** This operation returns an array of all the job applicants/candidates for the specified client. By default, this operation masks certain personally identifiable information (PII) in its response, such as applicant social security number and date of birth. Please refer to the API documentation article on Unmasking PII to learn how to unmask this data.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `id` (query, optional) — applicant identifier

**Responses:**
- `200` — successful operation → `JobApplicantResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /applicant/v1/createJobApplicant`
**Operation:** `createJobApplicant`

**Summary:** Create a new applicant or candidate for new hires

**Description:** This operation creates a new job applicant and returns a new applicantId. You can review applicants and their data on the Job Candidates form in PrismHR; to look up information for the applicant you created, enter the applicantId value in the Candidate Number field. This operation enables import of applicants/new hire candidates into PrismHR from an external source, such as an applicant tracking system. Since these external systems may vary substantially, this operation is designed to be as flexible as possible, with minimal restrictions and validations on the input fields.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `CreateJobApplicant`

**Responses:**
- `200` — successful operation → `JobApplicantResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---
