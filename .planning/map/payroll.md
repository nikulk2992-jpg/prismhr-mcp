# Service: `payroll`

**56 methods** in this service.

## `GET /payroll/v1/checkInitializationStatus`
**Operation:** `checkInitializationStatus`

**Summary:** Check payroll batch initialization status

**Description:** This operation will return the current status of a payroll batch initialization. This operation should be called repeatedly following a call to /payroll/initializePrismBatch in order to retrieve the updated status until batch initialization is complete; the 'initStatus' field will be either 'UNINITIALIZED,' 'PROCESSING,' or 'COMPLETE.' Any errors or warnings generated during payroll batch initialization are provided in the 'errorDetail' and 'warning' arrays. The following are internal payroll initialization statuses that may be returned by this operation. Note that this is not a complete list …

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — batch identifier

**Responses:**
- `200` — successful operation → `BatchStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getApprovalSummary`
**Operation:** `getApprovalSummary`

**Summary:** Get payroll batch summary for approval

**Description:** This operation will return a summary of an initialized payroll batch that is pending approval. Option DescriptionITEMIZEDDEDUCTIONSreturn an array of payroll deduction information, including the deduction code, class, and amount.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — batch identifier
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `ApprovalSummaryResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBatchInfo`
**Operation:** `getBatchInfo`

**Summary:** Get payroll batch information

**Description:** This operation returns payroll control information for the specified payroll batch.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch identifier

**Responses:**
- `200` — successful operation → `PayrollBatchInfoResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBatchListByDate`
**Operation:** `getBatchListByDate`

**Summary:** Return Payroll Batches Within a Date Range

**Description:** Use this operation to return a list of all payroll batches within a specified date range. If you want, you can also filter the results by pay group.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `startDate` (query, required) — starting date for the payroll batch range
- `endDate` (query, required) — ending date for the payroll batch range
- `dateType` (query, required) — whether to use pay periods, pay dates, or post dates when returning batches in the specified date range; valid values are PAY, PERIOD, and POST
- `payGroup` (query, optional) — enter a pay group if you want to only return batches associated with that group

**Responses:**
- `200` — successful operation → `BatchByDateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBatchListForApproval`
**Operation:** `getBatchListForApproval`

**Summary:** Get a list of batchids available for approval for client.

**Description:** This operation returns a list of batches for a specific client that are ready for client approval.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `BatchListForApprovalResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBatchListForInitialization`
**Operation:** `getBatchListForInitialization`

**Summary:** Get a list of batch IDs available for initialization for specified client.

**Description:** This operation returns a list of batches for a specific client that are ready for initialization.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `BatchListForApprovalResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBatchPayments`
**Operation:** `getBatchPayments`

**Summary:** Get batch payments information for an employee

**Description:** You can use this method to return all pre-calculated payments to be paid, during a specific payroll batch. These payments include bonuses, sales commissions, and expense reimbursements.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `payrollNumber` (query, required) — payroll identifier

**Responses:**
- `200` — successful operation → `BatchPaymentResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBatchStatus`
**Operation:** `getBatchStatus`

**Summary:** Get the statuses for a list of batches

