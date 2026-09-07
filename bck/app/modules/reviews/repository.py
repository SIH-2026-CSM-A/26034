"""Database operations for anonymous consumer review submissions."""

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ConsumerSafetyClaim, ProductReviewRow

COHORT_LOCK_QUERY = text(
    """SELECT pg_advisory_xact_lock(
        hashtextextended(:lock_key, 0)
    )"""
)
"""PostgreSQL transaction lock for one exact product-and-sentiment cohort."""

COHORT_LOCK_SEPARATOR = "|"
"""Separator used by the unambiguous advisory-lock key encoding."""


async def record_submission(
    session: AsyncSession,
    *,
    product_identifier: str,
    consumer_safety_claim: ConsumerSafetyClaim,
    threshold: int,
) -> bool:
    """Persist a submission and publish its cohort when the threshold is met."""
    if threshold < 1:
        raise ValueError("review publication threshold must be positive")

    lock_key = (
        f"{len(product_identifier)}{COHORT_LOCK_SEPARATOR}"
        f"{product_identifier}{COHORT_LOCK_SEPARATOR}{consumer_safety_claim.value}"
    )
    await session.execute(COHORT_LOCK_QUERY, {"lock_key": lock_key})

    session.add(
        ProductReviewRow(
            product_identifier=product_identifier,
            consumer_safety_claim=consumer_safety_claim,
        )
    )
    await session.flush()

    cohort_filter = (
        ProductReviewRow.product_identifier == product_identifier,
        ProductReviewRow.consumer_safety_claim == consumer_safety_claim,
    )
    counts = await session.execute(
        select(
            func.count(ProductReviewRow.id),
            func.count(ProductReviewRow.id).filter(ProductReviewRow.published_at.is_not(None)),
        ).where(*cohort_filter)
    )
    total_count, published_count = counts.one()
    should_publish = total_count >= threshold or published_count > 0
    if not should_publish:
        return False

    await session.execute(
        update(ProductReviewRow)
        .where(*cohort_filter, ProductReviewRow.published_at.is_(None))
        .values(published_at=func.now())
    )
    return True


async def published_consensus(
    session: AsyncSession, *, product_identifier: str
) -> list[tuple[ConsumerSafetyClaim, int]]:
    """Return only published sentiment aggregates for one normalized product identifier."""
    statement = (
        select(ProductReviewRow.consumer_safety_claim, func.count(ProductReviewRow.id))
        .where(
            ProductReviewRow.product_identifier == product_identifier,
            ProductReviewRow.published_at.is_not(None),
        )
        .group_by(ProductReviewRow.consumer_safety_claim)
        .order_by(ProductReviewRow.consumer_safety_claim.asc())
    )
    return list((await session.execute(statement)).tuples())
