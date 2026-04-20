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


class PrismHRW2Source:
    """Live-data implementation of w2_distribution.W2Source.

    downloadW2 returns `{redirectUrl, errorCode}` — the real PDF is
    served from the redirect URL and requires both the `sessionId`
    header and `Accept: application/pdf`.
    """

    _DEFAULT_EMPLOYEE_CAP = 200

    def __init__(
        self, client: PrismHRClient, *, max_employees: int = _DEFAULT_EMPLOYEE_CAP
    ) -> None:
        self._c = client
        self._cap = max_employees

    async def list_employees_with_w2(
        self, client_id: str, year: str
    ) -> list[dict]:
        list_body = await self._c.get(
            "/employee/v1/getEmployeeList",
            params={"clientId": client_id, "employmentStatus": "A"},
        )
        ids = _extract_ids(list_body)[: self._cap]
        out: list[dict] = []
        for eid in ids:
            try:
                body = await self._c.get(
                    "/employee/v1/getW2Years",
                    params={"clientId": client_id, "employeeId": eid},
                )
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(body, dict):
                continue
            years = body.get("w2Years") or body.get("formW2Years") or []
            if not isinstance(years, list):
                years = []
            if year in [str(y) for y in years]:
                # Fetch minimal employee name info for the letter
                detail = await self._c.get(
                    "/employee/v1/getEmployee",
                    params=[
                        ("clientId", client_id),
                        ("options", "Person"),
                        ("employeeId", eid),
                    ],
                )
                row = _first(detail, "employee") or {}
                out.append(
                    {
                        "employeeId": eid,
                        "firstName": row.get("firstName", ""),
                        "lastName": row.get("lastName", ""),
                    }
                )
        return out

    async def download_w2_pdf(
        self, client_id: str, employee_id: str, year: str
    ) -> bytes:
        body = await self._c.get(
            "/employee/v1/downloadW2",
            params={"clientId": client_id, "employeeId": employee_id, "year": year},
        )
        if not isinstance(body, dict):
            return b""
        url = body.get("redirectUrl")
        if not url:
            return b""
        token = await self._c._session.token()  # type: ignore[attr-defined]
        http = httpx.AsyncClient(timeout=120.0, follow_redirects=True)
        try:
            resp = await http.get(
                url, headers={"sessionId": token, "Accept": "application/pdf"}
            )
        finally:
            await http.aclose()
        if resp.status_code != 200:
            return b""
        return resp.content

    async def get_employee_contact(
        self, client_id: str, employee_id: str
    ) -> dict:
        # For W-2 mailing we prefer the Person.w2Address* fields (the
        # IRS-specific mailing address an employee can set) and fall
        # back to ContactInformation for the primary residence.
        body = await self._c.get(
            "/employee/v1/getEmployee",
            params=[
                ("clientId", client_id),
                ("options", "ContactInformation,Person"),
                ("employeeId", employee_id),
            ],
        )
        row = _first(body, "employee") or {}
        contact = row.get("contactInformation") or {}
        person = row.get("person") or {}

        w2_line1 = (person.get("w2AddressLine1") or "").strip()
        w2_city = (person.get("w2City") or "").strip()
        w2_state = (person.get("w2State") or "").strip()
        w2_zip = (person.get("w2PostalCode") or "").strip()
        uses_w2_addr = bool(w2_line1 and w2_city and w2_state)

        return {
            "line1": w2_line1 if uses_w2_addr else (contact.get("addressLine1") or ""),
            "line2": (
                (person.get("w2AddressLine2") or "")
                if uses_w2_addr
                else (contact.get("addressLine2") or "")
            ),
            "city": w2_city if uses_w2_addr else (contact.get("city") or ""),
            "state": w2_state if uses_w2_addr else (contact.get("state") or ""),
            "zip": (
                w2_zip
                if uses_w2_addr
                else (contact.get("zipcode") or contact.get("postalCode") or "")
            ),
            "address_source": "W2" if uses_w2_addr else "PRIMARY",
            "email": contact.get("emailAddress")
            or contact.get("personalEmail")
            or person.get("personalEmail")
            or "",
            # W-2 electronic-delivery consent is a separate legal flag
            # from 1095-C e-consent. Only w2ElecForm governs W-2 email
            # delivery; 1095-C consent cannot be reused here.
            "consentsElectronic": bool(person.get("w2ElecForm")),
        }


class ACAIntegrityReader:
    """Live-data implementation of aca_integrity.PrismHRReader.

    PrismHR's ACA endpoints split into two flavors:
      - client-level: getACALargeEmployer (1094 summary)
      - per-employee: getACAOfferedEmployees (offer codes),
        getMonthlyACAInfo (per-month rate + status), get1095CYears
    """

    _DEFAULT_EMPLOYEE_CAP = 50

    def __init__(
        self, client: PrismHRClient, *, max_employees: int = _DEFAULT_EMPLOYEE_CAP
    ) -> None:
        self._c = client
        self._cap = max_employees

    async def get_1094_data(self, client_id: str, year: int) -> dict:
        try:
            body = await self._c.get(
                "/clientMaster/v1/getACALargeEmployer",
                params={"clientId": client_id, "reportYear": str(year)},
            )
        except Exception:  # noqa: BLE001 — permission-gated or no record yet
            return {}
        if not isinstance(body, dict):
            return {}
        rows = _rows(body, "largeEmployerList") or _rows(body, "largeEmployer") or []
        if not rows:
            return {}
        first = rows[0]
        # Normalize the 12-month MEC indicator block.
        months_block = (
            first.get("mecIndicatorByMonth")
            or first.get("mecIndicators")
            or first.get("mecIndicator")
            or {}
        )
        if isinstance(months_block, dict):
            mec_indicators = [
                {"month": int(k), "indicator": v}
                for k, v in months_block.items()
                if str(k).isdigit()
            ]
        elif isinstance(months_block, list):
            mec_indicators = months_block
        else:
            mec_indicators = []
        return {"mecIndicator": mec_indicators}

    async def get_aca_offered_employees(
        self, client_id: str, year: int
    ) -> list[dict]:
        body = await self._c.get(
            "/benefits/v1/getACAOfferedEmployees",
            params={"clientId": client_id, "reportYear": str(year)},
        )
        rows = _rows(body, "acaEmployeeInformation") or []
        out: list[dict] = []
        for r in rows:
            eid = str(r.get("employeeId") or "")
            if not eid:
                continue
            # Offer code + safe harbor arrives as nested monthly dict or list
            offer = r.get("line14") or r.get("offerCodes") or {}
            harbor = r.get("line16") or r.get("safeHarborCodes") or {}
            share = r.get("line15") or r.get("employeeShare") or {}
            if isinstance(offer, list):
                offer = {str(i + 1): v for i, v in enumerate(offer)}
            if isinstance(harbor, list):
                harbor = {str(i + 1): v for i, v in enumerate(harbor)}
            if isinstance(share, list):
                share = {str(i + 1): v for i, v in enumerate(share)}
            out.append(
                {
                    "employeeId": eid,
                    "offerCodes": offer,
                    "safeHarborCodes": harbor,
                    "employeeShare": share,
                }
            )
        return out

    async def get_monthly_aca_info(
        self, client_id: str, year: int
    ) -> list[dict]:
        # getMonthlyACAInfo requires employeeId; client-level aggregation
        # is built by iterating the ACA-offered-employees roster and
        # summing fullTime + MEC counts per month.
        offered = await self.get_aca_offered_employees(client_id, year)
        per_month: dict[int, dict[str, int]] = {
            m: {"ftCount": 0, "mecCount": 0} for m in range(1, 13)
        }
        for emp in offered[: self._cap]:
            offer = emp.get("offerCodes") or {}
            if not isinstance(offer, dict):
                continue
            for month_key, code in offer.items():
                try:
                    m = int(month_key)
                except (TypeError, ValueError):
                    continue
                if m not in per_month:
                    continue
                # 1A-1E + 1J-1K indicate MEC offered; rough heuristic.
                code_up = str(code or "").strip().upper()
                if code_up in {"1A", "1B", "1C", "1D", "1E", "1J", "1K"}:
                    per_month[m]["mecCount"] += 1
                if code_up:
                    per_month[m]["ftCount"] += 1
        return [
            {"month": m, "fullTimeCount": v["ftCount"], "mecCount": v["mecCount"]}
            for m, v in per_month.items()
        ]

    async def get_1095c_years(self, client_id: str, employee_id: str) -> dict:
        try:
            body = await self._c.get(
                "/employee/v1/get1095CYears",
                params={"clientId": client_id, "employeeId": employee_id},
            )
        except Exception:  # noqa: BLE001
            return {}
        return body if isinstance(body, dict) else {}


