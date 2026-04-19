# Service: `generalLedger`

**13 methods** in this service.

## `GET /generalLedger/v1/getBulkOutstandingInvoices`
**Operation:** `getBulkOutstandingInvoices`

**Summary:** Retrieve list of client invoices

**Description:** This operation retrieves a list of outstanding invoices across multiple clients. To retrieve outstanding invoices for a specific client, call GeneralLedgerService.getOustandingInvoices. Note: If the web service user has client restrictions, the clientId is required. You can pass up to ten client IDs per call. The first call will initialize data retrieval; the endpoint responds with "buildStatus": "INIT". Subsequent calls should be formatted exactly as the initial call, plus the downloadId returned by the initial call. The returned status will be "buildStatus": "BUILD", "buildStatus": "ERROR", …

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, optional) — list of client identifiers
- `downloadId` (query, optional) — identifier used to check status of / download data
- `showOnlyDepositMatch` (query, optional) — enter a deposit value for the system to match; the endpoint returns the invoice with a balance that matches this value, if it exists

**Responses:**
- `200` — successful operation → `DataResponseWithMessages`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `500` — internal server error → _(no schema)_
- `501` — the request depends on functionality not supported by the server → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `GET /generalLedger/v1/getClientAccountingTemplate`
**Operation:** `getClientAccountingTemplate`

**Summary:** Retrieve client and global PEO accounting templates.

**Description:** Use this operation to retrieve details about the accounting template assigned to a particular client. If this template is associated with a global accounting template, information about the global template is also returned.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `GetClientAccountingTemplateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `500` — internal server error → _(no schema)_
- `501` — the request depends on functionality not supported by the server → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `GET /generalLedger/v1/getClientGLData`
**Operation:** `getClientGLData`

**Summary:** get PEO client accounting data

**Description:** Note: Web Service Users cannot call multiple concurrent instances of this method. Please wait until the first instance returns a buildStatus of "DONE," retrieve your download link, and then, if necessary, invoke this method again. If you try to call a second instance before the first one completes, the system will return HTTP response code 429 and you must complete the previous instance using the downloadId provided before initiating a new instance. This operation is used to retrieve PEO client accounting data from PrismHR for use by external programs. To use this API, provide a client ID and …

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — identifier used to check status of / download data
- `clientId` (query, required) — client identifier
- `payDateStart` (query, optional) — pay date range starting date (optional; formatted YYYY-MM-DD)
- `payDateEnd` (query, optional) — pay date range ending date (optional; formatted YYYY-MM-DD)
- `postDateStart` (query, optional) — post date range starting date (optional; formatted YYYY-MM-DD)
- `postDateEnd` (query, optional) — post date range ending date (optional; formatted YYYY-MM-DD)
- `batchId` (query, optional) — enter a payroll batch ID to return journal IDs for that specific batch; note that this cannot be combined with the date range filters

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /generalLedger/v2/getClientGLData`
**Operation:** `getClientGLData`

**Summary:** get PEO client accounting data

**Description:** Note: This is the non-asynchronous version of getClientGLData. It can retrieve up to 5000 client G/L records at a time. If more than 5000 records exist, this endpoint returns an error. In this case, you must adjust the filters in the request body or use the asynchronous version (v1) to retrieve greater than 5000 records per call. This operation is used to retrieve PEO client accounting data from PrismHR for use by external programs. To use this API, provide a client ID and either a pay date or post date range (you cannot use both filters). To retrieve all data on or before a specific date, ent…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `payDateStart` (query, optional) — pay date range starting date (optional; formatted YYYY-MM-DD)
- `payDateEnd` (query, optional) — pay date range ending date (optional; formatted YYYY-MM-DD)
- `postDateStart` (query, optional) — post date range starting date (optional; formatted YYYY-MM-DD)
- `postDateEnd` (query, optional) — post date range ending date (optional; formatted YYYY-MM-DD)
- `batchId` (query, optional) — enter a payroll batch ID to return journal IDs for that specific batch; note that this cannot be combined with the date range filters

