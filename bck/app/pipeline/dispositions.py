"""What kind of obligation each rule states, and which rules a sector can carve out.

The vocabulary the rest of the pipeline's judgement is written in. Nothing here builds a
finding; everything here decides what *sort* of thing a rule is, so that the modules which
do build findings carry no classification logic of their own.

Kept apart from :mod:`app.pipeline.findings` because these tables are the part a reviewer
checks line by line against the rule store. A wrong entry in one of them is a whole class
of rule silently unevaluated, and that is easier to see in a file that is only tables.
"""

from collections.abc import Sequence
from enum import StrEnum

from app.contracts import DeclarationField, FieldState
from app.modules.rules import OverrideTarget, RuleDefinition, Verdict
from app.pipeline.rule_snapshot import declaration_fields

FIELD_STATE_FROM_VERDICT: dict[Verdict, FieldState] = {
    Verdict.PASS: FieldState.PASS,
    Verdict.REVIEW: FieldState.REVIEW_REQUIRED,
    Verdict.POTENTIAL_VIOLATION: FieldState.FAIL,
}
"""``rules.Verdict`` to the per-field state it becomes.

Total over ``rules.Verdict`` and deliberately **not** total over ``FieldState``:
INSUFFICIENT_EVIDENCE and NOT_APPLICABLE have no source member here because no evaluator
returns them. They are reached by *not* evaluating a rule — a declaration nobody could
read, a refused measurement, an unconfirmed category — and that is the structure which
keeps them out of any expression that also produces FAIL. A mapping containing all five
would be one careless edit from routing "we could not read the label" to "the label is
wrong".

A guard test fails the day ``rules.Verdict`` gains a member, because the alternative is a
``KeyError`` surfacing at verdict assembly on a real scan.
"""


class Disposition(StrEnum):
    """How this pipeline treats one shape of rule condition."""

    DECLARATION = "declaration"
    """The rule requires a declaration to be borne. Evidence is extracted text."""

    MEASUREMENT = "measurement"
    """The rule states a physical threshold. Evidence is a calibrated measurement."""

    OBSERVATION = "observation"
    """The rule governs how or where a declaration appears. Evidence is an observation of
    the package that this pipeline does not gather yet."""

    LISTING = "listing"
    """The duty is owed by an e-commerce entity about a listing, not by the package."""

    NOT_AN_OBLIGATION = "not_an_obligation"
    """Routing metadata, a definition, or a method of computation — a sector override, a
    package definition, a carve-out, Rule 7(4)'s panel-area formulas. It shapes how other
    rules apply and states no duty of its own, so it produces no finding.

    The one disposition that legitimately emits nothing, which is why it is named rather
    than left as a fall-through. Rule 7(4) is the case worth spelling out: it says how to
    compute a principal display panel's area, which is an input to the Table-I lookup and
    not something a package can contravene.
    """


CONDITION_DISPOSITION: dict[str, Disposition] = {
    "declaration_required": Disposition.DECLARATION,
    "table_height": Disposition.MEASUREMENT,
    "width_ratio": Disposition.MEASUREMENT,
    "free_space": Disposition.MEASUREMENT,
    "pdp_area": Disposition.NOT_AN_OBLIGATION,
    "placement": Disposition.OBSERVATION,
    "declaration_manner": Disposition.OBSERVATION,
    "outer_container": Disposition.OBSERVATION,
    "ecommerce_country_of_origin_filter": Disposition.LISTING,
    "sector_override": Disposition.NOT_AN_OBLIGATION,
    "package_definition": Disposition.NOT_AN_OBLIGATION,
    "chapter_ii_scope": Disposition.NOT_AN_OBLIGATION,
    "other_law_carve_out": Disposition.NOT_AN_OBLIGATION,
    "numeric_constraint": Disposition.NOT_AN_OBLIGATION,
}
"""Every ``RuleCondition`` variant's ``kind``, and what this pipeline does with it.

Exhaustive by test: a variant added to ``app.modules.rules.conditions`` with no entry here
goes red rather than quietly producing no finding for every rule that uses it.
"""

