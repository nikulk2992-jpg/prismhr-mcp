"""ANSI X12 005010X220A1 (834) benefit enrollment writer.

Scope of this module: produce a valid, carrier-agnostic 834 5010 transaction
set from a structured Enrollment payload. Companion-guide-specific quirks
(qualifier overrides, REF segment choices, loop inclusion rules) are applied
by the carrier subpackage, not here.

Segment reference lives in `X220A1` section of the HIPAA implementation
guide. This writer is intentionally minimal — enough to pass structural
validation against public CGs for Guardian + BCBS Michigan during Phase 1.
Fields that vary per carrier are parameters on `Render834.__init__`;
anything we left out returns `[]` so carriers can override.

NOT a full 834 implementation. Explicit out-of-scope for v0:
- 835 response reconciliation
- Per-carrier testing frameworks
- Full SNIP-level 1-7 validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

SEG_SEP = "~"
ELE_SEP = "*"
SUB_SEP = ":"


# ---------- payload dataclasses (carrier-agnostic) ----------


@dataclass(slots=True)
class Coverage:
    """One benefit enrollment for an enrollee."""

    plan_code: str  # carrier's plan code (mapped by companion.py)
    coverage_level: Literal["EMP", "ESP", "ECH", "FAM"]  # emp only / + spouse / + child / family
    effective_date: date
    termination_date: date | None = None
    employer_contribution: Decimal | None = None
    employee_contribution: Decimal | None = None
    relationship: Literal["18", "01", "19", "G8"] = "18"  # 18=self, 01=spouse, 19=child, G8=other
    member_id: str | None = None  # required for dependents; for employee = SSN
    # Event type maintenance codes — 021=add, 001=change, 024=cancel
    maintenance_type: Literal["021", "001", "024"] = "021"
    maintenance_reason: str = "EC"  # EC=employee election; see HIPAA code list


@dataclass(slots=True)
class Enrollee:
    """Subscriber (employee) + dependents."""

    member_id: str
    first_name: str
    last_name: str
    middle_name: str = ""
    dob: date | None = None
    gender: Literal["M", "F", "U"] = "U"
    ssn: str | None = None
    address_line1: str = ""
    address_city: str = ""
    address_state: str = ""
    address_zip: str = ""
    hire_date: date | None = None
    employment_status: Literal["FT", "PT", "TERM"] = "FT"
    coverages: list[Coverage] = field(default_factory=list)
    dependents: list["Enrollee"] = field(default_factory=list)


@dataclass(slots=True)
class Enrollment:
    """Top-level file payload."""

    sender_id: str  # PEO/employer sender ID
    receiver_id: str  # carrier trading-partner ID
    control_number: str  # unique per file — used in ISA/GS/ST
    sponsor_name: str  # client / employer legal name
    sponsor_id: str  # FEIN or carrier-assigned group number
    production: bool = False  # False = 'T' test indicator in ISA15
    transaction_date: date = field(default_factory=date.today)
    enrollees: list[Enrollee] = field(default_factory=list)


# ---------- writer ----------


class Render834:
    """Renders an `Enrollment` payload to an 834 5010 transaction set.

    Carrier subpackages instantiate with their own `companion` config to
    override qualifiers, add optional segments, or swap code values.
    """

    def __init__(
        self,
        *,
        purpose_code: str = "00",  # 00=original, 15=re-submission, 04=change
        action_code: Literal["2", "4"] = "2",  # 2=change-only (maint updates), 4=full refresh
        interchange_version: str = "00501",
        implementation_convention_ref: str = "005010X220A1",
        sender_qualifier: str = "ZZ",  # mutually-defined
        receiver_qualifier: str = "ZZ",
    ) -> None:
        self.purpose_code = purpose_code
        self.action_code = action_code
        self.interchange_version = interchange_version
        self.impl_ref = implementation_convention_ref
        self.sender_qualifier = sender_qualifier
        self.receiver_qualifier = receiver_qualifier

    # ---- public API ----

    def render(self, enrollment: Enrollment) -> str:
        segments: list[str] = []
        segments.extend(self._isa(enrollment))
        segments.extend(self._gs(enrollment))
        segments.extend(self._st(enrollment))
        segments.extend(self._bgn(enrollment))
        segments.extend(self._sponsor_loops(enrollment))
        for enrollee in enrollment.enrollees:
            segments.extend(self._member_loop(enrollee, enrollment))
        segments.extend(self._se(segments, enrollment))
        segments.extend(self._ge(enrollment))
        segments.extend(self._iea(enrollment))
        return SEG_SEP.join(segments) + SEG_SEP

    # ---- envelope ----

    def _isa(self, e: Enrollment) -> list[str]:
        # ISA fields are FIXED-WIDTH in real EDI; for our purposes here we emit
        # the logical structure. A production writer would pad + uppercase per spec.
        usage = "P" if e.production else "T"
        return [
            ELE_SEP.join([
                "ISA",
                "00", " " * 10,                     # auth info
                "00", " " * 10,                     # security info
                self.sender_qualifier, e.sender_id.ljust(15),
                self.receiver_qualifier, e.receiver_id.ljust(15),
                e.transaction_date.strftime("%y%m%d"),
                e.transaction_date.strftime("%H%M"),
                "^",                                 # repetition separator
                self.interchange_version,
                e.control_number.rjust(9, "0"),
                "0",                                  # ack requested
                usage,
                SUB_SEP,                              # component element separator
            ]),
        ]

    def _gs(self, e: Enrollment) -> list[str]:
        return [
            ELE_SEP.join([
                "GS",
                "BE",                                 # functional ID for 834
                e.sender_id,
                e.receiver_id,
                e.transaction_date.strftime("%Y%m%d"),
                e.transaction_date.strftime("%H%M"),
                e.control_number,
                "X",
                self.interchange_version + "X220A1",
            ]),
        ]

    def _st(self, e: Enrollment) -> list[str]:
        return [ELE_SEP.join(["ST", "834", e.control_number.zfill(4), self.impl_ref])]

    def _bgn(self, e: Enrollment) -> list[str]:
        return [
            ELE_SEP.join([
                "BGN",
                self.purpose_code,
                e.control_number,
                e.transaction_date.strftime("%Y%m%d"),
                e.transaction_date.strftime("%H%M"),
                "",                                   # time zone code (optional)
                "",                                   # reference identification
                "",                                   # transaction type
                self.action_code,
            ]),
        ]

    def _sponsor_loops(self, e: Enrollment) -> list[str]:
        return [
            ELE_SEP.join(["N1", "P5", e.sponsor_name, "FI", e.sponsor_id]),  # sponsor
            ELE_SEP.join(["N1", "IN", "Payer", "FI", e.receiver_id]),        # insurer (payer)
        ]

    # ---- member loop ----

    def _member_loop(self, enrollee: Enrollee, e: Enrollment, subscriber: Enrollee | None = None) -> list[str]:
        segments: list[str] = []
        is_subscriber = subscriber is None
        coverage = enrollee.coverages[0] if enrollee.coverages else None
        # INS segment
        segments.append(
            ELE_SEP.join([
                "INS",
                "Y" if is_subscriber else "N",
                coverage.relationship if coverage else "18",
                coverage.maintenance_type if coverage else "021",
                coverage.maintenance_reason if coverage else "EC",
                enrollee.employment_status,
                "", "", "",
                "N",  # death indicator
            ])
        )
        # REF*0F — subscriber identifier (member id / SSN)
        segments.append(ELE_SEP.join(["REF", "0F", enrollee.member_id]))
        if enrollee.ssn:
            segments.append(ELE_SEP.join(["REF", "1L", enrollee.ssn]))
        # Subscriber-level dates
        if coverage:
            segments.append(
                ELE_SEP.join(["DTP", "356", "D8", coverage.effective_date.strftime("%Y%m%d")])
            )
            if coverage.termination_date:
                segments.append(
                    ELE_SEP.join(["DTP", "357", "D8", coverage.termination_date.strftime("%Y%m%d")])
                )
        if enrollee.hire_date and is_subscriber:
            segments.append(
                ELE_SEP.join(["DTP", "336", "D8", enrollee.hire_date.strftime("%Y%m%d")])
            )
        # NM1 name
        segments.append(
            ELE_SEP.join([
                "NM1", "IL", "1",
                enrollee.last_name, enrollee.first_name, enrollee.middle_name,
                "", "", "34", enrollee.ssn or enrollee.member_id,
            ])
        )
        # Address
        if enrollee.address_line1:
            segments.append(ELE_SEP.join(["N3", enrollee.address_line1]))
            if enrollee.address_city or enrollee.address_state or enrollee.address_zip:
                segments.append(
                    ELE_SEP.join([
                        "N4",
                        enrollee.address_city,
                        enrollee.address_state,
                        enrollee.address_zip,
                    ])
                )
        # Demographics
        if enrollee.dob or enrollee.gender:
            parts = ["DMG"]
            if enrollee.dob:
                parts.extend(["D8", enrollee.dob.strftime("%Y%m%d")])
            else:
                parts.extend(["", ""])
            parts.append(enrollee.gender)
            segments.append(ELE_SEP.join(parts))
        # Coverage loops
        for cov in enrollee.coverages:
            segments.extend(self._coverage_loop(cov))
        # Recurse into dependents — each dependent becomes its own INS loop
        # but keyed to the subscriber via INS01='N'
        for dep in enrollee.dependents:
            segments.extend(self._member_loop(dep, e, subscriber=enrollee))
        return segments

    def _coverage_loop(self, cov: Coverage) -> list[str]:
        segments: list[str] = []
        # HD*030 — health coverage
        parts = ["HD", cov.maintenance_type, "", cov.plan_code, "", cov.coverage_level]
        segments.append(ELE_SEP.join(parts))
        segments.append(
            ELE_SEP.join(["DTP", "348", "D8", cov.effective_date.strftime("%Y%m%d")])
        )
        if cov.termination_date:
            segments.append(
                ELE_SEP.join(["DTP", "349", "D8", cov.termination_date.strftime("%Y%m%d")])
            )
        # AMT segments for contributions (optional)
        if cov.employer_contribution is not None:
            segments.append(ELE_SEP.join(["AMT", "B9", str(cov.employer_contribution)]))
        if cov.employee_contribution is not None:
            segments.append(ELE_SEP.join(["AMT", "D2", str(cov.employee_contribution)]))
        return segments

    # ---- trailers ----

    def _se(self, segments_so_far: list[str], e: Enrollment) -> list[str]:
        # Count all non-envelope segments produced so far (after ST) + this SE
        st_idx = next(i for i, s in enumerate(segments_so_far) if s.startswith("ST" + ELE_SEP))
        segment_count = len(segments_so_far) - st_idx + 1
        return [ELE_SEP.join(["SE", str(segment_count), e.control_number.zfill(4)])]

    def _ge(self, e: Enrollment) -> list[str]:
        return [ELE_SEP.join(["GE", "1", e.control_number])]

    def _iea(self, e: Enrollment) -> list[str]:
        return [ELE_SEP.join(["IEA", "1", e.control_number.rjust(9, "0")])]
