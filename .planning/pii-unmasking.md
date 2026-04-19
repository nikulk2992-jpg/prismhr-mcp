# PII Unmasking — Reference

Source: PrismHR's "Unmasking Personally Identifiable Information" guide.

PrismHR masks sensitive fields by default on the `getEmployee`,
`getEmployeeBySsn`, and `getEmpRestricted` endpoints. SSN returns as
`***-**-****`, date of birth returns as `****-**-**`, ACH account
numbers as `****`, etc. To receive raw values, the Allowed Methods
grant for the API user must include one or more `NOMASK*` tokens.

## Why this matters for us

- The New Hire Audit and YTD Reconciliation workflows treat any
  non-empty masked string as "field on file." That is correct for
  **presence detection** but insufficient for checks that need the
  actual value (format validation, age math, ACH verification).
- The 401(k) Match Compliance workflow's catch-up check needs real
  `birthDate` to compute age >= 50. It currently depends on
  `getEmployee` with `NOMASKDOB`.
- ACA workflows need accurate employee share amounts; no PII unmask
  required for ACA line 15/16 work specifically, but the dependent
  coverage age-out workflow (#18 in the catalog) will need it.

## Grant syntax

In the Allowed Methods for Web Service Users form, append
`#TOKEN1|TOKEN2|...` to the method name:

    EmployeeService.getEmployee#NOMASKSSN|NOMASKDOB|NOMASKACH

In the API representation returned by `login/getAPIPermissions`, the
tokens live in the `options` array of the corresponding
`allowedMethods` entry:

    {
      "service": "EmployeeService.getEmployee",
      "options": ["NOMASKSSN", "NOMASKDOB"],
      "fromTime": "",
      "toTime": ""
    }

`scripts/request_permissions.py` supports this via the
`DESIRED_UNMASK` mapping — it merges the requested tokens into the
grant payload alongside the base service list.

## Unmask token → field map

| Token | Fields exposed |
|---|---|
| `NOMASKSSN` | `cobraSSN`, `ssn` |
| `NOMASKDOB` | `birthDate` |
| `NOMASKACH` | `accountNum` |
| `NOMASKMED` | `allergy`, `condition`, `program`, `height`, `weight`, `bloodType`, `bloodRh`, `drugTestResult`, `audiotTestResult`, `physExamResult` |
| `NOMASKDOC` | `autoInsurancePolicyId`, `driverLicenseId`, `eligibilityDocument`, `i9EligAuthName`, `i9EligDocNum`, `i9IdAuthName`, `i9IdDocNum`, `identificationDocument`, `miscTaxId`, `vehicleRegNo` |
| `NOMASKPER` | `ethnicCode` |
| `NOMASKALTID` | `alternateId` |

## Important notes

- Unmask grants take effect even when the web service user's
  "Disable Method Restrictions" flag is checked. Unmask is always
  evaluated from the Allowed Methods grid, never from the bypass
  flag.
- Unmask is **per-method**, not global. Granting `NOMASKDOB` to
  `getEmployee` does not automatically unmask DOB on
  `getEmployeeBySsn`.
- Requesting a token that is already present in the current grant is
  a no-op; the permission script diffs against
  `getAPIPermissions.options` and only adds missing tokens.

## Security posture — what we grant and why

Current plan for the Simploy UAT API user (minimal-necessary):

| Service | Tokens | Justification |
|---|---|---|
| `EmployeeService.getEmployee` | `NOMASKSSN`, `NOMASKDOB` | 401(k) catchup age math + SSN format validity in New Hire Audit |
| `EmployeeService.getEmployeeSSNList` | `NOMASKSSN` | Accurate SSN presence + duplicate-SSN detection |
| `EmployeeService.getEmployeeBySSN` | `NOMASKSSN` | SSN-based lookup workflows |

Not requested by default (each would need a documented workflow
requiring the data):

- `NOMASKACH` — direct deposit ACH detail. No current workflow needs it.
- `NOMASKMED` — medical / drug test results. Out of scope.
- `NOMASKDOC` — driver license, i-9 numbers, tax IDs. Requires a
  documents-centric workflow before we grant.
- `NOMASKPER` — ethnicCode. EEO/AAP workflows may need later.
- `NOMASKALTID` — alternate employee identifier. Rarely needed.

## Operational guardrails

1. **Every unmask grant triggers an internal audit log entry.** Who
   requested, which tokens, when, why.
2. **Raw responses from unmasked endpoints never land on disk.** The
   probe sanitizer already strips SSN patterns and redacts keys named
   `ssn`, `birthDate`, `accountNumber`, etc. Unmask widens the raw
   stream but not the stored footprint.
3. **`.planning/verified-responses/` is gitignored.** Even if a
   probe accidentally captures unmasked PII, it stays off the public
   repo.
4. **Production (`PRISMHR_MCP_ALLOW_PROD=true`) gate remains.** UAT is
   the default for all probe + dogfood scripts.