**Description:** The PayrollService.getBatchStatus method returns the statuses for a provided list of payroll batches. Description for the corresponding batch status can be referenced from the table below. Batch StatusBatch Status DescriptionTS.READYPayroll is ready for time sheet entryTS.ENTRYTime sheet entry in progressTSOKCOMPTime sheet entry completeINITIALPayroll calculation in progressINITOKPayroll calculation completedINITWARNPayroll calculation completed with warningINITFAILPayroll calculation completed with errorsAP.PENDCalculation pending approvalAP.READYPayroll calculation results approved by client…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchIds` (query, required) — comma separated list of batches (e.g. 20191,20192,20193...)

**Responses:**
- `200` — successful operation → `BatchStatusCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBillingCodeTotalsByPayGroup`
**Operation:** `getBillingCodeTotalsByPayGroup`

**Summary:** Get total billing amount for a client and batch broken out by pay group

**Description:** Use this operation to retrieve billing code totals for a specified payroll batch, broken out by pay group. You can also call this method with the COSTS option to return payroll billing costs. When applicable, this method also returns information about associated void vouchers and batches. The following table lists the available options that you can use. OptionDescriptionCostsreturn payroll billing costs

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch identifier
- `options` (query, required) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `BillingCodeTotalsByPayGroupResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBillingCodeTotalsForBatch`
**Operation:** `getBillingCodeTotalsForBatch`

**Summary:** Get total billing amount for a client and and batch

**Description:** This operation returns a list of billing codes and the total billing amount for the specified client and payroll batch. Please note the employeeCount is the total number of employees paid in the batch.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch identifier

**Responses:**
- `200` — successful operation → `PayrollBillingCodeTotalsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBillingCodeTotalsWithCosts`
**Operation:** `getBillingCodeTotalsWithCosts`

**Summary:** Get total billing amount with costs for a client and batch

**Description:** This method returns a list of billing codes, the total billing amount, and the total billing costs for the specified client and payroll batch. Please note the employeeCount is the total number of employees paid in the batch.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch identifier

**Responses:**
- `200` — successful operation → `PayrollBillingCodeTotalsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBillingRuleUnbundled`
**Operation:** `getBillingRuleUnbundled`

**Summary:** Get an unbundled billing rule for clientId and billingRuleNum

**Description:** This operation returns the unbundled billing rule information for the specified client and billing rule number.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `billingRuleNum` (query, required) — unbundled billing rule number

**Responses:**
- `200` — successful operation → `PayrollResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBillingVouchers`
**Operation:** `getBillingVouchers`

**Summary:** Get list of billing vouchers for clientId and date range

**Description:** This operation returns a list of employee billing vouchers for the specified client and pay dates. Billing vouchers are a detailed record of each item billed to a client on an invoice.The table lists the available options that you can use. OptionDescriptionInitializedthe return object will contain initialized payroll vouchers instead of completed onesPEOClientAccountingthe return object will contain accounting data from that voucher

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `payDateStart` (query, required) — starting pay date, inclusive (format YYYY-MM-DD)
- `payDateEnd` (query, required) — ending pay date, inclusive (format YYYY-MM-DD)
- `billType` (query, optional) — type of billing to retrieve the amount for: '1' (Gross Wages), '2' (FICA/Medicare), '3' (FICA/Social Security, '4' (FUTA), '5' (SUTA), '6' (Workers' Compensation, '7' (Other), '8' (Administrative Fees), '9' (Agency CR), or '10' (Inv Tax)
- `count` (query, optional) — number of vouchers returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')
- `options` (query, optional) — one or more of the following options: "Initialized" to return initialized billing vouchers instead of completed ones, "PEOClientAccounting" to return object accounting data from that voucher,

**Responses:**
- `200` — successful operation → `PayrollBillingVouchersResponseWithPagination`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[getBillingVouchersByBatch]]

---

## `GET /payroll/v1/getBillingVouchersByBatch`
**Operation:** `getBillingVouchersByBatch`

**Summary:** Get list of initialized or finalized billing vouchers for clientId and batchId

**Description:** Use this operation to retrieve billing vouchers based on the payroll batch that was used to generate them. Call this method with the Initialized option to return initialized billing vouchers instead of completed ones. You can also call this method with the BillSort option to return a billSort object, which specifies invoice sort settings as configured on the Client Details > Billing tab and the Billing Codes form in PrismHR.OptionDescriptionInitializedthe return object will contain initialized payroll vouchers instead of completed onesPEOClientAccountingthe return object will contain accountin…

**Parameters:**
- `sessionId` (header, required) — session token.
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch identifier
- `billType` (query, optional) — type of billing to retrieve the amount for: '1' (Gross Wages), '2' (FICA/Medicare), '3' (FICA/Social Security, '4' (FUTA), '5' (SUTA), '6' (Workers' Compensation, '7' (Other), '8' (Administrative Fees), '9' (Agency CR), or '10' (Inv Tax)
- `count` (query, optional) — number of vouchers returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')
- `options` (query, optional) — one or more of the following options: "Initialized" to return initialized billing vouchers instead of completed ones, "PEOClientAccounting" to return object accounting data from that voucher, "BillSort" to return a billSort object, which specifies invoice sort settings

**Responses:**
- `200` — successful operation → `BillingVouchersByBatchResponseWithPagination`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getBulkYearToDateValues`
**Operation:** `getBulkYearToDateValues`

