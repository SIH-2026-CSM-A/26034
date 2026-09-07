"""HTTP schema contracts for the anonymous review endpoints."""

import pytest
from pydantic import ValidationError

from app.core import ConsumerSafetyClaim
from app.modules.reviews.schemas import (
    PublishedConsensus,
    PublishedReviewsResponse,
    ReviewSubmissionRequest,
    ReviewSubmissionResponse,
)


def test_submission_request_trims_identifier_and_accepts_safe_sentiment() -> None:
    """Accept the canonical core sentiment and normalize the barcode boundary."""
    request = ReviewSubmissionRequest(
        product_identifier="  0012345678905  ", consumer_safety_claim="safe"
    )

    assert request.product_identifier == "0012345678905"
    assert request.consumer_safety_claim is ConsumerSafetyClaim.SAFE


def test_submission_request_rejects_unknown_fields() -> None:
    """Do not allow clients to supply row identity or other unowned metadata."""
    with pytest.raises(ValidationError):
        ReviewSubmissionRequest(
            product_identifier="8901234567890",
            consumer_safety_claim="safe",
            anonymous_token="client-supplied",
        )


def test_submission_request_rejects_invalid_sentiment() -> None:
    """Only SAFE and UNSAFE from the existing core enum are accepted."""
    with pytest.raises(ValidationError):
        ReviewSubmissionRequest(
            product_identifier="8901234567890", consumer_safety_claim="mostly_safe"
        )


def test_submission_response_contains_only_public_submission_state() -> None:
    """Submission responses contain no row identifier, token, timestamp, or count."""
    response = ReviewSubmissionResponse(
        product_identifier="8901234567890",
        consumer_safety_claim=ConsumerSafetyClaim.UNSAFE,
        publication_status="HELD",
    )

    assert response.model_dump(mode="json") == {
        "product_identifier": "8901234567890",
        "consumer_safety_claim": "unsafe",
        "publication_status": "HELD",
    }


def test_published_response_contains_only_published_aggregates() -> None:
    """Public reads expose aggregate sentiment counts without individual row metadata."""
    response = PublishedReviewsResponse(
        product_identifier="8901234567890",
        published_consensus=[
            PublishedConsensus(
                consumer_safety_claim=ConsumerSafetyClaim.SAFE,
                submission_count=3,
            )
        ],
    )

    assert response.model_dump(mode="json") == {
        "product_identifier": "8901234567890",
        "published_consensus": [{"consumer_safety_claim": "safe", "submission_count": 3}],
    }
