"""Vendor submission routing and jurisdiction scoping service under VND-001.

Pure service functions to route vendor self-scan evaluation results to the appropriate
officer tier and determine inspection visit requirements.

Import rule: vendor/ may import from app.contracts, app.core, and itself.
Nothing else — no pipeline, no other modules/.
"""

from typing import Any

from pydantic import Field
from sqlalchemy import Select

from app.contracts import ContractModel, Verdict
from app.core.rbac import Jurisdiction, Principal, RoleTier, scope_to_jurisdiction


class RoutingDecision(ContractModel):
    """Routing outcome for an evaluated vendor submission.

    Specifies the target officer tier, whether an on-site physical inspection visit is
    required, and whether action is required (or routes as informational).
    """

    target_tier: RoleTier = Field(
        description="The structural enforcement tier whose queue receives this outcome.",
    )
    requires_visit: bool = Field(
        description="Whether an on-site physical inspection visit is mandated.",
    )
    action_required: bool = Field(
        description="True if the result flags for officer action; False if purely informational.",
    )

    @property
    def officer_tier(self) -> RoleTier:
        """Alias for target_tier."""
        return self.target_tier

    @property
    def tier(self) -> RoleTier:
        """Alias for target_tier."""
        return self.target_tier

    @property
    def flags_for_action(self) -> bool:
        """Alias for action_required."""
        return self.action_required

    @property
    def is_informational(self) -> bool:
        """True when the result is informational only and requires no action."""
        return not self.action_required

    def __iter__(self):
        """Allow tuple unpacking as (target_tier, requires_visit)."""
        yield self.target_tier
        yield self.requires_visit

    def __getitem__(self, index: int) -> Any:
        """Allow index access matching tuple unpacking order."""
        return (self.target_tier, self.requires_visit, self.action_required)[index]


# Type aliases for callers using alternate naming conventions
VendorRoutingResult = RoutingDecision
RoutingResult = RoutingDecision


def route_verdict(
    jurisdiction: Jurisdiction,
    verdict: Verdict,
) -> RoutingDecision:
    """Determine routing tier and visit requirement for an evaluated vendor submission.

    Parameters
    ----------
    jurisdiction : Jurisdiction
        Territorial jurisdiction of the vendor establishment (state required,
        region and district optional).
    verdict : Verdict
        Package evaluation verdict: PASS, REVIEW, or POTENTIAL_VIOLATION.

    Returns
    -------
    RoutingDecision
        The destination officer tier, visit requirement flag, and action flag.
    """
    # Derive target tier purely from territorial jurisdiction depth:
    # District inspector when district is pinned, regional when region only,
    # otherwise state-level controller.
    if jurisdiction.district is not None and jurisdiction.district.strip():
        target_tier = RoleTier.DISTRICT
    elif jurisdiction.region is not None and jurisdiction.region.strip():
        target_tier = RoleTier.REGIONAL
    else:
        target_tier = RoleTier.STATE

    # Branch 1: PASS — Informational routing to the territorial officer's queue, no visit
    if verdict == Verdict.PASS:
        return RoutingDecision(
            target_tier=target_tier,
            requires_visit=False,
            action_required=False,
        )

    # Branch 2: REVIEW — Flags for officer action, no physical visit
    elif verdict == Verdict.REVIEW:
        return RoutingDecision(
            target_tier=target_tier,
            requires_visit=False,
            action_required=True,
        )

    # Branch 3: POTENTIAL_VIOLATION — Flags for action and mandates an on-site visit
    # Legible evidence indicates non-compliance. Triggers on-site inspection visit
    # routed to the territorial field inspecting tier.
    elif verdict == Verdict.POTENTIAL_VIOLATION:
        return RoutingDecision(
            target_tier=target_tier,
            requires_visit=True,
            action_required=True,
        )

    else:
        raise ValueError(f"Unrecognized verdict: {verdict!r}")


# Canonical function aliased under alternate calling conventions (single implementation)
route_vendor_submission = route_verdict
route_vendor_result = route_verdict


def scope_vendor_query(
    statement: Select[Any],
    principal: Principal,
    entity: Any,
) -> Select[Any]:
    """Narrow a SQLAlchemy SELECT statement to the territorial scope of the principal.

    Delegates directly to app.core.rbac.scope_to_jurisdiction.
    """
    return scope_to_jurisdiction(statement, principal, entity)


__all__ = [
    "RoutingDecision",
    "RoutingResult",
    "VendorRoutingResult",
    "route_vendor_result",
    "route_vendor_submission",
    "route_verdict",
    "scope_to_jurisdiction",
    "scope_vendor_query",
]
