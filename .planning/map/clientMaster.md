# Service: `clientMaster`

**81 methods** in this service.

## `GET /clientMaster/v1/getACALargeEmployer`
**Operation:** `getACALargeEmployer`

**Summary:** Get ACA large Employer

**Description:** This operation retrieves information about ACA Large Employer status for one client or all clients. Note: To return information for all clients, the web service user must not have client restrictions. When the endpoint returns data for all clients and more than 5000 client records exist, it also supports pagination. Use the count and startpage query parameters to navigate through the list. count specifies the number of client records to return per page, and startpage indicates the starting position in the list of pages. The operation also returns these parameters in the response object, along …

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier; if the web service user has no client restrictions, enter “ALL” to return this information for all clients
- `count` (query, optional) — number of records per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetACALargeEmployerResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getAllPrismClientContacts`
**Operation:** `getAllPrismClientContacts`

**Summary:** Get all Prism client contacts

**Description:** Use this method to get information of all contacts for a specific client managed in the PrismHR product.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `PrismClientContactResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getBackupAssignments`
**Operation:** `getBackupAssignments`

**Summary:** Get Backup Assignments

**Description:** Use this operation to retrieve a list of backup users for the various Account Assignment roles for the specified client (Payroll, Human Resources, Sales, I-9 Approver, and so on).

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `GetBackupAssignmentsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getBenefitGroup`
**Operation:** `getBenefitGroup`

**Summary:** Get a benefit group

**Description:** This method retrieves up to 20 of the specified client company's benefit groups, including the groups' basic definitions, as well as associated group benefit plans and cafeteria plan contributions (if any). It also returns the checksum to use when updating group information with setBenefitGroup.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `groupId` (query, required) — benefit group identifier(s) of the groups currently defined for the client

**Responses:**
- `200` — successful operation → `GetBenefitGroupResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getBillPending`
**Operation:** `getBillPending`

**Summary:** Get bill pending record

**Description:** Use this operation to retrieve data associated with line items in the Client Bill Pending record. You can also refine the returned results by specifying a status, startBillDate, endBillDate, and event

**Parameters:**
- `sessionId` (header, required) — session identifier
- `clientId` (query, required) — client identifier
- `status` (query, optional) — only return bill pending items in a particular status. Options are Pending, Complete, or All (default)
- `startBillDate` (query, optional) — enter a date to only return bill pending items created on or after that date
- `endBillDate` (query, optional) — enter a date to only return bill pending items created on or before that date
- `event` (query, optional) — enter an event to only return bill pending items associated with that event code

**Responses:**
- `200` — successful operation → `GetBillPendingResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getBundledBillingRule`
**Operation:** `getBundledBillingRule`

**Summary:** Get bundled billing rule(s)

**Description:** Use this operation to retrieve bundled billing rules. You can filter the returned rules by Workers' Compensation code and its associated state, or retrieve a specific rule by its Billing Rule ID

**Parameters:**
- `sessionId` (header, required) — session identifier
- `clientId` (query, required) — client identifier
- `billingRule` (query, optional) — enter a billing rule id to return a specific bundled billing rule
- `wcCode` (query, optional) — only return bundled billing rules for the workers' compensation code
- `state` (query, optional) — only return bundled billing rules for the associate state in the workers' compensation code

**Responses:**
- `200` — successful operation → `GetBundledBillingRuleResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getClientBillingBankAccount`
**Operation:** `getClientBillingBankAccount`

**Summary:** Get client billing bank account

**Description:** Use this operation to retrieve client billing bank account information.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `GetClientBillingBankAccountResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getClientCodes`
**Operation:** `getClientCodes`

**Summary:** Get code tables for the specified client

**Description:** This method returns one or more code tables as arrays (lists) for the specified client. Within the Options string parameter, specify one or more of the option names in the table below. Note that the names are not case sensitive. Note that with shift codes, many of the data elements will be empty depending on whether the client is configured to use mileage mode or shift mode as configured in the Client Master/Detail parameters. This operation also returns paginated results for the option Project. Use the count and startpage query parameters to navigate through the list of projects. count specif…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `options` (query, required) — single string containing one or more of the options mentioned in notes section
- `excludeObsolete` (query, optional) — use to exclude obsolete codes. Flag only applies for BenefitGroup, Deduction, Department, Division, Job, Location, Pay, Project, Reason, Relation, Status, Type , Work group options
- `count` (query, optional) — number of codes returned per page (currently only available for Project option)
- `startpage` (query, optional) — pagination start location (first page = '0') (currently only applies for Project option)

**Responses:**
- `200` — successful operation → `GetClientCodesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getClientEvents`
**Operation:** `getClientEvents`

**Summary:** Get client specific events

**Description:** Use this operation to retrieve client events and the data associated with those events. This includes codes for any division, location, pay group, and other client entity listed under this event.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client whose events you want to retrieve
- `organizer` (query, optional) — enter an organizer if you want to only return events associated with them
- `fromDate` (query, optional) — enter a date if you want to only return events that occur from this date
- `thruDate` (query, optional) — enter a date if you want to only return events that occur through this date

**Responses:**
- `200` — successful operation → `GetClientEventsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getClientList`
**Operation:** `getClientList`

**Summary:** Get clients list

**Description:** This method returns an array of clients with clientId, clientName, legalName and status properties, restricted by the web service user's security settings. It returns only clients with the status of active unless you set inActive to true, in which case it will return clients with any status other than active.

**Parameters:**
- `sessionId` (header, required) — session token
- `inActive` (query, optional) — use to indicate whether the operation should retrieve inactive clients instead of active clients (which is the default behavior)

**Responses:**
- `200` — successful operation → `GetClientListResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getClientLocationDetails`
**Operation:** `getClientLocationDetails`

**Summary:** Get client location detail

**Description:** This operation returns information about the specified client's worksite location. By default, this operation masks certain personally identifiable information (PII) in its response, such as ACH bank account numbers. Please refer to the API documentation article Unmasking PII to learn how to unmask this data.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `locationId` (query, required) — ID of the client's worksite location to retrieve

**Responses:**
- `200` — successful operation → `GetClientLocationResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v2/getClientLocationDetails`
**Operation:** `getClientLocationDetails`

**Summary:** Get client location detail V2 version

**Description:** This operation retrieves details for a specific client worksite location. By default, this operation masks certain personally identifiable information in its response, such as ACH bank account numbers. For more information about unmasking this data, see the documentation article “Unmasking PII”.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `locationId` (query, required) — ID of the client's worksite location to retrieve

**Responses:**
- `200` — successful operation → `GetClientLocationResponseV2`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getClientMaster`
**Operation:** `getClientMaster`

