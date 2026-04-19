# Service: `signOn`

**11 methods** in this service.

## `GET /signOn/v1/getEmployeeImage`
**Operation:** `getEmployeeImage`

**Summary:** Get employee image

**Description:** This operation enables downloading employee image data in Base64 format, if an image exists for the employee. The Base64 data must be manually converted back to an image.

**Parameters:**
- `sessionId` (header, required) — session token
- `userId` (query, required) — user ID of the employee

**Responses:**
- `200` — successful operation → `GetEmployeeImageResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /signOn/v1/getFavorites`
**Operation:** `getFavorites`

**Summary:** Get favorites

**Description:** This method returns an array of the user's favorite PrismHR forms with names and formIds. Using the formId, inbound single sign-on can access the PrismHR form directly; refer to the Single Sign-On User Guide for more information.

**Parameters:**
- `sessionId` (header, required) — session token
- `userId` (query, required) — user identifier

**Responses:**
- `200` — successful operation → `SignOnResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /signOn/v1/getVendorInfo`
**Operation:** `getVendorInfo`

**Summary:** Get vendor info

**Description:** Use this operation to retrieve vendor-specific custom field data associated with a particular PrismHR user.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `userId` (query, required) — ID of the PrismHR user associated with the vendor field or fields
- `extVendorId` (query, required) — SSO Service ID associated with the vendor in PrismHR
- `userType` (query, required) — type of PrismHR user. This value is used to look up the correct custom vendor fields for the user, client, and vendor. I (service provider), A (worksite trusted advisor), M (worksite manager), E (worksite employee),

**Responses:**
- `200` — successful operation → `GetVendorInfoResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /signOn/v1/redirectUrlByEmployee`
**Operation:** `redirectUrlByEmployee`

**Summary:** Redirect URL by employee

**Description:** This operation redirects employee users for single sign-on from a third-party product to PrismHR Employee Portal. To call this endpoint, a web service user must have it listed in their Allowed Methods.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `componentId` (query, optional) — for future development; does not currently impact the redirect URL

**Responses:**
- `200` — successful operation → `SignOnResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /signOn/v1/redirectUrlByUser`
**Operation:** `redirectUrlByUser`

**Summary:** Redirect URL by user

**Description:** Use this method to redirect any user type for inbound single sign-on from a third-party product to PrismHR, or Employee Portal. This method may also be used for outbound single sign-on using a PrismHR user ID into any SSO service defined on the account. The SSO service must be marked as "Outbound" under "Service Destination" in the SSO Services form. To call this endpoint, a web service user must have it listed in their Allowed Methods.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `userId` (query, required) — user identifier
- `userType` (query, required) — the user type for this transaction: 'E' (Employee), 'C' (Manager or Trusted Advisor), 'I' (Service Provider)
- `componentId` (query, optional) — For deep linking to a particular feature in the PrismHR product (such as New Hire), specify the form's process ID. Use prismSecurity/getUserDetails to get a list of all the process IDs that a specific user can access in the Prism Administrative Portal. To direct trusted advisors to the employee portal use componentId EMPLOYEEPORTALAPI. To direct managers to the employee portal enter the userType = “E” with no componentId entered.

**Responses:**
- `200` — successful operation → `SignOnResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /signOn/v1/registerPrismEmployee`
**Operation:** `registerPrismEmployee`

**Summary:** Register PrismHR Employee

**Description:** This operation enables single sign-on to PrismHR Employee Portal. The client specified must be a PrismHR client, and the employee must be employed by that client. If the employee has more than one employer, all of the employing clients must also be PrismHR clients. The return value depends on the user's registration: If this employee is already registered (has a user ID) then the existing userId is returned, along with a flag isNew set to false. If not already registered, a new userId is automatically assigned and returned, along with the flag isNew set to true. It is not possible to assign a …

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`, `employeeId`

**Responses:**
- `200` — successful operation → `SignOnResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `409` — the request conflicts with the current state of the record → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /signOn/v1/registerPrismManager`
**Operation:** `registerPrismManager`

**Summary:** Register PrismHR Manager User

**Description:** This operation registers a Prism (M)anager or Trusted (A)dvisor user for use with our SSO services. This operation does not support setting passwords or password reset parameters, so the user created here cannot be used to login directly to PrismHR. The userRole and dataSecurity arrays are required. Use PrismSecurityService.getUserDataSecurity to obtain a data security object shell for any clients you wish to grant access. Along with entity access, you can also use this endpoint to set up Manager/PTO approver access. To set it up, pass only one value for the entityCode attribute. Allowed value…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `RegisterPrismManagerRequest`

**Responses:**
- `200` — successful operation → `RegisterPrismManagerResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the request conflicts with the current state of the record → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /signOn/v1/registerPrismPrehire`
**Operation:** `registerPrismPrehire`

**Summary:** Register PrismHR Prehire

**Description:** This method allows a single sign-on to PrismHR Onboarding. This method accepts the clientId and EITHER a prehire ID OR an SSN and last name. The client specified must be a PrismHR client, and the prehire must be registered with that client. If SSN and last name are provided, the prehire cannot have already begun the prehire workflow process. The return value depends on the user's registration: If this prehire is already registered (has a user ID) then the existing userId is returned, along with a flag isNew set to false. If not already registered, a new userId is automatically assigned and ret…

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`

**Responses:**
- `200` — successful operation → `SignOnResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the request conflicts with the current state of the record → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /signOn/v1/setEmployeeImage`
**Operation:** `setEmployeeImage`

**Summary:** Set employee image

**Description:** This operation enables uploading an employee image. The image format must be jpg and the image data must be sent in Base64.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetEmployeeImageRequest`

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

## `POST /signOn/v1/setVendorInfo`
**Operation:** `setVendorInfo`

**Summary:** create or update custom vendor fields

**Description:** Use this operation to create or update custom fields associated with a specific PrismHR user, client, and SSO vendor. Use the checksum value returned by SignOnService.getVendorInfo when calling this method.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetVendorInfoRequest`

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

## `POST /signOn/v1/validateTssoToken`
**Operation:** `validateTssoToken`

**Summary:** Validate TssoToken

**Description:** Use this method to redirect any user from a PrismHR product to a third-party product.

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `SignOnResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---
