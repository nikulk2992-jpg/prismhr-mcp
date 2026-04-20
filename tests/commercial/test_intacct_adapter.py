"""Intacct adapter — unit tests against a mocked XML endpoint via respx."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.accounting.intacct import (  # noqa: E402
    INTACCT_XML_URL,
    IntacctClient,
    IntacctCredentials,
    IntacctGLReader,
)


def _creds() -> IntacctCredentials:
    return IntacctCredentials(
        sender_id="senderX",
        sender_password="senderP",
        company_id="SIMPLOY",
        user_id="svc",
        user_password="pw",
    )


_SAMPLE_SUCCESS = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <control>
    <status>success</status>
  </control>
  <operation>
    <authentication><status>success</status></authentication>
    <result>
      <status>success</status>
      <function>readByQuery</function>
      <controlid>f1</controlid>
      <data listtype="gldetail" count="2" numremaining="0" resultId="">
        <gldetail>
          <recordno>111</recordno>
          <accountno>6000</accountno>
          <trx_amount>1000.00</trx_amount>
          <trx_type>D</trx_type>
          <customerid>CLT1</customerid>
          <departmentid>SALES</departmentid>
          <locationid>HQ</locationid>
          <entry_date>2026-04-10</entry_date>
          <batchno>JE-555</batchno>
          <source>PR</source>
        </gldetail>
        <gldetail>
          <recordno>112</recordno>
          <accountno>2100</accountno>
          <trx_amount>1000.00</trx_amount>
          <trx_type>C</trx_type>
          <customerid>CLT1</customerid>
          <departmentid></departmentid>
          <locationid></locationid>
          <entry_date>2026-04-10</entry_date>
          <batchno>JE-555</batchno>
          <source>PR</source>
        </gldetail>
      </data>
    </result>
  </operation>
</response>
"""


_SAMPLE_ERROR = """<?xml version="1.0"?>
<response>
  <operation>
    <result>
      <status>failure</status>
      <errormessage>
        <error>
          <description2>Invalid company</description2>
        </error>
      </errormessage>
    </result>
  </operation>
</response>
"""


@pytest.mark.asyncio
@respx.mock
async def test_gl_reader_normalizes_rows() -> None:
    respx.post(INTACCT_XML_URL).mock(
        return_value=httpx.Response(200, text=_SAMPLE_SUCCESS)
    )
    async with httpx.AsyncClient() as http:
        client = IntacctClient(_creds(), http=http)
        reader = IntacctGLReader(client)
        rows = await reader.list_payroll_gl_lines(
            "CLT1",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
        )

    assert len(rows) == 2
    assert rows[0]["glAccount"] == "6000"
    assert rows[0]["amount"] == "1000.00"
    assert rows[0]["debitCredit"] == "D"
    assert rows[0]["clientDim"] == "CLT1"
    assert rows[0]["departmentDim"] == "SALES"
    assert rows[0]["docRef"] == "JE-555"
    assert rows[0]["source"] == "PR"
    assert rows[1]["debitCredit"] == "C"


@pytest.mark.asyncio
@respx.mock
async def test_intacct_error_raises() -> None:
    respx.post(INTACCT_XML_URL).mock(
        return_value=httpx.Response(200, text=_SAMPLE_ERROR)
    )
    async with httpx.AsyncClient() as http:
        client = IntacctClient(_creds(), http=http)
        reader = IntacctGLReader(client)
        with pytest.raises(RuntimeError, match="Intacct error"):
            await reader.list_payroll_gl_lines(
                "CLT1",
                period_start=date(2026, 4, 1),
                period_end=date(2026, 4, 30),
            )


@pytest.mark.asyncio
@respx.mock
async def test_gl_reader_query_contains_period_and_client() -> None:
    captured: dict = {}

    def _cap(request):
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(200, text=_SAMPLE_SUCCESS)

    respx.post(INTACCT_XML_URL).mock(side_effect=_cap)
    async with httpx.AsyncClient() as http:
        client = IntacctClient(_creds(), http=http)
        reader = IntacctGLReader(client)
        await reader.list_payroll_gl_lines(
            "CLT42",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        )

    body = captured["body"]
    assert "CLT42" in body
    assert "2026-01-01" in body
    assert "2026-03-31" in body
    assert "source = &apos;PR&apos;" in body


def test_credentials_from_env_reads_all_fields(monkeypatch) -> None:
    monkeypatch.setenv("INTACCT_SENDER_ID", "S")
    monkeypatch.setenv("INTACCT_SENDER_PASSWORD", "SP")
    monkeypatch.setenv("INTACCT_COMPANY_ID", "SIMPLOY")
    monkeypatch.setenv("INTACCT_USER_ID", "U")
    monkeypatch.setenv("INTACCT_USER_PASSWORD", "UP")
    monkeypatch.setenv("INTACCT_ENTITY_ID", "ENT")
    c = IntacctCredentials.from_env()
    assert c.sender_id == "S"
    assert c.company_id == "SIMPLOY"
    assert c.entity_id == "ENT"


def test_credentials_from_env_raises_on_missing(monkeypatch) -> None:
    for k in (
        "INTACCT_SENDER_ID", "INTACCT_SENDER_PASSWORD", "INTACCT_COMPANY_ID",
        "INTACCT_USER_ID", "INTACCT_USER_PASSWORD", "INTACCT_ENTITY_ID",
    ):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError, match="Missing Intacct env var"):
        IntacctCredentials.from_env()