**Summary:** Get bulk year to date values

**Description:** Use this operation to download a JSON object summary of year-to-date values for different payroll variables, such as total deductions or total hours worked. You can also filter the results by client, employee, or a particular 'as of' date. If you submit a value in the voucherId input parameter, any value in the asOfDate parameter will be ignored. In addition, please note that this method only returns year-to-date data for up to one year, starting from January first of the current year or the year provided in asOfDate. Note 1: For information about properly using this operation to keep third-pa…

**Parameters:**
- `sessionId` (header, required) — session token
- `downloadId` (query, optional) — used to check status of and eventually download the compiled YTD data
- `clientId` (query, optional) — return results for only this client
- `employeeId` (query, optional) — return results for only this employee
- `voucherId` (query, optional) — return results for only this voucher
- `asOfDate` (query, optional) — the method will return year-to-date payroll data starting from January first of the year provided and ending in this date. This value is ignored if you enter a voucherId

**Responses:**
- `200` — successful operation → `DataResponseWithWarnings`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getClientsWithVouchers`
**Operation:** `getClientsWithVouchers`

**Summary:** Get the list of clients with at least one payroll voucher

**Description:** This operation returns a list of clients who have at least one payroll voucher during the specified date range, and that the web services user is permitted to access as defined in the web services user configuration.

**Parameters:**
- `sessionId` (header, required) — session token
- `payDateStart` (query, required) — starting pay date, inclusive (format YYYY-MM-DD)
- `payDateEnd` (query, required) — ending pay date, inclusive (format YYYY-MM-DD)

**Responses:**
- `200` — successful operation → `ClientsWithVouchersResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getEmployee401KContributionsByDate`
**Operation:** `getEmployee401KContributionsByDate`

**Summary:** Get list of employee 401K contributions

**Description:** This operation retrieves employee 401(k) contributions associated with vouchers within a specified date range. The operation retrieves a maximum of 5000 payroll vouchers for any multi-day range. By default, this operation masks certain personally identifiable information (PII) in its response, such as employee social security number and date of birth. Please refer to the API documentation article Unmasking PII to learn how to unmask this data. The options table lists all the data attribute classes. Option DescriptionCENSUSthe return object will contain census data of the employee as part of th…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `startDate` (query, required) — start of the period from which to pull payroll vouchers
- `endDate` (query, required) — end of the period from which to pull payroll vouchers
- `retirementPlanId` (query, optional) — enter a 401(k) plan ID to return data about that plan. Leave empty to return data for all plans
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `Contribution401KByDateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getEmployeeForBatch`
**Operation:** `getEmployeeForBatch`

**Summary:** Get list of employee IDs for clientId and batchId

**Description:** This operation returns a list of employee IDs for the specified client and payroll batch. Please note the employeeCount is the total number of employees paid in the batch.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch identifier

**Responses:**
- `200` — successful operation → `EmployeeForBatchResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getEmployeeOverrideRates`
**Operation:** `getEmployeeOverrideRates`

**Summary:** Get list of employee override rates

**Description:** You can use this method to return employee override rate information.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `OverrideRatesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getEmployeePayrollSummary`
**Operation:** `getEmployeePayrollSummary`

**Summary:** Get an employee's payroll summary

**Description:** Use this operation to return a voucher-by-voucher payroll summary for the specified client, employee, and year.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `year` (query, required) — year for which you want to return payroll summary data

**Responses:**
- `200` — successful operation → `EmployeePayrollSummaryResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getExternalPtoBalance`
**Operation:** `getExternalPtoBalance`

**Summary:** Get external PTO balance data

**Description:** Use this operation to retrieve PTO balance information that was written to the PrismHR system from an external source by PayrollService.setExternalPtoBalance. By default, this operation does not return historical PTO data. To obtain historical information, set includeHistory to true. This endpoint is intended for clients that are set up to use external PTO balances only. The client must have the External PTO used option enabled on the Other tab of the Client Details form. Typically, enabling this option means that PTO accrual and management occur in a separate application, such as a time syste…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch identifier
- `includeHistory` (query, optional) — whether to include historical PTO balance data in the response; valid values are true, false (default), or empty string

**Responses:**
- `200` — successful operation → `GetExternalPtoBalanceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getManualChecks`
**Operation:** `getManualChecks`

**Summary:** Retrieve information about manual checks

**Description:** The PayrollService.getManualChecks operation returns a list of manual checks entered into the system. Once the manual check has been posted to a payroll, voucher information may be obtained by calling PayrollService.getPayrollVoucherById with the voucherNumber returned by this operation.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `reference` (query, optional) — manual check reference number (optional)
- `employeeId` (query, optional) — employee identifier filter (optional)
- `checkDate` (query, optional) — check date filter formatted as YYYY-MM-DD (optional)
- `checkStatus` (query, optional) — check status filter: (POST)ed, (INIT)ialized, or (PEND)ing (optional)

**Responses:**
- `200` — successful operation → `ManualChecksResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getPayrollApproval`
**Operation:** `getPayrollApproval`

**Summary:** Get payroll approval info for a client.

**Description:** This operation returns payroll approval information for a specific batch. Use the checksum value from this method to approve or deny a payroll via PayrollService.setPayrollApproval.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — batch identifier

**Responses:**
- `200` — successful operation → `PayrollApprovalResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getPayrollBatchWithOptions`
**Operation:** `getPayrollBatchWithOptions`

**Summary:** Get a list of batches with payroll control options

**Description:** This operation returns a list of payroll batches along with their batch-specific Payroll Control options

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — ID of the payroll batch to return

**Responses:**
- `200` — successful operation → `PayrollBatchWithOptionsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getPayrollNotes`
**Operation:** `getPayrollNotes`

**Summary:** Get payroll notes

**Description:** This operation returns a list of payroll notes for the specified client.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `PayrollNotesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getPayrollSchedule`
**Operation:** `getPayrollSchedule`

**Summary:** Get a payroll schedule using scheduleCode

**Description:** This operation returns the details of the specified payroll schedule.

**Parameters:**
- `sessionId` (header, required) — session token
- `scheduleCode` (query, required) — payroll schedule identifier

**Responses:**
- `200` — successful operation → `GetPayrollScheduleResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[getPayrollScheduleCodes]]