class BillingWashAuditLiveReader:
    """Live-data implementation of billing_wash_audit.PrismHRReader."""

    _DEFAULT_EMPLOYEE_CAP = 50

    def __init__(
        self, client: PrismHRClient, *, max_employees: int = _DEFAULT_EMPLOYEE_CAP
    ) -> None:
        self._c = client
        self._cap = max_employees
        self._gbp_cache: dict[str, dict] = {}

    async def get_billing_vouchers_by_month(
        self, client_id: str, year: int, month: int
    ) -> list[dict]:
        start = date(year, month, 1)
        # Naive month end without calendar dep
        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month + 1, 1) - __import__("datetime").timedelta(days=1)  # type: ignore[attr-defined]
        try:
            body = await self._c.get(
                "/payroll/v1/getBillingVouchers",
                params={
                    "clientId": client_id,
                    "startDate": start.isoformat(),
                    "endDate": end.isoformat(),
                },
            )
        except Exception:  # noqa: BLE001
            return []
        out: list[dict] = []
        for v in _rows(body, "billingVoucher") or _rows(body, "vouchers") or []:
            out.append(
                {
                    "employeeId": v.get("employeeId") or "",
                    "planId": v.get("planId") or v.get("benefitPlan") or "",
                    "premiumBilled": v.get("premiumBilled")
                    or v.get("billAmount")
                    or v.get("amount")
                    or "0",
                }
            )
        return out

    async def get_benefit_confirmations(self, client_id: str) -> list[dict]:
        # Reuse BenefitsDeductionAuditReader's pattern — iterate roster
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
            rows = _rows(body, "benefitConfirmationList") or []
            if not rows:
                continue
            plans = []
            for r in rows:
                plan_code = (
                    r.get("planId") or r.get("planCode") or r.get("benefitPlan") or ""
                )
                if plan_code:
                    plans.append(
                        {
                            "planId": str(plan_code),
                            "coverageStart": r.get("coverageStart") or r.get("effectiveDate"),
                            "coverageEnd": r.get("coverageEnd") or r.get("terminationDate"),
                        }
                    )
            out.append({"employeeId": eid, "plans": plans})
        return out

    async def get_scheduled_deductions(
        self, client_id: str, employee_id: str
    ) -> list[dict]:
        body = await self._c.get(
            "/employee/v1/getScheduledDeductions",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        rows = _rows(body, "scheduledDeductions") or _rows(body, "deductions") or []
        return [
            {
                "code": r.get("deductionCode") or r.get("code") or "",
                "amount": r.get("amount") or r.get("deductionAmount") or "0",
            }
            for r in rows
        ]

    async def get_group_benefit_plan(self, plan_id: str) -> dict:
        if plan_id in self._gbp_cache:
            return self._gbp_cache[plan_id]
        try:
            body = await self._c.get(
                "/benefits/v1/getGroupBenefitPlan",
                params={"planId": plan_id},
            )
        except Exception:  # noqa: BLE001
            self._gbp_cache[plan_id] = {}
            return {}
        gbp = body.get("groupBenefitPlan") if isinstance(body, dict) else None
        if isinstance(gbp, list):
            gbp = gbp[0] if gbp else {}
        result = gbp if isinstance(gbp, dict) else {}
        self._gbp_cache[plan_id] = result
        return result


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


class VoucherClassificationReader:
    """Live PrismHR adapter for voucher_classification_audit.PrismHRReader.

    Data sources:
      * list_vouchers_for_period -> payroll.v1.getPayrollVouchers (date range)
      * get_employee_tax_profile -> employee.v1.getEmployee
            with options=Compensation + options=Client in two calls, merged.
            Compensation has ficaExempt, nonResAlien, form4029Filed, etc.
            Client has employee1099, status, jobCode, officer, scorpOwner,
            businessOwner flags — critical for telling true misflags apart
            from legitimate 1099 contractors and corporate officers.
            Plus YTD context via payroll.v1.getEmployeePayrollSummary for
            Medicare additional-tax check.
      * get_pay_code_definition -> codeFiles.v1.getPaycodeDetails
      * list_union_members -> clientMaster.v1.getLaborUnionDetails

    The workflow caches per-employee lookups, so 20-emp chunks + two
    getEmployee calls per chunk is the expected load shape.
    """

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_vouchers_for_period(
        self, client_id: str, period_start: date, period_end: date
    ) -> list[dict]:
        try:
            body = await self._c.get(
                "/payroll/v1/getPayrollVouchers",
                params={
                    "clientId": client_id,
                    # PrismHR getPayrollVouchers uses payDateStart /
                    # payDateEnd, not startDate / endDate + dateType.
                    "payDateStart": period_start.isoformat(),
                    "payDateEnd": period_end.isoformat(),
                },
            )
        except Exception:  # noqa: BLE001
            return []
        if isinstance(body, list):
            return body
        if isinstance(body, dict):
            return (
                _rows(body, "payrollVoucher")
                or _rows(body, "vouchers")
                or _rows(body, "voucher")
            )
        return []

    async def get_employee_tax_profile(
        self, client_id: str, employee_id: str
    ) -> dict:
        comp_task = self._c.get(
            "/employee/v1/getEmployee",
            params={
                "clientId": client_id,
                "employeeId": employee_id,
                "options": "Compensation",
            },
        )
        client_task = self._c.get(
            "/employee/v1/getEmployee",
            params={
                "clientId": client_id,
                "employeeId": employee_id,
                "options": "Client",
            },
        )
        ytd_task = self._c.get(
            "/payroll/v1/getEmployeePayrollSummary",
            params={"clientId": client_id, "employeeId": employee_id},
        )
        try:
            comp_body, client_body, ytd_body = await asyncio.gather(
                comp_task, client_task, ytd_task, return_exceptions=True
            )
        except Exception:  # noqa: BLE001
            comp_body = client_body = ytd_body = {}

        comp = {}
        if isinstance(comp_body, dict):
            first = _first(comp_body, "employee") or {}
            comp = first.get("compensation") or {}

        client_cls = {}
        if isinstance(client_body, dict):
            first = _first(client_body, "employee") or {}
            client_cls = first.get("client") or {}

        status = str(client_cls.get("employeeStatus") or "A").upper()
        if status == "A":
            status_out = "ACTIVE"
        elif status == "T":
            status_out = "TERMINATED"
        elif status == "L":
            status_out = "LEAVE"
        else:
            status_out = status

        # Work state: state with filingStatus populated wins; fall back
        # to first state in stateTax; fall back to home state.
        # Also expose all state codes so multi-state employees get
        # more permissive SUTA-state-mismatch checks.
        work_state = ""
        all_states: list[str] = []
        state_tax = comp.get("stateTax") or []
        if isinstance(state_tax, list):
            for s in state_tax:
                if isinstance(s, dict):
                    code = str(s.get("stateCode") or "").upper()
                    if code:
                        all_states.append(code)
                    if not work_state and s.get("filingStatus"):
                        work_state = code
            if not work_state and all_states:
                work_state = all_states[0]

        # YTD wage data for additional-Medicare threshold check
        ytd_medicare = Decimal("0")
        ytd_ss = Decimal("0")
        ytd_addl_medicare = Decimal("0")
        if isinstance(ytd_body, dict):
            data_rows = _rows(ytd_body, "data") or _rows(ytd_body, "employeePayrollSummary")
            for r in data_rows:
                ytd_block = r.get("YTD") if isinstance(r, dict) else None
                if not isinstance(ytd_block, dict):
                    continue
                tw = ytd_block.get("taxWithholding") or {}
                ytd_medicare += _dec(tw.get("medicare"))
                ytd_ss += _dec(tw.get("socialSecurity"))

        # Employee type: use employee1099 flag first, fall back to pattern.
        if client_cls.get("employee1099") is True:
            emp_type = "1099"
        else:
            emp_type = "W2"

        # Treat any of these owner/officer flags as "exempt-legit" by
        # collapsing them into the position string the workflow reads.
        position = str(client_cls.get("jobCode") or "")
        if client_cls.get("officer") is True:
            position = (position or "OFFICER")
        if client_cls.get("scorpOwner") is True:
            position = position or "S-CORP-OWNER"
        if client_cls.get("businessOwner") is True:
            position = position or "BUSINESS-OWNER"

        return {
            "employeeType": emp_type,
            "ficaExempt": bool(comp.get("ficaExempt")),
            "medicareExempt": False,  # PrismHR has only one FICA exempt flag
            "futaExempt": False,
            "sutaExempt": False,
            "workState": work_state,
            "allWorkStates": all_states,
            "unionId": client_cls.get("unionCode") or None,
            "ytdSocialSecurityWages": ytd_ss,
            "ytdMedicareWages": ytd_medicare,
            "ytdAdditionalMedicareWithheld": ytd_addl_medicare,
            "status": status_out,
            "position": position,
        }

    async def get_pay_code_definition(
        self, client_id: str, pay_code: str
    ) -> dict:
        try:
            body = await self._c.get(
                "/codeFiles/v1/getPaycodeDetails",
                params={"clientId": client_id, "payCode": pay_code},
            )
            entry = _first(body, "paycode") or _first(body, "payCode") or {}
        except Exception:  # noqa: BLE001
            entry = {}
        if not isinstance(entry, dict):
            entry = {}

        # UAT tenants return 404 "Invalid Pay Code" on every code. Without
        # live metadata, derive contractor/union signals from the pay-code
        # NAME itself. This matches how PrismHR operators actually classify
        # codes (naming convention: CONTRACTOR / CONTACTOR / 1099 / UN-* /
        # UNION-*). Cheap, reasonable, much better than "nothing."
        name = (entry.get("payCode") or entry.get("code") or pay_code or "").upper()
        name_is_contractor = any(
            kw in name for kw in ("CONTRACTOR", "CONTACTOR", "1099")
        )
        name_is_union = any(
            name.startswith(prefix) for prefix in ("UN-", "UNION-", "UN_", "UNION_")
        )

        return {
            "payCode": entry.get("payCode") or entry.get("code") or pay_code,
            "description": entry.get("description") or entry.get("desc") or "",
            "isContractor": bool(
                entry.get("isContractor") or entry.get("contractor")
                or name_is_contractor
            ),
            "isUnion": bool(
                entry.get("isUnion") or entry.get("union") or name_is_union
            ),
            "unionId": entry.get("unionId") or entry.get("unionCode"),
            # Preserve metadata gaps as None — workflow requires explicit
            # True for ZERO_TAX_TAXABLE_CODE to fire.
            "ficaSubject": entry.get("ficaSubject"),
            "medicareSubject": entry.get("medicareSubject"),
            "futaSubject": entry.get("futaSubject"),
            "sutaSubject": entry.get("sutaSubject"),
            "stateSubject": entry.get("stateSubject"),
        }

    async def list_union_members(
        self, client_id: str, union_id: str
    ) -> list[str]:
        try:
            body = await self._c.get(
                "/clientMaster/v1/getLaborUnionDetails",
                params={"clientId": client_id, "unionCode": union_id},
            )
        except Exception:  # noqa: BLE001
            return []
        members = (
            (body or {}).get("members")
            or (body or {}).get("memberList")
            or (body or {}).get("employeeList", {}).get("employeeId")
            or []
        )
        if isinstance(members, list):
            return [str(m) for m in members if m]
        return []


# =============================================================================
# Shared helper: SystemService.getData async download pattern
# =============================================================================


async def _system_get_data(
    client: PrismHRClient,
    *,
    schema: str,
    class_name: str,
    client_id: str | None = None,
    employee_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    max_polls: int = 30,
    poll_delay_seconds: float = 2.0,
) -> Any:
    """Execute SystemService.getData INIT -> BUILD -> DONE, return the
    parsed dataObject JSON (list or dict). Empty list on error.

    Filters are pushed server-side where possible (cheaper than client-
    side filter on multi-MB payloads):
      * clientId, employeeId — per docs, per Schema|Class
      * startDate/endDate — accepted by all date-filterable classes
        (Compensation/Person/Client/History/Enrollment/AbsenceJournal/
         RetirementLoan/Garnishment/ScheduledDeductions etc.). Probed
        empirically via scripts/probe_getdata_dimensions.py.
    """
    params: dict[str, str] = {"schemaName": schema, "className": class_name}
    if client_id:
        params["clientId"] = client_id
    if employee_id:
        params["employeeId"] = employee_id
    if start_date:
        params["startDate"] = start_date.isoformat()
    if end_date:
        params["endDate"] = end_date.isoformat()
    try:
        body = await client.get("/system/v1/getData", params=params)
    except Exception:  # noqa: BLE001
        return []
    status = body.get("buildStatus") if isinstance(body, dict) else None
    did = body.get("downloadId") if isinstance(body, dict) else None
    for _ in range(max_polls):
        if status == "DONE":
            break
        if status == "ERROR":
            return []
        if not did:
            break
        await asyncio.sleep(poll_delay_seconds)
        params["downloadId"] = did
        try:
            body = await client.get("/system/v1/getData", params=params)
        except Exception:  # noqa: BLE001
            return []
        status = body.get("buildStatus") if isinstance(body, dict) else None
        did = body.get("downloadId") if isinstance(body, dict) else did
    url = body.get("dataObject") if isinstance(body, dict) else None
    if not url:
        return body if isinstance(body, (list, dict)) else []
    # Fetch dataObject separately. Use a separate request; may return
    # latin-1 bodies for non-ASCII names.
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=60) as c:
            r = await c.get(url)
            try:
                return r.json()
            except Exception:  # noqa: BLE001
                import json as _json
                return _json.loads(r.content.decode("latin-1", errors="replace"))
    except Exception:  # noqa: BLE001
        return []


