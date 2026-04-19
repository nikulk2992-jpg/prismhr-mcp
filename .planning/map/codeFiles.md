# Service: `codeFiles`

**40 methods** in this service.

## `GET /codeFiles/v1/getBillingCode`
**Operation:** `getBillingCode`

**Summary:** Get Billing codes

**Description:** This operation returns a list of client billing codes and their setup information. If more than 5000 billing codes match the criteria, this operation returns a paginated list. Use the count and startpage query parameters to navigate through the list of codes. count specifies the number of billing codes to return per page, and startpage indicates the starting position in the list. The operation returns these parameters in the response object as well, along with the total number of codes.You can also retrieve information about a single specific billing code, or restrict the output to non-obsolet…

**Parameters:**
- `sessionId` (header, required) — session token.
- `billingCode` (query, optional) — enter a billing code to only retrieve information about that code
- `onlyActive` (query, optional) — if true, the response only includes non-obsolete billing codes
- `count` (query, optional) — number of billing codes returned per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetBillingCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getClientCategoryList`
**Operation:** `getClientCategoryList`

**Summary:** Get client category list

**Description:** This operation returns the list of client categories. If more than 5000 client categories match the criteria, this operation returns a paginated list. Use the count and startpage query parameters to navigate through the list of client categories. count specifies the number of client categories to return per page, and startpage indicates the starting position in the list. The operation returns these parameters in the response object as well, along with the total number of client categories. You can also retrieve information about a single specific client category, or for all available client ca…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientCategoryId` (query, optional) — enter a client category ID to only retrieve information about that client category ID
- `count` (query, optional) — number of client category records to return per page
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetClientCategoryListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getContactTypeList`
**Operation:** `getContactTypeList`

**Summary:** Get Contact Type List

**Description:** Use this operation to retrieve a list of contact types.

**Parameters:**
- `sessionId` (header, required) — session token.

**Responses:**
- `200` — successful operation → `GetContactTypeListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getCourseCodesList`
**Operation:** `getCourseCodesList`

**Summary:** Get all courses associated with a particular client.

**Description:** The CodeFileService.getCourseCodesList method returns all courses associated with a client. This method returns a checksum for each course that can be used to update an existing course via the CodeFileService.setCourseCode method. Note: You can now now enter a single course code in the optional single course code field in CodeFileService.getCourseCodesList method, to return a single course code.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `courseCodeId` (query, optional) — single course code to return

**Responses:**
- `200` — successful operation → `CourseCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getDeductionCodeDetails`
**Operation:** `getDeductionCodeDetails`

**Summary:** Get Deduction code details

**Description:** This operation returns the configuration details for a specified deduction code.

**Parameters:**
- `sessionId` (header, required) — session token
- `deductionCode` (query, required) — deduction code ID

**Responses:**
- `200` — successful operation → `GetDeductionCodeDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getDepartmentCode`
**Operation:** `getDepartmentCode`

**Summary:** Get specified department code file for a particular client

**Description:** This operation returns information about a department code for the specified client. The provided checksum may be used with codeFiles.setDepartmentCode.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `departmentCode` (query, required) — department code

**Responses:**
- `200` — successful operation → `DepartmentCodeFileResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getDivisionCode`
**Operation:** `getDivisionCode`

**Summary:** Get specified division code file for a particular client

**Description:** This operation returns information about a division code for the specified client. The provided checksum may be used with CodeFileService.setDivisionCode. By default, this operation masks certain personally identifiable information (PII) in its response, such as Bank Account Number. Please refer to the API documentation article Unmasking PII to learn how to unmask this data.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `divisionCode` (query, required) — division code

**Responses:**
- `200` — successful operation → `DivisionCodeFileWithACHResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getEeoCodes`
**Operation:** `getEeoCodes`

**Summary:** Get EEO setup codes

**Description:** Use this operation to retrieve information about codes used during setup of EEO-1 reporting in PrismHR. There are three eeoCodeTypes: Class codes, Position Group codes, and Ethnic codes. You can retrieve information for only one eeoCodeType per call. This operation returns the code or codes in the object that corresponds to that code type. The other two response objects will return null You can also use the eeoCode option to filter the response to a specific setup code.

**Parameters:**
- `sessionId` (header, required) — session token
- `eeoCodeType` (query, required) — type of EEO-1 setup code to return; allowed values are 'Class', 'Group', and 'Ethnic'
- `eeoCode` (query, optional) — enter a setup code to only return information about that code, or leave blank to return all codes for the specified type

**Responses:**
- `200` — successful operation → `EeoCodesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getEventCodes`
**Operation:** `getEventCodes`

**Summary:** Returns event codes file for the specified client

**Description:** The CodeFiles.getEventCodes method returns a list of event codes and their descriptions.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier

**Responses:**
- `200` — successful operation → `EventCodesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getHolidayCodeList`
**Operation:** `getHolidayCodeList`

**Summary:** Get global holiday code list for this PEO

**Description:** Returns the system level list of Holidays with dates and description for this PEO. If the 'year' parameter is provided, the results will be filtered for the provided calendar year. If the 'year' parameter is omitted, all results will be returned. Checksum will only be provided if year is omitted so that entire result set is returned.

**Parameters:**
- `sessionId` (header, required) — session token
- `year` (query, optional) — year filter (format: YYYY)

**Responses:**
- `200` — successful operation → `HolidayCodeListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getNAICSCodeList`
**Operation:** `getNAICSCodeList`

**Summary:** Get NAICS Code List

**Description:** Use this endpoint to retrieve the details of one or all North American Industry Classification System (NAICS) codes that identify various industries including those that are obsolete in PrismHR. To retrieve the details of a particular NAICS code, pass it in the naicsCode parameter. Leave it blank to retrieve the details of all NAICS codes in PrismHR. This operation also returns paginated results. Use the count and startpage query parameters to navigate through the list of NAICS codes. count specifies the number of NAICS Codes to return per page, and startpage indicates the starting position in…

**Parameters:**
- `sessionId` (header, required) — session token
- `naicsCode` (query, optional) — a six-digit NAICS identifier that identifies the industry, for example, 311221. To retrieve the details of a particular NAICS code, enter it here. Leave it blank to retrieve the details of all NAICS codes in PrismHR.
- `count` (query, optional) — number of NAICS code records returned per page (default: 5000)
- `startpage` (query, optional) — pagination start location (first page = '0')

**Responses:**
- `200` — successful operation → `GetNAICSListResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getPayGrades`
**Operation:** `getPayGrades`

**Summary:** Get Client Pay Grades

**Description:** This operation returns information about one or more pay grade codes for a specific client.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `payGradeCode` (query, optional) — enter a pay grade code to only return information about that code, or leave blank to return all codes

**Responses:**
- `200` — successful operation → `PayGradesResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getPaycodeDetails`
**Operation:** `getPaycodeDetails`

**Summary:** Get Pay Code details

**Description:** Use this operation to retrieve pay code setup details

**Parameters:**
- `sessionId` (header, required) — session token.
- `paycodeId` (query, required) — pay code identifier

**Responses:**
- `200` — successful operation → `GetPaycodeDetailsResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getPositionClassifications`
**Operation:** `getPositionClassifications`

**Summary:** Returns position classifications.

**Description:** This operation retrieves information about position classification (position class) codes for a client. Use the positionClass input parameter to retrieve a specific position class code. This endpoint also returns a checksum for each code, which may be used when calling CodeFileService.setPositionClassification.

**Parameters:**
- `sessionId` (header, required) — session token
- `positionClass` (query, optional) — position class

**Responses:**
- `200` — successful operation → `PositionClassificationGetResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getPositionCode`
**Operation:** `getPositionCode`

**Summary:** Returns position code for the specified client.

**Description:** Use the CodeFiles.getPositionCodeDetails to return information about position codes.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `positionCode` (query, required) — position code

**Responses:**
- `200` — successful operation → `PositionCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getProjectCode`
**Operation:** `getProjectCode`

**Summary:** Returns project code for the specified client

**Description:** The CodeFilesService.getProjectCode method returns details about a single project code including certified payroll details information. Use the checksum provided to update a project code via CodeFilesService.setProjectCode. Note: you can obtain a list of project codes via ClientMasterService.getClientCodes with the Project option.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `projectCode` (query, required) — project code

**Responses:**
- `200` — successful operation → `ProjectCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getProjectPhase`
**Operation:** `getProjectPhase`

**Summary:** Returns project phases for the specified client.

**Description:** Use the CodeFiles.getProjectPhase to return information about project phases.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `classCode` (query, optional) — project class code
- `projectPhaseCode` (query, optional) — project phase code

**Responses:**
- `200` — successful operation → `ProjectPhaseResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /codeFiles/v1/getRatingCode`
**Operation:** `getRatingCode`

**Summary:** Get rating codes for specific client

**Description:** Use this operation to retrieve a list of rating codes for employee performance reviews. If you include a ratingCodeId in your input, the method only returns information about that rating code.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client whose rating codes you want to retrieve
- `ratingCodeId` (query, optional) — enter a valid rating code ID to return information about only that rating code

**Responses:**
- `200` — successful operation → `RatingCodeGetResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getShiftCode`
**Operation:** `getShiftCode`

**Summary:** Get specified shift code file for a particular client

**Description:** This operation returns information about a shift code for the specified client. The provided checksum may be used with codeFiles.setShiftCode.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `shiftCode` (query, required) — shift code

**Responses:**
- `200` — successful operation → `ShiftCodeFileResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getSkillCode`
**Operation:** `getSkillCode`

**Summary:** Returns skill code for the specified client

**Description:** The CodeFileService.getSkillCode method returns the details of a single skill code. Use the checksum returned to update a skill code via the CodeFileService.setSkillCode method. To obtain a complete list of a client's skill codes use ClientMasterService.getClientCodes with Skill as the option.

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `skillCode` (query, required) — skill code

**Responses:**
- `200` — successful operation → `SkillCodeGetResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `GET /codeFiles/v1/getUserDefinedFields`
**Operation:** `getUserDefinedFields`

