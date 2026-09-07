"""Application behavior for anonymous consumer sentiment submissions."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ConsumerSafetyClaim
from app.modules.reviews import repository
from app.modules.reviews.constants import (
    PRODUCT_IDENTIFIER_MAX_LENGTH,
    get_review_publication_threshold,
)


def normalize_product_identifier(product_identifier: str) -> str:
    """Trim and validate the supplied product identifier without changing its digits."""
    if not isinstance(product_identifier, str):
        raise ValueError("product_identifier must be a string")

    normalized = product_identifier.strip()
    if not normalized:
        raise ValueError("product_identifier must not be empty")
    if len(normalized) > PRODUCT_IDENTIFIER_MAX_LENGTH:
        raise ValueError(
            f"product_identifier must be at most {PRODUCT_IDENTIFIER_MAX_LENGTH} characters"
        )
    return normalized


async def record_submission(
    session: AsyncSession,
    *,
    product_identifier: str,
    consumer_safety_claim: ConsumerSafetyClaim,
    threshold: int | None = None,
) -> bool:
    """Record one normalized submission inside the caller's transaction."""
    normalized_identifier = normalize_product_identifier(product_identifier)
    if not isinstance(consumer_safety_claim, ConsumerSafetyClaim):
        raise ValueError("consumer_safety_claim must be a ConsumerSafetyClaim")
    publication_threshold = get_review_publication_threshold() if threshold is None else threshold
    return await repository.record_submission(
        session,
        product_identifier=normalized_identifier,
        consumer_safety_claim=consumer_safety_claim,
        threshold=publication_threshold,
    )


async def get_published_consensus(
    session: AsyncSession, *, product_identifier: str
) -> list[tuple[ConsumerSafetyClaim, int]]:
    """Return published aggregates for one normalized product identifier."""
    normalized_identifier = normalize_product_identifier(product_identifier)
    return await repository.published_consensus(session, product_identifier=normalized_identifier)
