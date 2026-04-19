"""Guardian 834 renderer — composes the generic writer with Guardian's CG."""

from __future__ import annotations

from ..render import Enrollment, Render834
from .companion import DEFAULT_GUIDE, GuardianCompanionGuide


def render_guardian(
    enrollment: Enrollment,
    *,
    guide: GuardianCompanionGuide | None = None,
) -> str:
    """Render an Enrollment payload to Guardian-flavored 834 5010 text.

    Parameters
    ----------
    enrollment : Enrollment
        Carrier-agnostic enrollment payload produced upstream from PrismHR
        data.
    guide : GuardianCompanionGuide, optional
        Companion-guide overrides. Defaults to `DEFAULT_GUIDE` — suitable for
        local/test runs only; production use MUST pass a guide loaded from
        the per-PEO config store.
    """
    guide = guide or DEFAULT_GUIDE
    # Apply Guardian-specific plan code mapping if provided
    if guide.plan_code_map:
        for enrollee in enrollment.enrollees:
            for cov in enrollee.coverages:
                cov.plan_code = guide.plan_code_map.get(cov.plan_code, cov.plan_code)
            for dep in enrollee.dependents:
                for cov in dep.coverages:
                    cov.plan_code = guide.plan_code_map.get(cov.plan_code, cov.plan_code)

    # Apply guide to the envelope
    enrollment.sender_id = guide.sender_id
    enrollment.receiver_id = guide.receiver_id
    enrollment.production = guide.production

    writer = Render834(
        purpose_code=guide.purpose_code,
        action_code=guide.action_code,
        interchange_version=guide.interchange_version,
        implementation_convention_ref=guide.implementation_convention_ref,
        sender_qualifier=guide.sender_qualifier,
        receiver_qualifier=guide.receiver_qualifier,
    )
    return writer.render(enrollment)
