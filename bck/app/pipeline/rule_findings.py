"""One rule, the evidence available, and the findings that follow.

Each function here answers the same question for a different shape of obligation: given
this rule and what we actually managed to observe, what may we say about each declaration
it governs? They are pure and take no session, no clock and no image, so every branch
below is reachable in a test without a database or a model.

**The ordering that matters.** :func:`sector_findings` runs before any evaluator. A sector
override is a carve-out rather than a stricter path — G.S.R. 778(E) does not raise the bar
for a medical device, it moves character height, width and the panel declaration to the
Medical Devices Rules, 2017 outright — so whether the packaged rules govern an obligation
at all is settled first. Evaluating a carved-out obligation and filtering the answer
afterwards would produce a finding under a provision that does not apply to the package.

**The distinction that matters.** A missing declaration is INSUFFICIENT_EVIDENCE when we
never obtained the evidence to look for it, and a finding about the package when we
looked. Those are different branches reached from different inputs, never a state chosen
by widening a condition.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from app.contracts import (
    DeclarationField,
    FieldFinding,
    FieldState,
    MeasurementResult,
    NormalisedField,
)
from app.modules.rules import (
    ProductCategory,
    RuleDefinition,
    Verdict,
    controlling_framework,
    evaluate_rule,
)
from app.pipeline.dispositions import FIELD_STATE_FROM_VERDICT, SECTOR_GOVERNED_RULES
from app.pipeline.rule_snapshot import snapshot_from_rule

UNCONFIRMED_CATEGORY_REASON = (
    "the product category has not been confirmed, and a sector rule may move this "
    "obligation to another framework. Confirm the category to evaluate it — an "
    "unconfirmed category is not a finding about the package."
)
"""Why a sector-gated obligation was not evaluated.

Named rather than inline because the test suite needs to recognise a finding the gate
produced. A test that selects a sector-gated rule's findings without confirming a category
gets only findings carrying this reason, and is then asserting about the gate rather than
about whatever builder it meant to exercise —
``tests/pipeline/sector_gate.findings_for_rule`` refuses that shape by looking for this
exact text, so the two cannot drift apart into a substring match that silently stops
matching.
"""


@dataclass(frozen=True)
class EvidenceContext:
    """Everything observed about one scan, and what an absence of evidence means for it.

    Passed whole rather than as loose arguments so that a new kind of evidence does not
    change the signature of every builder, and so no builder can be called with half of
    it.
    """

    rule_set_version: str
    evaluation_date: date
    declared: Mapping[DeclarationField, tuple[NormalisedField, ...]]
    """Declarations resolved to canonical values, by obligation.

    A *tuple* per obligation, not one value. Rule 6(1)(a) is a single obligation covering
    manufacturer, packer and importer — and by Explanation II a marketer or brand owner —
    so a package bearing "Manufactured by" and "Marketed by" yields two bound declarations
    against one obligation. ``app.modules.extraction.bind_spans`` returns both and says in
    as many words not to pick one arbitrarily; collapsing them here would do exactly that,
    and would drop an address an officer may need to see.
    """

    measurements: Mapping[str, MeasurementResult]
    """Measurement results keyed by the rule condition kind that needs them."""

    product_category: ProductCategory | None
    """The officer's *confirmed* category. ``None`` routes no sector override."""

    source_is_listing: bool
    """Whether this scan came from a catalogue record rather than a photograph."""

    unreadable_reason: str | None
    """What a declaration's absence means. A reason here says the evidence to look for it
    was never obtained, so an absence is INSUFFICIENT_EVIDENCE carrying this text.
    ``None`` says we looked, so an absence is a finding about the package."""


def finding(
    rule: RuleDefinition,
    field: DeclarationField,
    state: FieldState,
    reason: str,
    context: EvidenceContext,
    **values: str | tuple[str, ...] | None,
) -> FieldFinding:
    """One finding, carrying the rule as it stood at this moment, by value."""
    return FieldFinding(
        field=field,
        state=state,
        rule_snapshot=snapshot_from_rule(rule, context.rule_set_version),
        reason=reason,
        **values,  # type: ignore[arg-type]
    )


