# Service: `documentService`

**4 methods** in this service.

## `GET /documentService/v1/getDocumentTypes`
**Operation:** `getDocumentTypes`

**Summary:** Get document types

**Description:** The operation returns information about document types related to PrismHR Document Management.

**Parameters:**
- `sessionId` (header, required) — session token
- `documentTypeId` (query, optional) — document type ID(s)

**Responses:**
- `200` — successful operation → `DocumentTypesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /documentService/v1/getRuleset`
**Operation:** `getRuleset`

**Summary:** Get document management ruleset

**Description:** For internal use only.

**Parameters:**
- `sessionId` (header, required) — session token
- `userId` (query, required) — username
- `clientId` (query, required) — client identifier
- `userType` (query, required) — user type: 'I' (Internal User (service provider)), 'C' (Worksite Manager), 'A' (Worksite Trusted Advisor), or 'E' (Employee)
- `context` (query, required) — name of the ruleset

**Responses:**
- `200` — successful operation → `documentResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /documentService/v1/uploadDocument`
**Operation:** `uploadDocument`

**Summary:** Upload Document

**Description:** This operation uploads a document to the Document Management service. Use DocumentService.getDocumentTypes to obtain the documentType (id) and scope available on the account. Note: Document data in the fileData field must use Base64 encoding. Please use an external conversion tool to obtain the fileData in the proper format; the PrismHR API does not provide Base64 encoding functionality.

**Request body:**
- Content-Type: `application/json`
- Schema: `UploadDoc`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /documentService/v1/validateSsoToken`
**Operation:** `validateSsoToken`

**Summary:** Validate ssoToken with context from DocumentService.getRuleset

**Description:** For internal use only.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `ssoToken`

**Responses:**
- `200` — successful operation → `ImagingSignOnResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---
