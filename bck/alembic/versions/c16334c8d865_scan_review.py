"""Officer review of a verdict, and the confirmed product category that routes a scan.

Two additions, both of which exist to keep a decision out of the software's hands.

``scans.product_category`` is the officer's *confirmed* category. Nullable, because the
null is the meaningful value: with no confirmed category the sector dispatch routes
nothing, and every obligation a sector could carve out is INSUFFICIENT_EVIDENCE rather
than evaluated against rules that may not apply to the package. It is a plain string
rather than an enum type because the vocabulary lives in ``app.modules.rules`` and
``app.core`` may not import it; the value is constrained where it enters, at the request
boundary.

``reviews`` is the human confirmation step, as a record. Append-only in shape: there is
no UPDATE path in the repository, and a correction is a new row whose ``supersedes_id``
names the row it replaces. That is what makes "nothing reaches a finalised status without
an officer" structural — finalisation is the existence of a row here, never a column on
``scans`` that a later job could set.

**Why this is hand-written.** Autogenerate emitted ``CREATE TYPE verdict`` for
``reviews.overridden_verdict``, because ``sa.Enum`` inside ``create_table`` creates its
type implicitly and does not know ``64a9392a6859`` already made this one. Running it
failed with ``type "verdict" already exists``. The column below therefore references the
existing type with ``create_type=False``, and the downgrade drops only ``review_action``
— the type this revision actually created. Dropping ``verdict`` here would take the
``verdicts`` table's column with it.

Revision ID: c16334c8d865
Revises: 64a9392a6859
Create Date: 2026-09-06 13:08:16.583005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c16334c8d865"
down_revision: str | None = "64a9392a6859"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


review_action = sa.Enum(
    "confirm",
    "reject",
    "override",
    "annotate",
    "request_recapture",
    name="review_action",
    create_constraint=True,
)
"""Created by this revision, and therefore dropped by its downgrade."""

existing_verdict = postgresql.ENUM(
    "PASS",
    "REVIEW",
    "POTENTIAL_VIOLATION",
    name="verdict",
    create_type=False,
)
"""Created by ``64a9392a6859``. Referenced here, never created and never dropped."""


def upgrade() -> None:
    op.add_column("scans", sa.Column("product_category", sa.String(length=64), nullable=True))

    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("verdict_id", sa.Uuid(), nullable=False),
        sa.Column("action", review_action, nullable=False),
        sa.Column("officer_id", sa.String(length=120), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("overridden_verdict", existing_verdict, nullable=True),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], name=op.f("fk_reviews_scan_id_scans")),
        sa.ForeignKeyConstraint(
            ["supersedes_id"], ["reviews.id"], name=op.f("fk_reviews_supersedes_id_reviews")
        ),
        sa.ForeignKeyConstraint(
            ["verdict_id"], ["verdicts.id"], name=op.f("fk_reviews_verdict_id_verdicts")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reviews")),
    )
    op.create_index(op.f("ix_reviews_scan_id"), "reviews", ["scan_id"], unique=False)
    op.create_index(
        "ix_reviews_scan_id_created_at", "reviews", ["scan_id", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_reviews_scan_id_created_at", table_name="reviews")
    op.drop_index(op.f("ix_reviews_scan_id"), table_name="reviews")
    op.drop_table("reviews")
    review_action.drop(op.get_bind(), checkfirst=False)
    op.drop_column("scans", "product_category")
