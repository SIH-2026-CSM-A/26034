"""One nullable ``ward`` column on ``scans`` for where a package was inspected.

The dashboard used to derive a ward from ``hash(scan_id) % 6`` over six invented names.
That was never a location — it was a placeholder that could read as one. This column
holds the GHMC ward the officer actually named at capture, so the jurisdiction heatmap
aggregates a recorded value rather than a hash.

A *location*, not a level of authority. It sits outside
:func:`app.core.rbac.scope_to_jurisdiction` — a ward is finer than the three RBAC tiers,
the system holds no ward-to-district map to validate it against, and nothing keys
visibility on it. That is also why it is the one column on this table populated from the
request body rather than from the caller's verified token; see ``app.core.models.Scan``.

Nullable, with no backfill in the schema: a row written before this revision named no
ward, and ``NULL`` reads as exactly that. The demonstration seed backfills its own rows
with a spread of real wards through ``scripts/seed_demo.py --backfill-wards`` — data, not
schema, and never a migration's job.

Revision ID: 5b522f144ba0
Revises: 5c88e68c05c0
Create Date: 2026-09-08 07:24:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5b522f144ba0"
down_revision: str | None = "5c88e68c05c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("ward", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("scans", "ward")
