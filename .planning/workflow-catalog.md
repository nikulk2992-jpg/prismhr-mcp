# Workflow Catalog — `prismhr-mcp-simploy` Tier 2

Master list of workflow opportunities derived from the PrismHR
documentation bible + live UAT probing. Each row ties a real PEO pain
point to verified (or authorized) PrismHR endpoints.

Status legend:
- **LIVE** — shipped + passing tests + live UAT dogfood
- **BUILT** — code shipped, dogfood pending
- **SPEC** — designed, unbuilt
- **SCOPED** — identified in bible, needs design

---

## Domain 1 — Onboarding / HR

| # | Workflow | Status | Primary Endpoints | Bible anchor |
|---|---|---|---|---|
| 1 | New Hire Onboarding Audit | **LIVE** | getEmployeeList, getEmployee, getAddressInfo (ContactInformation), getEverifyStatus, getScheduledDeductions, checkForGarnishments | Ch "Employee Details — Status Change" |
| 2 | I-9 / Document Expiration Sweep | SPEC | getDocExpirations (verified) | Ch "New Hire Documents" |
| 3 | E-Verify Case Aging | SPEC | getEverifyStatus × case-open dates | Ch "E-Verify Processing" |
| 4 | Terminated Employee Cleanup | SPEC | employee events, getCobraEmployee, final-check status | Ch "Employee Status — Termination" |

## Domain 2 — Payroll

| # | Workflow | Status | Primary Endpoints |
|---|---|---|---|
| 5 | Payroll Batch Health Check | **LIVE** | getBatchListFor(Approval|Initialization), getBatchStatus, getBatchInfo, getPayrollVoucherForBatch, getApprovalSummary |
| 6 | YTD Payroll Reconciliation | **LIVE** | getBulkYearToDateValues (async), getPayrollVouchers (paginated) |
| 7 | Manual Check Audit | SPEC | getManualChecks × voucher trail |
| 8 | Overtime Anomaly Detection | SPEC | voucher line-items × standardHours × historical baseline |
| 9 | Pay Group Schedule Adherence | SPEC | getPayrollSchedule × batch finalization dates |
| 10 | Scheduled-Payment Integrity | SPEC | getScheduledPayments × voucher reconciliation |

## Domain 3 — Benefits

| # | Workflow | Status | Primary Endpoints |
|---|---|---|---|
| 11 | Benefits-Deduction Audit | **BUILT** | getClientBenefitPlans, getGroupBenefitPlan (prDednCode/pr125Dedn/billCode), getBenefitConfirmationList, getScheduledDeductions |
| 12 | Billing-vs-Payroll Wash Audit | **BUILT** | getBillingVouchers × enrollments × getGroupBenefitPlan |
| 13 | ACA Configuration Integrity | **BUILT** | get1094 form data, getACAOfferedEmployees, getMonthlyACAInfo, get1095CYears |
| 14 | COBRA Eligibility Sweep | SPEC | getCobraCodes, getCobraEmployee × termination events |
| 15 | Benefit Adjustment Trail | SPEC | getBenefitAdjustments × audit log |
| 16 | Domestic Partner Plan Link | SPEC | getGroupBenefitPlan.dpPlanId + dependency check |
| 17 | FSA/HSA Contribution Limit Tracker | SPEC | getSection125Plans × getBulkYTDValues |
| 18 | Dependent Coverage Age-Out | SPEC | getDependents × DOB × age-26 threshold |
| 19 | Benefit Rate Change Drift | SPEC | getGroupBenefitRates × period-over-period delta |

## Domain 4 — Retirement

| # | Workflow | Status | Primary Endpoints |
|---|---|---|---|
| 20 | 401(k) Match Rule Compliance | **BUILT** | getRetirementPlan, get401KMatchRules, getEmployee401KContributionsByDate, getScheduledDeductions |
| 21 | Retirement Loan Status | SPEC | getRetirementLoans × repayment schedule |
| 22 | True-Up Calculation | SPEC | match rules × full-year contributions × expected true-up |
| 23 | Retirement Census Generator (Empower/Voya/Fidelity) | SPEC | Bulk YTD + plan + loans → carrier file |

## Domain 5 — Compliance

| # | Workflow | Status | Primary Endpoints |
|---|---|---|---|
| 24 | W-2 Readiness Check | SPEC | get1099Years, get1095CYears, YTD × tax withholding completeness |
| 25 | 941 Quarterly Reconciliation | SPEC | quarterly voucher totals × tax liability |
| 26 | Garnishment Payment History | SPEC | getGarnishmentDetails, getGarnishmentPaymentHistory |
| 27 | State Tax Setup Validator | SPEC | getSutaRates × employee work-state × client registration |
| 28 | Workers Comp Exposure | SPEC | getWCAccrualModifiers × wc codes × standardHours |
| 29 | OSHA 300A Assist | SPEC | getOSHA300Astats × incident data |
| 30 | 1094-C MEC Indicator Sweep | **BUILT** (inside ACA integrity) | — |
| 31 | 1095-C Safe Harbor Code Completeness | **BUILT** (inside ACA integrity) | — |
| 32 | IRS AIR Submission Pre-Flight | SPEC | Validate file against 1094/1095 common-errors list |

