"""One rule, the evidence available, and the findings that follow.

Each function here answers the same question for a different shape of obligation: given
this rule and what we actually managed to observe, what may we say about each declaration
it governs? They are pure and take no session, no clock and no image, so every branch
below is reachable in a test without a database or a model.

**The ordering that matters.** :func:`scope_findings` runs before :func:`sector_findings`,
and both run before any evaluator. Rule 3 decides whether Chapter II reaches the package at
all; only then is it worth asking whether a sector has moved one obligation inside it. A
sector override is a carve-out rather than a stricter path — G.S.R. 778(E) does not raise the bar
for a medical device, it moves character height, width and the panel declaration to the
Medical Devices Rules, 2017 outright — so whether the packaged rules govern an obligation
at all is settled first. Evaluating a carved-out obligation and filtering the answer
afterwards would produce a finding under a provision that does not apply to the package.

**The distinction that matters.** A missing declaration is INSUFFICIENT_EVIDENCE when we
never obtained the evidence to look for it, and a finding about the package when we
looked. Those are different branches reached from different inputs, never a state chosen
by widening a condition.

**And a third case, which is neither.** A declaration read twice in readings that
contradict each other is REVIEW_REQUIRED. The evidence was obtained — that is what rules
out INSUFFICIENT_EVIDENCE — and which reading the package bears is an officer's decision,
which is what rules out FAIL. It gets its own branch above every other, so no widening of
an existing condition can reach it and no edit to one can reroute it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from app.contracts import (
    CompetingReadings,
    DeclarationField,
    FieldFinding,
    FieldState,
    MeasurementResult,
    NormalisedField,
)
from app.modules.rules import (
    ProductCategory,
    RuleDefinition,
    ScopeDecision,
    ScopeStatus,
    Verdict,
    controlling_framework,
    evaluate_rule,
)
from app.pipeline.dispositions import (
    COMMODITY_CONDITIONED_RULES,
    FACT_CONDITIONED_RULES,
    FIELD_STATE_FROM_VERDICT,
    SECTOR_GOVERNED_RULES,
)
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

    contested: Mapping[DeclarationField, tuple[CompetingReadings, ...]]
    """Obligations read more than once, in readings that contradict each other.

    Separate from :attr:`declared` because a contested obligation has no resolved value:
    every reading here was read successfully, and none of them has been established as the
    declaration the package bears. That is why it routes to REVIEW_REQUIRED and not to
    INSUFFICIENT_EVIDENCE — the failure is not in our reading.

    A *tuple* per obligation for the same reason :attr:`declared` carries one. Rule 6(1)(a)
    is a single obligation covering manufacturer, packer and importer, so two spatially
    distinct bilingual pairs can each disagree against it. A single
    :class:`~app.contracts.CompetingReadings` per key would drop one of them silently.
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

    not_for_retail_sale_observed: bool = False
    """Whether the marker Rule 2(bb) and 2(bc) require was read off this package.

    ``False`` means *not observed* and never "the package bears no such mark". Nothing is
    inferred from it: a ``False`` here produces no finding and no reason text, and the scan
    evaluates exactly as it would have done without this field. Only ``True`` does anything,
    and what it does is route to an officer.

    Computed by the orchestrator, which holds the spans; this context deliberately carries
    only normalised evidence. Always ``False`` on the catalogue path, where a listing
    supplies declarations by obligation and carries no marker to read.
    """

    institutional_or_industrial_confirmed: bool = False
    """The officer's *confirmed* Rule 3(c) exclusion. ``False`` confirms nothing.

    The same shape as :attr:`product_category`, and for the same reason: routing a package
    out of Chapter II is a legal determination, and this system does not make it on a
    classifier's guess. An officer asserts it; the label only ever indicates it.
    """


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