**Summary:** Get client master data

**Description:** This method returns the entire Client Master data object for the specified client, as well as a checksum.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `GetClientMasterResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getClientOwnership`
**Operation:** `getClientOwnership`

**Summary:** Get client ownership details

**Description:** Use this operation to retrieve client ownership information as configured on the Client Details > Benefits tab. This operation also returns a checksum for data updates to the Client Details/Client Master record.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `GetClientOwnershipResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getDocExpirations`
**Operation:** `getDocExpirations`

**Summary:** Return docs that will expire within 'daysOut' days from current date

**Description:** Use this method to retrieve a list of employees' documents with an expiration date on or before the specified numbers of days from the current date. This method retrieves either Form I-9 documents (such as passports) or skills recorded in the Skills & Education tab of Employee Details (such as certifications).

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `employeeId` (query, optional) — employee identifier
- `docTypes` (query, required) — type of document: 'I9' (Form I-9 documents) or 'SKILL' (skills from Employee Details)
- `daysOut` (query, required) — number of days (for example, 42 to retrieve documents that have expired or will expire six weeks from today).

**Responses:**
- `200` — successful operation → `ExpiringDocumentsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getEmployeeListByEntity`
**Operation:** `getEmployeeListByEntity`

**Summary:** Get employee list by entity

**Description:** Use this operation to retrieve a list of employees associated with a particular client entity (for example, a division, worksite location, or project).

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `entityType` (query, required) — The type of entity specified by the entityId (location, division, workGroup, position, skill, shift, benefitGroup, project or department).
- `statusClass` (query, optional) — Specify a value to only return employees within that status class. Valid values are A (active), L (on leave), T (terminated), or a combination of these. If no value is specified, the method returns employees of all status classes.
- `entityId` (query, required) — entity identifier

**Responses:**
- `200` — successful operation → `EmployeeListByEntityResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getEmployeesInPayGroup`
**Operation:** `getEmployeesInPayGroup`

**Summary:** Get employees by pay group

**Description:** This operation retrieves a list of employees who are assigned to the specified pay group.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `payGroup` (query, required) — pay group identifier

**Responses:**
- `200` — successful operation → `EmployeePayGroupResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getGLCutbackCheckPost`
**Operation:** `getGLCutbackCheckPost`

**Summary:** Get GLCutbackCheckPost

**Description:** Use this endpoint to get general ledger cutback check posting information for the specified employer and save it to a file that the organization can import into their accounting software. Once posted, the data will no longer be available to post again unless regenerated manually in PrismHR. To regenerate a file, navigate to Reset Accounting in PrismHR.

**Parameters:**
- `sessionId` (header, required) — session token
- `glCompany` (query, required) — employer ID (GL company identifier)
- `tranDate` (query, required) — transaction date (date of the payroll), MM/DD/YY format

**Responses:**
- `200` — successful operation → `GLPostResultResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getGLData`
**Operation:** `getGLData`

**Summary:** Get GL data

**Description:** Use this endpoint to retrieve not-yet-posted transaction dates, employer IDs (glCompany identifiers), and amounts associated with the specified type. This information is available for users to export as a file, which they can then import into their accounting software.

**Parameters:**
- `sessionId` (header, required) — session token
- `type` (query, required) — type must be one of: 'Journal' (data available for journal posting), 'Invoice' (data available for invoice posting), or 'Cutback' (data available for check posting)

