"""Typed HTTP shapes for anonymous consumer sentiment."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core import ConsumerSafetyClaim
from app.modules.reviews.constants import PRODUCT_IDENTIFIER_MAX_LENGTH

ProductIdentifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=PRODUCT_IDENTIFIER_MAX_LENGTH,
    ),
]
"""A normalized product identifier accepted by the review API."""

PublicationStatus = Literal["HELD", "PUBLISHED"]
"""The only public states of one submitted sentiment report."""


class ReviewSchema(BaseModel):
    """Base schema that rejects fields outside the review API contract."""

    model_config = ConfigDict(extra="forbid")


class ReviewSubmissionRequest(ReviewSchema):
    """Anonymous sentiment submitted for one normalized product identifier."""

    product_identifier: ProductIdentifier
    consumer_safety_claim: ConsumerSafetyClaim


class ReviewSubmissionResponse(ReviewSchema):
    """Public result of accepting one anonymous sentiment submission."""

    product_identifier: ProductIdentifier
    consumer_safety_claim: ConsumerSafetyClaim
    publication_status: PublicationStatus


class PublishedConsensus(ReviewSchema):
    """A published count for one exact consumer sentiment value."""

    consumer_safety_claim: ConsumerSafetyClaim
    submission_count: int = Field(ge=1)


class PublishedReviewsResponse(ReviewSchema):
    """Published consumer sentiment aggregates for one product identifier."""

    product_identifier: ProductIdentifier
    published_consensus: list[PublishedConsensus]
