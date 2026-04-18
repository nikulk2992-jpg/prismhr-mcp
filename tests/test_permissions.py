"""Permissions subsystem — manifest, consent store, manager, cascade revoke."""

from __future__ import annotations

from pathlib import Path

import pytest

from prismhr_mcp.permissions import (
    MANIFEST,
    ConsentStore,
    PermissionDeniedError,
    PermissionManager,
    Scope,
)
from prismhr_mcp.permissions.scopes import lookup, manifest_by_category


def _mgr(tmp_path: Path, peo_id: str = "TEST-PEO", env: str = "uat") -> PermissionManager:
    store = ConsentStore(cache_dir=tmp_path, peo_id=peo_id, environment=env)
    return PermissionManager(store=store)


def test_manifest_contains_every_scope() -> None:
    enum_scopes = set(Scope)
    spec_scopes = {spec.scope for spec in MANIFEST}
    assert enum_scopes == spec_scopes


def test_categories_partition_the_manifest() -> None:
    by_cat = manifest_by_category()
    total = sum(len(specs) for specs in by_cat.values())
    assert total == len(MANIFEST)


def test_default_state_denies_all(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    assert mgr.granted == frozenset()
    with pytest.raises(PermissionDeniedError, match="PERMISSION_NOT_GRANTED"):
        mgr.check(Scope.CLIENT_READ)


def test_grant_persists_across_manager_instances(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.grant([Scope.CLIENT_READ])

    mgr2 = _mgr(tmp_path)
    assert Scope.CLIENT_READ in mgr2.granted


def test_granting_employee_read_auto_includes_client_read(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.grant([Scope.EMPLOYEE_READ])
    assert Scope.CLIENT_READ in mgr.granted
    assert Scope.EMPLOYEE_READ in mgr.granted


def test_revoking_prereq_cascades(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.grant([Scope.EMPLOYEE_READ])  # brings CLIENT_READ along
    mgr.revoke([Scope.CLIENT_READ])
    # EMPLOYEE_READ requires CLIENT_READ, so it should be dropped too.
    assert Scope.CLIENT_READ not in mgr.granted
    assert Scope.EMPLOYEE_READ not in mgr.granted


def test_replace_clears_old_grants(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.grant([Scope.CLIENT_READ, Scope.EMPLOYEE_READ, Scope.PAYROLL_READ])
    mgr.replace([Scope.BILLING_READ])
    assert mgr.granted == frozenset({Scope.BILLING_READ})


def test_check_surfaces_missing_prereqs_in_context(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    try:
        mgr.check(Scope.EMPLOYEE_READ)
    except PermissionDeniedError as exc:
        assert "client:read" in exc.context["missing_prereqs"]
    else:
        pytest.fail("expected PermissionDeniedError")


def test_consent_file_scoped_to_peo_and_environment(tmp_path: Path) -> None:
    mgr_uat = _mgr(tmp_path, peo_id="TEST-PEO", env="uat")
    mgr_uat.grant([Scope.CLIENT_READ])

    mgr_prod = _mgr(tmp_path, peo_id="TEST-PEO", env="prod")
    assert Scope.CLIENT_READ not in mgr_prod.granted

    mgr_other_peo = _mgr(tmp_path, peo_id="OTHER", env="uat")
    assert Scope.CLIENT_READ not in mgr_other_peo.granted


def test_corrupt_consent_file_treated_as_empty(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    mgr.grant([Scope.CLIENT_READ])
    # Trash the file.
    cfile = next(tmp_path.glob("consent-*.json"))
    cfile.write_text("not json", encoding="utf-8")

    mgr2 = _mgr(tmp_path)
    assert mgr2.granted == frozenset()


def test_lookup_raises_for_unknown_scope() -> None:
    with pytest.raises(KeyError):
        lookup("not-a-real-scope")  # type: ignore[arg-type]


def test_unknown_scope_string_rejected(tmp_path: Path) -> None:
    mgr = _mgr(tmp_path)
    with pytest.raises(ValueError, match="Unknown scope"):
        mgr.grant(["bogus:scope"])
