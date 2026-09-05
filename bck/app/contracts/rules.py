"""Encoded rules and the versioned sets they ship in.

A rule is data, not code. It carries the gazette it came from, the text it was read out
of, the window it is in force for, and the parameters an evaluator applies. Rule numbers
and thresholds are read out of ``rules-corpus/`` and never written from memory.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, JsonValue, model_validator

from app.contracts.base import ContractModel
from app.contracts.enums import DeclarationField, RuleSeverity, RuleStatus, ToleranceBasis


class RuleDefinition(ContractModel):
    """One encoded provision of the Legal Metrology (Packaged Commodities) Rules 2011.

    An unsourced rule number is the failure mode this type exists to prevent, so
    :attr:`gazette_ref` is required and rejected when blank. Construction fails rather
    than the rule being loaded and flagged afterwards — a rule that reaches an evaluator
    at all is one that named its source.

    What is *not* checked here: that :attr:`gazette_ref` names a file that exists in
    ``rules-corpus/``. Contracts performs no I/O. The rule loader owns that check.
    """

    rule_id: str = Field(min_length=1)
    """Stable identifier for this rule, unique within a rule set. Findings and citations
    reference it, so it must not be reused for a different provision."""

    clause_ref: str = Field(min_length=1)
    """The provision as an officer would cite it — ``6(1)(a)``, ``7(2)``, ``26``."""

    gazette_ref: str = Field(min_length=1)
    """The source document this rule was read out of, named as it appears in
    ``rules-corpus/``.

    Required and non-empty. A rule with no gazette reference does not ship: without it
    nobody reviewing a finding can check the rule against the law, and a rule number
    with no source behind it is exactly the thing this system must not put in front of
    an officer.
    """

    source_text: str = Field(min_length=1)
    """The provision's own words, quoted from the gazette. What a reviewer checks the
    encoding against, and what an evidence bundle reproduces."""

    status: RuleStatus
    """Whether the encoding has been confirmed against the primary source."""

    effective_from: date
    """First date this rule is in force. Evaluated against the scan date, so a rule
    notified but not yet commenced is encoded rather than omitted."""

    effective_to: date | None = None
    """Last date this rule is in force, or ``None`` while it remains current."""

    applies_to: tuple[str, ...] = ()
    """Category or sector selectors this rule is limited to. Empty means it applies to
    every package, subject to :attr:`conditions`."""

    conditions: dict[str, JsonValue] = Field(default_factory=dict)
    """Predicates the evaluator must satisfy before the rule applies at all — net
    quantity thresholds, package form, whether another law governs the field."""

    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    """Rule-specific values the evaluator reads: band tables, required formats, permitted
    unit bases. Copied by value into every verdict that uses them."""

    evidence_requirement: tuple[DeclarationField, ...] = ()
    """Declarations that must have been read before this rule can return anything other
    than :attr:`~app.contracts.enums.FieldState.INSUFFICIENT_EVIDENCE`."""

    requires_measurement: bool = False
    """Whether evaluating this rule needs a physical measurement as well as a
    declaration. Rule 7 height checks do; a format rule does not."""

    severity: RuleSeverity
    """How a breach routes in the officer workflow. Operational, not a legal grading."""

    rounding_increment: Decimal | None = None
    """The increment a value must be expressed in steps of, where the rule prescribes one
    — "rounded to the nearest 5 paise" is a transformation applied to the declared value.

    Separate from :attr:`tolerance`, and never merged with it. A rounding increment
    transforms a value in steps; a tolerance accepts a difference between two values.
    They diverge at every boundary: with an increment of 0.05, a declared 1.02 is wrong
    and 1.05 is right; with a tolerance of 0.05, both are accepted against 1.00.
    """

    tolerance: Decimal | None = None
    """The difference permitted between a declared value and a required or measured one.

    Read together with :attr:`tolerance_basis`, which says whether the figure is an
    absolute amount or a percentage.
    """

    tolerance_basis: ToleranceBasis | None = None
    """How to read :attr:`tolerance`. Required whenever a tolerance is set."""

    @model_validator(mode="after")
    def _check_window_and_tolerance(self) -> "RuleDefinition":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to precedes effective_from")
        if (self.tolerance is None) != (self.tolerance_basis is None):
            raise ValueError(
                "tolerance and tolerance_basis are set together — a bare figure cannot "
                "be read as an amount or as a percentage"
            )
        return self

    def in_force_on(self, on: date) -> bool:
        """Whether this rule is in force on ``on``.

        Evaluation is always against the date of the scan, never against today, so
        replaying an old scan reaches the same rules it originally did.
        """
        if on < self.effective_from:
            return False
        return self.effective_to is None or on <= self.effective_to


class RuleSetVersion(ContractModel):
    """An immutable, published set of rules, identified by version.

    A verdict records the version string it was evaluated under. Publishing a new version
    never edits an old one, so a past verdict remains reproducible against the rules that
    actually produced it.
    """

    version: str = Field(min_length=1)
    """The version identifier, unique and never reissued."""

    published_at: datetime
    """When this version was published."""

    rules: tuple[RuleDefinition, ...] = Field(min_length=1)
    """Every rule in this version. An empty rule set has nothing to evaluate and is
    rejected rather than silently passing every package."""

    @model_validator(mode="after")
    def _rule_ids_are_unique(self) -> "RuleSetVersion":
        seen = [rule.rule_id for rule in self.rules]
        if len(set(seen)) != len(seen):
            raise ValueError("rule_id values must be unique within a rule set")
        return self
