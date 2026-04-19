"""Guardian 834 5010 rendering — structural tests with synthetic data."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

# Add commercial/ to the path so tests can import without installing it.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "commercial"))

from simploy.carriers.guardian import render_guardian  # noqa: E402
from simploy.carriers.guardian.companion import GuardianCompanionGuide  # noqa: E402
from simploy.carriers.render import (  # noqa: E402
    Coverage,
    Enrollee,
    Enrollment,
)


def _synthetic_enrollment() -> Enrollment:
    cov = Coverage(
        plan_code="DEN-PPO",
        coverage_level="FAM",
        effective_date=date(2026, 1, 1),
        employer_contribution=Decimal("125.00"),
        employee_contribution=Decimal("37.50"),
        maintenance_type="021",
    )
    spouse_cov = Coverage(
        plan_code="DEN-PPO",
        coverage_level="FAM",
        effective_date=date(2026, 1, 1),
        relationship="01",
        maintenance_type="021",
    )
    spouse = Enrollee(
        member_id="SPOUSE-001",
        first_name="JANE",
        last_name="EMPLOYEE",
        dob=date(1985, 6, 12),
        gender="F",
        coverages=[spouse_cov],
    )
    emp = Enrollee(
        member_id="EMP-001",
        first_name="JOHN",
        last_name="EMPLOYEE",
        dob=date(1983, 4, 20),
        gender="M",
        ssn="123456789",
        address_line1="123 MAIN ST",
        address_city="OMAHA",
        address_state="NE",
        address_zip="68102",
        hire_date=date(2024, 2, 1),
        coverages=[cov],
        dependents=[spouse],
    )
    return Enrollment(
        sender_id="SIMPLOY",
        receiver_id="GUARDIAN",
        control_number="000000001",
        sponsor_name="ACME CORP",
        sponsor_id="FEIN-12345",
        production=False,
        transaction_date=date(2026, 4, 19),
        enrollees=[emp],
    )


def test_envelope_segments_present() -> None:
    out = render_guardian(_synthetic_enrollment())
    assert "ISA*" in out
    assert "GS*BE*" in out  # BE = 834 functional ID
    assert "ST*834*" in out
    assert "BGN*" in out
    assert "SE*" in out
    assert "GE*" in out
    assert "IEA*" in out


def test_subscriber_name_and_ssn_present() -> None:
    out = render_guardian(_synthetic_enrollment())
    # NM1*IL*1*lastName*firstName
    assert "NM1*IL*1*EMPLOYEE*JOHN" in out
    # REF*1L for SSN on subscriber
    assert "REF*1L*123456789" in out


def test_dependent_relationship_code_is_not_self() -> None:
    out = render_guardian(_synthetic_enrollment())
    segments = out.split("~")
    # Dependent INS segment should have relationship code '01' (spouse) and
    # INS01='N' (not the subscriber).
    dep_ins = [s for s in segments if s.startswith("INS*N*01*")]
    assert dep_ins, f"no dependent INS segment found. segments: {[s for s in segments if s.startswith('INS')]}"


def test_coverage_hd_and_effective_date() -> None:
    out = render_guardian(_synthetic_enrollment())
    assert "HD*021**DEN-PPO**FAM" in out
    assert "DTP*348*D8*20260101" in out


def test_test_environment_indicator() -> None:
    out = render_guardian(_synthetic_enrollment())
    # ISA15 usage indicator — 'T' for test, 'P' for production.
    # Our production=False enrollment should yield 'T'.
    # Position inside ISA segment.
    isa = next(s for s in out.split("~") if s.startswith("ISA*"))
    # The segment is long; check 'T' literal appears among the ISA fields.
    assert "*T*" in isa


def test_amt_contributions_present() -> None:
    out = render_guardian(_synthetic_enrollment())
    assert "AMT*B9*125.00" in out  # employer
    assert "AMT*D2*37.50" in out   # employee


def test_plan_code_map_override() -> None:
    guide = GuardianCompanionGuide(plan_code_map={"DEN-PPO": "GDN-DEN-HIGH"})
    out = render_guardian(_synthetic_enrollment(), guide=guide)
    assert "GDN-DEN-HIGH" in out
    assert "DEN-PPO" not in out


def test_se_segment_count_includes_all_text_segments() -> None:
    out = render_guardian(_synthetic_enrollment())
    segments = [s for s in out.split("~") if s]
    # Find ST and SE positions; SE count should match the number of segments
    # from ST through SE inclusive.
    st_idx = next(i for i, s in enumerate(segments) if s.startswith("ST*"))
    se_idx = next(i for i, s in enumerate(segments) if s.startswith("SE*"))
    expected_count = (se_idx - st_idx) + 1
    reported_count = int(segments[se_idx].split("*")[1])
    assert reported_count == expected_count, (
        f"SE segment count {reported_count} does not match actual segments "
        f"{expected_count}"
    )
