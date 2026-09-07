"""One pass over the rule set: every finding the available evidence supports.

The composition point of the judgement half of the pipeline.
:mod:`app.pipeline.dispositions` says what kind of obligation each rule states,
:mod:`app.pipeline.rule_findings` and :mod:`app.pipeline.measurement_findings` turn one
rule into findings, and this walks the active rules and puts the two together.

Deterministic and pure: no clock — the evaluation date is carried on the context — no
I/O, no model, no agent loop. Replaying the same evidence returns the same findings, which
is what makes a verdict an officer acted on reproducible on demand.
"""

from collections.abc import Callable, Sequence

from app.contracts import DeclarationField, FieldFinding
from app.modules.rules import RuleDefinition, ScopeDecision, chapter_ii_scope, is_active
from app.pipeline.dispositions import (
    Disposition,
    disposition_of,
    governed_declarations,
    required_declarations,
)
from app.pipeline.measurement_findings import measurement_findings
from app.pipeline.rule_findings import (
    EvidenceContext,
    declaration_findings,
    listing_findings,
    observation_findings,
    scope_findings,
    sector_findings,
)
from app.pipeline.rule_snapshot import declaration_fields

RuleFindingBuilder = Callable[
    [RuleDefinition, tuple[DeclarationField, ...], EvidenceContext], list[FieldFinding]
]

BUILDERS: dict[Disposition, RuleFindingBuilder] = {
    Disposition.DECLARATION: declaration_findings,
    Disposition.MEASUREMENT: measurement_findings,
    Disposition.OBSERVATION: observation_findings,
    Disposition.LISTING: listing_findings,
}
"""Which builder answers each disposition.

A table rather than an ``if``/``elif`` chain so that every disposition but
NOT_AN_OBLIGATION must name a builder, and a disposition added without one raises here
instead of falling through to no finding. NOT_AN_OBLIGATION is absent deliberately: it is
the only disposition that emits nothing, and :func:`build_findings` says so in one line
rather than leaving it to a missing key.
"""


def build_findings(
    rules: Sequence[RuleDefinition], context: EvidenceContext
) -> tuple[FieldFinding, ...]:
    """Every finding the evidence in ``context`` supports, for the rules active on its date.

    Rules are filtered to those in force on the evaluation date first: a scan dated before
    an amendment is adjudicated under the rules as they then stood, not as they stand when
    the record is read.
    """
    active = [rule for rule in rules if is_active(rule, context.evaluation_date)]
    governed = required_declarations(active)

    # Rule 3 is asked once per scan, not once per rule. Whether Chapter II reaches this
    # package is a property of the package, so re-deriving it inside the loop would answer
    # the same question twenty times and leave twenty chances for the answers to differ.
    scope = chapter_ii_scope(
        net_quantity=context.declared.get(DeclarationField.NET_QUANTITY, ()),
        not_for_retail_sale_observed=context.not_for_retail_sale_observed,
        institutional_or_industrial_confirmed=context.institutional_or_industrial_confirmed,
    )

    findings: list[FieldFinding] = []
    for rule in active:
        findings.extend(
            _findings_for_rule(rule, active_scope=governed, scope=scope, context=context)
        )
    return tuple(findings)


def _findings_for_rule(
    rule: RuleDefinition,
    *,
    active_scope: tuple[DeclarationField, ...],
    scope: ScopeDecision,
    context: EvidenceContext,
) -> list[FieldFinding]:
    """The findings one rule produces, with applicability settled before evaluation.

    Two applicability questions, asked widest first. Rule 3 decides whether Chapter II
    reaches the package at all; a sector override decides whether one obligation inside it
    has moved to another framework. Asking the narrower one first would route a package
    outside the chapter to the Medical Devices Rules, 2017.
    """
    disposition = disposition_of(rule)
    if disposition is Disposition.NOT_AN_OBLIGATION:
        return []

    if disposition is Disposition.DECLARATION:
        fields = declaration_fields(rule)
    else:
        fields = governed_declarations(rule, active_scope)
    if not fields:
        return []

    out_of_scope = scope_findings(rule, fields, scope, context)
    if out_of_scope is not None:
        return out_of_scope

    settled = sector_findings(rule, fields, context)
    if settled is not None:
        return settled

    return BUILDERS[disposition](rule, fields, context)
