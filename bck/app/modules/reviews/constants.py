"""Configuration constants for anonymous consumer review publication."""

import os
from typing import Final

from app.core import ProductReviewRow

REVIEW_PUBLICATION_THRESHOLD: Final[int] = 3
"""Uncalibrated prototype prior for publishing matching anonymous submissions.

Three is the smallest repeated-matching cohort chosen for this prototype. It is not
legally required, statistically validated, or evidence that a product is safe or unsafe.
"""

REVIEW_PUBLICATION_THRESHOLD_ENVIRONMENT_VARIABLE: Final[str] = "PCCS_REVIEW_PUBLICATION_THRESHOLD"
"""Reviews-local environment variable for overriding the publication prior."""

PRODUCT_IDENTIFIER_MAX_LENGTH: Final[int] = int(
    ProductReviewRow.__table__.c.product_identifier.type.length
)
"""The maximum identifier length supplied by the existing CORE-004 table."""


def get_review_publication_threshold() -> int:
    """Return the configured positive publication threshold."""
    raw_value = os.environ.get(REVIEW_PUBLICATION_THRESHOLD_ENVIRONMENT_VARIABLE)
    if raw_value is None:
        return REVIEW_PUBLICATION_THRESHOLD

    try:
        threshold = int(raw_value)
    except ValueError as error:
        raise ValueError(
            f"{REVIEW_PUBLICATION_THRESHOLD_ENVIRONMENT_VARIABLE} must be a positive integer"
        ) from error

    if threshold < 1:
        raise ValueError(
            f"{REVIEW_PUBLICATION_THRESHOLD_ENVIRONMENT_VARIABLE} must be a positive integer"
        )
    return threshold
