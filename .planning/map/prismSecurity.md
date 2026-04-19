# Service: `prismSecurity`

**17 methods** in this service.

## `GET /prismSecurity/v1/getAllowedEmployeeList`
**Operation:** `getAllowedEmployeeList`

**Summary:** Get list of allowed employees

**Description:** This endpoint returns a list of employees associated with the specified client and accessible to the specified PrismHR user. You can also filter and paginate the response, if necessary. Use employeeId, firstName, and lastName to filter the response by employee name or ID. The API matches these values against the beginning of the employee name or ID. For example, if you specify "Jo" in the lastName field, the API would return any employees with surnames that begin with those characters, such as Johnson or Jones. If you enter a value in more than one field, the API will only return employees who…

**Parameters:**
- `sessionId` (header, required) — session token
- `prismUserId` (query, required) — PrismHR username
- `clientId` (query, required) — client identifier
- `employeeId` (query, optional) — employee ID filter
- `lastName` (query, optional) — employee last name filter
- `firstName` (query, optional) — employee first name filter
- `employeeStatusClass` (query, optional) — available options are A T L which are Active, Terminated, On Leave
- `startpage` (query, optional) — pagination start location (first page = '0')
- `count` (query, optional) — number of records returned per page

**Responses:**
- `200` — successful operation → `PrismSecurityResponseWithPagination`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/getClientList`
**Operation:** `getClientList`

**Summary:** Get list of allowed clients

**Description:** This operation returns a list of client IDs that the PrismHR user can access.

**Parameters:**
- `sessionId` (header, required) — session token
- `prismUserId` (query, required) — the PrismHR username

**Responses:**
- `200` — successful operation → `PrismSecurityResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/getEmployeeClientList`
**Operation:** `getEmployeeClientList`

**Summary:** Get list of applicable clients for a provided employee user.

**Description:** This operation returns the list of clients and the employee's status ((A)ctive, (T)erminated, or (O)nboarding) for the specified employee user. This operation will only work with employee users, internal and trusted advisor users will return an error.

**Parameters:**
- `sessionId` (header, required) — session token
- `prismUserId` (query, optional) — Prism user identifier
- `employeeId` (query, optional) — employee identifier

**Responses:**
- `200` — successful operation → `PrismSecurityEmployeeClientList`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/getEmployeeList`
**Operation:** `getEmployeeList`

**Summary:** Get list of allowed employees

**Description:** This operation returns a list of employee IDs employed by the specified client that the PrismHR user can access.

**Parameters:**
- `sessionId` (header, required) — session token
- `prismUserId` (query, required) — the PrismHR username
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `PrismSecurityResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/getEntityAccess`
**Operation:** `getEntityAccess`

**Summary:** Get entities access for a user

**Description:** This operation returns the entities that a PrismHR worksite manager or trusted advisor user can access (entities are worksite locations, departments, divisions, shifts, and workgroups). If the user does not have entity access permission, this operation returns the infoMessage: “This user is not set up for entity access for the client passed.”

**Parameters:**
- `sessionId` (header, required) — session token
- `prismUserId` (query, required) — the PrismHR username
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `PrismSecurityResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/getManagerList`
**Operation:** `getManagerList`

**Summary:** Get list of managers that can see a given employee.

**Description:** This operation returns the list of PrismHR users that can see/manage a specifed user. Only users who are worksite managers or worksite trusted advisors are retrieved.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `PrismSecurityManagerList`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/getUserDataSecurity`
**Operation:** `getUserDataSecurity`

**Summary:** Get entity access settings

**Description:** This operation returns client entity access settings for a specified PrismHR user or client. If providing a user, they must be a Worksite Employee, Worksite Manager, or Worksite Trusted Advisor. Along with entity access, this endpoint will also retrieve Manager/PTO approver access if it exists and the entityCode will return a value of either MD (Manager Direct Reports), MH (Manager Full Hierarchy), PD (PTO Approver Direct Reports) or PH (PTO Approver Full Hierarchy) and the typeCode and typeDesc attributes will be returned as null. If the user is not provided or is a Worksite Employee, then a …

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `prismUserId` (query, optional) — ID of a Worksite Employee, Worksite Manager, or Worksite Trusted Advisor user (optional - omit to retrieve client data security object shell)

**Responses:**
- `200` — successful operation → `UserDataSecurityResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/getUserDetails`
**Operation:** `getUserDetails`

**Summary:** Get PrismHR user details

**Description:** This operation returns the User Details of a PrismHR user.

**Parameters:**
- `sessionId` (header, required) — session token
- `prismUserId` (query, required) — the PrismHR username

**Responses:**
- `200` — successful operation → `UserDetailResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/getUserList`
**Operation:** `getUserList`

**Summary:** Get list of PrismHR users

**Description:** This operation returns the list of PrismHR users. Only users who are service providers, worksite trusted advisors, or worksite managers are retrieved. You can choose to filter the list by client or user type.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, optional) — client identifier
- `userType` (query, optional) — user type: 'I' (service provider), 'M' (worksite manager), or 'A' (worksite trusted advisor)

**Responses:**
- `200` — successful operation → `PrismSecurityResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v2/getUserList`
**Operation:** `getUserList`

**Summary:** Get list of PrismHR users

**Description:** This operation returns the list of PrismHR users. Only users who are service providers, worksite trusted advisors, or worksite managers are retrieved. You can choose to filter the list by client or user type. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of users. count specifies the number of users to return per page, and startpage indicates the starting position in the user list. The operation returns these parameters in the response object as well, along with the total number of users. Note: If no clientId is passed,…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, optional) — client identifier
- `userType` (query, optional) — user type: 'I' (service provider), 'M' (worksite manager), or 'A' (worksite trusted advisor)
- `count` (query, optional) — number of users to return per page
- `startpage` (query, optional) — pagination start location (first page = '0’)

**Responses:**
- `200` — successful operation → `PrismSecurityResponseV2`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/getUserRoleDetails`
**Operation:** `getUserRoleDetails`