## Domain 6 — Billing / AR

| # | Workflow | Status | Primary Endpoints |
|---|---|---|---|
| 33 | Outstanding Invoice Aging | SPEC | getBulkOutstandingInvoices × client |
| 34 | Billing-vs-Payroll Reconciliation | SPEC | getBillingVouchers × getPayrollVouchers at client level |
| 35 | Prepay-vs-Liability Sweep | SPEC | getGroupBenefitPlan prepay flags × monthly billing |
| 36 | G/L Template Integrity | SPEC | getClientAccountingTemplate × every code's GL mapping |
| 37 | SUTA Billing Rate Drift | SPEC | getSutaBillingRates × period-over-period |
| 38 | Workers Comp Billing Modifier Sync | SPEC | getWCBillingModifiers × state codes |
| 39 | Unbundled Billing Rule Audit | SPEC | getUnbundledBillingRules × pay vouchers |

## Domain 7 — Client Onboarding / Setup

| # | Workflow | Status | Primary Endpoints |
|---|---|---|---|
| 40 | Client Go-Live Readiness | SPEC | getClientMaster, getClientOwnership, getPayrollSchedule, getPayGroupDetails, getClientBenefitPlans, getRetirementPlanList |
| 41 | NAICS / Industry Validation | SPEC | getNAICSCodeList × client config |
| 42 | Pay Group Employee Balance | SPEC | getEmployeesInPayGroup × schedule |
| 43 | Location Setup Completeness | SPEC | getClientLocationDetails × SUTA / WC by state |
| 44 | Labor Allocation Drift | SPEC | getLaborAllocations × department/division codes |

## Domain 8 — PTO / Absence

| # | Workflow | Status | Primary Endpoints |
|---|---|---|---|
| 45 | PTO Balance Reconciliation | SPEC | getPaidTimeOff, getPtoClasses, getPtoAutoEnrollRules |
| 46 | Absence Journal Audit | SPEC | getAbsenceJournal × time-off taken × balance |
| 47 | PTO Class Assignment Sanity | SPEC | getEmployee × getPtoClasses coverage |

## Domain 9 — Carrier Feeds (Tier 2 + Tier 3)

| # | Workflow | Status | Primary Endpoints |
|---|---|---|---|
| 48 | Guardian 834 Enrollment File | **LIVE** (prototype; SFTP deferred) | Benefit confirmations + eligibility + coverage → X12 834 5010 |
| 49 | BCBS Michigan 834 | SPEC | Same pattern as Guardian + MI companion guide |
| 50 | Sun Life EDX Feed | SPEC | EDX flat-file spec |
| 51 | Voya 401(k) PDI | SPEC | Fixed-width 401(k) deferral + match feed |
| 52 | Empower 401(k) PDI | SPEC | Same pattern |
| 53 | Fidelity Tape-Spec Feed | SPEC | Fidelity recordkeeper format |

---

## Workflow density by domain

| Domain | Count | Built + Live | % Shipped |
|---|---:|---:|---:|
| Onboarding / HR | 4 | 1 | 25% |
| Payroll | 6 | 2 | 33% |
| Benefits | 9 | 3 | 33% |
| Retirement | 4 | 1 | 25% |
| Compliance | 9 | 2 | 22% |
| Billing / AR | 7 | 0 | 0% |
| Client Setup | 5 | 0 | 0% |
| PTO / Absence | 3 | 0 | 0% |
| Carrier Feeds | 6 | 1 | 17% |
| **Total** | **53** | **10** | **19%** |

---

## What the bible unlocks that probing alone misses

1. **Form fields not in API responses.** `getClientBenefitPlans` omits
   the Deduction Code that `getGroupBenefitPlan` carries — bible
   confirmed the mapping, API probing can't find a field that isn't
   exposed by the endpoint you happened to hit.
2. **Validation rules.** Bible names the exact IRS penalty amounts
   ($270, $2,320, $3,480) and the specific submission errors (blank
   Box 16, MEC set to No) that trigger them. Workflow #13 directly
   encodes these.
3. **State-machine semantics.** "getApprovalSummary only works on
   INIT batches" is in the bible; probe alone would just see 400s.
4. **Cross-module dependencies.** GBP form + Benefit Rules + GL
   Template all interlock. Bible shows the full chain.
5. **Common error catalogs.** Bible has explicit "Common Sources of
   Coding Issues" sections in ACA, retirement, billing. Each section
   is a ready-made workflow brief.

---

## Next build priorities (bible-validated)

1. **#34 Billing-vs-Payroll Reconciliation (client level)** — bible
   calls this out as the single biggest billing/revenue risk for PEOs.
2. **#26 Garnishment Payment History** — regulatory + client-facing
   signal, data already verified.
3. **#24 W-2 Readiness** — Q1 2026 deadline, high urgency.
4. **#14 COBRA Eligibility Sweep** — bible shows explicit COBRA
   qualifying-event workflow; codifies penalty exposure.
5. **#40 Client Go-Live Readiness** — Simploy onboarding internal use.
