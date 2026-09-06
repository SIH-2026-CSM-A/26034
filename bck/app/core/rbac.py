"""The enforcement hierarchy, as data.

Legal Metrology enforcement is territorial: an officer's authority runs over a named
area and stops at its edge. Three levels of officer, each scoped one level narrower than
the one above. That shape is fixed by the department's structure, so it is modelled
here as a single ordered enum — declaration order *is* the hierarchy and each member's
value *is* the jurisdiction column it pins. A fourth level would be one more member, not
one more permission function.

What is **not** fixed is what each level is called. Nomenclature varies by state and the
pilot state is not chosen, so every designation string lives in
:class:`app.core.config.Settings` and nothing in this module knows one. A check that
compared against the word "Inspector" would break the first time a state used a different
title; a check that compares tiers does not.

This module holds no FastAPI and no configuration. It is importable by anything.
"""

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator
from sqlalchemy import Select

from app.contracts import ContractModel


class RoleTier(StrEnum):
    """The three structural levels of the enforcement hierarchy, broadest first.

    Members are ordered, and the order carries meaning: :attr:`rank` and
    :attr:`scope_fields` are both derived from position, so the "each tier is one level
    narrower than the one above" property cannot drift out of step with the enum.

    Each member's value is the :class:`Jurisdiction` field that tier is pinned to. That
    is deliberate — it makes the tier and the column it filters on the same fact, rather
    than two facts a future edit could separate.
    """

    STATE = "state"
    """Authority over a whole state. The broadest tier; sees every region within it."""

    REGIONAL = "region"
    """Authority over one region of a state. Sees every district within that region."""

    DISTRICT = "district"
    """Authority over one district. The narrowest tier, and the one that does the
    day-to-day inspecting."""

    @property
    def rank(self) -> int:
        """Position in the hierarchy. ``0`` is the broadest tier."""
        return list(RoleTier).index(self)

    @property
    def scope_fields(self) -> tuple[str, ...]:
        """The :class:`Jurisdiction` fields a principal at this tier is pinned to.

        ``STATE`` is pinned to its state only, and so sees every region and district in
        it. ``DISTRICT`` is pinned to all three, and so sees one district.
        """
        return tuple(tier.value for tier in list(RoleTier)[: self.rank + 1])

    def covers(self, other: "RoleTier") -> bool:
        """Whether this tier's authority is at least as broad as ``other``'s.

        The whole permission comparison. There is no ``is_controller()`` or
        ``is_inspector()`` to keep in sync with this.
        """
        return self.rank <= other.rank


class Jurisdiction(ContractModel):
    """The territory an officer's authority runs over.

    Levels below the officer's tier are ``None`` — a state-level officer has no single
    region, and saying so with ``None`` is what lets :func:`scope_to_jurisdiction` filter
    on exactly the levels that are pinned.
    """

    state: str = Field(min_length=1)
    """The state. Every officer has one, at every tier."""

    region: str | None = None
    """The region within the state. Set for regional and district officers only."""

    district: str | None = None
    """The district within the region. Set for district officers only."""


class Principal(ContractModel):
    """An authenticated officer: who they are, at what tier, over what territory.

    Only ever built from a token whose signature has already been verified, or from a
    credential check against configured officers. Nothing in a request body may become a
    ``Principal`` — see :func:`app.core.auth.principal_from_token`.
    """

    subject: str = Field(min_length=1)
    """The officer's username. Carried as the token's ``sub`` claim."""

    tier: RoleTier
    """Which of the three structural levels this officer sits at."""

    jurisdiction: Jurisdiction
    """The territory, filled to exactly the depth ``tier`` requires."""

    @model_validator(mode="after")
    def _jurisdiction_fills_exactly_its_tier(self) -> "Principal":
        """Reject a jurisdiction that does not match the tier, in either direction.

        Load-bearing, not tidiness. A ``DISTRICT`` principal with ``district=None``
        produces a filter with one fewer equality predicate, which silently widens that
        officer's visibility to their whole region. Refusing to construct it at all means
        that widening cannot reach a query.
        """
        pinned = self.tier.scope_fields
        for tier in RoleTier:
            value = getattr(self.jurisdiction, tier.value)
            if tier.value in pinned:
                if value is None or not value.strip():
                    raise ValueError(
                        f"a {self.tier.name} principal must name its {tier.value}",
                    )
            elif value is not None:
                raise ValueError(
                    f"a {self.tier.name} principal must not name a {tier.value}; "
                    f"its authority is not narrowed to one",
                )
        return self


def scope_to_jurisdiction(statement: Select[Any], principal: Principal, entity: Any) -> Select[Any]:
    """Narrow a SELECT to the records inside ``principal``'s jurisdiction.

    One equality predicate per pinned level, ANDed onto the statement. An inspector's
    statement gains three and returns their district; a controller's gains one and
    returns their whole state.

    ``entity`` is the mapped class being selected. If it has no column for a pinned
    level, ``getattr`` raises here rather than quietly producing an unfiltered query.

    The ceiling: this constrains the statement it is handed. A caller that never calls it
    is not scoped, and no permission check elsewhere will catch that. Closing it properly
    means a repository layer that owns the session and applies this on the way past — the
    upgrade path once there is a persistence layer to put it in.
    """
    for field in principal.tier.scope_fields:
        statement = statement.where(
            getattr(entity, field) == getattr(principal.jurisdiction, field)
        )
    return statement
