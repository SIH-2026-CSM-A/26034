"""What each evidence entry holds, and therefore when it may be destroyed.

``evidence_entries.asset_type`` is the field a retention window is read from. It is
required with no server default, deliberately: a default would let an entry carry a
disposition nobody chose, on the one column that decides whether evidence is destroyed.
``ADD COLUMN ... NOT NULL`` with no default succeeds only on an empty table, which is the
wanted behaviour — a database holding rows should fail loudly here rather than have a
retention class invented for evidence already captured. ``evidence_entries`` held zero
rows when this was written, and the project has never been deployed.

The value is also inside :func:`app.modules.evidence.chain.compute_entry_hash`. Outside
it, an entry could be relabelled from one asset class to another, fall under a different
retention rule, and ``verify_chain`` would still report the chain intact.

**Three members, not a taxonomy.** A member ships only alongside something that consumes
it — a retention window, a purge branch, or a hash input. Adding one later needs a
hand-written ``ALTER TYPE evidence_asset_type ADD VALUE``, which cannot run inside a
transaction and which ``alembic check`` does not report as drift: it passes clean and then
fails at the first insert with ``invalid input value for enum``.

The type is created and dropped explicitly rather than left to ``sa.Enum``'s implicit
creation inside ``add_column``, so the downgrade is symmetric and
``test_every_enum_type_holds_exactly_its_python_members`` can see it disappear. The column
therefore references the type with ``create_type=False`` — creating it twice is the
failure ``c16334c8d865`` recorded hitting.

Revision ID: a3f1d2e7b504
Revises: c16334c8d865
Create Date: 2026-09-07 10:22:41.118904
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a3f1d2e7b504"
down_revision: str | None = "c16334c8d865"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EVIDENCE_ASSET_TYPE_LABELS = ("PRODUCT_IMAGE", "PERSONAL_DATA", "AUDIT_LOG")

evidence_asset_type = sa.Enum(
    *EVIDENCE_ASSET_TYPE_LABELS,
    name="evidence_asset_type",
    create_constraint=True,
)
"""Created by this revision, and therefore dropped by its downgrade."""


def upgrade() -> None:
    evidence_asset_type.create(op.get_bind(), checkfirst=False)
    op.add_column(
        "evidence_entries",
        sa.Column(
            "asset_type",
            postgresql.ENUM(
                *EVIDENCE_ASSET_TYPE_LABELS,
                name="evidence_asset_type",
                create_type=False,
            ),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("evidence_entries", "asset_type")
    evidence_asset_type.drop(op.get_bind(), checkfirst=False)
