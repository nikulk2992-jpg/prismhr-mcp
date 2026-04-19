# Service: `humanResources`

**7 methods** in this service.

## `GET /humanResources/v1/getAssignedPendingApprovals`
**Operation:** `getAssignedPendingApprovals`

**Summary:** get a list of pending approvals

**Description:** This API operation returns a list of pending approvals assigned to a specified PrismHR user

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, optional) — client identifier
- `prismUserId` (query, required) — the PrismHR username for which assigned pending approvals should be returned

**Responses:**
- `200` — successful operation → `PendingApprovalsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /humanResources/v1/getOnboardTasks`
**Operation:** `getOnboardTasks`

**Summary:** Get onboarding tasks

**Description:** Use this operation to download a JSON object summary of onboarding tasks for clients. You can also filter the results by clientList (comma separated client ids), task, or fromDate. Note 1: For information about properly using this operation to keep third-party application data synchronized, please see the getData Best Practices documentation. Note 2: Web Service Users cannot call multiple concurrent instances of this method. Please wait until the first instance returns a buildStatus of 'DONE', retrieve your download link, and then, if necessary, invoke this method again. If you try to call a s…

**Parameters:**
- `sessionId` (header, required) — session identifier
- `downloadId` (query, optional) — used to check status of and eventually download the onboard tasks data
- `clientList` (query, optional) — comma separated list of client ids
- `fromDate` (query, optional) — only return tasks from the date entered to the current date
- `task` (query, optional) — only return tasks for the task id. Valid task ids are 1 -> I9 section 1, 2 -> Employee information, 3 -> I9 Section 2 or 4 -> All other forms

**Responses:**
- `200` — successful operation → `DataResponseWithWarnings`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /humanResources/v1/getStaffingPlacement`
**Operation:** `getStaffingPlacement`

**Summary:** Get staffing placement record

**Description:** Use this operation to return information about a specific staffing placement. Use the checksum returned by this method to update an existing placement using HumanResourcesService.setStaffingPlacement.

**Parameters:**
- `sessionId` (header, required) — session identifier
- `vendorId` (query, required) — vendor identifier
- `staffingClient` (query, required) — client identifier under the vendor
- `placementId` (query, required) — staffing placement identifier

**Responses:**
- `200` — successful operation → `GetStaffingPlacementResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[getStaffingPlacementList]]

---

## `GET /humanResources/v1/getStaffingPlacementList`
**Operation:** `getStaffingPlacementList`

**Summary:** Get staffing placement ids

**Description:** Use this operation to retrieve a list of staffing placement IDs associated with a specified employee. You can also filter the output by client ID. This operation also returns paginated results when more than 500 placement IDs are returned. Use the count and startpage query parameters to navigate through the list of placement IDs. count specifies the number of placement IDs to return per page, and startpage indicates the starting position in the placement ID list. The operation returns these parameters in the response object as well, along with the total number of placement IDs.

**Parameters:**
- `sessionId` (header, required) — session identifier
- `clientId` (query, optional) — client identifier
- `employeeId` (query, required) — employee identifier
- `isActive` (query, optional) — if true, will return active placements IDs with no endDate or a future endDate; if false (default), will return all placement IDs
- `count` (query, optional) — number of placements returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetStaffingPlacementListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /humanResources/v1/performOnboardingAction`
**Operation:** `performOnboardingAction`

**Summary:** perform action on onboarding tasks

**Description:** Use this operation to initiate specific onboarding actions based on the provided input parameters. Currently the only available action is sending a reminder email to the user who needs to perform the action 'SENDREMINDER'. This method enables you to send one or more reminder emails per input taskId and prehireId as long as all those tasks are the same type.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`, `prehireId`, `taskId`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /humanResources/v1/reassignPendingApprovals`
**Operation:** `reassignPendingApprovals`

**Summary:** assign pending approvals from one PrismHR user to another

**Description:** This API operation reassigns pending approvals from one PrismHR user to another. Pending approvals may be obtained by calling HumanResourcesService.getAssignedPendingApprovals. All valid approval IDs provided will be assigned from the fromUser provided to the toUser. If any invalid approval IDs are provided, an error message and error code will be provided for the applicable approval ID in the updateResult array. Error codes are defined in the following table. Error codeDescription 0 Approval record successfully reassigned. NOT_FOUND Approval ID not found. NOT_ASSIGNED Approval is not currentl…

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `approvalId`, `clientId`, `fromUser`, `toUser`

**Responses:**
- `200` — successful operation → `ReassignPendingApprovalsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /humanResources/v1/setStaffingPlacement`
**Operation:** `setStaffingPlacement`

**Summary:** create or update staffing placement record

**Description:** Use this operation to create or update staffing placement records. Use the checksum value returned by HumanResourcesService.getStaffingPlacement when calling this method.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetStaffingPlacementRequest`

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
