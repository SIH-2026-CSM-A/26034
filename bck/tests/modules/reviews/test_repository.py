"""Persistence behavior for anonymous consumer review publication."""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import ConsumerSafetyClaim, ProductReviewRow
from app.modules.reviews import service
from app.modules.reviews.constants import REVIEW_PUBLICATION_THRESHOLD

pytestmark = pytest.mark.postgres

BARCODE = "8901234567890"
PUBLICATION_THRESHOLD = REVIEW_PUBLICATION_THRESHOLD


async def stored_reviews(session: AsyncSession) -> list[ProductReviewRow]:
    """Return stored review rows in insertion-independent order."""
    statement = select(ProductReviewRow).order_by(
        ProductReviewRow.submitted_at, ProductReviewRow.id
    )
    return list((await session.scalars(statement)).all())


async def record_submission(session: AsyncSession, claim: ConsumerSafetyClaim) -> bool:
    """Record one submission in the transaction shape the router will use."""
    async with session.begin():
        return await service.record_submission(
            session,
            product_identifier=BARCODE,
            consumer_safety_claim=claim,
        )


async def test_threshold_minus_one_submission_is_held(session: AsyncSession) -> None:
    """A cohort below the publication threshold remains unpublished."""
    published = await record_submission(session, ConsumerSafetyClaim.SAFE)
    rows = await stored_reviews(session)

    assert published is False
    assert len(rows) == 1
    assert rows[0].published_at is None


async def test_threshold_crossing_publishes_all_matching_rows(session: AsyncSession) -> None:
    """The threshold-crossing submission publishes the complete matching cohort."""
    await record_submission(session, ConsumerSafetyClaim.SAFE)
    await record_submission(session, ConsumerSafetyClaim.SAFE)
    published = await record_submission(session, ConsumerSafetyClaim.SAFE)
    rows = await stored_reviews(session)

    assert published is True
    assert len(rows) == PUBLICATION_THRESHOLD
    assert all(row.published_at is not None for row in rows)


async def test_threshold_plus_one_submission_is_published_immediately(
    session: AsyncSession,
) -> None:
    """A matching submission after publication is immediately made visible."""
    for _ in range(PUBLICATION_THRESHOLD):
        await record_submission(session, ConsumerSafetyClaim.SAFE)

    published = await record_submission(session, ConsumerSafetyClaim.SAFE)
    rows = await stored_reviews(session)

    assert published is True
    assert len(rows) == PUBLICATION_THRESHOLD + 1
    assert all(row.published_at is not None for row in rows)


async def test_opposing_sentiment_cohorts_publish_independently(session: AsyncSession) -> None:
    """SAFE publication does not publish a sub-threshold UNSAFE cohort."""
    for _ in range(PUBLICATION_THRESHOLD):
        await record_submission(session, ConsumerSafetyClaim.SAFE)
    await record_submission(session, ConsumerSafetyClaim.UNSAFE)

    rows = await stored_reviews(session)
    safe_rows = [row for row in rows if row.consumer_safety_claim is ConsumerSafetyClaim.SAFE]
    unsafe_rows = [row for row in rows if row.consumer_safety_claim is ConsumerSafetyClaim.UNSAFE]

    assert all(row.published_at is not None for row in safe_rows)
    assert all(row.published_at is None for row in unsafe_rows)


async def test_published_consensus_excludes_held_cohorts(session: AsyncSession) -> None:
    """Public aggregation includes only cohorts whose rows are published."""
    for _ in range(PUBLICATION_THRESHOLD):
        await record_submission(session, ConsumerSafetyClaim.SAFE)
    await record_submission(session, ConsumerSafetyClaim.UNSAFE)

    aggregates = await service.get_published_consensus(session, product_identifier=BARCODE)

    assert aggregates == [(ConsumerSafetyClaim.SAFE, PUBLICATION_THRESHOLD)]


async def test_published_consensus_can_show_both_sentiments(session: AsyncSession) -> None:
    """Opposing cohorts are published and aggregated independently."""
    for claim in (ConsumerSafetyClaim.SAFE, ConsumerSafetyClaim.UNSAFE):
        for _ in range(PUBLICATION_THRESHOLD):
            await record_submission(session, claim)

    aggregates = await service.get_published_consensus(session, product_identifier=BARCODE)

    assert aggregates == [
        (ConsumerSafetyClaim.SAFE, PUBLICATION_THRESHOLD),
        (ConsumerSafetyClaim.UNSAFE, PUBLICATION_THRESHOLD),
    ]


async def test_concurrent_same_cohort_threshold_crossing_publishes_every_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Separate sessions serialize a same-cohort threshold crossing atomically."""

    async def submit() -> bool:
        """Submit one matching review through its own session and transaction."""
        async with session_factory() as separate_session, separate_session.begin():
            return await service.record_submission(
                separate_session,
                product_identifier=BARCODE,
                consumer_safety_claim=ConsumerSafetyClaim.SAFE,
            )

    responses = await asyncio.gather(*(submit() for _ in range(PUBLICATION_THRESHOLD)))

    async with session_factory() as verification_session:
        rows = await stored_reviews(verification_session)
        assert len(rows) == PUBLICATION_THRESHOLD
        assert all(row.published_at is not None for row in rows)
        assert responses.count(True) == 1


async def test_concurrent_opposing_cohorts_publish_independently(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Separate SAFE and UNSAFE locks preserve independent concurrent cohorts."""

    async def submit(claim: ConsumerSafetyClaim) -> bool:
        """Submit one sentiment through a separate request-equivalent session."""
        async with session_factory() as separate_session, separate_session.begin():
            return await service.record_submission(
                separate_session,
                product_identifier=BARCODE,
                consumer_safety_claim=claim,
            )

    responses = await asyncio.gather(
        *(
            submit(claim)
            for claim in (ConsumerSafetyClaim.SAFE, ConsumerSafetyClaim.UNSAFE)
            for _ in range(PUBLICATION_THRESHOLD)
        )
    )

    async with session_factory() as verification_session:
        rows = await stored_reviews(verification_session)
        assert len(rows) == PUBLICATION_THRESHOLD * 2
        assert all(row.published_at is not None for row in rows)
        assert responses.count(True) == 2