SCOPE_FIELD_STATE: dict[ScopeStatus, FieldState] = {
    ScopeStatus.EXCLUDED: FieldState.NOT_APPLICABLE,
    ScopeStatus.UNCERTAIN: FieldState.REVIEW_REQUIRED,
}
"""What each settled scope status means for one field.

``GOVERNED`` is absent deliberately, and its absence is the control flow: a governed
package produces no scope findings at all and falls through to the ordinary builders. Only
the two statuses that *settle* a rule appear here.

Neither value is FAIL and neither is INSUFFICIENT_EVIDENCE. Rule 3 removes the duty or says
we cannot yet tell whether it arises; neither is a statement that the package fell short,
and neither is a statement about our reading. Both are set directly rather than derived
through ``FIELD_STATE_FROM_VERDICT``, which stays non-total over ``FieldState`` for exactly
the reason its own docstring gives.
"""


def scope_findings(
    rule: RuleDefinition,
    fields: tuple[DeclarationField, ...],
    scope: ScopeDecision,
    context: EvidenceContext,
) -> list[FieldFinding] | None:
    """Findings that settle a rule before applicability, or ``None`` to carry on.

    Rule 3 is prior to the sector question. A sector override moves one obligation to
    another framework; Rule 3 decides whether the chapter holding that obligation reaches
    the package at all. Answering the narrower question first would attribute a package
    outside Chapter II to the Medical Devices Rules, 2017, which is a different wrong
    answer rather than a smaller one.
    """
    state = SCOPE_FIELD_STATE.get(scope.status)
    if state is None:
        return None

    return [
        finding(
            rule,
            field,
            state,
            f"{scope.limb} — {scope.reason}",
            context,
        )
        for field in fields
    ]


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


def commodity_condition_findings(
    rule: RuleDefinition, fields: tuple[DeclarationField, ...], context: EvidenceContext
) -> list[FieldFinding] | None:
    """Findings for a rule its own text limits by commodity, or ``None`` to carry on.

    The same two cases as :func:`sector_findings`, for the same reasons. With no confirmed
    category we do not know whether the rule's condition is met, so nothing has been
    established about the package — INSUFFICIENT_EVIDENCE, never FAIL. With a category that
    cannot meet the condition, the duty does not arise — NOT_APPLICABLE, never PASS: the
    package did not satisfy the obligation, it never had it.
    """
    conditioned = COMMODITY_CONDITIONED_RULES.get(rule.rule_id)
    if conditioned is None:
        return None
    phrase, excluded = conditioned

    if context.product_category is None:
        return [
            finding(
                rule,
                field,
                FieldState.INSUFFICIENT_EVIDENCE,
                f"{rule.clause_ref} applies only to a commodity which {phrase}, and the "
                f"product category has not been confirmed. Confirm the category to evaluate "
                f"it — an unconfirmed category is not a finding about the package.",
                context,
            )
            for field in fields
        ]

    if context.product_category not in excluded:
        return None

    return [
        finding(
            rule,
            field,
            FieldState.NOT_APPLICABLE,
            f"{rule.clause_ref} applies only to a commodity which {phrase}. An officer has "
            f"confirmed this package as {context.product_category.value}, which is not for "
            f"human consumption, so this obligation does not arise for it.",
            context,
        )
        for field in fields
    ]


def fact_condition_findings(
    rule: RuleDefinition, fields: tuple[DeclarationField, ...], context: EvidenceContext
) -> list[FieldFinding] | None:
    """An absent declaration whose duty depends on an unestablished fact, or ``None``.

    Settles a field only in the one case the ordinary builder would get wrong: the
    declaration was looked for, is not there, and the rule requires it only on a condition
    nobody has established. Every other case — borne, contested, or unreadable — carries on
    to :func:`declaration_findings` unchanged, so this can only ever replace a FAIL.
    """
    phrase = FACT_CONDITIONED_RULES.get(rule.rule_id)
    if phrase is None or context.unreadable_reason is not None:
        return None
    absent = [
        field
        for field in fields
        if not context.declared.get(field) and not context.contested.get(field)
    ]
    if len(absent) != len(fields):
        return None
    return [
        finding(
            rule,
            field,
            FieldState.REVIEW_REQUIRED,
            f"the declaration was looked for and is not present, but {rule.clause_ref} "
            f'requires it only on a condition — "{phrase}" — that neither the record nor '
            f"a product category establishes. Whether the duty arises for this package is "
            f"an officer's judgement, so its absence is not reported as a shortfall.",
            context,
        )
        for field in absent
    ]


