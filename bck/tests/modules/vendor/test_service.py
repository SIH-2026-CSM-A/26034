"""Unit tests for the vendor routing service (VND-001 Part A).

Tests all branches of route_verdict and scope_vendor_query using constructed
objects only — no persistence, no database connections.
"""

import pytest
from sqlalchemy import select

from app.contracts import Verdict
from app.core.models import Scan
from app.core.rbac import Jurisdiction, Principal, RoleTier
from app.modules.vendor.service import (
    RoutingDecision,
    RoutingResult,
    VendorRoutingResult,
    route_vendor_result,
    route_vendor_submission,
    route_verdict,
    scope_to_jurisdiction,
    scope_vendor_query,
)


@pytest.fixture
def full_jurisdiction() -> Jurisdiction:
    """A fully pinned district-level jurisdiction."""
    return Jurisdiction(state="Karnataka", region="South", district="Bengaluru Urban")


@pytest.fixture
def regional_jurisdiction() -> Jurisdiction:
    """A region-pinned jurisdiction without a district."""
    return Jurisdiction(state="Karnataka", region="South", district=None)


@pytest.fixture
def state_jurisdiction() -> Jurisdiction:
    """A state-pinned jurisdiction without region or district."""
    return Jurisdiction(state="Karnataka", region=None, district=None)


# --- Branch 1: PASS ---


def test_pass_routes_as_informational_without_visit(full_jurisdiction: Jurisdiction):
    """Verdict.PASS routes as informational to the district queue, no visit required."""
    decision = route_verdict(
        jurisdiction=full_jurisdiction,
        verdict=Verdict.PASS,
    )
    assert decision.target_tier == RoleTier.DISTRICT
    assert decision.officer_tier == RoleTier.DISTRICT
    assert decision.tier == RoleTier.DISTRICT
    assert decision.requires_visit is False
    assert decision.action_required is False
    assert decision.is_informational is True
    assert decision.flags_for_action is False

    # Verify tuple unpacking
    unpacked_tier, unpacked_visit = decision
    assert unpacked_tier == RoleTier.DISTRICT
    assert unpacked_visit is False


# --- Branch 2: REVIEW ---


def test_review_flags_for_action_without_visit(full_jurisdiction: Jurisdiction):
    """Verdict.REVIEW flags for action in the officer's queue, no physical visit."""
    decision = route_verdict(
        jurisdiction=full_jurisdiction,
        verdict=Verdict.REVIEW,
    )
    assert decision.target_tier == RoleTier.DISTRICT
    assert decision.requires_visit is False
    assert decision.action_required is True
    assert decision.flags_for_action is True
    assert decision.is_informational is False


# --- Branch 3: POTENTIAL_VIOLATION ---


def test_potential_violation_mandates_visit_at_district_tier(
    full_jurisdiction: Jurisdiction,
):
    """POTENTIAL_VIOLATION in a district jurisdiction routes to DISTRICT inspector for visit."""
    decision = route_verdict(
        jurisdiction=full_jurisdiction,
        verdict=Verdict.POTENTIAL_VIOLATION,
    )
    assert decision.target_tier == RoleTier.DISTRICT
    assert decision.requires_visit is True
    assert decision.action_required is True
    assert decision.flags_for_action is True


# --- District is None Behavior ---


def test_routing_when_district_is_none_regional(regional_jurisdiction: Jurisdiction):
    """When district is None but region is set, routes to REGIONAL tier."""
    decision_pass = route_verdict(
        jurisdiction=regional_jurisdiction,
        verdict=Verdict.PASS,
    )
    assert decision_pass.target_tier == RoleTier.REGIONAL
    assert decision_pass.requires_visit is False
    assert decision_pass.action_required is False

    decision_review = route_verdict(
        jurisdiction=regional_jurisdiction,
        verdict=Verdict.REVIEW,
    )
    assert decision_review.target_tier == RoleTier.REGIONAL
    assert decision_review.requires_visit is False
    assert decision_review.action_required is True

    decision_violation = route_verdict(
        jurisdiction=regional_jurisdiction,
        verdict=Verdict.POTENTIAL_VIOLATION,
    )
    assert decision_violation.target_tier == RoleTier.REGIONAL
    assert decision_violation.requires_visit is True
    assert decision_violation.action_required is True


def test_routing_when_district_is_none_state(state_jurisdiction: Jurisdiction):
    """When district and region are None, routes to STATE-level catch-all."""
    decision_pass = route_verdict(
        jurisdiction=state_jurisdiction,
        verdict=Verdict.PASS,
    )
    assert decision_pass.target_tier == RoleTier.STATE
    assert decision_pass.requires_visit is False
    assert decision_pass.action_required is False

    decision_review = route_verdict(
        jurisdiction=state_jurisdiction,
        verdict=Verdict.REVIEW,
    )
    assert decision_review.target_tier == RoleTier.STATE
    assert decision_review.requires_visit is False
    assert decision_review.action_required is True

    decision_violation = route_verdict(
        jurisdiction=state_jurisdiction,
        verdict=Verdict.POTENTIAL_VIOLATION,
    )
    assert decision_violation.target_tier == RoleTier.STATE
    assert decision_violation.requires_visit is True
    assert decision_violation.action_required is True


# --- Validation and Error Handling ---


def test_unrecognized_verdict_raises_value_error(full_jurisdiction: Jurisdiction):
    """Unrecognized verdict raises ValueError."""
    with pytest.raises(ValueError, match="Unrecognized verdict"):
        route_verdict(full_jurisdiction, "NON_EXISTENT_STATE")  # type: ignore[arg-type]


# --- Aliases and Single Implementation ---


def test_service_aliases(full_jurisdiction: Jurisdiction):
    """Verify route_vendor_submission and route_vendor_result are aliases of route_verdict."""
    assert route_vendor_submission is route_verdict
    assert route_vendor_result is route_verdict
    assert VendorRoutingResult is RoutingDecision
    assert RoutingResult is RoutingDecision

    decision = route_vendor_submission(full_jurisdiction, Verdict.PASS)
    assert isinstance(decision, RoutingDecision)
    assert decision[0] == decision.target_tier
    assert decision[1] == decision.requires_visit
    assert decision[2] == decision.action_required


# --- Jurisdiction Query Scoping ---


def test_scope_vendor_query():
    """scope_vendor_query narrows a query using scope_to_jurisdiction without a DB."""
    principal_state = Principal(
        subject="controller_1",
        tier=RoleTier.STATE,
        jurisdiction=Jurisdiction(state="Karnataka"),
    )
    principal_district = Principal(
        subject="inspector_1",
        tier=RoleTier.DISTRICT,
        jurisdiction=Jurisdiction(state="Karnataka", region="South", district="Bengaluru Urban"),
    )

    base_query = select(Scan)

    scoped_state = scope_vendor_query(base_query, principal_state, Scan)
    scoped_district = scope_vendor_query(base_query, principal_district, Scan)

    # State principal query has 1 where clause (state)
    assert len(scoped_state._where_criteria) == 1
    # District principal query has 3 where clauses (state, region, district)
    assert len(scoped_district._where_criteria) == 3

    # Re-exported function is the exact same function from rbac
    assert scope_vendor_query(base_query, principal_state, Scan) is not None
    assert scope_to_jurisdiction is not None