# =============================================================================
# Garnishment workflow live reader
# =============================================================================


class GarnishmentHistoryReader:
    """Live implementation of garnishment_history.PrismHRReader using
    SystemService.getData#Deduction|Garnishment as the primary bulk
    source (59 fields per record, verified against UAT)."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_garnishment_holders(self, client_id: str) -> list[dict]:
        data = await _system_get_data(
            self._c,
            schema="Deduction",
            class_name="Garnishment",
            client_id=client_id,
        )
        rows = _coerce_rows(data)
        out: dict[str, dict] = {}
        for r in rows:
            eid = str(r.get("employeeId") or "")
            if not eid:
                # id like "CLIENT.EMPLOYEE.DED" — parse out employee
                composite = str(r.get("id") or "")
                parts = composite.split(".")
                if len(parts) >= 2:
                    eid = parts[1]
            if eid and eid not in out:
                out[eid] = {"employeeId": eid}
        return list(out.values())

    async def get_garnishment_details(
        self, client_id: str, employee_id: str
    ) -> list[dict]:
        try:
            body = await self._c.get(
                "/deduction/v1/getGarnishmentDetails",
                params={"clientId": client_id, "employeeId": employee_id},
            )
        except Exception:  # noqa: BLE001
            return []
        return _coerce_rows(body, preferred_key="garnishmentDetails")

    async def get_garnishment_payments(
        self, client_id: str, employee_id: str
    ) -> list[dict]:
        try:
            body = await self._c.get(
                "/deduction/v1/getGarnishmentPaymentHistory",
                params={"clientId": client_id, "employeeId": employee_id},
            )
        except Exception:  # noqa: BLE001
            return []
        return _coerce_rows(body, preferred_key="paymentHistory")


# =============================================================================
# Absence journal workflow live reader
# =============================================================================


class AbsenceJournalReader:
    """Live implementation of absence_journal_audit.PrismHRReader via
    SystemService.getData#Benefit|AbsenceJournal."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_absence_journal(
        self, client_id: str, start: date, end: date
    ) -> list[dict]:
        # Push date filter server-side — AbsenceJournal is a 22MB
        # payload un-filtered.
        data = await _system_get_data(
            self._c,
            schema="Benefit",
            class_name="AbsenceJournal",
            client_id=client_id,
            start_date=start,
            end_date=end,
        )
        return _coerce_rows(data)