**Summary:** Get user-defined fields for the specified field type

**Description:** Use this operation to retrieve user-defined fields from any part of the system where they exist. Use the **fieldType** input parameter to specify which type of user-defined fields you want to return (for example, enter Divisions if you want to return user-defined fields associated with a specific division). The fieldType parameter accepts the following values: * GroupBenefitPlans (Benefit Groups) * ClientDetails * DeliveryMethods * EmployeeDependents (typeId = employeeId.dependentId) * Departments * Divisions * RetirementPlanEnrollment * EmployeeBenefitsEnrollment (typeId = employeeId.benefitp…

**Parameters:**
- `sessionId` (header, required) — session token
- `clientId` (query, required) — client identifier
- `fieldType` (query, required) — type of user-defined fields you want to return (see the implementation notes for details)
- `typeId` (query, optional) — list of type identifiers (for example, department or worksite location IDs) associated with the fieldType. A maximum of 20 typeId values can be entered to retrieve user defined fields except ClientDetails which only allows one at a time.

**Responses:**
- `200` — successful operation → `UserDefinedFieldsGetResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setContactType`
**Operation:** `setContactType`

**Summary:** Set Contact Type

**Description:** Use this operation to create or update a contact type.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetContactTypeRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setCourseCode`
**Operation:** `setCourseCode`

**Summary:** Set a course code file for the specified client

**Description:** The CodeFileService.setCourseCode method updates or creates a course code. Use the checksum returned from CodeFileService.getCourseCode to update an existing course code. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `CourseCodeFile`

**Responses:**
- `200` — successful operation → `SetCourseCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /codeFiles/v1/setDeductionCodeDetails`
**Operation:** `setDeductionCodeDetails`

**Summary:** Set Deduction Code Details

**Description:** This operation sets the configuration details of a specified deduction code. When using this endpoint to update an existing code, provide the checksum value returned by CodeFileService.getDeductionCodeDetails for that code.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetDeductionCodeDetailsRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setDepartmentCode`
**Operation:** `setDepartmentCode`

**Summary:** Set a department code file for the specified client

**Description:** This operation creates or updates information about a department code for the specified client.The checksum is required when updating an existing department code and can be obtained by calling codeFiles/getDepartmentCode. If creating a new department code, omit checksum or provide checksum of zero ('0'). This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when wri…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `DepartmentCodeFileRequest`

**Responses:**
- `200` — successful operation → `DepartmentCodeFileResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setDivisionCode`
**Operation:** `setDivisionCode`

**Summary:** Set a division code file for the specified client

**Description:** This operation creates or updates information about a division code for the specified client.The checksum is required when updating an existing division code and can be obtained by calling codeFiles/getDivisionCode. If creating a new division code, omit checksum or provide checksum of zero ('0'). This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `DivisionCodeFile`

**Responses:**
- `200` — successful operation → `DivisionCodeFileResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

**Related:** [[setDivisionCodeWithAch]]

---

## `POST /codeFiles/v1/setDivisionCodeWithAch`
**Operation:** `setDivisionCodeWithAch`

**Summary:** Set a division code with ACH file for the specified client

**Description:** The CodeFile.setDivisionCodeWithAch method creates or updates information about a division code including ACH information for the specified client. The checksum is required when updating an existing division code, and can be obtained by calling the CodeFile.getDivisionCode method. If you are creating a new division code, omit the checksum or provide a checksum of zero ('0'). To update bank transit, account number, and account type, the ACH status must be set to active. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with th…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `DivisionCodeFileWithACH`

**Responses:**
- `200` — successful operation → `DivisionCodeFileWithACHResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setEthnicCode`
**Operation:** `setEthnicCode`

**Summary:** create or update ethnic code

**Description:** This operation creates or updates an EEO ethnic code. To retrieve existing ethnic codes, call CodeFilesService.getEeoCodes with eeoCodeType = ‘Ethnic’.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetEthnicCodeRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setEventCode`
**Operation:** `setEventCode`

**Summary:** Set an event code for a specified client

**Description:** Use the CodeFileService.setEventCode method to create or update an existing event code.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `EventCodesSetRequest`

**Responses:**
- `200` — successful operation → `EventCodesSetResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setPaycodeDetails`
**Operation:** `setPaycodeDetails`

**Summary:** Set Pay code details

**Description:** Use this operation to create or update a pay code. The provided checksum in codeFiles.getPaycodeDetails may be used to update a pay code. Please note that updating certain fields of an existing pay code that has been used to process payrolls can have serious ramifications. Please consider creating a new pay code instead.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetPayCodeDetailsRequest`

**Responses:**
- `200` — successful operation → `GenericUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setPositionClassification`
**Operation:** `setPositionClassification`

**Summary:** Set Position Classification

**Description:** This operation creates and updates position classifications. A checksum is required when updating an existing code. Obtain this checksum by calling CodeFileService.getPositionClassifications. If you are creating a new position classification, omit the checksum or provide a checksum of zero ('0').

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetPositionClassificationRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setPositionCode`
**Operation:** `setPositionCode`

**Summary:** The CodeFileService.setPositionCode method creates or edits an existing position.

**Description:** The CodeFilesService.setPositionCode method creates or updates a position/job code. Use CodeFilesService.getPositionCode checksum to make updates to a position code. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `PositionCodeRequest`

**Responses:**
- `200` — successful operation → `PositionCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /codeFiles/v1/setProjectClass`
**Operation:** `setProjectClass`

**Summary:** The CodeFileService.setProjectClass method creates or edits an existing project class.

**Description:** You can use the new method CodeFilesService.setProjectClass to create or update a project class. To get a list of existing project classes for a client, use ClientMasterService.getClientCodes with the option ProjClass.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ProjectClassRequest`

**Responses:**
- `200` — successful operation → `ProjectClassResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setProjectCode`
**Operation:** `setProjectCode`

**Summary:** Set a project code for a specified client

**Description:** The CodeFileService.setProjectCode method creates or edits an existing project code. To obtain the checksum to update a skill code for this method, call the CodeFileService.getProjectCode method. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record. The parameters "clientId", "id" , "description" and "checksum" are required to perform this operation. All other parameters may be omitted from the request object or set to null (not "null", which would be interpreted as a string). String values may be cleared by providin…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ProjectData`

**Responses:**
- `200` — successful operation → `ProjectCodeResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setProjectPhase`
**Operation:** `setProjectPhase`

**Summary:** Set a project phase for the specified client

**Description:** Use the CodeFiles.setProjectPhase to create a new phase or edit an existing phase.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SetProjectPhaseRequest`

**Responses:**
- `200` — successful operation → `SetProjectPhaseResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /codeFiles/v1/setRatingCode`
**Operation:** `setRatingCode`

**Summary:** Create or update a rating code.

**Description:** Use this operation to create or update a rating code used for employee performance reviews.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `RatingCodeSetRequest`

**Responses:**
- `200` — successful operation → `UpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /codeFiles/v1/setShiftCode`
**Operation:** `setShiftCode`

**Summary:** Set a shift code file for the specified client

**Description:** This operation creates or updates information about a shift code for the specified client. The checksum is required when updating an existing shift code and can be obtained by calling codeFiles/getShiftCode. If creating a new shift code, omit checksum or provide checksum of zero ('0'). Pay codes for regularPayCode and overtimePayCode can be obtained by calling clientMaster/getClientCodes. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The check…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `ShiftCodeFile`

**Responses:**
- `200` — successful operation → `CodeFileBasicUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /codeFiles/v1/setSkillCode`
**Operation:** `setSkillCode`

**Summary:** Set a skill code for a specified client

**Description:** The CodeFileService.setSkillCode method creates or edits an existing skill code. To obtain the checksum to update a skill code for this method, call the CodeFileService.getSkillCode method. This API requires that all data retrieved from the corresponding get operation be supplied in the request object along with the provided checksum. Any omitted data will be deleted from the database. The checksum is used to ensure that the data retrieved from the database is up-to-date when writing the updates back to the record.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `SkillCodeSetRequest`

**Responses:**
- `200` — successful operation → `SkillCodeGetResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---

## `POST /codeFiles/v1/setUserDefinedFields`
**Operation:** `setUserDefinedFields`

**Summary:** Set user-defined fields for the specified field type

**Description:** Use this operation to update any user-defined field for any entity in PrismHR. You must provide the checksum value returned by the getUserDefinedFields operation. Use the **fieldType** input parameter to specify which type of user-defined fields you want to update (for example, enter Divisions if you want to update user-defined fields associated with a specific division). The fieldType parameter accepts the following values: * GroupBenefitPlans (Benefit Groups) * ClientDetails * DeliveryMethods * EmployeeDependents (typeId = employeeId.dependentId) * Departments * Divisions * RetirementPlanEnr…

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `CustomFieldsUpdate`

**Responses:**
- `200` — successful operation → `CustomFieldsUpdateResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `409` — the record specified for updating has been modified since it was last read → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_
- `503` — the record specified for updating is currently locked by another user → _(no schema)_

---

## `POST /codeFiles/v1/setWorkGroupCode`
**Operation:** `setWorkGroupCode`

**Summary:** The CodeFileService.setWorkGroupCode method creates or edits an existing work

**Description:** You can use the new CodeFile.setWorkGroup method to create or update work groups. To return work group information, use ClientMasterService.getClientCodes with Workgroup as the option.

**Request body:**
- Content-Type: `application/xml, application/json`
- Schema: `WorkGroupRequest`

**Responses:**
- `200` — successful operation → `WorkGroupResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `404` — the requested resource could not be found → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — internal server error → _(no schema)_

---
