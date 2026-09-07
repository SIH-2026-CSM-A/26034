"""The discriminated union of rule conditions the YAML store may express.

One variant per shape of legal obligation, discriminated on ``kind``. A rule carries
exactly one. Adding an obligation means adding a variant here and a rule to the store;
it never means widening an existing variant to mean two things.

Rule 8 and Rule 9 are the clearest case. Rule 8 governs *where* a declaration appears and
Rule 9 governs *how* it appears — different obligations, different evidence, different
consequences — so they get :class:`PlacementCondition` and :class:`FreeSpaceCondition`
against :class:`DeclarationMannerCondition` and :class:`OuterContainerCondition`, and are
never collapsed into one check.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import (
    ConstituentSimilarity,
    NonEmptyText,
    NonNegativeDecimal,
    OverrideTarget,
    PackageType,
    PositiveDecimal,
    ProductCategory,
    StrictRuleModel,
)


class DeclarationRequiredCondition(StrictRuleModel):
    """Describe mandatory declarations and their source-defined exceptions."""

    kind: Literal["declaration_required"]
    declarations: tuple[NonEmptyText, ...] = Field(min_length=1)
    exceptions: tuple[NonEmptyText, ...]


class TableBand(StrictRuleModel):
    """Describe one inclusive-upper-bound Rule 7 Table-I band."""

    minimum_area_exclusive_cm2: NonNegativeDecimal | None
    maximum_area_inclusive_cm2: PositiveDecimal | None
    normal_minimum_height_mm: PositiveDecimal
    moulded_minimum_height_mm: PositiveDecimal


class TableHeightCondition(StrictRuleModel):
    """Describe the complete Rule 7 Table-I height lookup."""

    kind: Literal["table_height"]
    bands: tuple[TableBand, ...] = Field(min_length=1)


class WidthRatioCondition(StrictRuleModel):
    """Describe the Rule 7(3) width-to-height threshold and exceptions."""

    kind: Literal["width_ratio"]
    minimum_width_to_height_ratio: PositiveDecimal
    exempt_characters: tuple[NonEmptyText, ...] = Field(min_length=1)


class PdpAreaCondition(StrictRuleModel):
    """Describe Rule 7(4) PDP formulas and excluded package regions."""

    kind: Literal["pdp_area"]
    cylindrical_multiplier: PositiveDecimal
    other_shape_multiplier: PositiveDecimal
    allow_legally_identified_pdp_area: bool
    excluded_regions: tuple[NonEmptyText, ...] = Field(min_length=1)


class OtherLawCarveOutCondition(StrictRuleModel):
    """Describe Rule 7(5) declarations whose sizing remains preserved."""

    kind: Literal["other_law_carve_out"]
    preserved_declarations: tuple[NonEmptyText, ...] = Field(min_length=1)


class PlacementCondition(StrictRuleModel):
    """Describe Rule 8(1) — the panel every declaration must appear on.

    Placement only. What the declaration must *look like* once it is there is Rule 9 and
    a different condition.
    """

    kind: Literal["placement"]
    required_location: Literal["principal_display_panel"]


class FreeSpaceCondition(StrictRuleModel):
    """Describe the Rule 8(1) proviso clearance around the quantity declaration.

    Both multiples are expressed against the height of the numeral in the declaration,
    which is how the rule states them, so the requirement scales with the package instead
    of being frozen to one millimetre figure. This is geometrically measurable, and the
    rule carrying this condition therefore states a *measurement* evidence requirement
    rather than a text span.
    """

    kind: Literal["free_space"]
    above_below_multiple_of_numeral_height: PositiveDecimal
    left_right_multiple_of_numeral_height: PositiveDecimal


class DeclarationMannerCondition(StrictRuleModel):
    """Describe Rule 9(1) — how a declaration must be rendered, not where."""

    kind: Literal["declaration_manner"]
    legible_and_prominent: Literal[True]
    contrasting_colour_declarations: tuple[NonEmptyText, ...] = Field(min_length=1)
    contrast_exempt_surfaces: tuple[NonEmptyText, ...]
    handwritten_must_be_clear_unambiguous_and_legible: bool


class OuterContainerCondition(StrictRuleModel):
    """Describe Rule 9(3) — declarations on an outer container or wrapper."""

    kind: Literal["outer_container"]
    outer_must_carry_all_declarations: Literal[True]
    transparent_outer_exempt_when_inner_readable: bool
    inner_declarations_not_required_when_outer_complete: bool


class PackageDefinitionCondition(StrictRuleModel):
    """Describe a package composition defined by the rules.

    A definition classifies; it does not itself propose a violation. The rule carrying it
    therefore states ``REVIEW`` severity, because failing to *be* a group package is not
    a finding — being one and then being judged against the wrong obligations is.

    The last two flags record only what a clause actually states. Rule 2(kc) alone
    describes constituents that are "individual packaged or labelled pieces" saleable
    "either in individual pieces or the package as a whole"; Rules 2(ka) and 2(kb) say
    neither, so both are ``false`` there. That pair is what separates a multi-piece
    package from a group package in the one way that matters downstream — a piece that
    is separately labelled and separately saleable has to stand as a retail package in
    its own right, which is a different question from what the outer wrapper carries.
    **Which declarations follow from that is not stated in G.S.R. 722(E) and is not
    encoded here.**
    """

    kind: Literal["package_definition"]
    package_type: PackageType
    intended_for_retail_sale: Literal[True]
    minimum_constituent_count: int = Field(ge=2)
    constituent_similarity: ConstituentSimilarity
    constituents_individually_packaged_or_labelled: bool
    retail_sale_of_individual_pieces_permitted: bool
    illustrations: tuple[NonEmptyText, ...] = Field(min_length=1)


class SectorOverrideCondition(StrictRuleModel):
    """Describe deterministic routing of named obligations to another framework.

    ``sector`` is a :class:`~app.modules.rules.base.ProductCategory` and ``overrides``
    names the obligations that leave the packaged rules. Both are open vocabularies
    rather than a single hard-coded sector, so a new sector is a rule in the store and
    not a branch in the evaluator.

    ``package_type`` narrows an override to one kind of package. ``None`` means any
    package type, which is what the sector-wide provisos state and how every override
    behaves by default. The proviso to Rule 2(kc) is the case that needs it: it hands
    food articles to the Food Safety and Standards Act, 2006 *for multi-piece packages*,
    and an override that ignored the qualifier would fire on every food package and
    produce a routing the gazette does not support.

    ``disapplies_rule_33_relaxation`` is separate from ``overrides`` on purpose. The
    other entries move an obligation elsewhere; this one removes a *relaxation* that
    would otherwise be available. Folding it into the same list would make "routed" and
    "no longer excused" indistinguishable to anything reading the record back.
    """

    kind: Literal["sector_override"]
    sector: ProductCategory
    controlling_framework: NonEmptyText
    package_type: PackageType | None = None
    overrides: tuple[OverrideTarget, ...] = Field(min_length=1)
    disapplies_rule_33_relaxation: bool = False


class EcommerceFilterCondition(StrictRuleModel):
    """Describe the country-of-origin filter required for imported listings."""

    kind: Literal["ecommerce_country_of_origin_filter"]
    imported_products_only: Literal[True]
    searchable: Literal[True]
    sortable: Literal[True]


class ChapterScopeCondition(StrictRuleModel):
    """Describe Rule 3 — the packages Chapter II does not reach.

    The one condition that speaks to whether the other rules apply at all rather than to
    what a package must bear. It is stated negatively in the gazette and is encoded
    negatively here: these are thresholds *above which* the chapter stops applying.

    ``_inclusive_`` in each name is the boundary, and it is load-bearing. Rule 3(a)
    excludes a quantity of "more than 25 kilogram or 25 litre", so 25 kilogram exactly is
    still inside Chapter II. The same convention as
    :attr:`TableBand.maximum_area_inclusive_cm2`.

    ``not_for_retail_sale_marker`` is the phrase Rule 2(bb) and Rule 2(bc) *as substituted*
    require an industrial or institutional package to bear. It is carried here, on the
    scope condition, because it is the only limb of Rule 3(c) that a label can evidence —
    but it belongs textually to clause 2(bb)/2(bc) and not to Rule 3, and the rule
    carrying this condition says so in its ``clause_ref``.
    """

    kind: Literal["chapter_ii_scope"]
    maximum_weight_inclusive_kg: PositiveDecimal
    maximum_volume_inclusive_l: PositiveDecimal
    bagged_commodities: tuple[NonEmptyText, ...] = Field(min_length=1)
    bagged_maximum_inclusive_kg: PositiveDecimal
    not_for_retail_sale_marker: NonEmptyText


class NumericConstraint(StrictRuleModel):
    """Keep rounding-increment and tolerance semantics explicitly separate."""

    kind: Literal["numeric_constraint"]
    rounding_increment: PositiveDecimal | None = None
    tolerance: NonNegativeDecimal | None = None

    @model_validator(mode="after")
    def require_exactly_one_numeric_concept(self) -> NumericConstraint:
        """Require one comparison concept so rounding cannot alias tolerance."""
        values = (self.rounding_increment, self.tolerance)
        if sum(value is not None for value in values) != 1:
            raise ValueError("exactly one of rounding_increment or tolerance is required")
        return self


RuleCondition = Annotated[
    DeclarationRequiredCondition
    | TableHeightCondition
    | WidthRatioCondition
    | PdpAreaCondition
    | OtherLawCarveOutCondition
    | PlacementCondition
    | FreeSpaceCondition
    | DeclarationMannerCondition
    | OuterContainerCondition
    | PackageDefinitionCondition
    | SectorOverrideCondition
    | EcommerceFilterCondition
    | ChapterScopeCondition
    | NumericConstraint,
    Field(discriminator="kind"),
]