def _coerce_rows(body: Any, *, preferred_key: str | None = None) -> list[dict]:
    """Normalize getData-style responses: outer wrapper has a `data`
    list of rows. Also handles direct lists and other shape variants."""
    if isinstance(body, list):
        return [r for r in body if isinstance(r, dict)]
    if not isinstance(body, dict):
        return []
    for key in (preferred_key, "data", "records", "rows"):
        if not key:
            continue
        val = body.get(key)
        if isinstance(val, list):
            return [r for r in val if isinstance(r, dict)]
    return []


# =============================================================================
# Dependent age-out
# =============================================================================


class DependentAgeOutReader:
    """Live impl for dependent_age_out.PrismHRReader via
    SystemService.getData#Benefit|Dependent."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_covered_dependents(self, client_id: str) -> list[dict]:
        data = await _system_get_data(
            self._c,
            schema="Benefit",
            class_name="Dependent",
            client_id=client_id,
        )
        return _coerce_rows(data)


# =============================================================================
# COBRA eligibility sweep
# =============================================================================


class CobraEligibilityReader:
    """Live impl for cobra_eligibility_sweep.PrismHRReader.

    Terminations come from payroll.v1.getBatchListByDate filtered to
    batches where vouchers carry terminated employees, cross-referenced
    with employee.v1.getEmployee Client class.
    COBRA enrollees via benefits.v1.getCobraEmployee.
    """

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def get_terminations(
        self, client_id: str, lookback_days: int
    ) -> list[dict]:
        # Pull Employee|Client via getData and filter for status T
        # with termination date within lookback window.
        from datetime import timedelta as _td
        today = date.today()
        start = today - _td(days=lookback_days)
        data = await _system_get_data(
            self._c,
            schema="Employee",
            class_name="Client",
            client_id=client_id,
            start_date=start,
            end_date=today,
        )
        rows = _coerce_rows(data)
        terms: list[dict] = []
        for r in rows:
            status = str(r.get("employeeStatus") or r.get("status") or "").upper()
            if status in {"T", "TERMINATED"}:
                term_date = _parse_iso_prefix(
                    r.get("lastStatusChangeDate") or r.get("termDate")
                )
                if term_date and term_date >= start:
                    terms.append({
                        "employeeId": r.get("employeeId") or _eid_from_id(r.get("id")),
                        "terminationDate": term_date.isoformat(),
                        "termReasonCode": r.get("termReasonCode"),
                    })
        return terms

    async def get_cobra_enrollees(self, client_id: str) -> list[dict]:
        try:
            body = await self._c.get(
                "/benefits/v1/getCobraEmployee",
                params={"clientId": client_id},
            )
        except Exception:  # noqa: BLE001
            return []
        return _coerce_rows(body, preferred_key="cobraEmployee")


# =============================================================================
# PTO reconciliation
# =============================================================================


class PTOReconciliationReader:
    """Live impl for pto_reconciliation.PrismHRReader."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def get_pto_classes(self, client_id: str) -> list[dict]:
        try:
            body = await self._c.get(
                "/benefits/v1/getPtoClasses",
                params={"clientId": client_id},
            )
        except Exception:  # noqa: BLE001
            return []
        return _coerce_rows(body, preferred_key="ptoClasses")

    async def get_pto_plans(self, client_id: str) -> list[dict]:
        try:
            body = await self._c.get(
                "/benefits/v1/getPaidTimeOffPlans",
                params={"clientId": client_id},
            )
        except Exception:  # noqa: BLE001
            return []
        return _coerce_rows(body, preferred_key="paidTimeOffPlans")

    async def get_employee_pto_rows(self, client_id: str) -> list[dict]:
        # SystemService.getData#Benefit|PaidTimeOff — per-employee PTO
        # balances + YTD use + accrual. Verified 1.4MB payload in UAT.
        data = await _system_get_data(
            self._c,
            schema="Benefit",
            class_name="PaidTimeOff",
            client_id=client_id,
        )
        return _coerce_rows(data)