---

## `GET /payroll/v1/getPayrollScheduleCodes`
**Operation:** `getPayrollScheduleCodes`

**Summary:** Get a list of available schedule codes with their description

**Description:** This operation returns a list of schedule codes and their descriptions.

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `PayrollScheduleCodesResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getPayrollSummary`
**Operation:** `getPayrollSummary`

**Summary:** Get payroll summary

**Description:** This operation returns a list of completed payroll batches for a given client, for the specified batch types and calendar year. It can also return details of a specified payroll batch broken out by an employee, which is the default option, or by pay code, position, department, location, division, shift, or project. To retrieve a specific breakout of a payroll batch data: pass a batchId, set includeDetails to true and specify the appropriate sort value.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `year` (query, optional) — calendar year (YYYY). Must be an existing year not greater than the current year and will default to the current year if no value is passed. Required if no batchId is passed. If both year and batchId are passed, the year value will be ignored
- `batchType` (query, optional) — one or more type of payroll batches separated by a comma to return: A=All Types is the default option; R=Scheduled; S=Special; J=Adjustment; V=Reversal; M=Manual. If you pass A then you cannot pass any of the other values
- `batchId` (query, optional) — valid payroll batch identifier for the selected client. If both year and batchId are passed, the year value will be ignored
- `includeDetails` (query, optional) — can only be true if a batchId is passed. true will return the details of all the payroll vouchers for the given batchId in conjunction with sort. false will return only the payroll history
- `sort` (query, optional) — specify the sort details to return for the list of payroll vouchers for the given batchId. You can only use this parameter if includeDetails is set to true. Only one of the following values is allowed: PAYCODE, POSITION, DEPT, LOC, DIV, SHIFT, PROJ and EMPLOYEE (default value)

