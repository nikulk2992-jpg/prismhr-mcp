"""Adapters bridging the OSS core's PrismHRClient to workflow readers.

Workflows declare narrow reader protocols; adapters translate each
protocol method into one or more PrismHR endpoint calls. Keeping this
split means workflows remain testable with in-memory fakes while still
talking to real PrismHR in production.
"""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from typing import Any, TYPE_CHECKING

import httpx

from prismhr_mcp.clients.prismhr import PrismHRClient

if TYPE_CHECKING:
    from simploy.config.plan_deduction_map import PlanDeductionMap


class PrismHRClientReader:
    """Implements `new_hire_audit.PrismHRReader` against a live PrismHRClient.

    `get_employee_list` is a two-pass call because PrismHR's
    getEmployeeList returns only IDs (no hire date) and has no
    server-side hire-date filter. We fetch IDs, then getEmployee in
    batches of up to 20, then filter client-side. The
    `max_detail_fetch` cap bounds the total number of detail calls so
    a large roster does not produce hundreds of requests.
    """

    # PrismHR's getEmployee accepts up to 20 comma-separated IDs per call.
    _DETAIL_BATCH_SIZE = 20
    # Default cap on how many employee detail records we will fetch
    # during a list-level probe; callers can override by wrapping.
    _DEFAULT_DETAIL_CAP = 200

    def __init__(
        self,
        client: PrismHRClient,
        *,
        max_detail_fetch: int = _DEFAULT_DETAIL_CAP,
    ) -> None:
        self._c = client
        self._cap = max_detail_fetch

    async def get_employee_list(self, client_id: str, hired_since: date) -> list[dict]:
        # Step 1: fetch all active employee IDs for the client.
        list_body = await self._c.get(
            "/employee/v1/getEmployeeList",
            params={"clientId": client_id, "employmentStatus": "A"},
        )
        ids = _extract_ids(list_body)
        if not ids:
            return []
        # Step 2: detail-fetch in bounded batches. PrismHR wants repeated
        # `employeeId` query params (NOT comma-separated). `options=Client`
        # pulls in hireDate + status; Person pulls in ssn via getEmployee.
        ids_to_probe = sorted(ids, reverse=True)[: self._cap]
        details: list[dict] = []
        for i in range(0, len(ids_to_probe), self._DETAIL_BATCH_SIZE):
            chunk = ids_to_probe[i : i + self._DETAIL_BATCH_SIZE]
            params: list[tuple[str, str]] = [
                ("clientId", client_id),
                ("options", "Person,Client"),
            ]
            params.extend(("employeeId", eid) for eid in chunk)
            body = await self._c.get("/employee/v1/getEmployee", params=params)
            rows = _rows(body, "employee") or []
            details.extend(rows)
        # Step 3: filter client-side by hire date >= hired_since. The
        # relevant field is client.lastHireDate (most recent rehire) and
        # falls back to firstHireDate for employees who were never rehired.
        results: list[dict] = []
        for r in details:
            client_block = r.get("client") or {}
            raw_hire = (
                client_block.get("lastHireDate")
                or client_block.get("firstHireDate")
                or client_block.get("statusDate")
                or ""
            )
            parsed = _parse_iso_prefix(raw_hire)
            if parsed is None or parsed < hired_since:
                continue
            results.append(
                {
                    "employeeId": r.get("id") or r.get("employeeId") or "",
                    "firstName": r.get("firstName", ""),
                    "lastName": r.get("lastName", ""),
                    "hireDate": raw_hire,
                }
            )
        return results

    async def get_employee(self, client_id: str, employee_id: str) -> dict:
        # Pull Person + SSN list. Person's ssn field is absent from our UAT
        # surface; use getEmployeeSSNList for SSN presence detection. Value
        # may be masked (e.g. "***-**-****"); "present" is non-empty string.
        detail = await self._c.get(
            "/employee/v1/getEmployee",
            params=[
                ("clientId", client_id),
                ("options", "Person"),
                ("employeeId", employee_id),
            ],
        )
        row = _first(detail, "employee") or {}
        ssn_body = await self._c.get(
            "/employee/v1/getEmployeeSSNList",
            params={"clientId": client_id},
        )
        ssn_map = {
            r.get("employeeId"): r.get("ssn")
            for r in _rows(ssn_body, "employeeSSNList")
            if isinstance(r, dict)
        }
        return {
            "employeeId": row.get("id") or row.get("employeeId") or employee_id,
            "ssn": ssn_map.get(employee_id, "") or "",
        }

    async def get_address(self, client_id: str, employee_id: str) -> dict:
        # ContactInformation option returns {addressLine1, city, state, zipcode}
        # at the top level of contactInformation (not nested under homeAddress).
        body = await self._c.get(
            "/employee/v1/getEmployee",
            params=[
                ("clientId", client_id),
                ("options", "ContactInformation"),
                ("employeeId", employee_id),
            ],
        )
        row = _first(body, "employee") or {}
        contact = row.get("contactInformation") or {}
        return {
            "line1": contact.get("addressLine1") or contact.get("line1") or "",
            "city": contact.get("city", ""),
            "state": contact.get("state", ""),
            "zip": contact.get("zipcode") or contact.get("postalCode") or "",
        }

    async def get_everify(self, client_id: str, employee_id: str) -> dict:
        body = await self._c.get(
            "/employee/v1/getEverifyStatus",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        # Real shape: {everifyStatus: {everifyFlag, everifyCaseNo, everifyCaseStatus}}
        ev = (body or {}).get("everifyStatus") or {}
        if isinstance(ev, list):
            ev = ev[0] if ev else {}
        return {
            "everifyStatus": ev.get("everifyCaseStatus") or ev.get("everifyFlag") or "",
        }

    async def get_scheduled_deductions(self, client_id: str, employee_id: str) -> dict:
        body = await self._c.get(
            "/employee/v1/getScheduledDeductions",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        rows = _rows(body, "scheduledDeductions") or _rows(body, "deductions") or []
        return {"scheduledDeductions": rows}

    async def check_garnishments(self, client_id: str, employee_id: str) -> dict:
        body = await self._c.get(
            "/employee/v1/checkForGarnishments",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        row = body or {}
        has = bool(row.get("hasGarnishments") or row.get("garnishmentCount", 0))
        return {
            "hasGarnishments": has,
            "setupComplete": bool(row.get("setupComplete", has)),
        }


class BenefitsDeductionAuditReader:
    """Live-data implementation of benefits_deduction_audit.PrismHRReader.

    PrismHR's getBenefitConfirmationList is per-employee (despite the
    'List' name), so this adapter iterates the client's employee roster
    and aggregates confirmations. Bounded by `max_employees` to avoid
    accidentally probing hundreds of records on a large client.
    """

    _DEFAULT_EMPLOYEE_CAP = 100

    def __init__(
        self,
        client: PrismHRClient,
        *,
        max_employees: int = _DEFAULT_EMPLOYEE_CAP,
        plan_deduction_map: "PlanDeductionMap | None" = None,
    ) -> None:
        self._c = client
        self._cap = max_employees
        self._pdm = plan_deduction_map

    async def get_active_benefit_plans(self, client_id: str) -> list[dict]:
        # Plan -> deduction-code mapping resolution order:
        #   1. Operator-supplied YAML (self._pdm) — works even without
        #      getGroupBenefitPlan permission.
        #   2. getGroupBenefitPlan(planId) — the authoritative source.
        #      Fields: prDednCode, prDednCodepp (payroll), pr125Dedn,
        #      pr125Dednpp (Section 125), billCode, prepayBillCode.
        #   3. Inline fields on getClientBenefitPlans response (rare).
        body = await self._c.get(
            "/benefits/v1/getClientBenefitPlans",
            params={"clientId": client_id},
        )
        rows = _rows(body, "benefitPlanOverview") or _rows(body, "benefitPlan") or []
        out: list[dict] = []
        for r in rows:
            code = r.get("planId") or r.get("planCode") or ""
            if not code:
                continue
            expected: set[str] = set()

            # Source 1: YAML mapping.
            if self._pdm is not None:
                expected.update(self._pdm.expected_deduction_codes(client_id, code))

            # Source 2: getGroupBenefitPlan — authoritative when authorized.
            if not expected:
                expected.update(await self._fetch_gbp_deduction_codes(code))

            # Source 3: inline fields on getClientBenefitPlans (defensive).
            for k in ("deductionCode", "deductionCodes", "dedCode", "payrollDeductionCode"):
                v = r.get(k)
                if isinstance(v, str) and v:
                    expected.add(v)
                elif isinstance(v, list):
                    expected.update(str(x) for x in v if x)

            out.append({"planId": code, "expectedDeductionCodes": sorted(expected)})
        return out

    async def _fetch_gbp_deduction_codes(self, plan_id: str) -> set[str]:
        """Pull the deduction codes off a plan's Group Benefit Plan record.

        Returns an empty set on 403 (permission gated) or any other
        error, so the workflow degrades gracefully to skipping the plan.
        """
        try:
            body = await self._c.get(
                "/benefits/v1/getGroupBenefitPlan",
                params={"planId": plan_id},
            )
        except Exception:  # noqa: BLE001 — permission / transport issues are non-fatal
            return set()
        if not isinstance(body, dict):
            return set()
        if body.get("errorCode") not in (None, "", "0"):
            return set()
        gbp = body.get("groupBenefitPlan")
        if isinstance(gbp, list):
            gbp = gbp[0] if gbp else {}
        if not isinstance(gbp, dict):
            return set()
        codes: set[str] = set()
        for field_name in ("prDednCode", "prDednCodepp", "pr125Dedn", "pr125Dednpp"):
            v = gbp.get(field_name)
            if isinstance(v, str) and v.strip():
                codes.add(v.strip())
        return codes

    async def get_benefit_confirmations(self, client_id: str) -> list[dict]:
        # Fetch the active employee roster (IDs only), then iterate
        # getBenefitConfirmationList per-employee up to the cap.
        list_body = await self._c.get(
            "/employee/v1/getEmployeeList",
            params={"clientId": client_id, "employmentStatus": "A"},
        )
        ids = _extract_ids(list_body)[: self._cap]
        out: list[dict] = []
        for eid in ids:
            try:
                body = await self._c.get(
                    "/benefits/v1/getBenefitConfirmationList",
                    params={"clientId": client_id, "employeeId": eid},
                )
            except Exception:  # noqa: BLE001
                continue
            rows = (
                _rows(body, "benefitConfirmationList")
                or _rows(body, "benefitConfirmation")
                or _rows(body, "confirmations")
                or []
            )
            if not rows:
                continue
            first = rows[0] if isinstance(rows[0], dict) else {}
            out.append(
                {
                    "employeeId": eid,
                    "firstName": first.get("firstName", ""),
                    "lastName": first.get("lastName", ""),
                    "plans": [
                        {
                            "planId": str(
                                r.get("planId")
                                or r.get("planCode")
                                or r.get("benefitPlan")
                                or ""
                            )
                        }
                        for r in rows
                        if r.get("planId") or r.get("planCode") or r.get("benefitPlan")
                    ],
                }
            )
        return out

    async def get_scheduled_deductions(
        self, client_id: str, employee_id: str
    ) -> list[dict]:
        body = await self._c.get(
            "/employee/v1/getScheduledDeductions",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        rows = (
            _rows(body, "scheduledDeductions")
            or _rows(body, "scheduledDeduction")
            or _rows(body, "deductions")
            or []
        )
        return [
            {
                "code": r.get("deductionCode") or r.get("code") or "",
                "amount": r.get("amount") or r.get("deductionAmount") or "0",
                "frequency": r.get("frequency", ""),
            }
            for r in rows
        ]


class YTDReconciliationReader:
    """Live-data implementation of ytd_reconciliation.PrismHRReader."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def get_bulk_ytd(self, client_id: str, year: int) -> list[dict]:
        # getBulkYearToDateValues is an async download:
        #   1. First call returns {downloadId, buildStatus: "INIT"}.
        #   2. Subsequent calls with the same params + downloadId return
        #      buildStatus=BUILD or DONE.
        #   3. When DONE, `dataObject` holds a URL where the compiled
        #      JSON is served; the session token is required to fetch it.
        base_params = {"clientId": client_id, "asOfDate": f"{year}-12-31"}
        body = await self._c.get("/payroll/v1/getBulkYearToDateValues", params=base_params)
        if not isinstance(body, dict):
            return []

        download_id = body.get("downloadId")
        status = (body.get("buildStatus") or "").upper()
        while download_id and status not in ("DONE", "ERROR", ""):
            await asyncio.sleep(2)
            body = await self._c.get(
                "/payroll/v1/getBulkYearToDateValues",
                params={**base_params, "downloadId": download_id},
            )
            status = (body.get("buildStatus") or "").upper()

        if status != "DONE":
            return []

        data_url = body.get("dataObject")
        if not data_url:
            return []
        # Fetch the compiled JSON via the same session. The OSS client
        # speaks PrismHR paths only, so use its underlying session token
        # against an absolute URL via a fresh httpx call.
        token = await self._c._session.token()  # type: ignore[attr-defined]
        http = httpx.AsyncClient(timeout=120.0)
        try:
            resp = await http.get(
                data_url,
                headers={"sessionId": token, "Accept": "application/json"},
            )
            if resp.status_code != 200:
                # Stream server returned an error — log nothing (silent in
                # dogfood) and let the workflow report as YTD_MISSING.
                return []
            try:
                payload = resp.json()
            except ValueError:
                return []
        finally:
            await http.aclose()
        # Payload shape per bible: { "data": [ { "employeeId": ..., "YTD": {...} } ] }
        if isinstance(payload, dict):
            return _rows(payload, "data") or _rows(payload, "values") or []
        return []

    async def get_vouchers(self, client_id: str, year: int) -> list[dict]:
        # PrismHR caps getPayrollVouchers at 5000 per response; paginate
        # via startpage + count until exhausted. Walk by quarter to stay
        # well under the cap for high-voucher clients.
        out: list[dict] = []
        quarters = [
            (f"{year}-01-01", f"{year}-03-31"),
            (f"{year}-04-01", f"{year}-06-30"),
            (f"{year}-07-01", f"{year}-09-30"),
            (f"{year}-10-01", f"{year}-12-31"),
        ]
        for start, end in quarters:
            page = 0
            while True:
                try:
                    body = await self._c.get(
                        "/payroll/v1/getPayrollVouchers",
                        params={
                            "clientId": client_id,
                            "payDateStart": start,
                            "payDateEnd": end,
                            "startpage": str(page),
                            "count": "1000",
                        },
                    )
                except Exception:  # noqa: BLE001 — empty window or throttle
                    break
                rows = _rows(body, "payrollVoucher") or _rows(body, "vouchers") or []
                if not rows:
                    break
                out.extend(rows)
                if len(rows) < 1000:
                    break
                page += 1
        return out


class RetirementMatchReader:
    """Live-data implementation of retirement_match_compliance.PrismHRReader."""

    _DEFAULT_EMPLOYEE_CAP = 50

    def __init__(self, client: PrismHRClient, *, max_employees: int = _DEFAULT_EMPLOYEE_CAP) -> None:
        self._c = client
        self._cap = max_employees

    async def get_retirement_plan(self, client_id: str) -> dict:
        body = await self._c.get(
            "/clientMaster/v1/getRetirementPlanList",
            params={"clientId": client_id},
        )
        for cr in _rows(body, "clientRetirement"):
            plans = cr.get("retirementPlanList") or []
            if plans and isinstance(plans[0], dict):
                return {
                    "retirePlan": plans[0].get("retirePlan") or "401K",
                    "startDate": plans[0].get("startDate"),
                    "endDate": plans[0].get("endDate"),
                }
        return {"retirePlan": "401K"}

    async def get_401k_match_rules(self, client_id: str, plan_id: str) -> list[dict]:
        try:
            body = await self._c.get(
                "/benefits/v1/get401KMatchRules",
                params={
                    "clientId": client_id,
                    "retirementPlanId": plan_id,
                    "benefitGroupId": "1",
                },
            )
        except Exception:  # noqa: BLE001
            return []
        return _rows(body, "match401KRules") or _rows(body, "matchRules") or []

    async def get_employee_401k_contributions(
        self, client_id: str, year: int
    ) -> list[dict]:
        # Iterate active employees and call getEmployee401KContributionsByDate
        # per-employee up to the cap.
        list_body = await self._c.get(
            "/employee/v1/getEmployeeList",
            params={"clientId": client_id, "employmentStatus": "A"},
        )
        ids = _extract_ids(list_body)[: self._cap]
        out: list[dict] = []
        for eid in ids:
            try:
                body = await self._c.get(
                    "/payroll/v1/getEmployee401KContributionsByDate",
                    params={
                        "clientId": client_id,
                        "employeeId": eid,
                        "startDate": f"{year}-01-01",
                        "endDate": f"{year}-12-31",
                    },
                )
            except Exception:  # noqa: BLE001
                continue
            ee = Decimal("0")
            er = Decimal("0")
            gross = Decimal("0")
            for r in _rows(body, "employee401KContributions") + _rows(body, "contribution"):
                ee += _dec(r.get("employeeContribution") or r.get("employeeDeferral"))
                er += _dec(r.get("employerMatch") or r.get("employerContribution"))
                gross += _dec(r.get("grossWages") or r.get("ytdGross"))
            out.append(
                {
                    "employeeId": eid,
                    "employeeContribution": str(ee),
                    "employerMatch": str(er),
                    "ytdGross": str(gross),
                }
            )
        return out

    async def get_scheduled_deductions(
        self, client_id: str, employee_id: str
    ) -> list[dict]:
        body = await self._c.get(
            "/employee/v1/getScheduledDeductions",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        rows = (
            _rows(body, "scheduledDeductions")
            or _rows(body, "scheduledDeduction")
            or _rows(body, "deductions")
            or []
        )
        return [
            {"code": r.get("deductionCode") or r.get("code") or ""}
            for r in rows
        ]

    async def get_employee_dob(self, client_id: str, employee_id: str):  # type: ignore[no-untyped-def]
        from datetime import date

        body = await self._c.get(
            "/employee/v1/getEmployee",
            params=[
                ("clientId", client_id),
                ("options", "Person"),
                ("employeeId", employee_id),
            ],
        )
        row = _first(body, "employee") or {}
        person = row.get("person") or {}
        raw = person.get("birthDate")
        if not raw or "*" in str(raw):
            return None
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None


def _dec(raw) -> Decimal:  # type: ignore[no-untyped-def]
    if raw in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return Decimal("0")


class PayrollBatchHealthReader:
    """Live-data implementation of `payroll_batch_health.PrismHRReader`."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_open_batches(self, client_id: str) -> list[dict]:
        """Combine the open-batch-list endpoints + a recent-dated fallback.

        getBatchListForApproval and getBatchListForInitialization both
        return rows under `availableBatches`. When those are empty (a
        very quiet client or a UAT sandbox), fall back to the last 30
        days of getBatchListByDate so the workflow has something to
        audit.
        """
        out: dict[str, dict] = {}
        for path in (
            "/payroll/v1/getBatchListForApproval",
            "/payroll/v1/getBatchListForInitialization",
        ):
            try:
                body = await self._c.get(path, params={"clientId": client_id})
            except Exception:  # noqa: BLE001 — one endpoint may be unauthorized
                continue
            for row in (
                _rows(body, "availableBatches")
                + _rows(body, "batchList")
                + _rows(body, "batches")
            ):
                bid = str(row.get("batchId") or row.get("id") or "")
                if bid and bid not in out:
                    out[bid] = row

        if not out:
            from datetime import date, timedelta

            today = date.today()
            try:
                body = await self._c.get(
                    "/payroll/v1/getBatchListByDate",
                    params={
                        "clientId": client_id,
                        "startDate": (today - timedelta(days=90)).isoformat(),
                        "endDate": today.isoformat(),
                        "dateType": "POST",
                    },
                )
                for row in (
                    _rows(body, "batchList")
                    + _rows(body, "availableBatches")
                ):
                    bid = str(row.get("batchId") or "")
                    if bid:
                        out[bid] = row
            except Exception:  # noqa: BLE001
                pass

        return list(out.values())

    async def get_batch_status(self, client_id: str, batch_id: str) -> dict:
        body = await self._c.get(
            "/payroll/v1/getBatchStatus",
            params={"clientId": client_id, "batchIds": batch_id},
        )
        # Real field name is batchStatuses (plural); rows contain
        # {batchId, status}. Old field names kept as fallback for future
        # schema variations.
        rows = (
            _rows(body, "batchStatuses")
            or _rows(body, "batchStatus")
            or _rows(body, "batchStatusCodes")
            or _rows(body, "batches")
            or []
        )
        if not rows:
            return {}
        row = rows[0]
        return {
            "status": row.get("status") or row.get("batchStatus") or "",
            "statusDescription": (
                row.get("statusDescription")
                or row.get("batchStatusDescription")
                or ""
            ),
        }

    async def get_batch_info(self, client_id: str, batch_id: str) -> dict:
        body = await self._c.get(
            "/payroll/v1/getBatchInfo",
            params={"clientId": client_id, "batchId": batch_id},
        )
        return _first(body, "batchInfo") or {}

    async def get_batch_vouchers(self, client_id: str, batch_id: str) -> list[dict]:
        body = await self._c.get(
            "/payroll/v1/getPayrollVoucherForBatch",
            params={"clientId": client_id, "batchId": batch_id},
        )
        # Real field is payrollVoucher (singular); older alternates kept.
        return (
            _rows(body, "payrollVoucher")
            or _rows(body, "voucher")
            or _rows(body, "vouchers")
            or []
        )

    async def get_approval_summary(self, client_id: str, batch_id: str) -> dict:
        try:
            body = await self._c.get(
                "/payroll/v1/getApprovalSummary",
                params={"clientId": client_id, "batchId": batch_id},
            )
        except Exception:
            # getApprovalSummary is INIT-only and returns 400 on other states;
            # treat as "no summary available" rather than a workflow failure.
            return {}
        if isinstance(body, dict) and body.get("errorCode") not in (None, "", "0"):
            return {}
        return body if isinstance(body, dict) else {}


def _rows(body: Any, key: str) -> list[dict]:
    if not isinstance(body, dict):
        return []
    val = body.get(key)
    if isinstance(val, list):
        return val
    return []


def _parse_iso_prefix(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


class _IDExtractor:
    pass


def _extract_ids(body: Any) -> list[str]:
    """PrismHR's getEmployeeList returns {employeeList: {employeeId: [ids]}}."""
    if not isinstance(body, dict):
        return []
    bucket = body.get("employeeList")
    if isinstance(bucket, dict):
        ids = bucket.get("employeeId") or bucket.get("employeeIds")
        if isinstance(ids, list):
            return [str(x) for x in ids if x]
    if isinstance(bucket, list):
        return [
            str(r.get("employeeId") or r.get("empId"))
            for r in bucket
            if isinstance(r, dict) and (r.get("employeeId") or r.get("empId"))
        ]
    return []


def _first(body: Any, key: str) -> dict | None:
    if not isinstance(body, dict):
        return None
    val = body.get(key)
    if isinstance(val, list) and val:
        return val[0] if isinstance(val[0], dict) else None
    if isinstance(val, dict):
        return val
    return None