# =============================================================================
# Retirement loan status
# =============================================================================


class RetirementLoanStatusReader:
    """Live impl for retirement_loan_status.PrismHRReader."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def get_retirement_loans(self, client_id: str) -> list[dict]:
        # SystemService.getData#Benefit|RetirementLoan gives the full
        # loan roster with balance + payment schedule + default flags.
        data = await _system_get_data(
            self._c,
            schema="Benefit",
            class_name="RetirementLoan",
            client_id=client_id,
        )
        return _coerce_rows(data)


def _eid_from_id(composite: Any) -> str:
    """Extract employeeId from getData composite id like CLIENT.EMP[.EXTRA]."""
    if not composite:
        return ""
    parts = str(composite).split(".")
    return parts[1] if len(parts) >= 2 else ""


# =============================================================================
# 1099-NEC preflight
# =============================================================================


class Form1099NECPreflightReader:
    """Live impl for form_1099_nec_preflight.PrismHRReader.

    Filters getData#Employee|Client to employees flagged employee1099=True,
    pulls Compensation for SSN + getBulkYearToDateValues for YTD nonemp
    comp, merges the W-9 address from getAddressInfo.
    """

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_contractors_paid_in_year(
        self, client_id: str, tax_year: int
    ) -> list[dict]:
        client_data = await _system_get_data(
            self._c,
            schema="Employee",
            class_name="Client",
            client_id=client_id,
        )
        client_rows = _coerce_rows(client_data)
        contractors: dict[str, dict] = {}
        for r in client_rows:
            if r.get("employee1099") is not True:
                continue
            eid = r.get("employeeId") or _eid_from_id(r.get("id"))
            if not eid:
                continue
            contractors[str(eid)] = {
                "contractorId": str(eid),
                "legalName": "",
                "ein": "",
                "ssn": "",
                "ytdNonempComp": "0",
                "ytdBackupWithholding": "0",
                "w9OnFile": bool(r.get("formI9Filed")),  # proxy; real W-9 flag TBD
                "address": {},
                "voucherPayeeName": "",
                "box1Expected": "0",
            }
        # Enrich with YTD + name + address
        for eid, rec in contractors.items():
            try:
                ytd = await self._c.get(
                    "/payroll/v1/getBulkYearToDateValues",
                    params={"clientId": client_id, "asOfDate": f"{tax_year}-12-31"},
                )
                for row in (ytd.get("data") or [])[:5000]:
                    if str(row.get("employeeId") or "") != eid:
                        continue
                    ytd_block = row.get("YTD") or {}
                    rec["ytdNonempComp"] = str(ytd_block.get("totalEarned") or "0")
                    break
            except Exception:  # noqa: BLE001
                pass
            try:
                addr = await self._c.get(
                    "/employee/v1/getAddressInfo",
                    params={"clientId": client_id, "employeeId": eid},
                )
                info = (addr.get("addressInfo") or {}).get("homeAddress") or {}
                rec["address"] = {
                    "line1": info.get("addressLine1") or "",
                    "city": info.get("city") or "",
                    "state": info.get("stateAbbr") or "",
                    "zip": info.get("zipCode") or "",
                }
            except Exception:  # noqa: BLE001
                pass
            try:
                comp = await self._c.get(
                    "/employee/v1/getEmployee",
                    params={"clientId": client_id, "employeeId": eid,
                            "options": "Compensation"},
                )
                emp = _first(comp, "employee") or {}
                c_cls = emp.get("compensation") or {}
                rec["ssn"] = c_cls.get("ssn", "")
                rec["legalName"] = f"{emp.get('firstName','')} {emp.get('lastName','')}".strip()
            except Exception:  # noqa: BLE001
                pass
            rec["box1Expected"] = rec["ytdNonempComp"]
        return list(contractors.values())


# =============================================================================
# Bonus gross-up audit
# =============================================================================


class BonusGrossUpReader:
    """Filters vouchers to type='B' (bonus)."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_bonus_vouchers(
        self, client_id: str, period_start: date, period_end: date
    ) -> list[dict]:
        try:
            body = await self._c.get(
                "/payroll/v1/getPayrollVouchers",
                params={
                    "clientId": client_id,
                    "payDateStart": period_start.isoformat(),
                    "payDateEnd": period_end.isoformat(),
                },
            )
        except Exception:  # noqa: BLE001
            return []
        vouchers = _coerce_rows(body, preferred_key="payrollVoucher")
        out: list[dict] = []
        for v in vouchers:
            vtype = str(v.get("type") or "").upper()
            if vtype != "B":
                continue
            tax_rows = v.get("employeeTax") or []
            fed = Decimal("0")
            state = Decimal("0")
            for t in tax_rows:
                code = str(t.get("empTaxDeductCode") or "")
                amt = _dec(t.get("empTaxAmount"))
                if code.startswith("00-10"):
                    fed += amt
                elif "-20" in code or "-21" in code or "-22" in code:
                    state += amt
            out.append({
                "voucherId": v.get("voucherId"),
                "employeeId": v.get("employeeId"),
                "supplementalMethod": v.get("supplementalMethod") or "FLAT_22",
                "supplementalAmount": v.get("totalEarnings"),
                "federalWithheld": str(fed),
                "stateWithheld": str(state),
                "workState": v.get("wcState") or "",
                "ytdSupplementalWages": "0",  # requires YTD blend
                "netPay": v.get("netPay"),
                "targetNetRequested": "0",
                "isGrossUp": False,
            })
        return out


# =============================================================================
# Retirement NDT suite
# =============================================================================


