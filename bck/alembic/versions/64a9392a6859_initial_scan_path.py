"""Initial scan path: scans, verdicts, field findings and the evidence chain.

The four tables the scan path writes, and nothing else. No users table — officers are
still seeded from ``OFFICERS`` — and no table for a module that has no caller yet.

**About the downgrade.** Autogenerate emits ``CREATE TYPE`` implicitly, through the
``sa.Enum`` columns in ``create_table``, and emits no ``DROP TYPE`` at all. A downgrade
that only dropped the tables would leave six enum types behind, and the *next*
``upgrade head`` would fail with ``type "field_state" already exists`` — one command
after the one that actually caused it. So the enum types are dropped explicitly below,
from the same type objects the upgrade created them from, which is why those objects are
defined once at module level rather than inline.

The downgrade destroys evidence records. It exists for development and for the
upgrade/downgrade/upgrade check that proves the type drops are real. On a deployment
holding verdicts an officer has acted on, the recovery is a restore, not a downgrade.

Revision ID: 64a9392a6859
Revises:
Create Date: 2026-09-06 09:26:09.510414
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "64a9392a6859"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


scan_source_type = sa.Enum(
    "physical_label", "catalogue_record", name="scan_source_type", create_constraint=True
)
scan_status = sa.Enum(
    "received", "processing", "complete", "failed", name="scan_status", create_constraint=True
)
calibration_method = sa.Enum(
    "artwork", "reference_object", "none", name="calibration_method", create_constraint=True
)
verdict = sa.Enum("PASS", "REVIEW", "POTENTIAL_VIOLATION", name="verdict", create_constraint=True)
field_state = sa.Enum(
    "PASS",
    "FAIL",
    "REVIEW_REQUIRED",
    "NOT_APPLICABLE",
    "INSUFFICIENT_EVIDENCE",
    name="field_state",
    create_constraint=True,
)
declaration_field = sa.Enum(
    "NAME_AND_ADDRESS",
    "COUNTRY_OF_ORIGIN",
    "COMMON_OR_GENERIC_NAME",
    "NET_QUANTITY",
    "MANUFACTURE_DATE",
    "BEST_BEFORE_DATE",
    "RETAIL_SALE_PRICE",
    "DIMENSIONS",
    "OTHER_PRESCRIBED_MATTER",
    "CONSUMER_CARE",
    "UNIT_SALE_PRICE",
    name="declaration_field",
    create_constraint=True,
)

ENUM_TYPES = (
    declaration_field,
    field_state,
    verdict,
    calibration_method,
    scan_status,
    scan_source_type,
)
"""Every enum type this revision creates, in the order the downgrade drops them."""

json_document = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
"""``jsonb`` on PostgreSQL. Matches ``app.core.models.Json`` so ``alembic check`` is quiet."""


def upgrade() -> None:
    """Create the scan path."""
    op.create_table(
        "scans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", scan_source_type, nullable=False),
        sa.Column("status", scan_status, nullable=False),
        sa.Column("calibration_method", calibration_method, nullable=False),
        sa.Column("state", sa.String(length=120), nullable=False),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=True),
        sa.Column("officer_id", sa.String(length=120), nullable=False),
        sa.Column("rule_set_version", sa.String(length=64), nullable=False),
        sa.Column("image_refs", json_document, nullable=False),
        sa.Column("capture_metadata", json_document, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scans")),
    )
    op.create_index(
        "ix_scans_state_region_district",
        "scans",
        ["state", "region", "district"],
        unique=False,
    )

    op.create_table(
        "evidence_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("storage_ref", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name=op.f("fk_evidence_entries_scan_id_scans")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_entries")),
        sa.UniqueConstraint(
            "scan_id", "sequence", name=op.f("uq_evidence_entries_scan_id_sequence")
        ),
    )
    op.create_index(
        op.f("ix_evidence_entries_scan_id"), "evidence_entries", ["scan_id"], unique=False
    )

    op.create_table(
        "verdicts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("verdict", verdict, nullable=False),
        sa.Column("subject_ref", sa.Text(), nullable=False),
        sa.Column("rule_set_version", sa.String(length=64), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("field_providers", json_document, nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], name=op.f("fk_verdicts_scan_id_scans")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verdicts")),
    )
    op.create_index(op.f("ix_verdicts_scan_id"), "verdicts", ["scan_id"], unique=False)

    op.create_table(
        "field_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("verdict_id", sa.Uuid(), nullable=False),
        sa.Column("field", declaration_field, nullable=False),
        sa.Column("state", field_state, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("observed_value", sa.Text(), nullable=True),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("rule_snapshot", json_document, nullable=False),
        sa.Column("evidence_span_ids", json_document, nullable=False),
        sa.Column("evidence_regions", json_document, nullable=False),
        sa.ForeignKeyConstraint(
            ["verdict_id"], ["verdicts.id"], name=op.f("fk_field_findings_verdict_id_verdicts")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_field_findings")),
    )
    op.create_index(
        op.f("ix_field_findings_verdict_id"), "field_findings", ["verdict_id"], unique=False
    )


def downgrade() -> None:
    """Drop the scan path, including the enum types autogenerate would have left behind."""
    op.drop_index(op.f("ix_field_findings_verdict_id"), table_name="field_findings")
    op.drop_table("field_findings")
    op.drop_index(op.f("ix_verdicts_scan_id"), table_name="verdicts")
    op.drop_table("verdicts")
    op.drop_index(op.f("ix_evidence_entries_scan_id"), table_name="evidence_entries")
    op.drop_table("evidence_entries")
    op.drop_index("ix_scans_state_region_district", table_name="scans")
    op.drop_table("scans")

    bind = op.get_bind()
    for enum_type in ENUM_TYPES:
        enum_type.drop(bind, checkfirst=False)
