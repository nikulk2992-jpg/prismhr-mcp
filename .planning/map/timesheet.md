# Service: `timesheet`

**7 methods** in this service.

## `GET /timesheet/v1/getBatchStatus`
**Operation:** `getBatchStatus`

**Summary:** Get the status of a payroll batch

**Description:** This operation returns the current status of the specified payroll batch. The returned checksum is used with /timesheet/finalizePrismBatchEntry in order to ensure that the payroll batch has not been changed since it was last read.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch number

**Responses:**
- `200` — successful operation → `TimesheetBatchStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /timesheet/v1/getParamData`
**Operation:** `getParamData`

**Summary:** Get the list of available templates and batches

**Description:** This operation retrieves the list of templates and payroll batches that are available for web use.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `userId` (query, optional) — user identifier used to match data submitted by Timesheet.upload with call to Timesheet.accept; the strings must match to ensure that separate upload sessions do not include the same information

**Responses:**
- `200` — successful operation → `TimesheetGetParamDataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /timesheet/v1/getTimeSheetData`
**Operation:** `getTimeSheetData`

**Summary:** Get the timesheet data for a payroll batch

**Description:** Use this method to get time sheet data for PrismHR clients. This operation returns the employees in the payroll batch and any associated timesheet data: charge date, pay code, hours/units paid, hours worked, pay rate, pay amount, position, location, division, department, project, shift, and project phase.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch number

**Responses:**
- `200` — successful operation → `TimesheetGetTimeSheetDataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /timesheet/v1/accept`
**Operation:** `accept`

**Summary:** Commit the data to the batch

**Description:** This operation performs a final validation against the pay import data that is in temporary storage and then commits the data to the payroll batch.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `batchList`, `clientId`, `uploadId`, `userId`

**Responses:**
- `200` — successful operation → `TimesheetAcceptResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /timesheet/v1/finalizePrismBatchEntry`
**Operation:** `finalizePrismBatchEntry`

**Summary:** Finalize all employees' time sheets

**Description:** This operation finalizes all of the employees' time sheets for the specified batch. Any errors on individual employees' time sheets that cause the batch not to be finalized will result in an error. The checksum returned by /timesheet/getBatchStatus is required in order to ensure that the payroll batch has not been changed since it was last read.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `batchId`, `checksum`, `clientId`

**Responses:**
- `200` — successful operation → `TimesheetBasicResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /timesheet/v1/reject`
**Operation:** `reject`

**Summary:** Revert the status of the batch

**Description:** This operation reverts the status of the payroll batch and also clears the temporary holding area and any uploaded data contained within. Call this method if the client application decides not to approve pay data that has been uploaded.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `batchList`, `clientId`, `uploadId`, `userId`

**Responses:**
- `200` — successful operation → `TimesheetRejectResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /timesheet/v1/upload`
**Operation:** `upload`

**Summary:** Upload pay import data into a temporary holding area

**Description:** This operation uploads the pay import data into a temporary holding area and performs validations against the data. The response identifies those records that did not pass validation. This operation can be called repeatedly, and it will overwrite the previous upload. This allows the client application to look at the response, correct problems, and then upload again. Note that it also returns an uploadId, which is used for the TimesheetService.reject and TimesheetService.approve operations.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `batchList`, `clientId`, `fileData`, `templateId`, `userId`

**Responses:**
- `200` — successful operation → `TimesheetUploadResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---