SECTOR_GOVERNED_RULES: dict[str, OverrideTarget] = {
    "R6-1-A": OverrideTarget.MANUFACTURER_DECLARATION,
    "R6-1-D": OverrideTarget.DATE_DECLARATION,
    "R6-1-D-GSR-722E": OverrideTarget.DATE_DECLARATION,
    "R7-2-TABLE-I": OverrideTarget.TABLE_HEIGHT,
    "R7-3-WIDTH-RATIO": OverrideTarget.WIDTH_RATIO,
    "R8-1-PDP-PLACEMENT": OverrideTarget.PDP_DECLARATION,
    "R2-KA-COMBINATION-PACKAGE": OverrideTarget.PACKAGE_DEFINITION,
    "R2-KB-GROUP-PACKAGE": OverrideTarget.PACKAGE_DEFINITION,
    "R2-KC-MULTI-PIECE-PACKAGE": OverrideTarget.PACKAGE_DEFINITION,
}
"""Which packaged rule each sector override target actually moves.

The store says an override redirects ``table_height``; it does not say that
``R7-2-TABLE-I`` is the rule stating it. That link lives here, and it is what lets an
unconfirmed product category hold back exactly the obligations a sector could carve out
rather than every rule or none of them.

A guard test asserts every target named by an active override in the store appears as a
value here, so a new sector override cannot arrive with nothing gated behind it.
"""

RULE_DECLARATION_SCOPE: dict[str, tuple[DeclarationField, ...]] = {
    "R8-1-FREE-SPACE": (DeclarationField.NET_QUANTITY,),
}
"""Rules whose own text narrows them to particular declarations.

Rule 8(1)'s proviso states its clearance around the *quantity* declaration, and the
store's evidence requirement for that rule says so in as many words. A rule absent from
this mapping governs every declaration the store requires, which is derived from the store
rather than restated here.
"""


def required_declarations(rules: Sequence[RuleDefinition]) -> tuple[DeclarationField, ...]:
    """Every declaration the supplied rules require, in store order, de-duplicated.

    Derived rather than listed: the declarations a sizing or manner rule governs are the
    declarations the store obliges a package to bear, so the two cannot drift apart. Add a
    Rule 6(1) obligation to the store and Rule 7 and Rule 9 start governing it with no
    edit here.
    """
    seen: list[DeclarationField] = []
    for rule in rules:
        if CONDITION_DISPOSITION[rule.conditions.kind] is Disposition.DECLARATION:
            seen.extend(declaration_fields(rule))
    return tuple(dict.fromkeys(seen))


def governed_declarations(
    rule: RuleDefinition, fallback: tuple[DeclarationField, ...]
) -> tuple[DeclarationField, ...]:
    """The declarations one rule governs — its own narrowing, or every required one."""
    return RULE_DECLARATION_SCOPE.get(rule.rule_id, fallback)


def disposition_of(rule: RuleDefinition) -> Disposition:
    """What sort of obligation ``rule`` states.

    Raises rather than defaulting. A rule that produces no finding is an obligation nobody
    checked, and downstream that is indistinguishable from a package with nothing wrong
    with it — the same reason
    :class:`~app.pipeline.rule_snapshot.UnmappedDeclarationError` raises.
    """
    try:
        return CONDITION_DISPOSITION[rule.conditions.kind]
    except KeyError:
        raise UnknownConditionError(
            f"rule {rule.rule_id} has condition kind {rule.conditions.kind!r}, which has "
            f"no disposition; add it to CONDITION_DISPOSITION rather than letting every "
            f"rule that uses it produce no finding"
        ) from None


class UnknownConditionError(LookupError):
    """A rule carries a condition kind with no stated disposition."""