**Responses:**
- `200` — successful operation → `ClientGlDataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /generalLedger/v1/getGLCodes`
**Operation:** `getGLCodes`

**Summary:** get a list of General Ledger account codes and their descriptions

**Description:** Use this operation to retrieve General Ledger account codes and their descriptions.

**Parameters:**
- `sessionId` (header, required) — session token
- `glCode` (query, optional) — optional GL code parameter to get the information just for that code

**Responses:**
- `200` — successful operation → `GLAccountCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /generalLedger/v1/getGLDetailDownload`
**Operation:** `getGLDetailDownload`

**Summary:** download accounting g/l detail report

**Description:** Note: Web Service Users cannot call multiple concurrent instances of this method. Please wait until the first instance returns a buildStatus of "DONE," retrieve your download link, and then, if necessary, invoke this method again. If you try to call a second instance before the first one completes, the system will return HTTP response code 429 and you must complete the previous instance using the downloadId provided before initiating a new instance. This operation is used to generate and download an accounting G/L detail report. To use this API, provide a payroll batch ID or payroll date range…

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — identifier used to check status of / download data
- `batchId` (query, optional) — payroll batch identifier (either batchId or date range is required)
- `startDate` (query, optional) — pay date range starting date (either batchId or date range is required; formatted YYYY-MM-DD)
- `endDate` (query, optional) — pay date range ending date (either batchId or date range is required; formatted YYYY-MM-DD)
- `clientId` (query, optional) — client identifier(s) (either one or many clientId(s) or employerId(s) or neither; cannot include both)
- `employerId` (query, optional) — employer identifier(s) (either one or many clientId(s) or employerId(s) or neither; cannot include both)
- `glAccount` (query, optional) — G/L account report filter
- `glCostCenter` (query, optional) — G/L cost center report filter
- `glDetailCodeType` (query, optional) — G/L detail code type report filter; valid values are (B)enefits, (BI)lling, (C)hecks, (D)eductions, (DD) direct deposit, (FSA) flexible savings accounts, (HSA) health savings accounts, (P)ay, (R)etirement, (T)axes, and (W)orkers comp
- `glDetailCode` (query, optional) — G/L detail code report filter
- `voucherId` (query, optional) — voucher ID report filter
- `checkNumber` (query, optional) — check number report filter
- `employeeId` (query, optional) — employee ID report filter

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /generalLedger/v1/getGLInvoiceDetail`
**Operation:** `getGLInvoiceDetail`

**Summary:** Get posted and unposted invoice detail

**Description:** You can use the new endpoint GeneralLedgerService.getGLInvoiceDetail to retrieve detail data about items on the PrismHR External Invoice Post form. In PrismHR, these invoice details display when you click the transaction date of a specific invoice on the form. The endpoint returns data for a specific employer (glCompany) and invoice date. By default, this endpoint returns unposted data. You can use the includePosted request parameter to return both posted and unposted data. Please note: The web service user method and client restrictions for this operation are handled differently from other Pr…

**Parameters:**
- `sessionId` (header, required) — session token
- `glCompany` (query, required) — employer identifier associated with the G/L invoices)
- `invDate` (query, required) — invoice date (format: MM/DD/YY)
- `includePosted` (query, optional) — whether to include posted invoices in the response

**Responses:**
- `200` — successful operation → `GLInvoiceDetailResponse`
- `204` — no content → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /generalLedger/v1/getGLSetup`
**Operation:** `getGLSetup`

**Summary:** get a list of general ledger accounts

**Description:** Use this operation to retrieve G/L setup information. You can find this information in the System|Change|G/L Setup form in PrismHR.

