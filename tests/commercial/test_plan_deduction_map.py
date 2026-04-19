"""Plan-to-deduction-code map loader — unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.config.plan_deduction_map import (  # noqa: E402
    PlanDeductionMap,
    load_plan_deduction_map,
)


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "pdm.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_missing_file_returns_empty_map(tmp_path: Path) -> None:
    pdm = load_plan_deduction_map(tmp_path / "does-not-exist.yaml")
    assert not pdm
    assert pdm.expected_deduction_codes("001010", "MED") == []


def test_default_block_applies_when_no_client_override(tmp_path: Path) -> None:
    p = _write(tmp_path, """
_default:
  MED-BASE:
    deduction_codes: [MED, MEDPT]
  DEN-PPO:
    deduction_codes: DEN
""")
    pdm = load_plan_deduction_map(p)
    codes = pdm.expected_deduction_codes("CLIENT-X", "MED-BASE")
    assert codes == ["MED", "MEDPT"]
    assert pdm.expected_deduction_codes("ANY", "DEN-PPO") == ["DEN"]


def test_client_block_overrides_default(tmp_path: Path) -> None:
    p = _write(tmp_path, """
_default:
  MED-BASE:
    deduction_codes: [MED]

CLIENT-001:
  MED-BASE:
    deduction_codes: [MED-PREMIUM]
""")
    pdm = load_plan_deduction_map(p)
    assert pdm.expected_deduction_codes("OTHER", "MED-BASE") == ["MED"]
    assert pdm.expected_deduction_codes("CLIENT-001", "MED-BASE") == ["MED-PREMIUM"]


def test_section125_and_deduction_codes_combine(tmp_path: Path) -> None:
    p = _write(tmp_path, """
_default:
  FSA-HC:
    deduction_codes: [FSAHC]
    section125_deduction_codes: [125-FSA]
""")
    pdm = load_plan_deduction_map(p)
    assert pdm.expected_deduction_codes("X", "FSA-HC") == ["FSAHC", "125-FSA"]


def test_plan_absent_from_map_returns_empty(tmp_path: Path) -> None:
    p = _write(tmp_path, """
_default:
  ONE:
    deduction_codes: [A]
""")
    pdm = load_plan_deduction_map(p)
    assert pdm.expected_deduction_codes("X", "TWO") == []


def test_empty_file_returns_empty_map(tmp_path: Path) -> None:
    p = _write(tmp_path, "")
    pdm = load_plan_deduction_map(p)
    assert not pdm


def test_bill_codes_exposed_via_lookup(tmp_path: Path) -> None:
    p = _write(tmp_path, """
_default:
  MED:
    deduction_codes: [D]
    bill_codes: [BILL1, BILL2]
""")
    pdm = load_plan_deduction_map(p)
    hit = pdm.lookup("X", "MED")
    assert hit is not None
    assert hit.bill_codes == ["BILL1", "BILL2"]
