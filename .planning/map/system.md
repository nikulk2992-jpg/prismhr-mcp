# Service: `system`

**20 methods** in this service.

## `GET /system/v1/getACHFileList`
**Operation:** `getACHFileList`

**Summary:** Get ACH files list

**Description:** This operation returns a list of ACH files that can be downloaded using SystemService.streamACHData. Note: To call this endpoint, it must be listed in the web service user Allowed Methods table. In addition, the web service user cannot have any client restrictions. To gain access to Internal ACH file lists, add #INTERNAL to the end of the allowed method entry. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of ACH files. count specifies the number of files to return per page, and startpage indicates the starting position …

**Parameters:**
- `sessionId` (header, required) — session token
- `originatorId` (query, required) — ACH originator ID
- `postDateStart` (query, required) — starting date for range of post dates to return (format: YYYY-MM-DD)
- `postDateEnd` (query, optional) — optional end date for range of post dates to return (format: YYYY-MM-DD)
- `count` (query, optional) — number of ACH files returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetACHFileList`
- `204` — no content → _(no schema)_
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/getARTransactionReport`
**Operation:** `getARTransactionReport`

**Summary:** Generate an AR transaction report

**Description:** Use this operation to generate an AR transaction report. This will initialize the data retrieval and will respond with "buildStatus": "INIT". Subsequent calls to this API should be formatted exactly as the initial call, with the addition of the downloadId returned by the initial call. They will return either "buildStatus": "BUILD", "buildStatus": "ERROR", or "buildStatus": "DONE". If buildStatus is DONE, then "dataObject" will contain the URL where the data can be retrieved. Note: Web Service Users cannot call multiple concurrent instances of this method. Please wait until the first instance r…

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — identifier used to check status of / download data
- `startDate` (query, required) — AR transaction report start date (format: YYYY-MM-DD)
- `endDate` (query, required) — AR transaction report end date (format: YYYY-MM-DD)
- `clientId` (query, optional) — use this option to limit the response to one or more client IDs(optional)

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/getData`
**Operation:** `getData`

**Summary:** Retrieve datasets from the system

**Description:** Note: Web Service Users cannot call multiple concurrent instances of this method. Please wait until the first instance returns a buildStatus of "DONE," retrieve your download link, and then, if necessary, invoke this method again. If you try to call a second instance before the first one completes, the system will return HTTP response code 429 and you must complete the previous instance using the downloadId provided before initiating a new instance. This operation is used to retrieve data from PrismHR for use by external programs. The particular data to be returned is specified by the schemaNa…

**Parameters:**
- `sessionId` (header, required) — session token
- `schemaName` (query, required) — name of the object schema
- `className` (query, required) — name of the object class
- `downloadId` (query, optional) — identifier used to check status of / download data
- `clientId` (query, optional) — client identifiers, comma seperated list of client ids (optional for getData#Client|Pay and getData#Client|Deduction otherwise required)
- `employeeId` (query, optional) — employee identifier (optional)
- `startDate` (query, optional) — start date (optional; formatted YYYY-MM-DD)
- `endDate` (query, optional) — end date (optional; formatted YYYY-MM-DD)

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/getEmployerDetails`
**Operation:** `getEmployerDetails`

**Summary:** Get Employer Details

**Description:** This operation returns information about all employers in your system. It is for Service Provider users only. If you submit a single employerId (optional), this operation returns that employer's information. Note: SystemService methods have additional security restrictions. Web service users with client restrictions cannot access any SystemService API operations. Additionally, to grant access, you must explicitly list the method in the Allowed Methods section for each web service user (the Disable Method Restrictions option is ignored).

**Parameters:**
- `sessionId` (header, required) — session token
- `employerId` (query, optional) — identification number for employer; if the web service user has client restrictions, enter clientId.employerId to retrieve data about a single employer

**Responses:**
- `200` — successful operation → `EmployerDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/getInvoiceData`
**Operation:** `getInvoiceData`

**Summary:** Get Invoice Data

**Description:** Use this operation to retrieve data from a specified invoice or from all invoices associated with a particular payroll batch. This corresponds to the Client/View/Invoices form in PrismHR. Note: To use this endpoint, it must be listed in the Allowed Methods table of the web service user (the Disable Method Restrictions setting is ignored). Otherwise, it returns HTTP response code 403.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, optional) — payroll batch ID, if returning all invoice data for a batch
- `invoiceId` (query, optional) — invoice ID, if returning data about a specific invoice

