"""The rule-store document: what one rule is, and what a version of the store holds.

The vocabulary a rule is written in lives in :mod:`app.modules.rules.base`, the shapes of
obligation it may express in :mod:`app.modules.rules.conditions`, and what evaluating one
produces in :mod:`app.modules.rules.results`. This file is only the record itself.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .base import NonEmptyText, RuleStatus, Severity, StrictRuleModel
from .conditions import RuleCondition


class RuleDefinition(StrictRuleModel):
    """RUL-001 stand-in; CTR-002 migration is an app.contracts import substitution."""

    rule_id: NonEmptyText
    clause_ref: NonEmptyText
    gazette_ref: NonEmptyText
    source_text: NonEmptyText
    status: RuleStatus
    effective_from: date
    effective_to: date | None
    applies_to: tuple[NonEmptyText, ...] = Field(min_length=1)
    conditions: RuleCondition
    evidence_requirement: NonEmptyText
    severity: Severity

    @field_validator("gazette_ref")
    @classmethod
    def validate_gazette_filename(cls, value: str) -> str:
        """Require a bare PDF filename rather than a path or empty reference."""
        if Path(value).name != value or not value.lower().endswith(".pdf"):
            raise ValueError("gazette_ref must be a bare PDF filename")
        return value

    @model_validator(mode="after")
    def validate_effective_window(self) -> RuleDefinition:
        """Reject an effective interval whose end precedes its start."""
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")
        return self


class RuleStoreDocument(StrictRuleModel):
    """Describe the versioned top-level YAML rule-store document."""

    schema_version: Literal[1]
    rules: tuple[RuleDefinition, ...] = Field(min_length=1)
