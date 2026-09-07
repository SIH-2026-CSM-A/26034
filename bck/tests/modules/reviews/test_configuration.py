"""Tests for the reviews-local publication threshold configuration."""

import pytest

from app.modules.reviews.constants import (
    REVIEW_PUBLICATION_THRESHOLD,
    get_review_publication_threshold,
)


def test_default_review_publication_threshold_is_three(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the documented prototype prior when no override is configured."""
    monkeypatch.delenv("PCCS_REVIEW_PUBLICATION_THRESHOLD", raising=False)

    assert REVIEW_PUBLICATION_THRESHOLD == 3
    assert get_review_publication_threshold() == REVIEW_PUBLICATION_THRESHOLD


def test_review_publication_threshold_accepts_a_positive_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use a valid positive integer configured for the reviews module."""
    monkeypatch.setenv("PCCS_REVIEW_PUBLICATION_THRESHOLD", "5")

    assert get_review_publication_threshold() == 5


@pytest.mark.parametrize("invalid_value", ["0", "-1", "three", "1.5"])
def test_review_publication_threshold_rejects_invalid_overrides(
    monkeypatch: pytest.MonkeyPatch, invalid_value: str
) -> None:
    """Reject invalid threshold configuration instead of silently using the default."""
    monkeypatch.setenv("PCCS_REVIEW_PUBLICATION_THRESHOLD", invalid_value)

    with pytest.raises(ValueError):
        get_review_publication_threshold()
