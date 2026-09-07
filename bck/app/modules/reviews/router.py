"""FastAPI endpoints for anonymous consumer sentiment."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_session
from app.modules.reviews import service
from app.modules.reviews.schemas import (
    ProductIdentifier,
    PublishedConsensus,
    PublishedReviewsResponse,
    ReviewSubmissionRequest,
    ReviewSubmissionResponse,
)

reviews_router = APIRouter(prefix="/reviews", tags=["reviews"])

Session = Annotated[AsyncSession, Depends(get_session)]


@reviews_router.post("", status_code=status.HTTP_201_CREATED)
async def submit_review(
    body: ReviewSubmissionRequest, session: Session
) -> ReviewSubmissionResponse:
    """Persist one anonymous sentiment and report only its publication state."""
    async with session.begin():
        published = await service.record_submission(
            session,
            product_identifier=body.product_identifier,
            consumer_safety_claim=body.consumer_safety_claim,
        )

    return ReviewSubmissionResponse(
        product_identifier=body.product_identifier,
        consumer_safety_claim=body.consumer_safety_claim,
        publication_status="PUBLISHED" if published else "HELD",
    )


@reviews_router.get("/{product_identifier}")
async def get_published_reviews(
    product_identifier: ProductIdentifier, session: Session
) -> PublishedReviewsResponse:
    """Return only published sentiment aggregates for one product identifier."""
    aggregates = await service.get_published_consensus(
        session, product_identifier=product_identifier
    )
    return PublishedReviewsResponse(
        product_identifier=product_identifier,
        published_consensus=[
            PublishedConsensus(
                consumer_safety_claim=consumer_safety_claim,
                submission_count=submission_count,
            )
            for consumer_safety_claim, submission_count in aggregates
        ],
    )
