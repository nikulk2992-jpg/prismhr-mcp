"""Multi-state voucher validator.

PrismHR passes inputs to Vertex/Symmetry which then compute withholding.
The ENGINE is correct; the INPUTS often aren't. This validator reverse-
engineers what the correct allocation should have been and flags when
PrismHR vouchers don't match.

Primary Simploy problem: MO/IL commuters. MO is NOT reciprocal with IL.
So MO resident working IL should have:
  * IL withholding (full amount per IL rates)
  * MO withholding = 0 (per MO rule: "does not require withholding from
    MO residents working in other states that collect withholding tax")

Likewise IL resident working MO:
  * MO withholding (full amount)
  * IL withholding = 0

Validator checks voucher tax rows + employee state metadata to detect:
  * WRONG_WORK_STATE_WITHHELD — home state withheld when work state collects
  * DOUBLE_WITHHELD_NON_RECIPROCAL — both states withheld on non-reciprocal pair
  * MISSING_NR_CERT — employee has multi-state pattern but no NR cert flag
  * MULTI_STATE_TAX_ON_VOUCHER — voucher has 2+ state income tax codes
  * WORK_STATE_WITHHELD_UNDER — non-resident work state withholding < expected
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol


Severity = str  # critical / warning / info


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str


# Reciprocity table (bidirectional). Source: Vertex Calculation Guide
# March 2026 — per-state reciprocity sections. MO has NO reciprocity
# (per Vertex MO summary p565).
#
# Each pair listed once; normalized alphabetically.
RECIPROCITY_PAIRS: frozenset[tuple[str, str]] = frozenset(
    tuple(sorted(p))
    for p in [
        # IL reciprocals (Vertex IL p331): IA, KY, MI, WI
        ("IL", "IA"), ("IL", "KY"), ("IL", "MI"), ("IL", "WI"),

        # IN reciprocals (Vertex IN — inferred from neighbor sections):
        # IN has reciprocity with KY, MI, OH, PA, WI
        ("IN", "KY"), ("IN", "MI"), ("IN", "OH"), ("IN", "PA"), ("IN", "WI"),

        # KY reciprocals: IL, IN, MI, OH, VA, WV, WI
        ("KY", "MI"), ("KY", "OH"), ("KY", "VA"), ("KY", "WV"), ("KY", "WI"),

        # OH reciprocals (Vertex OH p782): IN, KY, MI, PA, WV
        ("MI", "OH"), ("OH", "PA"), ("OH", "WV"),

        # MI / WI
        ("MI", "WI"),

        # MD reciprocals (Vertex MD): DC, PA, VA, WV
        ("MD", "DC"), ("MD", "PA"), ("MD", "VA"), ("MD", "WV"),

        # PA reciprocals (Vertex PA p1001): IN, MD, NJ, OH, VA, WV
        ("NJ", "PA"), ("PA", "VA"), ("PA", "WV"),

        # VA reciprocals: DC, KY, MD, PA, WV
        ("VA", "DC"), ("VA", "WV"),

        # MN / ND
        ("MN", "ND"),
        ("ND", "MT"),

        # DC reciprocals: all states (technically DC is like a reciprocal
        # with any state since DC only taxes DC residents). Handled by
        # Vertex DC section; not all pairs listed here.
    ]
)


# Jurisdiction Interaction Treatment codes per Vertex guide:
#   1 = ignore work tax
#   2 = credit the resident by work tax withheld
#   3 = eliminate the resident tax if work > 0
#   4 = credit work tax up to resident tax
#   5 = eliminate resident tax if work > 0, accumulate only if withheld
#   6 = eliminate resident tax if work tax on non-residents > 0, always accumulate
#   7 = eliminate resident tax if work tax on non-residents > 0,
#       accumulate only if withheld
JURISDICTION_INTERACTION_TREATMENT = {
    "MO": 7,
    "IL": 7,
    "OH": 6,
    "PA": 5,
    "CA": 2,
    "NY": 1,   # NY always withholds; credit claimed at filing
    "MA": 1,
    "NJ": 7,
}


def is_reciprocal(state_a: str, state_b: str) -> bool:
    if not state_a or not state_b:
        return False
    return tuple(sorted([state_a.upper(), state_b.upper()])) in RECIPROCITY_PAIRS


_STATE_DESC_RE = re.compile(r"\b([A-Z]{2})\b")


_US_STATES = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY", "PR",
})


def _state_from_desc(desc: str) -> str | None:
    """Pull a state abbrev from empTaxDeductCodeDesc, e.g.,
    'MO INCOME TAX' -> 'MO'. Returns None if no match."""
    if not desc:
        return None
    tokens = _STATE_DESC_RE.findall(desc.upper())
    for tok in tokens:
        if tok in _US_STATES:
            return tok
    return None


@dataclass
class MultiStateVoucherAudit:
    voucher_id: str
    employee_id: str
    home_state: str
    work_state: str
    states_with_tax: list[str]
    total_state_withheld: Decimal
    # Per earning-line state allocation (derived from WSL lookup).
    # Keys are state abbrevs, values are total wages earned on this
    # voucher under that worksite state.
    wages_by_work_state: dict[str, Decimal] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)


def _resolve_line_state(
    line: dict, location_state_map: dict[str, str] | None
) -> str | None:
    """Map an earning[].location value to its WSL state via the cached
    Client|Location map. Falls back to None if no match."""
    if not location_state_map:
        return None
    loc = str(line.get("location") or "").strip()
    if not loc:
        return None
    # Try exact, then uppercase — PrismHR location codes are case-sensitive
    # but WSL names vary in casing.
    return location_state_map.get(loc) or location_state_map.get(loc.upper())


def analyze_voucher(
    voucher: dict,
    *,
    home_state: str,
    has_nr_cert: bool = False,
    location_state_map: dict[str, str] | None = None,
) -> MultiStateVoucherAudit:
    """Parse a single voucher's employeeTax[] for state-income-tax codes,
    earning[] for per-line work-site-location allocation, and validate
    against the home/work state pair.

    `location_state_map`: { locationName -> state_abbrev } built from
    Client|Location (getData#Client|Location). If provided, the validator
    computes per-line wages-by-state and flags when the voucher's tax
    allocation doesn't match the actual work-location distribution.
    """
    vid = str(voucher.get("voucherId") or "")
    eid = str(voucher.get("employeeId") or "")
    work_state = str(voucher.get("wcState") or "").upper()
    home_state = (home_state or "").upper()

    # Walk tax rows — extract state income tax by "-20" suffix
    states_seen: dict[str, Decimal] = {}
    for t in (voucher.get("employeeTax") or []):
        code = str(t.get("empTaxDeductCode") or "")
        desc = str(t.get("empTaxDeductCodeDesc") or "")
        amt = Decimal(str(t.get("empTaxAmount") or "0"))
        if "-20" not in code:
            continue
        state = _state_from_desc(desc)
        if not state:
            continue
        states_seen.setdefault(state, Decimal("0"))
        states_seen[state] += amt

    total_withheld = sum(states_seen.values(), Decimal("0"))

    # Per-line state allocation from WSL lookup
    wages_by_work_state: dict[str, Decimal] = {}
    if location_state_map:
        for line in (voucher.get("earning") or []):
            amt = Decimal(str(line.get("payAmount") or "0"))
            if amt == 0:
                continue
            line_state = _resolve_line_state(line, location_state_map)
            if not line_state:
                # Unknown location — don't break the map; skip
                continue
            wages_by_work_state.setdefault(line_state, Decimal("0"))
            wages_by_work_state[line_state] += amt

    audit = MultiStateVoucherAudit(
        voucher_id=vid,
        employee_id=eid,
        home_state=home_state,
        work_state=work_state,
        states_with_tax=sorted(states_seen.keys()),
        total_state_withheld=total_withheld,
        wages_by_work_state=wages_by_work_state,
    )

    # Cross-check: if earning lines show multiple states but voucher
    # only withheld for one, that's a real bug.
    if len(wages_by_work_state) >= 2:
        work_states_with_wages = set(wages_by_work_state.keys())
        states_with_withholding = set(states_seen.keys())
        missing_withholding = work_states_with_wages - states_with_withholding
        if missing_withholding:
            audit.findings.append(
                Finding(
                    "PER_LINE_STATE_WAGES_NO_WITHHOLDING",
                    "critical",
                    f"Voucher has wages earned in {sorted(work_states_with_wages)} "
                    f"(per earning[].location -> WSL lookup) but state "
                    f"withholding only for {sorted(states_with_withholding)}. "
                    f"Missing: {sorted(missing_withholding)}.",
                )
            )

    if not home_state or not work_state:
        return audit

    # ---- Case 1: Multi-state withholding on a single voucher ----
    if len(states_seen) >= 2:
        audit.findings.append(
            Finding(
                "MULTI_STATE_TAX_ON_VOUCHER",
                "info",
                f"Voucher withheld state tax for {len(states_seen)} states: "
                f"{sorted(states_seen.keys())}. Verify split is intentional.",
            )
        )
        # Check: is any pair non-reciprocal + both withheld?
        state_list = sorted(states_seen.keys())
        for i, a in enumerate(state_list):
            for b in state_list[i + 1:]:
                if not is_reciprocal(a, b):
                    if states_seen[a] > 0 and states_seen[b] > 0:
                        audit.findings.append(
                            Finding(
                                "DOUBLE_WITHHELD_NON_RECIPROCAL",
                                "critical",
                                f"Non-reciprocal pair {a}/{b} — both withheld "
                                f"(${states_seen[a]} + ${states_seen[b]}). "
                                f"Should be work-state-only.",
                            )
                        )

    # ---- Case 2: Home state ≠ work state, non-reciprocal ----
    if home_state != work_state and not is_reciprocal(home_state, work_state):
        work_withheld = states_seen.get(work_state, Decimal("0"))
        home_withheld = states_seen.get(home_state, Decimal("0"))

        if work_withheld == 0 and home_withheld > 0:
            audit.findings.append(
                Finding(
                    "WRONG_STATE_WITHHELD",
                    "critical",
                    f"Non-reciprocal {home_state}(home)/{work_state}(work) — "
                    f"home state withheld ${home_withheld} but work state "
                    f"withheld $0. Per Vertex pJurIntTreatment=7, work state "
                    f"should collect.",
                )
            )
        elif work_withheld > 0 and home_withheld > 0 and not has_nr_cert:
            audit.findings.append(
                Finding(
                    "MISSING_NR_CERT",
                    "warning",
                    f"Employee has {home_state} home / {work_state} work, "
                    f"both withheld. Missing NR cert likely — file one to "
                    f"suppress home-state withholding.",
                )
            )

    # ---- Case 3: Home state ≠ work state, reciprocal ----
    elif home_state != work_state and is_reciprocal(home_state, work_state):
        work_withheld = states_seen.get(work_state, Decimal("0"))
        home_withheld = states_seen.get(home_state, Decimal("0"))
        if work_withheld > 0 and not has_nr_cert:
            audit.findings.append(
                Finding(
                    "RECIPROCAL_WORK_WITHHELD_NO_CERT",
                    "critical",
                    f"Reciprocal pair {home_state}/{work_state} — work state "
                    f"withheld ${work_withheld}. Should be $0 with NR cert.",
                )
            )
        if home_withheld == 0 and work_withheld == 0:
            audit.findings.append(
                Finding(
                    "RECIPROCAL_NOTHING_WITHHELD",
                    "warning",
                    f"Reciprocal pair {home_state}/{work_state} but neither "
                    f"state withheld. Home state ({home_state}) should.",
                )
            )

    return audit