**Summary:** Get PrismHR user role details

**Description:** Use this operation to retrieve information about the form- and field-level access granted by a particular user role.

**Parameters:**
- `sessionId` (header, required) — session token
- `roleId` (query, required) — user role identifier

**Responses:**
- `200` — successful operation → `UserRoleDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /prismSecurity/v1/getUserRolesList`
**Operation:** `getUserRolesList`

**Summary:** Get PrismHR user roles list

**Description:** Use this operation to return a complete list of PrismHR user roles.

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `UserRolesListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /prismSecurity/v1/isClientAllowed`
**Operation:** `isClientAllowed`

**Summary:** Check if client is allowed

**Description:** This operation returns a Boolean value: True if the PrismHR user can access the specified client, otherwise False.

**Parameters:**
- `sessionId` (header, required) — session token
- `prismUserId` (query, required) — the PrismHR username
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `PrismSecurityResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /prismSecurity/v1/isEmployeeAllowed`
**Operation:** `isEmployeeAllowed`

**Summary:** Check if employee is allowed

**Description:** This operation returns a Boolean value: True if the PrismHR user can access the specified employee when employed by the specified client, otherwise False.

**Parameters:**
- `sessionId` (header, required) — session token
- `prismUserId` (query, required) — the PrismHR username
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `PrismSecurityResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /prismSecurity/v1/changeEmployeeUserType`
**Operation:** `changeEmployeeUserType`

**Summary:** Change a Prism user's type

**Description:** This operation changes a Prism user's type from (E)mployee to (M)anager or vice versa. If changing from E to M, then the userRole and dataSecurity arrays are required. If changing from M to E, then these arrays should be omitted from the request. Use PrismSecurityService.getUserDetails to obtain the required checksum and, if changing user type to M, PrismSecurityService.getUserDataSecurity to obtain a data security object shell for any clients you wish to grant access. Along with entity access, you can also use this endpoint to set up Manager/PTO approver access. To set it up, pass only one va…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PrismUserChange`

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

## `POST /prismSecurity/v1/setUserDataSecurity`
**Operation:** `setUserDataSecurity`

**Summary:** Change a Prism user's data security

**Description:** This operation changes a Prism user's data security settings for a given client. Use PrismSecurityService.getUserDataSecurity to obtain a data security object for any clients you wish to grant access. Along with entity access, you can also use this endpoint to set up Manager/PTO approver access. To set it up, you need to pass only one value for the entityCode attribute. Allowed values are MANAGERDIRECTREPORTS, PTOAPPROVERDIRECTREPORTS, MANAGERHIERARCHY or PTOAPPROVERHIERARCHY. The entityName attribute will get auto-populated. Please note: This API operation can only be used on user types M and…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PrismUserUpdateDataSecurity`

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

## `POST /prismSecurity/v1/updateManagerUserRole`
**Operation:** `updateManagerUserRole`

**Summary:** Change a Prism user's roles

**Description:** This operation changes a PrismHR user's roles, Human Resources roles, and Suppress Payroll Warning codes (only applicable to HR role Payroll Processor). Use PrismSecurityService.getUserDetails to obtain the required checksum. See tables below for valid Human Resources roles and Suppress Payroll Warning codes. Please note: This API operation can only be used on user types M and A; any other user type will return an error. Human Resource Roles HR Role Code HR Role Description MAN Employee's Manager (Leave Request Only) HRA H/R Action Approver PRA Payroll Approver PRP Payroll Processor TSE Time S…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PrismUserUpdateRoles`

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
