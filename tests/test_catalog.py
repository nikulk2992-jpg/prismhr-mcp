"""Catalog loader + validator tests — no network, fixture-based."""

from __future__ import annotations

import json

import pytest

from prismhr_mcp.catalog import (
    Catalog,
    MethodContract,
    ValidationError,
    load_catalog,
    validate_args,
)
from prismhr_mcp.catalog.catalog import ADMIN_ONLY_SERVICES, method_id_from_path


def _simple_get_contract(path: str, service: str, required_params: list[str]) -> MethodContract:
    return MethodContract(
        method_id=method_id_from_path(path, "GET"),
        path=path,
        http_method="GET",
        service=service,
        operation=path.split("/")[-1],
        summary="test",
        description="test",
        parameters=[
            {"name": "sessionId", "location": "header", "required": True, "description": ""},
            *[
                {"name": n, "location": "query", "required": True, "description": ""}
                for n in required_params
            ],
        ],
        request_body=None,
        responses={},
    )


def _post_contract_with_body(
    path: str,
    service: str,
    body_required: list[str],
    inline: bool = True,
) -> MethodContract:
    return MethodContract(
        method_id=method_id_from_path(path, "POST"),
        path=path,
        http_method="POST",
        service=service,
        operation=path.split("/")[-1],
        summary="test",
        description="test",
        parameters=[
            {"name": "sessionId", "location": "header", "required": True, "description": ""},
        ],
        request_body={
            "content_types": ["application/json"],
            "schema_refs": [],
            "required_fields": body_required,
            "fields": [{"name": f, "type": "string", "required": True} for f in body_required],
            "inline_schema_present": inline,
        },
        responses={},
    )


# ---------- catalog loader ----------


def test_catalog_loads_and_contains_known_methods() -> None:
    cat = load_catalog()
    assert len(cat) > 0, "catalog should not be empty"
    # This method must be present in the bible
    assert "payroll.v1.getBatchListByDate.GET" in cat
    # Login methods live in the admin list
    login_methods = cat.by_service("login")
    assert login_methods, "login methods should be indexed"
    assert all(m.is_admin for m in login_methods)


def test_catalog_verified_lookup() -> None:
    cat = load_catalog()
    verified = cat.verified()
    # The bundled verification.json was built from a real probe run — at
    # least a handful of payroll methods should be verified.
    verified_ids = {m.method_id for m in verified}
    assert "payroll.v1.getBatchListByDate.GET" in verified_ids or len(verified) >= 5


def test_catalog_search_returns_hits() -> None:
    cat = load_catalog()
    hits = cat.search("payroll batch")
    assert hits, "search for 'payroll batch' should find something"
    assert any("getBatchListByDate" in m.method_id for m in hits)


def test_admin_services_hard_blocked_flag() -> None:
    cat = load_catalog()
    for svc in ADMIN_ONLY_SERVICES:
        for m in cat.by_service(svc):
            assert m.is_admin, f"service {svc} should be admin-flagged"


# ---------- validator ----------


def test_validator_rejects_missing_query_param() -> None:
    c = _simple_get_contract("/payroll/v1/example", "payroll", ["clientId", "startDate"])
    with pytest.raises(ValidationError, match="Missing required parameter") as exc_info:
        validate_args(c, {"startDate": "2026-01-01"})
    assert exc_info.value.code == "MISSING_REQUIRED_PARAM"
    assert "clientId" in str(exc_info.value.context)


def test_validator_accepts_complete_args() -> None:
    c = _simple_get_contract("/payroll/v1/example", "payroll", ["clientId", "startDate"])
    out = validate_args(c, {"clientId": "001", "startDate": "2026-01-01"})
    assert out["query"] == {"clientId": "001", "startDate": "2026-01-01"}
    assert out["body"] == {}


def test_validator_rejects_missing_body_field() -> None:
    c = _post_contract_with_body("/foo/v1/doThing", "foo", ["clientId", "employeeId"])
    with pytest.raises(ValidationError, match="missing required field") as exc_info:
        validate_args(c, {"body": {"clientId": "001"}})
    assert exc_info.value.code == "MISSING_REQUIRED_BODY_FIELD"


def test_validator_passes_through_body_without_inline_schema() -> None:
    # When request_body has $ref only (no inline required list), the validator
    # should pass the body through without strict checking.
    c = _post_contract_with_body("/foo/v1/doThing", "foo", [], inline=False)
    c.request_body["required_fields"] = []  # type: ignore[index]
    out = validate_args(c, {"body": {"anything": "goes"}})
    assert out["body"] == {"anything": "goes"}


def test_session_id_is_never_required_of_callers() -> None:
    c = _simple_get_contract("/payroll/v1/example", "payroll", [])
    # Even with an empty args dict, sessionId shouldn't make validator fail
    out = validate_args(c, {})
    assert out["query"] == {}


# ---------- method_id ----------


def test_method_id_format() -> None:
    assert method_id_from_path("/payroll/v1/getBatchListByDate", "GET") == (
        "payroll.v1.getBatchListByDate.GET"
    )
    assert method_id_from_path("/employee/v1/getEmployee", "post") == (
        "employee.v1.getEmployee.POST"
    )