ONE_VALUE_FIELDS = frozenset({DeclarationField.MANUFACTURE_DATE, DeclarationField.BEST_BEFORE_DATE})
"""Obligations a package meets with exactly one value, so that two different bound values
are not two declarations but one reading that also caught something else.

The first real capture (2026-09-19) bound MANUFACTURE_DATE four times — "2044-09 |
2044-09 | 2024-07-15 | 2026-07-14", two from an address line and one from the use-by
date — and reported PASS on the lot. NAME_AND_ADDRESS is not here: a package legitimately
bears a manufacturer, a packer and an importer. Nor is NET_QUANTITY: a bilingual
disagreement over it is :class:`~app.contracts.CompetingReadings`, handled above.
"""


def declaration_findings(
    rule: RuleDefinition, fields: tuple[DeclarationField, ...], context: EvidenceContext
) -> list[FieldFinding]:
    """Whether each required declaration is borne, or why we cannot say."""
    return [_one_declaration(rule, field, context) for field in fields]


def _one_declaration(
    rule: RuleDefinition, field: DeclarationField, context: EvidenceContext
) -> FieldFinding:
    contested = context.contested.get(field, ())
    if contested:
        # Above `if values:` and load-bearing there, not incidentally first. A contested
        # obligation must never be reported as a satisfied one, and the ordering is what
        # guarantees it rather than an invariant asserted in another layer.
        # ``test_a_contested_declaration_outranks_a_resolved_one`` goes red on a reorder.
        readings = tuple(reading for competing in contested for reading in competing.readings)
        observed = " | ".join(reading.normalised_value for reading in readings)
        distinguished = ", ".join(dict.fromkeys(competing.reason.value for competing in contested))
        return finding(
            rule,
            field,
            # A literal, deliberately, and not FIELD_STATE_FROM_VERDICT[evaluate_rule(...)]
            # as the two branches below use. Nothing was evaluated here: the rule was never
            # applied because no declaration was resolved to apply it to. Routing a proposed
            # Verdict.REVIEW through the evaluator would return REVIEW unconditionally — a
            # round trip computing a constant — and would give this branch the FAIL branch's
            # exact expression, one token from sending a contested declaration to FAIL.
            FieldState.REVIEW_REQUIRED,
            f"this declaration was read {len(readings)} times and the readings do not "
            f"agree: {observed}. Each was read from the package, so the evidence was "
            f"obtained and nothing here is a gap in our reading. What is unresolved is "
            f"which reading the package bears, and that is an officer's decision rather "
            f"than this pipeline's ({distinguished}).",
            context,
            observed_value=observed,
            evidence_span_ids=tuple(
                dict.fromkeys(ref for reading in readings for ref in reading.span_refs)
            ),
        )

    values = context.declared.get(field, ())
    if field in ONE_VALUE_FIELDS:
        distinct = tuple(dict.fromkeys(value.normalised_value for value in values))
        if len(distinct) > 1:
            return finding(
                rule,
                field,
                FieldState.INSUFFICIENT_EVIDENCE,
                f"text on the panel was bound to this declaration {len(values)} times and the "
                f"values do not agree: {' | '.join(distinct)}. A package bears one such date, "
                f"so all but one of these is something else — a plot number, the other date — "
                f"and the reading cannot say which. No value is reported, and nothing follows "
                f"from one.",
                context,
                evidence_span_ids=tuple(
                    dict.fromkeys(ref for value in values for ref in value.span_refs)
                ),
            )
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
