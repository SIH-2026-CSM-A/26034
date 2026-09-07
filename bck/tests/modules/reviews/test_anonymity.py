"""Structural anonymity guarantees for the existing review persistence model."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ConsumerSafetyClaim, ProductReviewRow
from app.modules.reviews import service

pytestmark = pytest.mark.postgres

BARCODE = "8901234567890"


def test_product_review_schema_has_only_anonymous_review_fields() -> None:
    """The review table exposes no submitter identity or relationship fields."""
    column_names = set(ProductReviewRow.__table__.c.keys())

    assert column_names == {
        "id",
        "product_identifier",
        "consumer_safety_claim",
        "submitted_at",
        "published_at",
        "anonymous_token",
    }
    assert ProductReviewRow.__table__.foreign_keys == set()


async def test_each_persisted_review_receives_a_distinct_row_token(
    session: AsyncSession,
) -> None:
    """The row token is generated independently for each stored submission."""
    async with session.begin():
        for _ in range(2):
            await service.record_submission(
                session,
                product_identifier=BARCODE,
                consumer_safety_claim=ConsumerSafetyClaim.SAFE,
            )

    rows = list(
        (
            await session.scalars(
                select(ProductReviewRow).order_by(
                    ProductReviewRow.submitted_at, ProductReviewRow.id
                )
            )
        ).all()
    )

    assert len(rows) == 2
    assert rows[0].anonymous_token != rows[1].anonymous_token
