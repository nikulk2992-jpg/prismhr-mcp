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
        insurance_line_code="DEN",
        employer_contribution=Decimal("125.00"),
        employee_contribution=Decimal("37.50"),
        maintenance_type="021",
    )
    spouse_cov = Coverage(
        plan_code="DEN-PPO",
        coverage_level="FAM",
        effective_date=date(2026, 1, 1),
        insurance_line_code="DEN",
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
    # X220A1 HD element positions:
    #   HD01=021 (maintenance type)
    #   HD02=""  (maintenance reason — empty)
    #   HD03=DEN (insurance line code, required)
    #   HD04=DEN-PPO (plan code)
    #   HD05=FAM (coverage level)
    assert "HD*021**DEN*DEN-PPO*FAM" in out
    assert "DTP*348*D8*20260101" in out


def test_hd_segment_element_positions() -> None:
    """X220A1-compliant element positions for HD segment.

    Carriers validate by element index. plan_code at the wrong index
    reads as an insurance-line code and rejects the transaction.
    """
    out = render_guardian(_synthetic_enrollment())
    hd_segments = [s for s in out.split("~") if s.startswith("HD*")]
    assert hd_segments, "no HD segment found"
    for hd in hd_segments:
        elems = hd.split("*")
        # elems[0] = 'HD', [1]=HD01, [2]=HD02, [3]=HD03, [4]=HD04, [5]=HD05
        assert elems[1] == "021", f"HD01 maintenance type wrong: {elems}"
        assert elems[3] == "DEN", f"HD03 insurance line code wrong: {elems}"
        assert elems[4] == "DEN-PPO" or elems[4].startswith("GDN-"), (
            f"HD04 plan code wrong: {elems}"
        )
        assert elems[5] == "FAM", f"HD05 coverage level wrong: {elems}"


def test_ins_segment_element_positions() -> None:
    """X220A1-compliant element positions for INS segment.

    employment_status MUST be in INS08, not INS05. INS05 is benefit
    status code (A/C/S/T). Carriers mis-classify enrollees when shifted.
    """
    out = render_guardian(_synthetic_enrollment())
    ins_segments = [s for s in out.split("~") if s.startswith("INS*")]
    assert ins_segments, "no INS segment found"
    for ins in ins_segments:
        elems = ins.split("*")
        # INS01 subscriber ind
        assert elems[1] in {"Y", "N"}
        # INS02 relationship — 18=self, 01=spouse, 19=child
        assert elems[2] in {"18", "01", "19", "G8"}
        # INS03 maintenance type — 021/024
        assert elems[3] == "021"
        # INS04 maintenance reason
        assert elems[4] == "EC"
        # INS05 MUST be benefit status, default 'A' active
        assert elems[5] == "A", f"INS05 should be benefit status 'A', got {elems[5]!r}"
        # INS06, INS07 empty for non-COBRA, non-medicare
        assert elems[6] == ""
        assert elems[7] == ""
        # INS08 MUST be employment status (FT/PT/AC/RT/TE)
        assert elems[8] in {"AC", "FT", "PT", "RT", "TE"}, (
            f"INS08 should be employment status, got {elems[8]!r}"
        )
        # INS09 student status empty
        assert elems[9] == ""
        # INS10 death indicator
        assert elems[10] == "N"


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


def test_render_guardian_does_not_mutate_caller_enrollment() -> None:
    """Repeated renders with different guides must not bleed state."""
    enrollment = _synthetic_enrollment()
    original_sender = enrollment.sender_id
    original_receiver = enrollment.receiver_id
    original_plan_code = enrollment.enrollees[0].coverages[0].plan_code

    # Render once with a guide that maps plan codes + overrides IDs
    guide_a = GuardianCompanionGuide(
        sender_id="ALT-SENDER",
        receiver_id="ALT-RECEIVER",
        plan_code_map={"DEN-PPO": "GDN-DEN-HIGH"},
    )
    render_guardian(enrollment, guide=guide_a)

    # Caller's object must be unchanged
    assert enrollment.sender_id == original_sender
    assert enrollment.receiver_id == original_receiver
    assert enrollment.enrollees[0].coverages[0].plan_code == original_plan_code

    # A second render with a different guide should produce different output —
    # proving guide_a's values didn't persist on the input object.
    guide_b = GuardianCompanionGuide(
        sender_id="OTHER-SENDER",
        receiver_id="OTHER-RECEIVER",
        plan_code_map={"DEN-PPO": "OTHER-PLAN"},
    )
    out_b = render_guardian(enrollment, guide=guide_b)
    assert "OTHER-PLAN" in out_b
    assert "GDN-DEN-HIGH" not in out_b
    assert "ALT-SENDER" not in out_b