**Responses:**
- `200` — successful operation → `GLDataResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getGLInvoicePost`
**Operation:** `getGLInvoicePost`

**Summary:** Get GL invoice post

**Description:** Use this endpoint to get an employer’s G/L invoice posting information and save it to a file, which the organization can then import into their accounting software. Once posted, the data will no longer be available to post again unless regenerated manually in PrismHR. To regenerate a file, navigate to Reset Accounting in PrismHR. Call GeneralLedgerService.getGLInvoiceDetail to get detailed information about the invoice post.

**Parameters:**
- `sessionId` (header, required) — session token
- `glCompany` (query, required) — employer ID (GL company identifier)
- `invDate` (query, required) — invoice date (date of the payroll), MM/DD/YY format

**Responses:**
- `200` — successful operation → `GLPostResultResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getGLJournalPost`
**Operation:** `getGLJournalPost`

**Summary:** Get GL journal post

**Description:** Use this endpoint to get external general ledger journal posting information for the specified employer and save it to a file that the organization can import into their accounting software. Once posted, the data will no longer be available to post again unless regenerated manually in PrismHR. To regenerate a file, navigate to Reset Accounting in PrismHR.

**Parameters:**
- `sessionId` (header, required) — session token
- `glCompany` (query, required) — employer ID (GL company identifier)
- `tranDate` (query, required) — transaction date (date of the payroll), MM/DD/YY format

**Responses:**
- `200` — successful operation → `GLPostResultResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getGeoLocations`
**Operation:** `getGeoLocations`

**Summary:** Get GeoLocations matching for the ZIP code

**Description:** This method returns an array (list) of all Vertex GeoLocations matching the specified ZIP code. For each GeoLocation, the city, state, and county are also provided.

**Parameters:**
- `sessionId` (header, required) — session token
- `zipCode` (query, required) — the five-digit ZIP code used to match GeoLocations

**Responses:**
- `200` — successful operation → `GeoLocationResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getLaborAllocations`
**Operation:** `getLaborAllocations`

**Summary:** Get list of labor allocation templates

**Description:** This operation returns a list of labor allocation templates. By default, all labor allocation templates for the specified client will be returned. Optionally, a specific templateId may be specified so that only the details for that specific labor allocation template is returned. The checksum returned with each labor allocation template is used when updating that template using /clientMaster/setLaborAllocations.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `templateId` (query, optional) — template identifier

**Responses:**
- `200` — successful operation → `LaborAllocationTemplateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `GET /clientMaster/v1/getLaborUnionDetails`
**Operation:** `getLaborUnionDetails`

**Summary:** Get Labor Union Details

**Description:** The ClientMaster.getLaborUnionDetails method returns details for a specific labor union configured in PrismHR. Use the method ClientMasterService.getClientCodes with option Union to return the specified client's union codes.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `unionCode` (query, required) — union code

**Responses:**
- `200` — successful operation → `LaborUnionDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getMessageList`
**Operation:** `getMessageList`

**Summary:** Get message list

**Description:** This method returns a list (array) of messages without the body.

**Parameters:**
- `sessionId` (header, required) — session token
- `userId` (query, required) — user identifier
- `fromDate` (query, optional) — first date to retrieve, inclusive (format YYYY-MM-DD)
- `toDate` (query, optional) — last date to retrieve, inclusive (format YYYY-MM-DD)
- `unReadOnly` (query, optional) — _(no description)_

**Responses:**
- `200` — successful operation → `ClientMessageListResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getMessages`
**Operation:** `getMessages`

**Summary:** Get messages

**Description:** This method returns an array of messages, including the body of the message. The maximum number of messages is 20.

**Parameters:**
- `sessionId` (header, required) — session token
- `userId` (query, required) — user identifier
- `messageId` (query, required) — list of message IDs

**Responses:**
- `200` — successful operation → `ClientMessagesResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getOSHA300Astats`
**Operation:** `getOSHA300Astats`

**Summary:** Get OSHA 300A stats

**Description:** This method returns OSHA 300A statistics (data for the Summary of Work-Related Injuries and Illnesses) for the specified client. If you do not enter a location, the method calculates the totals for all of the client's locations for the specified reporting year. If you do specify a location, then the method returns the data for only that location and year.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `reportYear` (query, required) — report year
- `locationCode` (query, optional) — location code for report

**Responses:**
- `200` — successful operation → `ClientOSHA300AstatsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getPayDayRules`
**Operation:** `getPayDayRules`

**Summary:** Return pay day rules for the client

**Description:** Use this method to retrieve pay day rules for the client.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `PayDayRulesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getPayGroupDetails`
**Operation:** `getPayGroupDetails`

**Summary:** Get pay group details by pay group ID

**Description:** This method retrieves the details of the specified pay group.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `payGroupCode` (query, required) — pay group identifier

**Responses:**
- `200` — successful operation → `PayGroupDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getPayrollSchedule`
**Operation:** `getPayrollSchedule`

**Summary:** Get pay group and pay schedule for the specified client

**Description:** This method returns the pay group and pay schedule information for the specified client.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `PayrollScheduleResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getPrismClientContact`
**Operation:** `getPrismClientContact`

**Summary:** Get a Prism client contact

**Description:** Use this method to get information for a particular contact at a specific client managed in the PrismHR product.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `contactId` (query, required) — ID of the contact at the specified client to retrieve

**Responses:**
- `200` — successful operation → `PrismClientContactResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getRetirementPlanList`
**Operation:** `getRetirementPlanList`

**Summary:** Get Retirement Plan List

**Description:** This operation returns a list of all retirement benefit plans set up under the Benefits tab on the Client Details form in PrismHR for all or up to 10 selected clients. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of retirement benefit plans. count specifies the number of clients to return per page, and startpage indicates the starting position in the client list. The operation returns these parameters in the response object as well, along with the total number of clients. If the number of clients returned from the quer…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier; if the web service user has no client restrictions, enter “ALL” to return this information for all clients
- `count` (query, optional) — number of records per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetRetirementPlanListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getSutaBillingRates`
**Operation:** `getSutaBillingRates`