**Responses:**
- `200` — successful operation → `PayrollSummaryResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getPayrollVoucherById`
**Operation:** `getPayrollVoucherById`

**Summary:** Get a payroll voucher for clientId and voucherId

**Description:** This operation returns an employee payroll voucher for the specified client and voucher. Employee vouchers display details of the employee's earnings, deductions, taxes, and so on. By default, this operation masks certain personally identifiable information (PII) in its response, such as direct deposit account numbers. Please refer to the API documentation article Unmasking PII to learn how to unmask this data. Note for prismhr-api and API 1.30: To exclude directDeposit from the response, append #NODIRECTDEPOSIT to this endpoint in the Allowed Methods for your web service user. Example: Payrol…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `voucherId` (query, required) — payroll voucher number
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `PayrollVoucherResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getPayrollVoucherForBatch`
**Operation:** `getPayrollVoucherForBatch`

**Summary:** Get list of employee payroll vouchers for clientId and batchId

**Description:** This operation returns a list of employee payroll vouchers for the specified client and the payroll batch. Employee vouchers display details of the employee's earnings, deductions, taxes, and so on. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of vouchers. count specifies the number of vouchers to return per page, and startpage indicates the starting position in the voucher list. The operation returns these parameters in the response object as well, along with the total number of vouchers. By default, this operation ma…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `batchId` (query, required) — payroll batch identifier
- `count` (query, optional) — number of vouchers returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `PayrollResponseWithPagination`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getPayrollVouchers`
**Operation:** `getPayrollVouchers`

**Summary:** Get list of employee payroll vouchers for clientId and date range

**Description:** This operation returns a list of employee payroll vouchers for the specified client and pay dates. Employee vouchers display details of the employee's earnings, deductions, taxes, and so on. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of vouchers. count specifies the number of vouchers to return per page, and startpage indicates the starting position in the voucher list. The operation returns these parameters in the response object as well, along with the total number of vouchers. By default, this operation masks cert…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `payDateStart` (query, required) — starting pay date, inclusive (format YYYY-MM-DD)
- `payDateEnd` (query, required) — ending pay date, inclusive (format YYYY-MM-DD)
- `count` (query, optional) — number of vouchers returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `PayrollResponseWithPagination`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[getPayrollVouchersForEmployee]]

---

## `GET /payroll/v1/getPayrollVouchersForEmployee`
**Operation:** `getPayrollVouchersForEmployee`

**Summary:** Get list of employee payroll vouchers for employeeId, clientId, and dates

**Description:** This operation retrieves payroll vouchers for a specific employee, client, and date range. Employee vouchers display details of the employee's earnings, deductions, taxes, and so on. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of vouchers. count specifies the number of vouchers to return per page, and startpage indicates the starting position in the voucher list. The operation returns these parameters in the response object as well, along with the total number of vouchers. By default, this operation masks certain pers…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `payDateStart` (query, required) — start of date range
- `payDateEnd` (query, required) — end of date range
- `count` (query, optional) — number of vouchers returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')
- `options` (query, optional) — a string containing zero or more of the keywords in the options table

**Responses:**
- `200` — successful operation → `PayrollResponseWithPagination`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getProcessSchedule`
**Operation:** `getProcessSchedule`

**Summary:** Get a process schedule using processScheduleId

**Description:** This operation returns the details of the specified processing schedule.

**Parameters:**
- `sessionId` (header, required) — session token
- `processScheduleId` (query, required) — processing schedule identifier

