"""Unit tests for the 1Password credential fetcher + scrypt disk cache."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prismhr_mcp.auth.onepassword import CredentialError, OnePasswordClient


def _ok_runner(payload: dict) -> object:
    calls: list[list[str]] = []

    def runner(cmd: list[str]) -> tuple[int, str, str]:
        calls.append(cmd)
        return 0, json.dumps(payload), ""

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


def _fake_op_payload(username: str, password: str, peo_id: str) -> dict:
    return {
        "id": "fake-item-id",
        "title": "PrismHR UAT",
        "fields": [
            {"id": "username", "label": "username", "value": username},
            {"id": "password", "label": "password", "value": password},
            {"id": "peo", "label": "peoId", "value": peo_id},
            {"id": "ignore", "label": None, "value": "x"},
        ],
    }


def test_fetch_parses_fields(tmp_path: Path) -> None:
    runner = _ok_runner(_fake_op_payload("claudedemo", "s3cret", "624*D"))
    client = OnePasswordClient(cache_dir=tmp_path, runner=runner)

    creds = client.get(item="PrismHR UAT", vault="Simploy")

    assert creds == {"username": "claudedemo", "password": "s3cret", "peoId": "624*D"}
    assert runner.calls[0][:3] == ["op", "item", "get"]  # type: ignore[attr-defined]


def test_cache_hit_avoids_second_op_call(tmp_path: Path) -> None:
    runner = _ok_runner(_fake_op_payload("u", "p", "peo"))
    client = OnePasswordClient(cache_dir=tmp_path, runner=runner)

    client.get("PrismHR", "Simploy")
    client.get("PrismHR", "Simploy")

    assert len(runner.calls) == 1  # type: ignore[attr-defined]


def test_invalidate_forces_fresh_fetch(tmp_path: Path) -> None:
    runner = _ok_runner(_fake_op_payload("u", "p", "peo"))
    client = OnePasswordClient(cache_dir=tmp_path, runner=runner)

    client.get("PrismHR", "Simploy")
    client.invalidate("PrismHR", "Simploy")
    client.get("PrismHR", "Simploy")

    assert len(runner.calls) == 2  # type: ignore[attr-defined]


def test_op_failure_raises_credential_error(tmp_path: Path) -> None:
    def failing_runner(cmd: list[str]) -> tuple[int, str, str]:
        return 1, "", "not signed in to 1Password"

    client = OnePasswordClient(cache_dir=tmp_path, runner=failing_runner)
    with pytest.raises(CredentialError, match="not signed in"):
        client.get("PrismHR", "Simploy")


def test_corrupt_cache_treated_as_miss(tmp_path: Path) -> None:
    runner = _ok_runner(_fake_op_payload("u", "p", "peo"))
    client = OnePasswordClient(cache_dir=tmp_path, runner=runner)
    client.get("PrismHR", "Simploy")  # writes cache

    # Trash the cache file — should refetch gracefully, not crash.
    cache_file = next(tmp_path.glob("cred-*.enc"))
    cache_file.write_bytes(b"\x00\x01corrupt")

    client.get("PrismHR", "Simploy")
    assert len(runner.calls) == 2  # type: ignore[attr-defined]


def test_cached_credentials_roundtrip_through_encryption(tmp_path: Path) -> None:
    # Encryption must be a real roundtrip — decrypt has to yield the original dict.
    runner = _ok_runner(_fake_op_payload("alice", "hunter2", "peo-42"))
    client = OnePasswordClient(cache_dir=tmp_path, runner=runner)
    first = client.get("PrismHR", "Simploy")

    # Fresh client instance reads from disk only (runner should not be called).
    unused_runner = _ok_runner({"fields": []})
    fresh = OnePasswordClient(cache_dir=tmp_path, runner=unused_runner)
    second = fresh.get("PrismHR", "Simploy")

    assert first == second
    assert second["password"] == "hunter2"
    assert len(unused_runner.calls) == 0  # type: ignore[attr-defined]