**Summary:** Get SUTA billing rates

**Description:** The ClientMaster.getSutaBillingRates method returns client SUTA billing rate information for a given state, effective date, and (optional) location.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `stateCode` (query, required) — state identifier
- `locationCode` (query, optional) — identifier for a location within the state (optional)
- `effectiveDate` (query, required) — date when the SUTA billing rate goes into effect, in YYYY-MM-DD format

**Responses:**
- `200` — successful operation → `GetSutaBillRate`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v2/getSutaBillingRates`
**Operation:** `getSutaBillingRates`

**Summary:** Get SUTA billing rates (v2)

**Description:** This operation returns client state unemployment tax (SUTA) billing rate information. Provide a fromDate to return all rates for a particular client and state from that date onward. To return data for a specific date or location code, provide a value for effectiveDate or location. Note: You cannot provide values for both effectiveDate and fromDate at the same time. This operation returns paginated results. Use the count and startpage query parameters to navigate through the list of billing rates. count specifies the number of billing rates to return per page, and startpage indicates the starti…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `stateCode` (query, required) — two-character state identifier; enter “ALLSTATES” to return billing rates for all states
- `locationCode` (query, optional) — optional identifier for a specific location within the state; enter “ALL” to return billing rates for all locations
- `effectiveDate` (query, optional) — specify a date when the SUTA billing rate goes into effect (format: YYYY-MM-DD) to return only billing rates for that date; to use this field, fromDate must be empty
- `fromDate` (query, optional) — specify a date in YYYY-MM-DD format to return all billing rates from that date onward; to use this field, effectiveDate must be empty
- `count` (query, optional) — number of billing rates returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetSutaBillRateResponseV2`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getSutaRates`
**Operation:** `getSutaRates`

**Summary:** Get SUTA rates

**Description:** This operation returns information about client-level and (if allowed) employer-level state unemployment tax rates (SUTA rates). You can enter "ALLCLIENTS" or "ALLEMPLOYERS" to return SUTA rates for all entities. Enter an effectiveDate to return SUTA rates effective on that date. Otherwise, provide a fromDate, which returns SUTA rates that are effective on or after that date. Note: This endpoint has option-level security applied to the employerId field. To use this field, in the Allowed Methods grid for the web service user, enter ClientMasterService.getSutaRates#EMPLOYER. For more details, se…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, optional) — client identifier; required if employerId is empty; enter a client ID or enter "ALLCLIENTS" to return SUTA rates for all clients
- `employerId` (query, optional) — employer identifier; web service user’s client access must include clients of this employer; this field is restricted by option-level access control (see implementation note); enter an employer ID or enter "ALLEMPLOYERS" to return SUTA rates for all employers
- `effectiveDate` (query, optional) — enter a date (format: YYYY-MM-DD) to return only SUTA rates with that effective date
- `fromDate` (query, optional) — required if effectiveDate is empty; enter a date (format: YYYY-MM-DD) to return SUTA rates that are effective on or after that date
- `state` (query, required) — enter a state code to return SUTA rate information for that state, or enter "ALLSTATES"
- `count` (query, optional) — number of SUTA rates returned per page
- `startpage` (query, optional) — pagination startpage location (first page = '0')

**Responses:**
- `200` — successful operation → `GetSutaRatesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getUnbundledBillingRules`
**Operation:** `getUnbundledBillingRules`

**Summary:** Get unbundled billing rules

**Description:** This operation returns a list of unbundled billing rules for the specified client, or information about a specific billing rule. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of rules. count specifies the number of rules to return per page, and startpage indicates the starting position in the rule list. The operation returns these parameters in the response object as well, along with the total number of rules.To call this endpoint, a web service user must have it listed in their Allowed Methods. Value|Description U Unit…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `ruleId` (query, optional) — identifier for a specific billing rule to return
- `count` (query, optional) — number of billing rules returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetClientUnbundledBillingResponse`
- `204` — no content → _(no schema)_
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getWCAccrualModifiers`
**Operation:** `getWCAccrualModifiers`

**Summary:** Get client W/C accrual modifiers

**Description:** Use this operation to retrieve all client-level Workers' Compensation accrual modifiers associated with a specified client. You can also filter the response by state and effective date.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `stateCode` (query, optional) — enter a two-character state code to only include W/C modifiers for that state
- `effectiveDate` (query, optional) — enter a date to only return W/C modifiers effective on or after that date

**Responses:**
- `200` — successful operation → `GetWCAccrualModifiersResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /clientMaster/v1/getWCBillingModifiers`
**Operation:** `getWCBillingModifiers`

**Summary:** Get client W/C billing modifiers

**Description:** Use this operation to retrieve information about client-level Workers' Compensation billing modifiers.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `stateCode` (query, required) — two-character Workers' Compensation state code
- `locationCode` (query, optional) — worksite location associated with the modifier
- `existingEffectiveDate` (query, optional) — date on which the modifier takes effect

**Responses:**
- `200` — successful operation → `WCBillingModifiersResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/addBillPending`
**Operation:** `addBillPending`

**Summary:** add a bill pending record

**Description:** Use this operation to create a new client bill pending entry. Before using this method, please ensure that you have reviewed the relevant documentation in the PrismHR Billing User Guide. Note: If you have custom approvals logic related to negative-valued client bill pending entries, this method will not trigger that logic.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `AddBillPendingRequest`

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

## `POST /clientMaster/v1/cloneClient`
**Operation:** `cloneClient`

**Summary:** Clone a client

**Description:** Use this operation to clone an existing client and, optionally, any data from system entities associated with that client. This operation initializes the clone process and responds with a status indicator and process ID. To check the status of the clone process, call the endpoint again and pass in the same process ID.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `CloneClientRequest`

**Responses:**
- `200` — successful operation → `CloneClientResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `429` — too many requests - the request was made prior to the previous request being completed → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/createClientMaster`
**Operation:** `createClientMaster`

**Summary:** Create a new client master record

**Description:** This operation creates a new client record. A Client Federal Entity record will also be automatically created for certified PEOs.It is important to note for security purposes that if you need to prevent the creation of new clients through the API, then you must configure the user security to prevent this. See the section User Authentication and Data Access Authorization in the online documentation for more information on how to do this. Note: createClientMaster does not actually add contacts to the client record. Once you have created the client master record, use createPrismClientContact to c…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `CreateClientEntry`

**Responses:**
- `200` — successful operation → `CreateClientMasterResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/createNewMessage`
**Operation:** `createNewMessage`

**Summary:** Create new message

**Description:** The operation creates a new message. There must be a matching Prism userID for the API web service user in order to successfully create a message.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `NewMessage`

**Responses:**
- `200` — successful operation → `ServiceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/createPositionCode`
**Operation:** `createPositionCode`

**Summary:** Create position code

**Description:** This API operation has been deprecated. Please use CodeFilesService.setPositionCode instead

**Request body:**
- Content-Type: `*/*`
- Schema: `PositionCode`

**Responses:**
- `200` — successful operation → `ServiceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/createPrismClientContact`
**Operation:** `createPrismClientContact`

**Summary:** Create a new Prism client contact

**Description:** Use this endpoint to create a new contact for a client managed in the PrismHR product. Note: This endpoint validates contact addresses against internal Geolocation codes. To enter a contact address, you must provide at least a ZIP code and a two-character state code. You can also provide a city name, but the endpoint will return an error if this does not match the internal city value for the GeoCode. To obtain a list of valid cities, states, and Geolocation codes for a particular ZIP, call ClientMasterService.getGeolocations. If the provided ZIP and state correspond to multiple unique Geolocat…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `CreatePrismClientContact`

**Responses:**
- `200` — successful operation → `ClientContactCreateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/createSutaRates`
**Operation:** `createSutaRates`

**Summary:** Create SUTA Rates

**Description:** Use this method to define the SUTA billing rates for the client. (SUTA is the State Unemployment Tax Act.)

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SutaRate`

**Responses:**
- `200` — successful operation → `SutaRatesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/deleteBillPending`
**Operation:** `deleteBillPending`

**Summary:** delete a bill pending record

**Description:** Use this operation to delete a Client Bill Pending entry. Note: You can delete a bill pending entry that is included in a payroll batch if the batch has not yet been finalized. In this case, the payroll processor must recalculate the payroll. You also cannot delete a bill pending item included in a payroll batch if that batch is awaiting client approval. Please ensure to return all values retrieved from getBillPending for the corresponding entryReference while calling operation (except for covidInfo and auditInfo). The delete will only be successful if all the values passed match existing valu…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `DeleteBillPendingRequest`

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

## `POST /clientMaster/v1/deletePrismMessage`
**Operation:** `deletePrismMessage`

**Summary:** delete Prism message

**Description:** This operation deletes one or more user messages. If some of the requested message IDs cannot be deleted, the endpoint returns a successful response and the updateMessage array lists the message IDs that were not deleted.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `messageListToDelete`, `userId`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /clientMaster/v1/flagClientsForEverify`
**Operation:** `flagClientsForEverify`

**Summary:** Flag all clients for everify that are listed in the input

**Description:** Use this operation to enable the E-Verify flag for multiple clients. The Web Service User must have access to all flagged clients, otherwise an error is returned.Call this method with the UNFLAG option if you want to disable the E-Verification flag for any clients specified in the method input.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`

**Responses:**
- `200` — successful operation → `EverifyClientsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/flagLocationEverifyOverride`
**Operation:** `flagLocationEverifyOverride`

**Summary:** Flag client's location(s) for everify

**Description:** Use this operation to set the E-Verify override flag for multiple worksite locations, such that any employees hired to that location do not go through the E-Verify process in spite of the client-level E-Verify setting. This is the equivalent of enabling the "Exclude this Location from E-Verification" option on the Worksite Locations form in PrismHR. You can also call this method with the "UNFLAG" option if you want to disable this setting for the specified worksite locations. This method returns a 400 HTTP response code if you only enter one locationId, or if none of the specified locations ar…

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`, `locationId`

**Responses:**
- `200` — successful operation → `EverifyLocationResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /clientMaster/v1/removePrismClientContact`
**Operation:** `removePrismClientContact`

**Summary:** Remove a Prism client contact

**Description:** Use this method to delete a contact record from a client managed in the PrismHR product.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `contactId` (query, required) — ID of the contact at the client to remove

**Responses:**
- `200` — successful operation → `ServiceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setACALargeEmployer`
**Operation:** `setACALargeEmployer`

**Summary:** Set ACA large Employer

**Description:** This operation creates, updates, and deletes information in the client ACA Large Employer table, for a particular year. Note: You cannot create multiple entries for the same year. Instead, edit the existing year record. Pass an empty string in a field to delete the value in that field. If you want to preserve the value in a field while updating others, omit the field from the request body. To delete all large employer data associated with the year YYYY for this client, pass DELETE.YYYY in the deleteYear field.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetACALargeEmployerRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setAccountAssignments`
**Operation:** `setAccountAssignments`

**Summary:** Update the account roles associated with a client

**Description:** Use this method to assign users to the account roles listed on the Client Details > Account tab. You can also set the custom field names and values of the My Support Team Dashboard, if this feature is enabled. Call this method with the checksum returned by ClientMasterService.getClientMaster.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `AccountAssignmentsRequest`

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

## `POST /clientMaster/v1/setAlternateEmployers`
**Operation:** `setAlternateEmployers`

**Summary:** set alteranate Employers

**Description:** Use this operation to update the Alternate Employers grid located on the Other tab of Client Details. A checksum value from ClientMasterService.getClientMaster is required. Note: This endpoint replaces all existing grid values with the data in the request object. To preserve existing values, retrieve them using getClientMaster and then pass the entire list (with your changes) in the request to setAlternateEmployers.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetAlternateEmployersRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setBackupAssignments`
**Operation:** `setBackupAssignments`

**Summary:** Set Backup Assignments

**Description:** Use this operation to update the list of backup users for the various Account Assignment roles for a specified client (Payroll, Human Resources, Sales, I-9 Approver, and so on). This operation does not append new values. Instead, it replaces the entire list and deletes any existing entries if they are left out of the request. Be sure to send a request with all account assignments, including the existing ones, unless you want the system to delete them.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetBackupAssignmentsRequest`

**Responses:**
- `200` — successful operation → `SetBackupAssignmentsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setBenefitGroup`
**Operation:** `setBenefitGroup`

**Summary:** Set a benefit group

**Description:** Use this method to create or update a benefit group for a client company. Clients use benefit groups when they need to define different benefits for different employees, such as setting up benefits for most employees and different benefits for executives. When updating an existing benefit group, this method requires a checksum attribute, which is used to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call the ClientMasterService.getBenefitGroups operation. When creating a new benefit group, pass an empty string for the checksum. This API requires that…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BenefitGroupSetup`

**Responses:**
- `200` — successful operation → `SetBenefitGroupResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setBillingDetails`
**Operation:** `setBillingDetails`

**Summary:** Set billing details

**Description:** This operation sets client billing information. Typically, you would use this endpoint for a new client. These settings are found in the PrismHR Client Details > Billing tab. Note that a checksum attribute is required, which is used to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call the ClientMasterService.getClientMaster operation. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is use…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `BillingDetails`

**Responses:**
- `200` — successful operation → `GenericUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setBundledBillingRule`
**Operation:** `setBundledBillingRule`

**Summary:** create or update bundled billing rule

**Description:** Use this operation to create or update a bundled billing rule. You can call this method using the checksum value returned by ClientMasterService.getBundledBillingRule while updating a bundled billing rule. To create a new bundled billing rule, set 'NEW' in the billingRule attribute.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetBundledBillingRuleRequest`

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

## `POST /clientMaster/v1/setClientBillingBankAccount`
**Operation:** `setClientBillingBankAccount`

**Summary:** Set client billing bank account

**Description:** Use this operation to update client billing bank account information. Submit the checksum value returned by ClientMasterService.getClientBillingBankAccount. Note:To provide web service user access to this method, you must explicitly list it in the Allowed Methods table for that user.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetClientBillingBankAccountRequest`

**Responses:**
- `200` — successful operation → `ClientMasterFieldsUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /clientMaster/v1/setClientControl`
**Operation:** `setClientControl`

**Summary:** Set client control options

**Description:** Use this method to set the processing and employer accounting information for a client. Typically, you use this method for a new client. (These settings are found in the PrismHR Client Details Control tab.) This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ClientControl`

**Responses:**
- `200` — successful operation → `GenericUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setClientEvents`
**Operation:** `setClientEvents`

**Summary:** Create or update a client specific event

**Description:** Use this method to create or update a client specific event and its associated information. If you would like to create a new client specific event, pass value "NEW" in the eventId field. Please note: unlike the PrismHR user interface, this method does not support document uploads. Use the checksum value returned by ClientMasterService.getClientEvents when calling this method to update an existing event.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetClientEventsRequest`

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

## `POST /clientMaster/v1/setClientLocationDetails`
**Operation:** `setClientLocationDetails`

**Summary:** Create new worksite location

**Description:** The operation creates a new worksite location. Note 1: Certain messages related to the creation or update of a worksite location may be returned in the updateClientResult.updateMessages array. These messages will have a corresponding errorType of either ERROR, WARNING, or ADDRESS_MISMATCH. The worksite location can be assumed created/updated unless "errorCode" is non-zero. Note 2: ClientMasterService.setClientLocationDetails support Symmetry geocodes and address lookup. This feature can be enabled by setting the useSymmetry flag in the input object to true. If the street address provided in th…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `LocationCode`

**Responses:**
- `200` — successful operation → `SetClientLocationDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setClientOwnership`
**Operation:** `setClientOwnership`

**Summary:** Set client ownership details

**Description:** Use this operation to set up client ownership information (defined in the Benefits tab of Client Details in PrismHR). This operation requires a checksum for updates. You can obtain this checksum by calling ClientMasterService.getClientMaster. Each owner or owner relation must be associated with a client contact. To obtain a list of existing contacts, see ClientMasterService.getAllPrismClientContacts.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetClientOwnershipRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setClientPayroll`
**Operation:** `setClientPayroll`

**Summary:** Set client payroll options

**Description:** Use this method to set the payroll delivery methods for a client. Typically, you use this method for a new client. (These settings are found in the PrismHR Client Details Payroll tab.) This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ClientPayroll`

**Responses:**
- `200` — successful operation → `SetClientPayrollResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setClientTimeSheetPayCode`
**Operation:** `setClientTimeSheetPayCode`

**Summary:** Set client time sheet pay codes and default hours

**Description:** Use this method to set the client's time sheet pay code information and the default hours pay code. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record. Checksum can be obtained using ClientMasterService.getClientMaster.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `TimesheetPayCodes`

**Responses:**
- `200` — successful operation → `SetClientTimeSheetPayCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setCodeDescriptionOverride`
**Operation:** `setCodeDescriptionOverride`

**Summary:** Create or update a code description override

**Description:** This operation creates or updates a (P)ay, (D)eduction, (T)ax, or (B)enefit code description override. These override descriptions are client specific rather than global.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `clientId`, `code`, `codeType`, `overrideDescription`

**Responses:**
- `200` — successful operation → `CodeDescriptionOverrideResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setControlCodes`
**Operation:** `setControlCodes`

**Summary:** Set Control Codes

**Description:** Use this operation to update the codes assigned on the Control tab of the Client Details form, such as pay codes, deduction codes, and employee types. Note: If no array is passed in one of the input parameters, the existing code values are not changed. However, if an array is passed (including an empty array), this will overwrite the existing database values for that code type.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ControlCodesRequest`

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

## `POST /clientMaster/v1/setLaborAllocations`
**Operation:** `setLaborAllocations`

**Summary:** Create or update labor allocation template

**Description:** This operation creates or updates a labor allocation template. The checksum is required when updating an existing labor allocation template and may be obtained using /clientMaster/getLaborAllocations. To create a new labor allocation template, provide a checksum of zero (0) or omit the checksum parameter. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when wr…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `LaborAllocationTemplate`

**Responses:**
- `200` — successful operation → `LaborAllocationTemplateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /clientMaster/v1/setLaborUnionDetails`
**Operation:** `setLaborUnionDetails`

**Summary:** set labor union details

**Description:** Use this operation to update details about a labor union configured in PrismHR. Note: This endpoint can only be called when explicitly listed in the Allowed Methods settings for the web service user, even when Disable Method Restrictions is set. To obtain client union codes, call the endpoint ClientMasterService.getClientCodes with Union option. To obtain details about existing client labor unions, call ClientMasterService.getLaborUnionDetails.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetLaborUnionDetailsRequest`

**Responses:**
- `200` — successful operation → `SetLaborUnionDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setMessageToRead`
**Operation:** `setMessageToRead`

**Summary:** Set a message as alreadyRead status

**Description:** This method sets a flag in a message to indicate that it has been read.

**Parameters:**
- `sessionId` (header, required) — session token
- `userId` (query, required) — user identifier
- `messageId` (query, required) — message identifier

**Responses:**
- `200` — successful operation → `SetClientMessageToReadResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setPayDayRules`
**Operation:** `setPayDayRules`

**Summary:** sets payday rules for a client

**Description:** This operation sets payday rules for a client. Note that a checksum attribute is required, which is used to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call the getPayDayRules operation. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PayDayRules`

**Responses:**
- `200` — successful operation → `ServiceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setPayGroup`
**Operation:** `setPayGroup`

**Summary:** set pay group details by pay group code

**Description:** Use this operation to create a new pay group for a client. This API does not support updates to an existing pay group.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetPayGroupRequest`

**Responses:**
- `200` — successful operation → `SetPayGroupResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setRetirementPlan`
**Operation:** `setRetirementPlan`

**Summary:** Update the retirement plans associated with a client

**Description:** Use this operation to update the Retirement Plan IDs and TPA Plan IDs associated with a client. Note: you must enter all IDs, including existing ones, or else any existing IDs will be deleted. Use the checksum value from ClientMasterService.getClientMaster when calling this method. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back t…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetClientRetirementPlanRequest`

**Responses:**
- `200` — successful operation → `SetClientRetirementPlanResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /clientMaster/v1/setWCAccrualModifiers`
**Operation:** `setWCAccrualModifiers`

**Summary:** Set client W/C accrual modifiers

**Description:** Use this operation to create or update client-level Workers' Compensation accrual modifiers. Note that the effectiveRate field is automatically calculated by the system, so any value passed in this parameter will be ignored.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetWCAccrualModifiersRequest`

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

## `POST /clientMaster/v1/setWCBillingModifiers`
**Operation:** `setWCBillingModifiers`

**Summary:** Set client W/C billing modifiers

**Description:** Use this method to set the client's workers' compensation billing modifiers.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `WCBillingModifiers`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/setWorkersCompPolicy`
**Operation:** `setWorkersCompPolicy`

**Summary:** update or create Workers' Compensation insurance policy

**Description:** Use this operation to create or update a Workers' Compensation insurance policy for a specified client. To use this method, you must enter the checksum value from ClientMasterService.getClientMaster. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `WorkersCompPolicyUpdate`

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

## `POST /clientMaster/v1/updateClientAddress`
**Operation:** `updateClientAddress`

**Summary:** Update client address information

**Description:** This operation updates client address information. Note that a checksum attribute is required, which is used to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call the getClientMaster operation. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ClientAddressUpdate`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/updateClientMasterFields`
**Operation:** `updateClientMasterFields`

**Summary:** Update client master fields

**Description:** Use this operation to update individual client fields without the requirement of providing a checksum. The API will ignore any fields excluded from the input, as well as any fields set to null. The operation returns a checksum for the client master record updated. Note: If you pass a value in the invoiceNotes request field, include all existing invoice notes unless you want to delete them. Any notes omitted from the request will be deleted. SecurityThis operation supports field-level security: for any web service user, you can grant or deny access to a subset of the supported client fields.To …

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateClientFieldsRequest`

**Responses:**
- `200` — successful operation → `ClientMasterFieldsUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /clientMaster/v1/updateClientStatus`
**Operation:** `updateClientStatus`

**Summary:** update client status

**Description:** Use this operation to change the status of a client. To use this endpoint, you must include the checksum for the client, returned by ClientMasterService.getClientMaster. Note: If the new status code represents client termination, all request parameters are required except for employeeTermDate and employeeTermReason.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdateClientStatusRequest`

**Responses:**
- `200` — successful operation → `UpdateClientStatusResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/updateClientTaxInfo`
**Operation:** `updateClientTaxInfo`

**Summary:** update Client Tax Info

**Description:** This operation updates client-level tax setup. In PrismHR, this corresponds to the Tax tab of Client Details. Note: This endpoint clears any fields left empty in the request object. To avoid overwriting data by mistake, include all existing client tax setup data when calling this endpoint. This applies to sub-arrays clientTax, taxParameters, redir, sdiDedn, and taxesToSuppress.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ClientTaxInfoUpdate`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/updatePrismClientContact`
**Operation:** `updatePrismClientContact`

**Summary:** Update a Prism client contact

**Description:** Use this endpoint to update the information for an existing contact at a specific client managed in PrismHR. A checksum is required to avoid a conflict with other transactions that might be in flight. To obtain the checksum, call the ClientMasterService.getAllPrismClientContacts or ClientMasterService.getPrismClientContact endpoints. This endpoint requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from …

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `UpdatePrismClientContact`

**Responses:**
- `200` — successful operation → `ServiceResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /clientMaster/v1/updateWorksiteLocationAch`
**Operation:** `updateWorksiteLocationAch`

**Summary:** Update worksite location's ACH

**Description:** This method allows the user to update the ACH data associated with a client worksite location. To obtain the checksum for this method, call the ClientMasterService.getClientLocationDetails method. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `WorksiteLocationAchUpdate`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---
