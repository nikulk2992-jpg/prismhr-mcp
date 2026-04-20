"""Sage Intacct REST/XML Web Services adapter.

Intacct has two APIs:
  1. XML API (aka "Web Services") — the legacy, covers everything.
     POST to https://api.intacct.com/ia/xml/xmlgw.phtml with an XML
     envelope. Auth is senderId + senderPassword (company creds) plus
     login { companyId, userId, password } inside <authentication>.
  2. REST API — newer, OAuth 2.0, growing but not complete. GL detail
     queries are fine here.

This adapter uses XML API by default because:
  - Our primary call is GL journal detail by date range.
  - GLACCOUNT + GLENTRY + their dimensions are first-class XML objects.
  - REST GL detail coverage is spottier as of 2026.

Credentials (expected env vars, populated from 1Password at runtime):
  INTACCT_SENDER_ID         web services subscribing partner id
  INTACCT_SENDER_PASSWORD
  INTACCT_COMPANY_ID        top-level company (Simploy)
  INTACCT_USER_ID
  INTACCT_USER_PASSWORD
  INTACCT_ENTITY_ID         optional, sub-entity if multi-entity setup

Public surface for workflows:
  list_payroll_gl_lines(client_id, *, period_start, period_end)
  -> list[dict] matching payroll_gl_recon.IntacctReader contract.

Field mapping (Intacct -> our key):
  GLDETAIL.accountno       -> glAccount
  GLDETAIL.trx_amount      -> amount (abs value)
  GLDETAIL.trx_type        -> debitCredit ('D'|'C')
  GLDETAIL.customerid      -> clientDim
  GLDETAIL.departmentid    -> departmentDim
  GLDETAIL.locationid      -> locationDim
  GLDETAIL.entry_date      -> postDate
  GLDETAIL.batchno         -> docRef
  GLDETAIL.source          -> filtered to payroll sources

Source filter: by default this adapter only returns entries where
`GLDETAIL.source IN ('PR', 'PAYROLL', 'IMPRT-PR')` — Simploy's own
Intacct uses 'PR' for payroll imports. Override via source_codes kwarg
when pointing at a new client.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from typing import Iterable

import httpx


INTACCT_XML_URL = "https://api.intacct.com/ia/xml/xmlgw.phtml"

_DEFAULT_PAYROLL_SOURCES = ("PR", "PAYROLL", "IMPRT-PR")


@dataclass(frozen=True)
class IntacctCredentials:
    sender_id: str
    sender_password: str
    company_id: str
    user_id: str
    user_password: str
    entity_id: str | None = None

    @classmethod
    def from_env(cls) -> "IntacctCredentials":
        try:
            return cls(
                sender_id=os.environ["INTACCT_SENDER_ID"],
                sender_password=os.environ["INTACCT_SENDER_PASSWORD"],
                company_id=os.environ["INTACCT_COMPANY_ID"],
                user_id=os.environ["INTACCT_USER_ID"],
                user_password=os.environ["INTACCT_USER_PASSWORD"],
                entity_id=os.environ.get("INTACCT_ENTITY_ID"),
            )
        except KeyError as exc:
            missing = exc.args[0]
            raise RuntimeError(
                f"Missing Intacct env var: {missing}. Populate from 1Password "
                "before running."
            ) from exc


class IntacctClient:
    """Thin async XML client. One request-per-call; Intacct returns the
    full response as XML. We parse with stdlib ElementTree."""

    def __init__(
        self,
        credentials: IntacctCredentials,
        *,
        http: httpx.AsyncClient | None = None,
        url: str = INTACCT_XML_URL,
        timeout: float = 60.0,
    ) -> None:
        self._creds = credentials
        self._url = url
        self._timeout = timeout
        self._owns_http = http is None
        self._http = http or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def readByQuery(
        self,
        *,
        object_name: str,
        fields: str,
        query: str,
        page_size: int = 1000,
    ) -> list[dict]:
        """Execute a readByQuery and return flattened row dicts.

        Intacct paginates via returning `numremaining` > 0 + a resultId.
        We follow with readMore until drained.
        """
        rows: list[dict] = []
        result_id: str | None = None
        while True:
            if result_id:
                function = (
                    f"<readMore><resultId>{result_id}</resultId></readMore>"
                )
            else:
                function = (
                    f"<readByQuery>"
                    f"<object>{object_name}</object>"
                    f"<fields>{fields}</fields>"
                    f"<query>{_xml_escape(query)}</query>"
                    f"<pagesize>{page_size}</pagesize>"
                    f"</readByQuery>"
                )

            envelope = self._envelope(function)
            resp = await self._http.post(
                self._url,
                content=envelope.encode("utf-8"),
                headers={"Content-Type": "application/xml"},
            )
            resp.raise_for_status()
            tree = ET.fromstring(resp.text)
            self._raise_for_intacct_error(tree)

            data = tree.find(".//data")
            if data is None:
                break
            for el in data.findall(object_name.lower()) + data.findall(object_name):
                rows.append({child.tag: (child.text or "") for child in el})

            numremaining = int((data.get("numremaining") or "0"))
            result_id = data.get("resultId") or None
            if numremaining <= 0 or not result_id:
                break

        return rows

    # ---- internals ----

    def _envelope(self, function_xml: str) -> str:
        c = self._creds
        entity = (
            f"<locationid>{c.entity_id}</locationid>" if c.entity_id else ""
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<request>"
            "<control>"
            f"<senderid>{_xml_escape(c.sender_id)}</senderid>"
            f"<password>{_xml_escape(c.sender_password)}</password>"
            "<controlid>prismhr-mcp</controlid>"
            "<uniqueid>false</uniqueid>"
            "<dtdversion>3.0</dtdversion>"
            "<includewhitespace>false</includewhitespace>"
            "</control>"
            "<operation>"
            "<authentication><login>"
            f"<userid>{_xml_escape(c.user_id)}</userid>"
            f"<companyid>{_xml_escape(c.company_id)}</companyid>"
            f"<password>{_xml_escape(c.user_password)}</password>"
            f"{entity}"
            "</login></authentication>"
            "<content>"
            "<function controlid=\"f1\">"
            f"{function_xml}"
            "</function>"
            "</content>"
            "</operation>"
            "</request>"
        )

    @staticmethod
    def _raise_for_intacct_error(tree: ET.Element) -> None:
        status = tree.findtext(".//operation/result/status")
        if status and status.lower() != "success":
            desc = tree.findtext(".//operation/result/errormessage/error/description2") or ""
            raise RuntimeError(f"Intacct error: {desc or status}")


class IntacctGLReader:
    """Live implementation of payroll_gl_recon.IntacctReader.

    Pulls GLDETAIL rows for a period, filtered to payroll sources and
    (optionally) to a specific client customer id.
    """

    def __init__(
        self,
        client: IntacctClient,
        *,
        customer_field: str = "customerid",
        source_codes: Iterable[str] = _DEFAULT_PAYROLL_SOURCES,
    ) -> None:
        self._client = client
        self._customer_field = customer_field
        self._source_codes = tuple(source_codes)

    async def list_payroll_gl_lines(
        self, client_id: str, *, period_start: date, period_end: date
    ) -> list[dict]:
        source_filter = " OR ".join(
            f"source = '{s}'" for s in self._source_codes
        )
        query = (
            f"({source_filter}) "
            f"AND entry_date >= '{period_start.isoformat()}' "
            f"AND entry_date <= '{period_end.isoformat()}' "
            f"AND {self._customer_field} = '{client_id}'"
        )
        fields = (
            "recordno,accountno,trx_amount,trx_type,"
            f"{self._customer_field},departmentid,locationid,"
            "entry_date,batchno,source,document"
        )
        rows = await self._client.readByQuery(
            object_name="GLDETAIL",
            fields=fields,
            query=query,
        )
        return [self._normalize(r) for r in rows]

    def _normalize(self, r: dict) -> dict:
        return {
            "glAccount": (r.get("accountno") or "").strip(),
            "amount": r.get("trx_amount") or "0",
            "debitCredit": (r.get("trx_type") or "").strip().upper()[:1] or "D",
            "clientDim": (r.get(self._customer_field) or "").strip(),
            "departmentDim": (r.get("departmentid") or "").strip(),
            "locationDim": (r.get("locationid") or "").strip(),
            "postDate": (r.get("entry_date") or "").strip(),
            "docRef": (r.get("batchno") or r.get("document") or "").strip(),
            "source": (r.get("source") or "").strip(),
        }


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("'", "&apos;")
        .replace('"', "&quot;")
    )