**Responses:**
- `200` — successful operation → `ProcessScheduleResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[getProcessScheduleCodes]]

---

## `GET /payroll/v1/getProcessScheduleCodes`
**Operation:** `getProcessScheduleCodes`

**Summary:** Get a list of available process schedule IDs with their corresponding description

**Description:** This operation returns a list of proces schedule codes and their descriptions.

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `ProcessScheduleCodesResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getRetirementAdjVoucherListByDate`
**Operation:** `getRetirementAdjVoucherListByDate`

**Summary:** Get retirement adj voucher-list by date

**Description:** Use this operation to retrieve retirement adjustment voucher id’s by adjustment (pay date) or process date. This will initialize the data retrieval and will respond with "buildStatus": "INIT". Subsequent calls to this API should be formatted exactly as the initial call, with the addition of the downloadId returned by the initial call. They will return either "buildStatus": "BUILD", "buildStatus": "ERROR", or "buildStatus": "DONE". If buildStatus is DONE, then "dataObject" will contain the URL where the data can be retrieved. Note: Web Service Users cannot call multiple concurrent instances of …

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `dateType` (query, required) — P = date adjustment was processed, A = adjustment date
- `startDate` (query, required) — Process/Adjustment start date range (format: YYYY-MM-DD)
- `endDate` (query, required) — Process/Adjustment end date range (format: YYYY-MM-DD)
- `employeeId` (query, optional) — employee identifier
- `downloadId` (query, optional) — identifier used to check status of / download data

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getScheduledPayments`
**Operation:** `getScheduledPayments`

**Summary:** Get scheduled payments information for an employee

**Description:** This method returns an employee's scheduled payment information

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier

**Responses:**
- `200` — successful operation → `ScheduledPaymentResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getStandardHours`
**Operation:** `getStandardHours`

**Summary:** Get the list of standardHours objects for clientId

**Description:** This operation returns an array of standardHours objects for the specified client. The standardHours object includes its pay group ID, pay period, and the number of hours.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `StandardHoursResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/getYearToDateValues`
**Operation:** `getYearToDateValues`

**Summary:** Get period to date payroll values

**Description:** This operation returns period to date (year, quarter, and month) payroll values. Values include earnings, taxes, benefits, deductions, hours, etc.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `asOfDate` (query, optional) — the ending date for PTD calculation (format YYYY-MM-DD) - if omitted, today's date is used

**Responses:**
- `200` — successful operation → `PeriodToDateValuesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/payGroupScheduleReport`
**Operation:** `payGroupScheduleReport`

**Summary:** Pay Group Schedule Report

**Description:** This operation retrieves pay schedule information for a specified client, pay group, and date range. Calling the endpoint will initialize the data retrieval process, and the endpoint will respond with "buildStatus": "INIT". Subsequent calls to this API should be formatted exactly as the initial call, with the addition of the downloadId returned by the initial call. They will return either "buildStatus": "BUILD", "buildStatus": "ERROR", or "buildStatus": "DONE". If buildStatus is DONE, then "dataObject" will contain the URL where the compiled JSON data object may be retrieved. Note: Web Service…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client ID associated with the payGroup
- `payGroup` (query, required) — pay group identifier
- `payDateStart` (query, required) — start of report date range (format: YYYY-MM-DD)
- `payDateEnd` (query, required) — end of report date range (format: YYYY-MM-DD)
- `downloadId` (query, optional) — identifier used to check status/download data

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /payroll/v1/reprintCheckStub`
**Operation:** `reprintCheckStub`

**Summary:** Retrieve an employee's check stub

**Description:** The payroll/reprintCheckStub method generates a PDF check stub for the specified employee ID and voucher ID and returns a redirect URL which downloads the PDF check stub. If the PDF already exists on the server, this operation will return a status of DONE and a redirect URL to download the PDF check stub. If the PDF does NOT already exist on the server, calling payroll/reprintCheckStub will initiate the PDF generation process and return a status of BUILDING or PENDING. The method should then be called repeatedly until either the status is DONE or errorCode is not zero (0). Once the status is D…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, required) — employee identifier
- `voucherId` (query, required) — payroll voucher number

**Responses:**
- `200` — successful operation → `ReprintCheckStubResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/calculateManualCheck`
**Operation:** `calculateManualCheck`

**Summary:** Calculate a manual check

**Description:** The PayrollService.calculateManualCheck operation calculates the taxes for the provided manual check, generates a voucher that the system includes in the client's next payroll batch, and returns the calculated check amounts. The payroll registers are updated when the payroll processor posts the batch. If calculationOnly is set to false, the check will not be saved to the payroll system. To delete a manual check prior to payroll batch processing, use the PayrollService.deleteManualCheck API operation; once manual checks have been initialized in a batch, they may not be deleted. Note about calcu…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ManualCheckCalc`