**Responses:**
- `200` — successful operation → `GetInvoiceDataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/getMultiEntityGroupList`
**Operation:** `getMultiEntityGroupList`

**Summary:** Get Multi Entity Group List

**Description:** Returns a list of multi-entity groups, optionally filtered by clientId or multiEntityGroupId. Supports pagination with count and startpage parameters. The result includes the total number of multi-entity groups. Note: If there are any client restrictions on the web service user, you must pass a value for clientId. Only that specific client will be returned in the clientList, even if there are other clients associated with the multi-entity group. To see all clients associated with a multi-entity group, the web service user cannot have any client restrictions. This operation also returns paginat…

**Parameters:**
- `sessionId` (header, required) — Session token
- `count` (query, optional) — Number of multientity groups returned per page
- `startpage` (query, optional) — Pagination start location (first page = '0')
- `clientId` (query, optional) — client identifier
- `multiEntityGroupId` (query, optional) — multi-entity group identifier

**Responses:**
- `200` — Successful operation → `GetMultiEntityGroupList`
- `204` — No content → _(no schema)_
- `400` — Invalid request or missing parameters → _(no schema)_
- `401` — Unauthorized or expired sessionId → _(no schema)_
- `403` — User not authorized for this resource → _(no schema)_
- `500` — Internal server error → _(no schema)_

---

## `GET /system/v1/getPayee`
**Operation:** `getPayee`

**Summary:** Retrieve payee information

**Description:** This operation returns system Payee information. To call this endpoint, it must explicitly listed in the Allowed Methods table on the Web Service User form in PrismHR. By default, this operation masks certain personally identifiable information (PII) in its response, such as Bank Account Number. Please refer to the API documentation article Unmasking PII to learn how to unmask this data.

**Parameters:**
- `sessionId` (header, required) — session token
- `payeeId` (query, optional) — Enter payee id to return specific payee
- `payeeType` (query, optional) — Payee Type (G- Garnishing Authority, D- State Disbursement Unit, T- Tax Authority, C- Carrier, O- Other)

**Responses:**
- `200` — successful operation → `PayeeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/getPaymentsPending`
**Operation:** `getPaymentsPending`

**Summary:** Payments Pending information

**Description:** Use this operation to retrieve information about payments and wire transfers in Pending status. Batches with pending Wire Transfers have status WT.PEND, and batches with other payments pending have status PAYPEND. Specify a client ID to retrieve information for that client, or a client and batch number to retrieve information for only that batch. Note: If you specify a batch ID, you must also specify a client ID. This method returns a 404 error when no batches match the filter criteria.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, optional) — enter a client ID to return payments pending for only that client
- `batchId` (query, optional) — enter a batch number to return payment pending data for only that batch; a clientId is also required in this case
- `status` (query, optional) — enter either WT.PEND or PAYPEND to only return batches in that status

**Responses:**
- `200` — successful operation → `PaymentsPendingResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/getPositivePayCheckStub`
**Operation:** `getPositivePayCheckStub`

**Summary:** Get positive pay check stub

**Description:** Use this operation to retrieve Positive Pay check stub IDs and the bank account IDs associated with them. Note: SystemService endpoints have additional security restrictions. Web service users with client restrictions cannot access any SystemService API endpoints. To grant access to this endpoint, you must explicitly list it in the Allowed Methods section for each web service user. The Disable Method Restrictions option is ignored.

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `PositivePayCheckStubResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/getPositivePayFileList`
**Operation:** `getPositivePayFileList`

**Summary:** Get positive pay files list

**Description:** Use this operation to retrieve a list of the existing positive pay files you can recreate by calling SystemService.recreatePositivePay. You can enter a checking account name (if the positive pay file was created for a single account) or a file stub name (if the file was created for multiple accounts). You can also filter the response using either the single dateCreated parameter or a date range (you cannot use both). To return only the most recently created file for a given checkingAcct, set mostRecent to true. This operation also returns paginated results when more than 5000 files match the r…

