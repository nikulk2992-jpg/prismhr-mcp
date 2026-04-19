# Service: `login`

**6 methods** in this service.

## `GET /login/v1/checkPermissionsRequestStatus`
**Operation:** `checkPermissionsRequestStatus`

**Summary:** get status for API permissions request

**Description:** This API operation returns the status for the API permissions request.

**Parameters:**
- `sessionId` (header, required) — session token
- `webServiceUser` (query, required) — the web service user ID

**Responses:**
- `200` — successful operation → `PermissionsRequestStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /login/v1/getAPIPermissions`
**Operation:** `getAPIPermissions`

**Summary:** get current API permissions

**Description:** This API operation returns the current API permissions for the logged in web service user.

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `CurrentApiPermissionsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /login/v1/createPeoSession`
**Operation:** `createPeoSession`

**Summary:** Create a session token

**Description:** Authenticate and create a session token that can be used with subsequent calls to API operations. With each API call, you must check for the expiration of the API session, either by comparing the value in the errorMessage parameter against the literal string "this user session has expired" or by checking if the HTTP response code is 401: Unauthorized.

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `password`, `peoId`, `username`

**Responses:**
- `200` — successful operation → `loginResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `403` — the login attempt was unsuccessful → _(no schema)_
- `404` — the provided peoId could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the API is currently undergoing maintenance and is temporarily unavailable → _(no schema)_

---

## `POST /login/v1/invalidateSession`
**Operation:** `invalidateSession`

**Summary:** Invalidate a session token

**Description:** Use this method to invalidate session token.

**Parameters:**
- `sessionId` (header, required) — Session identifier

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `403` — the login attempt was unsuccessful → _(no schema)_
- `404` — the provided peoId could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the API is currently undergoing maintenance and is temporarily unavailable → _(no schema)_

---

## `POST /login/v1/keepAlive`
**Operation:** `keepAlive`

**Summary:** keep a session alive

**Description:** Use this method to ping and keep a session alive. You will require a valid session id to perform this operation.

**Parameters:**
- `sessionId` (header, optional) — session identifier

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the API is currently undergoing maintenance and is temporarily unavailable → _(no schema)_

---

## `POST /login/v1/requestAPIPermissions`
**Operation:** `requestAPIPermissions`

**Summary:** request new API permissions

**Description:** Use this method to request additional API permissions for a given web service user. This operations will not update user permissions, it will only save the update schema to be updated at a later time by the PEO or account owner. If there is already a pending update request saved for the specified user, the operation will return HTTP code 429 unless overwritePendingRequest is set to true. Note: Be sure to include all required methods and IPs, not just the new ones, as the permissions update process will change the web service user record to only include those provided here.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ApiPermissionsRequest`

**Responses:**
- `200` — successful operation → `ApiPermissionsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `429` — there is already a pending update request saved and overwritePendingRequest is false → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---