**Responses:**
- `200` — successful operation → `ManualCheckCalcResultResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/calculateNetToGross`
**Operation:** `calculateNetToGross`

**Summary:** Calculate gross payment amount for a target net check amount

**Description:** Please note that this API operation requires Prism and will not work in HRP. The PayrollService.calculateNetToGross method computes the gross amount that, after taxes and deductions, results in the amount of the check specified in targetNetPay. You can review the Batch Payment record for this employee and then write to batch by setting writeBatch to true. This updates the batch payments record. Note: the batch record associated with this payment should still be in Time Sheet Entry mode. If the batch has been initialized, it must be initialized again to retrieve this payment.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`, `deductPeriod`, `employeeId`, `payCode`, `payDate`, `payPeriod`, `targetNetPay`, `voucherType`

**Responses:**
- `200` — successful operation → `NetToGrossResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/createPayrollBatches`
**Operation:** `createPayrollBatches`

**Summary:** Create new manual or special payroll batch

**Description:** Use this method to create a new manual or special payroll batch. (A manual batch is generally a supplemental or unscheduled payroll for one or more employees. A special or unscheduled payroll batch is typically for specific pay groups.) The API requires at least one periodStart and periodEnd defined across all submitted Employee objects. If there is only one input across multiple Employee objects for the periodStart, periodEnd, weeksWorked, and deductPeriod, then those values are applied to each employee.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `CreatePayrollBatches`

**Responses:**
- `200` — successful operation → `CreatePayrollBatchesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/createPayrollNotes`
**Operation:** `createPayrollNotes`

**Summary:** Create payroll notes

**Description:** This operation creates a payroll note for the specified client. Notes are simply a way to communicate some information to the payroll processor. The note expires after thirty days.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `CreatePayrollNotes`

**Responses:**
- `200` — successful operation → `CreatePayrollNotesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/createPayrollSchedule`
**Operation:** `createPayrollSchedule`

**Summary:** Create a new payroll schedule

**Description:** The operation creates a new payroll schedule. Refer to the table to learn about the settings for each type of schedule; see also the descriptions in the model.Schedule TypeOptionsValid ValuesDailypayPeriodDEvery daypayDay0 (indicates that the payroll is every day of the week)''payPeriodEndnumber of days (in conjunction with periodEndBefAft)''periodEndBefAft'B' (days before payday) or 'A' (days after payday); applies to payPeriodEnd numberWeeklypayPeriodWOnce a week on the specified payday payDayday of the week; enter 1-7 ('1'=Monday, '2'=Tuesday, and so on)''payPeriodEndnumber of days''periodE…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PayrollSchedule`

**Responses:**
- `200` — successful operation → `CreateUpdatePayrollScheduleResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/deleteManualCheck`
**Operation:** `deleteManualCheck`

**Summary:** Delete a manual check

**Description:** The PayrollService.deleteManualCheck method deletes an unprocessed manual check entry. Once a manual check has been initialized in a batch, it may not be deleted. The checksum parameter is required and may be obtained by calling PayrollService.getManualChecks

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `checksum`, `clientId`, `reference`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/getPayrollAllocationRpt`
**Operation:** `getPayrollAllocationRpt`

**Summary:** Get payroll allocation report

**Description:** Use this operation to generate the Payroll Allocation Report for download as a CSV file. This report details payroll costs distributed across multiple cost centers, which you can specify in the sort parameters. You must provide a client ID and either a payroll number or a date range. The sort parameters (primarySort, secondarySort, and tertiarySort) define how the report data is structured. If you use multiple sort parameters, they must all be unique. The Boolean options can further refine the output. Note: This operation does not use any report parameters configured in the PrismHR UI. All rep…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PayrollAllocationReportRequest`

**Responses:**
- `200` — successful operation → `DataResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/initializePrismBatch`
**Operation:** `initializePrismBatch`

