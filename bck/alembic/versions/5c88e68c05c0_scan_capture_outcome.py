"""One nullable column on ``scans`` for what evaluation said about the capture.

``scans.capture_outcome_json`` holds a JSON ``app.pipeline.schemas.CaptureOutcome``: the
quality-gate refusal, the category proposal and the display category. Until now these rode
the submission response and were never stored, which was recorded on the schema as a
deliberate gap with a ticket of its own. Evaluation now finishes after the submission
response has been sent — a phone on a mobile network drops a request that sits silent for
the length of an OCR run — so the only way an officer sees these is by reading the scan
back, and that needs them on the row.

Nullable, with no backfill: a row written before this revision has nothing to report, and
``NULL`` is read as exactly that. Text rather than a JSON type so the mapped metadata
stays portable across the dialects the test suite runs against.

Revision ID: 5c88e68c05c0
Revises: 257f6bc96647
Create Date: 2026-09-08 05:12:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5c88e68c05c0"
down_revision: str | None = "257f6bc96647"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("capture_outcome_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scans", "capture_outcome_json")