**Parameters:**
- `sessionId` (header, required) — session token
- `checkingAcct` (query, optional) — enter the checking account used to create positive pay file
- `fileStub` (query, optional) — enter the file stub name used to create positive pay file
- `dateCreated` (query, optional) — specify a date in YYYY-MM-DD format to retrieve positive pay files created on that date; do not use in combination with start and end date parameters
- `dateCreatedStart` (query, optional) — start date to retrieve positive pay files created in a certain date range; must use in combination with dateCreatedEnd; do not use with dateCreated
- `dateCreatedEnd` (query, optional) — end date to retrieve positive pay files created within a certain date range; must use in combination with dateCreatedStart; do not use with dateCreated
- `mostRecent` (query, optional) — if true, the endpoint returns the most recently created positive pay file record for the specified checkingAcct and date parameters
- `count` (query, optional) — number of positive pay files returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `PositivePayFileList`
- `204` — no content → _(no schema)_
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/getUnbilledBenefitAdjustments`
**Operation:** `getUnbilledBenefitAdjustments`

**Summary:** Unbilled Benefit Adjustments information

**Description:** Note: Web Service Users cannot call multiple concurrent instances of this method. Please wait until the first instance returns a buildStatus of "DONE," retrieve your download link, and then, if necessary, invoke this method again. If you try to call a second instance before the first one completes, the system will return HTTP response code 429 and you must complete the previous instance using the downloadId provided before initiating a new instance. Use this operation to return benefit adjustments that have not yet been billed. You can also filter the response by adjustment period, employee st…

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — identifier used to check status of / download data
- `clientId` (query, optional) — use this option to limit the response to one or more client IDs
- `startDate` (query, optional) — adjustment period filter start date (in YYYY-MM-DD format)
- `endDate` (query, optional) — adjustment period filter end date (in YYYY-MM-DD format)
- `includeTermClient` (query, optional) — whether to include terminated clients in the response. Terminated clients are excluded by default.
- `statusClass` (query, optional) — use this option to restrict the response based on employee status class. Allowed values are T (terminated), A (active), and L (on leave).

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/identifyACHProcessLock`
**Operation:** `identifyACHProcessLock`

**Summary:** Identify ACH Process Lock

**Description:** This operation retrieves information about existing ACH process locks, specifically the associated user and the date and time of creation. ACH processes support multithreaded locks held by multiple users, so this endpoint can return information about two different lock holders. Note: To use this endpoint, it must be explicitly listed in the Allowed Methods table of the web service user.

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `ProcessLockInfo`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/positivePayDownload`
**Operation:** `positivePayDownload`

**Summary:** Download positive pay report

**Description:** Use this operation to generate a positive pay download file for one or more bank accounts. Provide a checkingAccount to generate a file for a single bank account, or provide a fileStub ID to generate for multiple bank accounts. By default this endpoint includes all available positive pay data. This will initialize the data retrieval and will respond with "buildStatus": "INIT". Subsequent calls to this API should be formatted exactly as the initial call, with the addition of the downloadId returned by the initial call. They will return either "buildStatus": "BUILD", "buildStatus": "ERROR", or "…

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — identifier used to check status of / download data
- `checkingAccount` (query, optional) — to generate a positive pay file for only one bank account, enter a checking account ID
- `fileStub` (query, optional) — to generate a positive pay file for multiple bank accounts, enter the File Stub ID for the bank accounts you want to include in the file.
- `startCheckDate` (query, optional) — to report for a specific date range, enter the start check date (format: YYYY-MM-DD); an endCheckDate value is required in this case
- `endCheckDate` (query, optional) — to report for a specific date range, enter the end check date (format: YYYY-MM-DD); a startCheckDate value is required in this case
- `includeVoidedChecks` (query, optional) — if true, includes voided check data in the file; if false (default), ignores voided check data

**Responses:**
- `200` — successful operation → `PositivePayDownloadResponse`
- `204` — no content → _(no schema)_
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/recreatePositivePay`
**Operation:** `recreatePositivePay`

**Summary:** Recreate positive pay report

**Description:** This operation recreates a previously generated positive pay file. Use the fileName value returned by SystemService.getPositivePayFileList. Note: Web Service Users with any client access restrictions cannot call this endpoint. Note: In order to use this endpoint, it must be explicitly listed in the Allowed Methods for the calling web service user.

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — identifier used to check status of / download data
- `fileName` (query, optional) — name of the positive pay file to recreate (returned by SystemService.getPositivePayFileList)