**Summary:** Attempt payroll batch initialization

**Description:** This operation will attempt to initialize a payroll batch. Use /payroll/checkInitializationStatus to check the status of the payroll batch initialization. Client must be a Prism account; this operation will not work in HRP.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `batchId`, `clientId`

**Responses:**
- `200` — successful operation → `PayrollBasicResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/payrollFinalization`
**Operation:** `payrollFinalization`

**Summary:** Finalize (post) a payroll batch

**Description:** Use this operation to finalize (post) a payroll batch. This initializes the asynchronous posting process; the API responds with "buildStatus": "INIT". Subsequent calls to this API should be formatted exactly as the initial call, with the addition of the downloadId returned by the initial call. It will return either "buildStatus": "WARN", "buildStatus": "BUILD", "buildStatus": "ERROR", or "buildStatus": "DONE". If buildStatus is DONE, the batch has posted. If the system encounters payroll warnings, finalization is halted and warnings are returned in the warning array. When this occurs, review t…

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `batchId`, `clientId`

**Responses:**
- `200` — successful operation → `PayrollFinalizationResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/setBillingRuleUnbundled`
**Operation:** `setBillingRuleUnbundled`

**Summary:** Set an unbundled billing rule

**Description:** Service providers define unbundled billing rules to set separate fees that they charge the client company. Use this endpoint to create or update billing rules for a specific client. To create a new billing rule, pass 'NEW' in billingRuleNum. Checksum validation is not required when creating new rules. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writin…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetBillingRuleUnbundled`

**Responses:**
- `200` — successful operation → `SetBillingRuleUnbundledResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/setEmployeeOverrideRates`
**Operation:** `setEmployeeOverrideRates`

**Summary:** Update employee override rates

**Description:** This method updates employee override rate information. Use the checksum value from PayrollService.getEmployeeOverrideRates to update an employee's record. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `OverrideRate`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/setExternalPtoBalance`
**Operation:** `setExternalPtoBalance`

**Summary:** Post external PTO balance data

**Description:** Use this operation to write employee PTO balances from an external source. Employee PTO data can be broken out into PTO plan descriptions (up to 20 per employee), where each plan description is associated with PTO balance, accrued, used, and carryover amounts. This endpoint is intended for clients that are set up to use external PTO balances only. The client must have the External PTO used option enabled on the Other tab of the Client Details form. Typically, enabling this option means that PTO accrual and management occur in a separate application, such as a time system. Note: This operation …

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetExternalPtoBalanceRequest`

**Responses:**
- `200` — successful operation → `SetExternalPtoBalanceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/setPayrollApproval`
**Operation:** `setPayrollApproval`

**Summary:** Approve / Deny a payroll

**Description:** Use this method to approve (Y) or deny (N) a payroll. To obtain the checksum, call PayrollService.getPayrollApproval. Note: For approvals to work properly for setPayrollApproval, please use a PrismHR user account with the exact same user ID as your web services user account. See Using the API > Setting Up PrismHR and Web Services User Accounts in the documentation.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PayrollApproval`

**Responses:**
- `200` — successful operation → `ServiceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/setScheduledPayments`
**Operation:** `setScheduledPayments`

**Summary:** Update employee scheduled payments

**Description:** You can use this method to create or update an employee's scheduled payments. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ScheduledPaymentUpdate`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /payroll/v1/updatePayrollBatchWithOptions`
**Operation:** `updatePayrollBatchWithOptions`

**Summary:** Update payroll batch data and options

**Description:** This operation updates payroll batch data and payroll batch option settings. You cannot update payroll batches if they were already posted. Please note: any updates made to the batch via this API operation will reset the batch status to "TS.READY." This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PayrollBatchWithOptionsRequest`

**Responses:**
- `200` — successful operation → `PayrollBatchWithOptionsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /payroll/v1/updatePayrollSchedule`
**Operation:** `updatePayrollSchedule`

**Summary:** Update payroll schedule

**Description:** Use this method to update the details for a payroll schedule. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `*/*`
- Schema: `PayrollSchedule`

**Responses:**
- `200` — successful operation → `CreateUpdatePayrollScheduleResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---