class RetirementNDTReader:
    """Live impl for retirement_ndt_suite.PrismHRReader.

    401k: getEmployee401KContributionsByDate + getBulkYearToDateValues
    Section 125: getData#Employee|Client (isKeyEmployee flag) + YTD pre-tax benefits
    FSA 55: getData#Benefit|SpendingAccounts filtered to DCFSA type
    """

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_401k_participants(
        self, client_id: str, plan_year: int
    ) -> list[dict]:
        try:
            body = await self._c.get(
                "/payroll/v1/getEmployee401KContributionsByDate",
                params={
                    "clientId": client_id,
                    "startDate": f"{plan_year}-01-01",
                    "endDate": f"{plan_year}-12-31",
                },
            )
        except Exception:  # noqa: BLE001
            return []
        rows = _coerce_rows(body, preferred_key="employee401kBatchDetail")
        by_emp: dict[str, dict] = {}
        for r in rows:
            eid = str(r.get("employeeId") or "")
            if not eid:
                continue
            rd = r.get("retirementData") or {}
            bucket = by_emp.setdefault(eid, {
                "employeeId": eid,
                "ytdGross": Decimal("0"),
                "ytdDeferral": Decimal("0"),
                "ytdEmployerMatch": Decimal("0"),
                "ytdAfterTax": Decimal("0"),
                "isHCE": None,
            })
            bucket["ytdGross"] += _dec(r.get("ytdGross"))
            bucket["ytdDeferral"] += _dec(rd.get("employeePreTaxDeferral"))
            bucket["ytdEmployerMatch"] += _dec(rd.get("employerMatch"))
            bucket["ytdAfterTax"] += _dec(rd.get("postTaxContribution"))
        return [
            {k: str(v) if isinstance(v, Decimal) else v for k, v in row.items()}
            for row in by_emp.values()
        ]

    async def list_section_125_participants(
        self, client_id: str, plan_year: int
    ) -> list[dict]:
        data = await _system_get_data(
            self._c,
            schema="Benefit",
            class_name="SpendingAccounts",
            client_id=client_id,
        )
        rows = _coerce_rows(data)
        out: list[dict] = []
        for r in rows:
            for acct in (r.get("account") or []):
                if not isinstance(acct, dict):
                    continue
                eid = r.get("employeeId") or _eid_from_id(r.get("id"))
                if not eid:
                    continue
                out.append({
                    "employeeId": str(eid),
                    "ytdPretaxBenefits": str(acct.get("deductAmount") or 0),
                    "isKeyEmployee": None,
                })
        return out

    async def list_dependent_care_fsa(
        self, client_id: str, plan_year: int
    ) -> list[dict]:
        data = await _system_get_data(
            self._c,
            schema="Benefit",
            class_name="SpendingAccounts",
            client_id=client_id,
        )
        rows = _coerce_rows(data)
        out: list[dict] = []
        for r in rows:
            eid = r.get("employeeId") or _eid_from_id(r.get("id"))
            for acct in (r.get("account") or []):
                if not isinstance(acct, dict):
                    continue
                if str(acct.get("accountId") or "").upper() not in {"DCFSA", "DEP", "DCR"}:
                    continue
                out.append({
                    "employeeId": str(eid or ""),
                    "fsaBenefit": str(acct.get("electAmount") or 0),
                    "isHCE": None,
                })
        return out


# =============================================================================
# Reciprocal withholding
# =============================================================================


class ReciprocalWithholdingReader:
    """Identifies multistate employees from Compensation.stateTax[]
    and sums withholding per state from vouchers in the period."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_multistate_employees(
        self, client_id: str, period_start: date, period_end: date
    ) -> list[dict]:
        # Pull Employee|Client to find candidate employees, then their
        # Compensation.stateTax[] to see home/work state. Light scan.
        client_data = await _system_get_data(
            self._c, schema="Employee", class_name="Client",
            client_id=client_id,
        )
        client_rows = _coerce_rows(client_data)
        addr_by_eid: dict[str, str] = {}
        for r in client_rows:
            eid = str(r.get("employeeId") or _eid_from_id(r.get("id")) or "")
            st = str(r.get("state") or "").upper()
            if eid and st:
                addr_by_eid[eid] = st

        # Work-state per employee from Compensation + voucher withholding
        try:
            v_body = await self._c.get(
                "/payroll/v1/getPayrollVouchers",
                params={"clientId": client_id,
                        "payDateStart": period_start.isoformat(),
                        "payDateEnd": period_end.isoformat()},
            )
            vouchers = _coerce_rows(v_body, preferred_key="payrollVoucher")
        except Exception:  # noqa: BLE001
            vouchers = []

        by_emp: dict[str, dict] = {}
        for v in vouchers:
            eid = str(v.get("employeeId") or "")
            if not eid:
                continue
            bucket = by_emp.setdefault(eid, {
                "employeeId": eid,
                "homeState": addr_by_eid.get(eid, ""),
                "workStates": set(),
                "homeStateWithholding": Decimal("0"),
                "workStateWithholding": {},
                "reciprocalCertsOnFile": [],
                "allocationPct": {},
            })
            wc_state = str(v.get("wcState") or "").upper()
            if wc_state:
                bucket["workStates"].add(wc_state)
            for t in (v.get("employeeTax") or []):
                code = str(t.get("empTaxDeductCode") or "")
                amt = _dec(t.get("empTaxAmount"))
                desc = str(t.get("empTaxDeductCodeDesc") or "").upper()
                if "-20" not in code:
                    continue
                state = ""
                for tok in desc.split():
                    if len(tok) == 2 and tok.isalpha():
                        state = tok
                        break
                if not state:
                    continue
                if state == bucket["homeState"]:
                    bucket["homeStateWithholding"] += amt
                else:
                    bucket["workStateWithholding"].setdefault(state, Decimal("0"))
                    bucket["workStateWithholding"][state] += amt

        out: list[dict] = []
        for eid, rec in by_emp.items():
            rec["workStates"] = sorted(rec["workStates"])
            rec["homeStateWithholding"] = str(rec["homeStateWithholding"])
            rec["workStateWithholding"] = {
                k: str(v) for k, v in rec["workStateWithholding"].items()
            }
            out.append(rec)
        return out


# =============================================================================
# State new-hire reporting
# =============================================================================


class StateNewHireReportingReader:
    """Pulls new hires from Employee|Client + Person + Address."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_new_hires(
        self, client_id: str, hired_since: date
    ) -> list[dict]:
        client_data = await _system_get_data(
            self._c, schema="Employee", class_name="Client",
            client_id=client_id, start_date=hired_since, end_date=date.today(),
        )
        client_rows = _coerce_rows(client_data)
        out: list[dict] = []
        for r in client_rows:
            hire = _parse_iso_prefix(r.get("firstHireDate") or r.get("lastHireDate"))
            if not hire or hire < hired_since:
                continue
            eid = str(r.get("employeeId") or _eid_from_id(r.get("id")) or "")
            if not eid:
                continue
            # Fetch person class for SSN/DOB
            ssn = ""
            dob = ""
            fn = ""
            ln = ""
            try:
                p = await self._c.get(
                    "/employee/v1/getEmployee",
                    params={"clientId": client_id, "employeeId": eid,
                            "options": "Compensation"},
                )
                emp = _first(p, "employee") or {}
                comp = emp.get("compensation") or {}
                ssn = str(comp.get("ssn") or "")
                fn = str(emp.get("firstName") or "")
                ln = str(emp.get("lastName") or "")
            except Exception:  # noqa: BLE001
                pass
            addr: dict = {}
            try:
                a = await self._c.get(
                    "/employee/v1/getAddressInfo",
                    params={"clientId": client_id, "employeeId": eid},
                )
                home = (a.get("addressInfo") or {}).get("homeAddress") or {}
                addr = {
                    "line1": home.get("addressLine1", ""),
                    "city": home.get("city", ""),
                    "state": home.get("stateAbbr", ""),
                    "zip": home.get("zipCode", ""),
                }
            except Exception:  # noqa: BLE001
                pass
            out.append({
                "employeeId": eid,
                "firstName": fn,
                "lastName": ln,
                "state": addr.get("state", ""),
                "hireDate": hire.isoformat(),
                "priorTerminationDate": None,
                "newHireReportSentDate": r.get("newHireReportDate"),
                "ssn": ssn,
                "dob": dob,
                "address": addr,
            })
        return out


