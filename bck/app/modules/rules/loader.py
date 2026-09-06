"""Strict, safe loader for YAML-backed legal rule definitions."""

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import RuleDefinition, RuleStoreDocument

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RULE_STORE_PATH = Path(__file__).resolve().parent / "data" / "rules.yaml"
DEFAULT_CORPUS_DIRECTORY = REPOSITORY_ROOT / "rules-corpus"


class RuleLoadError(ValueError):
    """Report a complete rule-store load failure without returning partial data."""


def _read_yaml(rule_store_path: Path) -> Any:
    """Read and safely parse one YAML rule-store document."""
    try:
        source = rule_store_path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuleLoadError(f"cannot read rule store {rule_store_path}: {error}") from error

    try:
        return yaml.safe_load(source)
    except yaml.YAMLError as error:
        raise RuleLoadError(f"invalid YAML in {rule_store_path}: {error}") from error


def _validate_gazette_references(
    rules: tuple[RuleDefinition, ...],
    corpus_directory: Path,
) -> None:
    """Require every gazette reference to resolve to a corpus file."""
    for rule in rules:
        gazette_path = corpus_directory / rule.gazette_ref
        if not gazette_path.is_file():
            raise RuleLoadError(
                f"rule {rule.rule_id} gazette_ref does not exist: {rule.gazette_ref}"
            )


def _validate_unique_rule_ids(rules: tuple[RuleDefinition, ...]) -> None:
    """Reject duplicate stable identifiers in a single rule-store version."""
    seen: set[str] = set()
    for rule in rules:
        if rule.rule_id in seen:
            raise RuleLoadError(f"duplicate rule_id: {rule.rule_id}")
        seen.add(rule.rule_id)


def load_rules(
    rule_store_path: Path = DEFAULT_RULE_STORE_PATH,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIRECTORY,
) -> tuple[RuleDefinition, ...]:
    """Load all rules atomically after strict schema and corpus validation."""
    parsed = _read_yaml(Path(rule_store_path))
    try:
        document = RuleStoreDocument.model_validate(parsed)
    except ValidationError as error:
        raise RuleLoadError(f"invalid rule schema: {error}") from error

    rules = document.rules
    _validate_unique_rule_ids(rules)
    _validate_gazette_references(rules, Path(corpus_dir))
    return rules


@lru_cache(maxsize=1)
def load_default_rules() -> tuple[RuleDefinition, ...]:
    """Load and cache the immutable packaged rule store."""
    return load_rules()


def rule_by_id(rule_id: str) -> RuleDefinition:
    """Return one packaged rule by stable identifier.

    Lives here rather than in an evaluator because every evaluator needs it and none of
    them should need each other to get it. A miss or a duplicate raises: an evaluator
    silently falling back to a built-in threshold is how a figure that is not in the
    gazette reaches a finding.
    """
    matches = [rule for rule in load_default_rules() if rule.rule_id == rule_id]
    if len(matches) != 1:
        raise ValueError(f"expected one rule for {rule_id}, found {len(matches)}")
    return matches[0]


def is_active(rule: RuleDefinition, evaluation_date: date) -> bool:
    """Return whether a rule is effective on the supplied date."""
    return rule.effective_from <= evaluation_date and (
        rule.effective_to is None or evaluation_date <= rule.effective_to
    )