**Responses:**
- `200` — successful operation → `PositivePayDownloadResponse`
- `204` — no content → _(no schema)_
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /system/v1/streamACHData`
**Operation:** `streamACHData`

**Summary:** Stream ACH Data

**Description:** This operation securely streams an ACH file requested by file name. Please note that, as it streams the requested data, the operation may take some time to complete the request. To determine the achFileName and achBatchId, call the endpoint SystemService.getACHFileList. This service supports .txt and .csv file types. Note: To use this endpoint, it must be listed in the web service user Allowed Methods grid. Note: This endpoint will not work if there are client restrictions on the web service user.

**Parameters:**
- `sessionId` (header, required) — session token
- `achBatchId` (query, required) — ACH Batch Identifier
- `achFileName` (query, required) — ACH File Name

**Responses:**
- `200` — successful operation → _(no schema)_
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /system/v1/getEmployeeHireType`
**Operation:** `getEmployeeHireType`

**Summary:** Determine hire type for given ssn

**Description:** This operation returns the type of hire that should occur for a given social security number, last name, and date of birth of a prospective hire (see the hire types table below). In addition, if a validation error occurs that could affect the hire process, information about this is returned also (see the validation codes table below). Note: The firstName parameter is optional. If you include firstName in your request, the system validates that it matches the employee's first name. If you leave firstName empty, these validations do not occur. Please note: this endpoint is meant for service prov…

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`, `dateOfBirth`, `lastName`, `ssn`

**Responses:**
- `200` — successful operation → `EmployeeHireTypeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /system/v1/import1095CData`
**Operation:** `import1095CData`

**Summary:** Import 1095C data

**Description:** Use this endpoint to import an employee’s Form 1095-C data. For details about importing this data, review the ACA 1095-C Data Import Specifications sheet, which is linked from the “API Reference Documents” page on the API documentation website. Note: SystemService methods have additional security restrictions. For this SystemService operation, the web service user cannot include client restrictions. To grant access, you must explicitly list the operation name in the Allowed Methods for each web service user (the Disable Method Restrictions option is ignored).

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `fileData`

**Responses:**
- `200` — successful operation → `Import1095CResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /system/v1/inactivatePrismUser`
**Operation:** `inactivatePrismUser`

**Summary:** inactivate prism user(s))

**Description:** Use this operation to inactivate one or more PrismHR users. To use this method, you must explicitly give permission to your Web Service User using the Web Service Users form in PrismHR. When calling this method, use the checksum valued returned by PrismSecurityService.getUserDetails. Please Note: this method will return a successful response if one user from the list is successfully inactivated. If any inactivations fail, this operation returns the reasons for those failures as warnings.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `InactivatePrismUserRequest`

**Responses:**
- `200` — successful operation → `UpdateResponseWithWarnings`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /system/v1/markReceivedPayments`
**Operation:** `markReceivedPayments`

**Summary:** Mark pending wire transfers received

**Description:** Use this operation to mark a pending wire transfer 'Received' for a given payroll batch.This changes the batch status from WT.PEND to INITCOMP. Use the batchId and amount input values to confirm the batch to update. Note: This operation only updates wire transfers, and does not work for batches in PAYPEND status. Use this operation together with SystemService.getPaymentsPending to identify batches awaiting wire transfers and confirm their receipt. You can retrieve the invoice amount from the response of getPaymentsPending.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `MarkReceivedPaymentsRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /system/v1/stopProcess`
**Operation:** `stopProcess`

**Summary:** Clear any process locks on a download process

**Description:** Use this operation to stop an asynchronous download while it is still processing. Use this operation to stop an asynchronous download while it is still processing. Note: A download process can only be stopped by the web service user that initiated it. Note: In order to use this endpoint, it must be explicitly listed in the Allowed Methods for the calling web service user. In the endPoint field, specify the name of the endpoint associated with the download. Reference the table below for a list of supported endpoints: Input Value Corresponding Endpoint getData SystemService.getData getClientGLDa…

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, required) — ID of the download to stop
- `endPoint` (query, required) — name of endpoint that initiated the download (ex: getData, etc)

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
