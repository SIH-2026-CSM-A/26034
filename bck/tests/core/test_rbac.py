"""What the hierarchy promises, proved against a real query.

The failure this file exists to catch is a permission check that looks correct in
isolation while the query it is supposed to guard returns everything anyway. So the
scoping tests here do not ask :func:`scope_to_jurisdiction` what it thinks — they build a
table, put records in it from six different jurisdictions, run the scoped statement
through a session, and assert the wrong ones are **absent** from the rows that come back.

Every test in this file runs once per designation profile (see ``conftest.py``).
"""

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rbac import Jurisdiction, Principal, RoleTier, scope_to_jurisdiction
from tests.core.conftest import (
    CONTROLLER,
    DEPUTY,
    INSPECTOR,
    RECORDS,
    ScanRecord,
    UnscopedRecord,
    visible_ids,
)


def test_an_inspector_sees_their_district_and_no_other(session: Session) -> None:
    assert visible_ids(session, INSPECTOR) == {"mh-pune-satara"}


def test_another_districts_records_are_absent_from_an_inspectors_query(
    session: Session,
) -> None:
    """The criterion, stated as absence rather than as a boolean.

    Neighbouring districts in the same region, a district in another region of the same
    state, and everything in another state — none of it is in the result set.
    """
    visible = visible_ids(session, INSPECTOR)
    for absent in (
        "mh-pune-pune",
        "mh-pune-solapur",
        "mh-nagpur-nagpur",
        "mh-nagpur-wardha",
        "ka-bengaluru-bengaluru",
        "ka-mysuru-mysuru",
    ):
        assert absent not in visible


def test_a_deputy_sees_their_whole_region_and_nothing_outside_it(session: Session) -> None:
    assert visible_ids(session, DEPUTY) == {
        "mh-pune-pune",
        "mh-pune-satara",
        "mh-pune-solapur",
    }


def test_a_controller_sees_their_whole_state_and_no_other_state(session: Session) -> None:
    visible = visible_ids(session, CONTROLLER)
    assert visible == {
        "mh-pune-pune",
        "mh-pune-satara",
        "mh-pune-solapur",
        "mh-nagpur-nagpur",
        "mh-nagpur-wardha",
    }
    assert not {"ka-bengaluru-bengaluru", "ka-mysuru-mysuru"} & visible


def test_every_record_is_reachable_by_someone(session: Session) -> None:
    """Guards the guard: a filter that returned nothing would pass every test above."""
    assert len(session.scalars(select(ScanRecord)).all()) == len(RECORDS)


def test_scoping_a_table_without_a_jurisdiction_column_raises() -> None:
    """Better a loud AttributeError than a silently unfiltered query."""
    with pytest.raises(AttributeError):
        scope_to_jurisdiction(select(UnscopedRecord), INSPECTOR, UnscopedRecord)


def test_tiers_are_ordered_broadest_first() -> None:
    assert [tier.rank for tier in RoleTier] == [0, 1, 2]
    assert RoleTier.STATE.covers(RoleTier.DISTRICT)
    assert not RoleTier.DISTRICT.covers(RoleTier.STATE)
    assert RoleTier.REGIONAL.covers(RoleTier.REGIONAL)


def test_each_tier_pins_one_level_more_than_the_one_above() -> None:
    """The structural invariant, derived from enum order rather than written out."""
    assert RoleTier.STATE.scope_fields == ("state",)
    assert RoleTier.REGIONAL.scope_fields == ("state", "region")
    assert RoleTier.DISTRICT.scope_fields == ("state", "region", "district")


def test_a_district_principal_without_a_district_cannot_be_constructed() -> None:
    """The widening hole, closed at construction.

    A DISTRICT principal with no district would produce a filter one predicate short and
    quietly see the whole region.
    """
    with pytest.raises(ValidationError):
        Principal(
            subject="inspector",
            tier=RoleTier.DISTRICT,
            jurisdiction=Jurisdiction(state="Maharashtra", region="Pune"),
        )


def test_a_controller_carrying_a_district_cannot_be_constructed() -> None:
    with pytest.raises(ValidationError):
        Principal(
            subject="controller",
            tier=RoleTier.STATE,
            jurisdiction=Jurisdiction(state="Maharashtra", region="Pune", district="Satara"),
        )


def test_a_blank_district_is_not_a_district() -> None:
    with pytest.raises(ValidationError):
        Principal(
            subject="inspector",
            tier=RoleTier.DISTRICT,
            jurisdiction=Jurisdiction(state="Maharashtra", region="Pune", district="   "),
        )


def test_designations_come_from_config_and_differ_between_profiles(
    designation_profile: str,
) -> None:
    """Proves the config swap is real, so the runs above are not the same run twice."""
    settings = get_settings()
    named = {tier: settings.designation(tier) for tier in RoleTier}
    assert len(set(named.values())) == len(RoleTier)
    if designation_profile == "alternate":
        assert named[RoleTier.STATE] == "Commissioner, Weights and Measures"
        spoken = " ".join(named.values())
        for default_word in ("Controller", "Deputy", "Inspector"):
            assert default_word not in spoken
    else:
        assert named[RoleTier.STATE] == "Controller of Legal Metrology"
