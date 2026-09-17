"""A ``note`` on ``complaints``, and at most one successor per complaint row.

The complaint lifecycle gained its transition endpoint: acknowledge, resolve and reject are
each a new row superseding the head of the thread. Two things the table needed for that.

**``note``.** A superseding row restates ``issue_summary`` by value and must not reword it,
so the officer's words about the transition itself — what the manufacturer did, why the
escalation closed — need a column of their own. Nullable, no backfill: a row written before
this revision recorded no note, and ``NULL`` reads as exactly that.

**``uq_complaints_supersedes_id``.** Append-only threads fork when two rows supersede the
same row. The route checks for a successor before writing, and this constraint is what
holds when two officers pass that check at the same moment. PostgreSQL exempts NULLs from
uniqueness, so every thread's first row is unaffected.

The upgrade fails, deliberately, on a database that already holds a forked thread: two
successors of one row is a history somebody has to read before a constraint is laid over
it, not something a migration should resolve by picking a winner.

Revision ID: 7d2e9a41c3b8
Revises: 5b522f144ba0
Create Date: 2026-09-17 19:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7d2e9a41c3b8"
down_revision: str | None = "5b522f144ba0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("complaints", sa.Column("note", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_complaints_supersedes_id", "complaints", ["supersedes_id"])


def downgrade() -> None:
    op.drop_constraint("uq_complaints_supersedes_id", "complaints", type_="unique")
    op.drop_column("complaints", "note")