def sector_findings(
    rule: RuleDefinition, fields: tuple[DeclarationField, ...], context: EvidenceContext
) -> list[FieldFinding] | None:
    """Findings that settle a rule before evaluation, or ``None`` to carry on.

    Returns findings in two cases and only two: the category is unconfirmed and a sector
    could move this obligation, or the category is confirmed and a sector has moved it.
    """
    target = SECTOR_GOVERNED_RULES.get(rule.rule_id)
    if target is None:
        return None

    if context.product_category is None:
        # Never FAIL: we do not yet know whether this obligation belongs to the packaged
        # rules at all, so nothing has been established about the package.
        return [
            finding(
                rule,
                field,
                FieldState.INSUFFICIENT_EVIDENCE,
                UNCONFIRMED_CATEGORY_REASON,
                context,
            )
            for field in fields
        ]

    routed = controlling_framework(target, context.product_category, context.evaluation_date)
    if routed is None:
        return None

    # A statutory carve-out removes the duty. NOT_APPLICABLE is neither a lesser PASS nor
    # a softened FAIL: the obligation does not exist for this package under these rules.
    return [
        finding(
            rule,
            field,
            FieldState.NOT_APPLICABLE,
            f"this obligation is governed by {routed.controlling_framework} for "
            f"{routed.sector} packages, per rule {routed.rule_id}. The packaged rules do "
            f"not decide it.",
            context,
        )
        for field in fields
    ]


def declaration_findings(
    rule: RuleDefinition, fields: tuple[DeclarationField, ...], context: EvidenceContext
) -> list[FieldFinding]:
    """Whether each required declaration is borne, or why we cannot say."""
    return [_one_declaration(rule, field, context) for field in fields]


def _one_declaration(
    rule: RuleDefinition, field: DeclarationField, context: EvidenceContext
) -> FieldFinding:
    values = context.declared.get(field, ())
    if values:
        # Every bound value for this obligation, and every span behind all of them. One
        # finding, because one obligation, but it cites the whole of what was read.
        return finding(
            rule,
            field,
            FIELD_STATE_FROM_VERDICT[evaluate_rule(rule, Verdict.PASS)],
            "the declaration is present and was read from the package.",
            context,
            observed_value=" | ".join(value.normalised_value for value in values),
            evidence_span_ids=tuple(
                dict.fromkeys(ref for value in values for ref in value.span_refs)
            ),
        )

    if context.unreadable_reason is not None:
        return finding(
            rule, field, FieldState.INSUFFICIENT_EVIDENCE, context.unreadable_reason, context
        )

    return finding(
        rule,
        field,
        FIELD_STATE_FROM_VERDICT[evaluate_rule(rule, Verdict(rule.severity.value))],
        "the declaration was looked for and is not present.",
        context,
    )


def observation_findings(
    rule: RuleDefinition, fields: tuple[DeclarationField, ...], context: EvidenceContext
) -> list[FieldFinding]:
    """A rule about how or where a declaration appears, whose observation we lack.

    The reason names the rule's own evidence requirement rather than a generic apology, so
    an officer reading the output can tell which observation is missing and a reviewer can
    tell which stage would supply it.
    """
    return [
        finding(
            rule,
            field,
            FieldState.INSUFFICIENT_EVIDENCE,
            "this rule governs how or where the declaration appears, and the observation "
            f"it needs is not gathered by this pipeline yet: {rule.evidence_requirement}.",
            context,
        )
        for field in fields
    ]


def listing_findings(
    rule: RuleDefinition, fields: tuple[DeclarationField, ...], context: EvidenceContext
) -> list[FieldFinding]:
    """A duty owed by an e-commerce entity about its listing, not by the package.

    Rule 6(10A) obliges the entity to give a listing a searchable and sortable country-of-
    origin filter. A photograph of a package cannot bear on that at all, so a physical
    scan answers NOT_APPLICABLE. A catalogue record could bear on it, but the filter is a
    property of the platform's interface rather than of the record we were handed, so we
    say we cannot see it rather than assuming it either way.
    """
    if not context.source_is_listing:
        return [
            finding(
                rule,
                field,
                FieldState.NOT_APPLICABLE,
                "this obligation is owed by an e-commerce entity about a product listing. "
                "A physical package scan is not a listing, so the duty does not arise.",
                context,
            )
            for field in fields
        ]
    return [
        finding(
            rule,
            field,
            FieldState.INSUFFICIENT_EVIDENCE,
            "whether the listing offers a searchable and sortable country-of-origin "
            "filter is a property of the platform's interface, which this record does "
            "not carry.",
            context,
        )
        for field in fields
    ]