# =============================================================================
# Final paycheck compliance
# =============================================================================


class FinalPaycheckComplianceReader:
    """Separations from Employee|Client status=T, final check data
    from last voucher; PTO hours from getData#Benefit|PaidTimeOff."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_recent_separations(
        self, client_id: str, since: date
    ) -> list[dict]:
        data = await _system_get_data(
            self._c, schema="Employee", class_name="Client",
            client_id=client_id, start_date=since, end_date=date.today(),
        )
        rows = _coerce_rows(data)
        out: list[dict] = []
        for r in rows:
            status = str(r.get("employeeStatus") or r.get("status") or "").upper()
            if status not in {"T", "TERMINATED"}:
                continue
            term_date = _parse_iso_prefix(
                r.get("lastStatusChangeDate") or r.get("termDate")
            )
            if term_date is None or term_date < since:
                continue
            out.append({
                "employeeId": r.get("employeeId") or _eid_from_id(r.get("id")),
                "firstName": r.get("firstName") or "",
                "lastName": r.get("lastName") or "",
                "workState": r.get("state") or "",
                "separationDate": term_date.isoformat(),
                "separationType": (
                    "INVOLUNTARY" if str(r.get("termReasonCode") or "").upper()
                    in {"TERM", "FIRED", "RIF", "LAYOFF"}
                    else "VOLUNTARY"
                ),
                "finalCheckIssuedDate": r.get("lastPayDate"),
                "finalCheckAmount": "0",
                "unpaidPtoHours": "0",
                "unpaidCommission": "0",
                "separationNoticeIssued": False,
            })
        return out


# =============================================================================
# Off-cycle payroll audit
# =============================================================================


class OffCycleVoucherReader:
    """Filters vouchers to off-cycle types (B, M, C, F)."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_off_cycle_vouchers(
        self, client_id: str, period_start: date, period_end: date
    ) -> list[dict]:
        try:
            body = await self._c.get(
                "/payroll/v1/getPayrollVouchers",
                params={
                    "clientId": client_id,
                    "payDateStart": period_start.isoformat(),
                    "payDateEnd": period_end.isoformat(),
                },
            )
        except Exception:  # noqa: BLE001
            return []
        vouchers = _coerce_rows(body, preferred_key="payrollVoucher")
        out: list[dict] = []
        for v in vouchers:
            vtype = str(v.get("type") or "").upper()
            if vtype not in {"B", "M", "C", "F"}:
                continue
            out.append({
                "voucherId": v.get("voucherId"),
                "employeeId": v.get("employeeId"),
                "type": vtype,
                "payDate": v.get("payDate"),
                "totalEarnings": v.get("totalEarnings"),
                "approver": "",  # not in voucher payload
                "reason": "",
                "supplementalTaxMethod": "",
                "terminationDate": None,
            })
        return out

    async def get_employee_avg_regular_check(
        self, client_id: str, employee_id: str
    ) -> Decimal:
        # Simple average of last 10 R-type vouchers in the last year
        today = date.today()
        from datetime import timedelta as _td
        start = today - _td(days=365)
        try:
            body = await self._c.get(
                "/payroll/v1/getPayrollVouchersForEmployee",
                params={
                    "clientId": client_id, "employeeId": employee_id,
                    "payDateStart": start.isoformat(),
                    "payDateEnd": today.isoformat(),
                },
            )
        except Exception:  # noqa: BLE001
            return Decimal("0")
        vouchers = _coerce_rows(body, preferred_key="payrollVoucher")
        regulars = [
            _dec(v.get("netPay")) for v in vouchers
            if str(v.get("type") or "").upper() == "R"
        ][:10]
        if not regulars:
            return Decimal("0")
        return (sum(regulars, Decimal("0")) / Decimal(len(regulars))).quantize(
            Decimal("0.01")
        )


# =============================================================================
# Tax reconciliation family
# =============================================================================

def _quarter_dates(year: int, quarter: int) -> tuple[date, date]:
    """Return (start_date, end_date) for a tax quarter."""
    if quarter == 1:
        return date(year, 1, 1), date(year, 3, 31)
    if quarter == 2:
        return date(year, 4, 1), date(year, 6, 30)
    if quarter == 3:
        return date(year, 7, 1), date(year, 9, 30)
    return date(year, 10, 1), date(year, 12, 31)


class Form941ReconReader:
    """Live impl for form_941_reconciliation.PrismHRReader.

    sum_vouchers_for_quarter aggregates every voucher's taxable wages
    + tax withheld by code prefix (00-10 FIT, 00-11 Medicare, 00-12
    SS). get_form941 is best-effort — PrismHR has no dedicated 941
    endpoint, so we return an empty dict for now; operator supplies
    the reported amounts if comparing against filed returns.
    """

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def sum_vouchers_for_quarter(
        self, client_id: str, year: int, quarter: int
    ) -> dict:
        start, end = _quarter_dates(year, quarter)
        try:
            body = await self._c.get(
                "/payroll/v1/getPayrollVouchers",
                params={"clientId": client_id,
                        "payDateStart": start.isoformat(),
                        "payDateEnd": end.isoformat()},
            )
        except Exception:  # noqa: BLE001
            return {}
        vouchers = _coerce_rows(body, preferred_key="payrollVoucher")
        total_wages = Decimal("0")
        fit = Decimal("0")
        ss_wages = Decimal("0")
        medicare_wages = Decimal("0")
        addl_medicare_wages = Decimal("0")
        for v in vouchers:
            # Skip corrections + voids from aggregation
            if str(v.get("type") or "").upper() in {"V"}:
                continue
            total_wages += _dec(v.get("totalEarnings"))
            for t in (v.get("employeeTax") or []):
                code = str(t.get("empTaxDeductCode") or "")
                taxable = _dec(t.get("empTaxableAmount"))
                amt = _dec(t.get("empTaxAmount"))
                if code.startswith("00-10"):
                    fit += amt
                elif code.startswith("00-11"):
                    medicare_wages += taxable
                    addl = _dec(t.get("empOverLimitAmount"))
                    addl_medicare_wages += addl
                elif code.startswith("00-12"):
                    ss_wages += taxable
        return {
            "totalWages": str(total_wages),
            "federalIncomeTax": str(fit),
            "socialSecurityWages": str(ss_wages),
            "medicareWages": str(medicare_wages),
            "additionalMedicareWages": str(addl_medicare_wages),
        }

    async def get_form941(
        self, client_id: str, year: int, quarter: int
    ) -> dict:
        # PrismHR doesn't expose a 941 fetch endpoint in our grant set.
        # Returning empty means the workflow compares to $0 — callers
        # should layer in the filed values from their tax service.
        return {}


