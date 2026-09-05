"""Findings, the verdict record they assemble into, and the catalogue ingestion record.

The verdict record is the evidence artefact. Everything a reviewer needs to understand
why an outcome was reached is carried on it by value, so it can be read years later
without the rest of the system agreeing with it.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import Field, JsonValue

from app.contracts.base import ContractModel
from app.contracts.enums import (
    DeclarationField,
    EvidenceProvider,
    FieldState,
    RuleSeverity,
    RuleStatus,
    ToleranceBasis,
    Verdict,
)
from app.contracts.rules import RuleDefinition


class RuleParameterSnapshot(ContractModel):
    """The rule as it stood at the moment of evaluation, copied by value.

    Not a reference to a rule row. The values are duplicated in because a rule set is
    published, amended and republished, and a verdict must keep meaning what it meant
    when it was issued. Joining a stored verdict back to a live rules table would
    re-adjudicate history: an amendment landing on Tuesday would silently change what
    Monday's scan is recorded as having found, and the officer who signed off on Monday's
    finding would have no way to see that it had moved.

    Build these with :meth:`from_rule` so the copy cannot be skipped by accident.
    """

    rule_id: str
    clause_ref: str
    gazette_ref: str
    source_text: str
    status: RuleStatus
    severity: RuleSeverity
    rule_set_version: str
    """The version of the rule set this rule was taken from, as a string. Recorded so a
    reviewer can find the published set, not so the record can be joined back to it."""

    parameters: dict[str, JsonValue]
    rounding_increment: Decimal | None
    tolerance: Decimal | None
    tolerance_basis: ToleranceBasis | None

    @classmethod
    def from_rule(cls, rule: RuleDefinition, rule_set_version: str) -> "RuleParameterSnapshot":
        """Copy the evaluation-relevant values off ``rule``.

        The returned snapshot shares no mutable state with ``rule``: later edits to the
        rule, or to its ``parameters`` mapping, do not reach a snapshot already taken.
        """
        return cls(
            rule_id=rule.rule_id,
            clause_ref=rule.clause_ref,
            gazette_ref=rule.gazette_ref,
            source_text=rule.source_text,
            status=rule.status,
            severity=rule.severity,
            rule_set_version=rule_set_version,
            parameters=dict(rule.parameters),
            rounding_increment=rule.rounding_increment,
            tolerance=rule.tolerance,
            tolerance_basis=rule.tolerance_basis,
        )


class FieldFinding(ContractModel):
    """The outcome of evaluating one declaration against one rule, with its evidence."""

    field: DeclarationField
    """The declaration this finding is about."""

    state: FieldState
    """The outcome. INSUFFICIENT_EVIDENCE is a statement about the observation, not about
    the package, and is never interchangeable with FAIL."""

    rule_snapshot: RuleParameterSnapshot
    """The rule as it stood when this finding was made, by value."""

    observed_value: str | None = None
    """What was read off the package, canonicalised. ``None`` where nothing was read."""

    expected_value: str | None = None
    """What the rule required, where the rule states a specific value or format."""

    reason: str = Field(min_length=1)
    """Why this state was reached, in terms a reviewing officer can act on. For
    INSUFFICIENT_EVIDENCE this is what could not be read and why, not a guess at what the
    package says."""

    evidence_span_ids: tuple[str, ...] = ()
    """The :attr:`~app.contracts.evidence.ExtractedSpan.span_id` values behind this
    finding. Empty for a finding made because nothing could be read."""


class VerdictRecord(ContractModel):
    """The complete, self-contained record of one evaluation.

    Deliberately carries **no** ``rule_definition_id``, ``rule_set_id`` or any other
    reference to a live rules table. Every rule parameter that shaped a finding is
    snapshotted onto :class:`FieldFinding.rule_snapshot` by value, and the rule set is
    recorded as a version string. This is a modelling decision rather than a database
    detail: with no reference to follow, a persistence layer built on this type has no
    way to re-adjudicate a stored verdict against rules that changed after it was issued.
    """

    subject_ref: str = Field(min_length=1)
    """What was evaluated — the scan identifier, or the catalogue listing identifier."""

    verdict: Verdict
    """The package-level recommendation. A recommendation, never a determination."""

    rule_set_version: str = Field(min_length=1)
    """The rule set version this evaluation ran under, copied in as a string."""

    evaluated_at: datetime
    """When the evaluation ran. Rule applicability was resolved against this instant, not
    against the time the record is read."""

    findings: tuple[FieldFinding, ...] = Field(min_length=1)
    """Every per-field finding, each carrying its own rule snapshot. A verdict with no
    findings behind it has no evidence chain and is rejected."""

    field_providers: dict[DeclarationField, EvidenceProvider] = Field(default_factory=dict)
    """Which provider produced the value used for each field.

    Part of the evidence chain: it is what lets a reviewer see that the retail sale price
    came from Tesseract and the net quantity from PaddleOCR, or that a value was entered
    by an officer rather than read. A field evaluated with no readable value has no entry
    here.
    """


class CatalogueRecord(ContractModel):
    """A structured product listing, as the second ingestion path alongside an image.

    E-commerce listings arrive as fields rather than pixels. Accepting them as a
    first-class type rather than rendering them into something image-shaped keeps the
    connection to any particular marketplace an adapter concern.
    """

    listing_id: str = Field(min_length=1)
    """The listing's identifier on its source platform."""

    platform: str = Field(min_length=1)
    """The marketplace or catalogue the record came from."""

    retrieved_at: datetime
    """When the listing was captured. Listings change; a verdict is about the listing as
    it stood at this moment."""

    title: str = ""
    """The listing title as displayed."""

    declared_fields: dict[DeclarationField, str] = Field(default_factory=dict)
    """Declarations as the listing states them, keyed by obligation. A field absent from
    this mapping was not declared in the listing — which is a finding about the listing,
    not a gap in the record."""

    seller_name: str | None = None
    """The seller as named by the platform, which is not necessarily the manufacturer,
    packer or importer the Rules require."""

    image_urls: tuple[str, ...] = ()
    """Listing images, if any, for the image path to evaluate alongside the declared
    text."""
