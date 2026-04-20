"""BCBS Michigan 834 renderer — generic writer + BCBS MI CG overrides."""

from __future__ import annotations

import copy
from dataclasses import replace

from ..render import Enrollment, Render834
from .companion import DEFAULT_GUIDE, BCBSMiCompanionGuide


def render_bcbs_mi(
    enrollment: Enrollment,
    *,
    guide: BCBSMiCompanionGuide | None = None,
) -> str:
    """Render an Enrollment payload to BCBS Michigan 834 5010 text.

    Caller's Enrollment is never mutated (deep-copied).
    """
    guide = guide or DEFAULT_GUIDE
    working = copy.deepcopy(enrollment)

    if guide.plan_code_map:
        for enrollee in working.enrollees:
            for cov in enrollee.coverages:
                cov.plan_code = guide.plan_code_map.get(cov.plan_code, cov.plan_code)
            for dep in enrollee.dependents:
                for cov in dep.coverages:
                    cov.plan_code = guide.plan_code_map.get(cov.plan_code, cov.plan_code)

    working = replace(
        working,
        sender_id=guide.sender_id,
        receiver_id=guide.receiver_id,
        production=guide.production,
    )

    writer = Render834(
        purpose_code=guide.purpose_code,
        action_code=guide.action_code,
        interchange_version=guide.interchange_version,
        implementation_convention_ref=guide.implementation_convention_ref,
        sender_qualifier=guide.sender_qualifier,
        receiver_qualifier=guide.receiver_qualifier,
    )
    return writer.render(working)