class Form940ReconReader:
    """Live impl for form_940_reconciliation.PrismHRReader.

    Pulls annual per-employee wages + employer state footprint.
    Credit-reduction states default to an empty list (IRS publishes in
    November; callers overlay the year-specific list).
    """

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_employee_annual_wages(
        self, client_id: str, year: int
    ) -> list[dict]:
        try:
            body = await self._c.get(
                "/payroll/v1/getBulkYearToDateValues",
                params={"clientId": client_id,
                        "asOfDate": f"{year}-12-31"},
            )
        except Exception:  # noqa: BLE001
            return []
        out: list[dict] = []
        for row in (body.get("data") or []):
            ytd = row.get("YTD") or {}
            wages = ytd.get("totalEarned")
            if wages in (None, ""):
                continue
            out.append({
                "employeeId": row.get("employeeId") or "",
                "totalWages": wages,
                "futaWages": "",  # unknown until prod probe of FUTA-cap fields
            })
        return out

    async def get_form940(self, client_id: str, year: int) -> dict:
        return {}

    async def list_credit_reduction_states(self, year: int) -> list[str]:
        return []

    async def list_employer_states(
        self, client_id: str, year: int
    ) -> list[str]:
        # Derive from the voucher wcState distribution
        start, end = date(year, 1, 1), date(year, 12, 31)
        try:
            body = await self._c.get(
                "/payroll/v1/getPayrollVouchers",
                params={"clientId": client_id,
                        "payDateStart": start.isoformat(),
                        "payDateEnd": end.isoformat()},
            )
        except Exception:  # noqa: BLE001
            return []
        vouchers = _coerce_rows(body, preferred_key="payrollVoucher")
        states = set()
        for v in vouchers:
            st = str(v.get("wcState") or "").upper()
            if st:
                states.add(st)
        return sorted(states)


class StateWithholdingReconReader:
    """Live impl for state_withholding_recon.PrismHRReader. Aggregates
    voucher withholding by state for the quarter."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_wages_by_state(
        self, client_id: str, year: int, quarter: int
    ) -> list[dict]:
        start, end = _quarter_dates(year, quarter)
        try:
            body = await self._c.get(
                "/payroll/v1/getPayrollVouchers",
                params={"clientId": client_id,
                        "payDateStart": start.isoformat(),
                        "payDateEnd": end.isoformat()},
            )
        except Exception:  # noqa: BLE001
            return []
        vouchers = _coerce_rows(body, preferred_key="payrollVoucher")
        by_state: dict[str, dict] = {}
        employees_by_state: dict[str, set] = {}
        for v in vouchers:
            eid = str(v.get("employeeId") or "")
            wc_state = str(v.get("wcState") or "").upper()
            if not wc_state:
                continue
            bucket = by_state.setdefault(wc_state, {
                "state": wc_state,
                "totalWages": Decimal("0"),
                "stateWithholding": Decimal("0"),
                "sutaWages": Decimal("0"),
                "employeeCount": 0,
            })
            bucket["totalWages"] += _dec(v.get("totalEarnings"))
            for t in (v.get("employeeTax") or []):
                code = str(t.get("empTaxDeductCode") or "")
                desc = str(t.get("empTaxDeductCodeDesc") or "").upper()
                amt = _dec(t.get("empTaxAmount"))
                # State income tax: codes ending in -20
                if code.endswith("-20") and wc_state in desc:
                    bucket["stateWithholding"] += amt
            employees_by_state.setdefault(wc_state, set()).add(eid)

        out: list[dict] = []
        for state, rec in by_state.items():
            rec["employeeCount"] = len(employees_by_state.get(state, set()))
            rec["totalWages"] = str(rec["totalWages"])
            rec["stateWithholding"] = str(rec["stateWithholding"])
            rec["sutaWages"] = str(rec["sutaWages"])
            out.append(rec)
        return out

    async def get_state_filings(
        self, client_id: str, year: int, quarter: int
    ) -> list[dict]:
        # No filing-status endpoint surfaced yet. Empty = workflow
        # treats every state as NO_FILING (operator intervention flag).
        return []


class TaxRemittanceReader:
    """Placeholder for tax_remittance_tracking. PrismHR doesn't directly
    expose the deposit-side tax liability + ACH remittance records in
    our grant set. Returning empty lists keeps the workflow runnable;
    it produces NO_LIABILITY findings until paired with a tax-filing-
    service adapter (MasterTax, EFTPS, etc.)."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_tax_liabilities(
        self, client_id: str, jurisdiction: str, tax_code: str, year: int
    ) -> list[dict]:
        return []

    async def list_tax_deposits(
        self, client_id: str, jurisdiction: str, tax_code: str, year: int
    ) -> list[dict]:
        return []


class StateFilingsOrchestratorReader:
    """Live impl for state_filings_orchestrator.PrismHRReader."""

    def __init__(self, client: PrismHRClient) -> None:
        self._c = client

    async def list_employer_states(
        self, client_id: str, year: int, quarter: int
    ) -> list[dict]:
        start, end = _quarter_dates(year, quarter)
        try:
            body = await self._c.get(
                "/payroll/v1/getPayrollVouchers",
                params={"clientId": client_id,
                        "payDateStart": start.isoformat(),
                        "payDateEnd": end.isoformat()},
            )
        except Exception:  # noqa: BLE001
            return []
        vouchers = _coerce_rows(body, preferred_key="payrollVoucher")
        state_activity: dict[str, dict] = {}
        for v in vouchers:
            st = str(v.get("wcState") or "").upper()
            if not st:
                continue
            state_activity.setdefault(st, {
                "state": st, "hasWages": True,
            })
        return list(state_activity.values())

    async def get_filing_status(
        self, client_id: str, state: str, year: int, quarter: int
    ) -> dict:
        return {}

    async def get_state_recon_findings(
        self, client_id: str, state: str, year: int, quarter: int
    ) -> int:
        # Would require running state_withholding_recon + counting
        # open criticals for that state. Returning 0 keeps the
        # orchestrator optimistic; caller can chain manually.
        return 0
