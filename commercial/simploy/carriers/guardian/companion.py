"""Guardian companion-guide overrides.

Captures the carrier-specific choices Guardian makes on top of the X220A1
standard — qualifier values, sender/receiver IDs, plan-code conventions.
Values here come from the public user guide + the per-case trading-partner
setup letter Guardian issues during onboarding.

Every field has a reasonable default for a test/stage environment; production
values are set per PEO via Settings (never hardcoded into the package).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardianCompanionGuide:
    """Guardian 834 5010 companion-guide values."""

    # Trading partner identifiers
    sender_id: str = "SIMPLOY"
    receiver_id: str = "GUARDIAN"  # Guardian trading-partner ID — override per case
    sender_qualifier: str = "ZZ"   # Guardian typically uses mutually-defined
    receiver_qualifier: str = "ZZ"

    # Transaction envelope
    interchange_version: str = "00501"
    implementation_convention_ref: str = "005010X220A1"

    # Purpose and action codes
    purpose_code: str = "00"       # 00 = original
    action_code: str = "2"          # 2 = change-only (Guardian supports both 2 and 4)

    # Test vs production indicator
    production: bool = False

    # Plan-code map — Guardian's internal plan codes. Keys are Simploy-side
    # plan codes (from PrismHR), values are Guardian's codes. Overridden by the
    # assistant config per client.
    plan_code_map: dict[str, str] | None = None


DEFAULT_GUIDE = GuardianCompanionGuide()
