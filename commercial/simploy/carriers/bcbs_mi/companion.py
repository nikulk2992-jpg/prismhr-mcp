"""BCBS Michigan 834 companion-guide values.

Regional-plan carrier; uses BCBS Michigan's trading-partner setup.
Notable specifics vs Guardian default:
- sender_id = "SIMPLOY-MI" (BCBS MI trading-partner per Simploy case)
- receiver_id = "BCBSM" (BCBS Michigan trading-partner ID)
- Typically accepts both change-only (action 2) and full-refresh (4);
  BCBS MI recommends weekly full refresh for groups < 200 lives.
- HD03 insurance line codes used: HLT (medical), DEN (dental),
  VIS (vision), RX (prescription carveout if applicable).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BCBSMiCompanionGuide:
    sender_id: str = "SIMPLOY-MI"
    receiver_id: str = "BCBSM"
    sender_qualifier: str = "ZZ"
    receiver_qualifier: str = "ZZ"
    interchange_version: str = "00501"
    implementation_convention_ref: str = "005010X220A1"
    purpose_code: str = "00"
    action_code: str = "2"
    production: bool = False
    plan_code_map: dict[str, str] | None = None


DEFAULT_GUIDE = BCBSMiCompanionGuide()