**Parameters:**
- `sessionId` (header, required) — session token
- `glTemplate` (query, required) — ID of the general ledger template you want to access
- `glType` (query, required) — type of G/L data to retrieve. The table lists the available glTypes that you can use. glTypeDescriptionBthe return object will contain Benefit Plan dataLthe return object will contain Billing Code dataCthe return object will contain Bank Account dataDthe return object will contain Deduction Code dataMthe return object will contain Miscellaneous Item dataPthe return object will contain Pay Code dataRthe return object will contain Retirement dataFSAthe return object will contain Flexible Spending Account dataHSAthe return object will contain Health Savings Account dataTthe return object will contain Tax related data(state value is required in this case)Wthe return object will contain Worker's Compensation (state-based) dataWPthe return object will contain Worker's Compensation (policy-based) data
- `glObjectId` (query, optional) — enter a gl object identifier if you want to retrieve G/L setup information related to a specific gl type
- `state` (query, optional) — two-character state code; only required for Tax G/L type

**Responses:**
- `200` — successful operation → `GetGLSetupResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /generalLedger/v1/getOutstandingInvoices`
**Operation:** `getOutstandingInvoices`

**Summary:** Retrieve list of client invoices

**Description:** Use this operation to retrieve a list of client invoices that are "outstanding" from an accounting perspective (not overdue and not yet paid). You can also return information about a specific invoice by specifying an invoice deposit "match" amount.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `showOnlyDepositMatch` (query, optional) — enter a deposit value for the system to match; the endpoint returns the invoice with a balance that matches this value, if it exists

**Responses:**
- `200` — successful operation → `GetOutstandingInvoicesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `500` — internal server error → _(no schema)_
- `501` — the request depends on functionality not supported by the server → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `GET /generalLedger/v1/getPendingCashReceipts`
**Operation:** `getPendingCashReceipts`

**Summary:** get a paginated list of cash receipts and, optionally, any associated G/L deposit and post

**Description:** Use this operation to retrieve G/L data about cash receipts that are still pending (not yet paid). You can retrieve data about a specific batch, or set the cashReceiptBatchId to "ALL" to return all pending cash receipts. If desired, you can also include G/L post and deposit information for the batch; this data can still be returned even when no pending cash receipts exist. Note: Web service users cannot call this endpoint if they have any client access restrictions. In addition, to call this endpoint, a web service user must have it listed in their Allowed Methods. This operation returns pagin…

**Parameters:**
- `sessionId` (header, required) — session token
- `cashReceiptBatchId` (query, required) — ID of the cash receipts batch to retrieve; enter "ALL" to return all
- `includePostType` (query, optional) — set value to true to include a list of G/L posting options in the response
- `includeDepositType` (query, optional) — set value to true to include a list of G/L deposit options in the response
- `count` (query, optional) — number of vouchers returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetPendingCashReceiptsResponseWithPagination`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /generalLedger/v1/deleteCashReceipts`
**Operation:** `deleteCashReceipts`

**Summary:** deleteCashReceipts

**Description:** Use this operation to delete cash receipt accounting records from the system. Please note the following security requirements for using this endpoint: This endpoint must be included in the Allowed Methods grid for the chosen Web Service User. Web Service Users are not allowed to call this operation if they have any client access restrictions.

**Parameters:**
- `sessionId` (header, required) — session token
- `cashReceiptBatchId` (query, required) — identifier for the cash receipts batch to delete

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

## `POST /generalLedger/v1/depositCashReceipt`
**Operation:** `depositCashReceipt`

**Summary:** deposit Cash Receipt.

**Description:** Use this operation to post cash receipt data to the accounting journal or to create a pending cash receipt. Note: This endpoint has additional security requirements. First, the web service user cannot have any client restrictions. Second, the web service user must have the endpoint name listed in their Allowed Methods grid.This endpoint makes significant changes to accounting records in the system: before working with it, please review the relevant sections of the online help and the PrismHR Accounting User Guide. or prepaidDebitAccount fields without any input value, the system will delete an…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `DepositCashReceipt`

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

## `POST /generalLedger/v1/setGLSetup`
**Operation:** `setGLSetup`

**Summary:** update the GL accounting template.

**Description:** Use this operation to update G/L setup information. The operation only updates this data. It does not create new G/L records. If you pass in an empty string for any field other than the id of the glType, the system will delete any existing value stored in the corresponding database field.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `GLSetupRequest`

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
