"""Vendors, vendor attribution, manufacturer escalations and anonymous consumer reports.

Four tables landed together and ahead of their callers, because migrations are single-owner
here: VND-001, CMP-001 and RVW-001 each need one of these, and landing them reactively
would queue three people behind one. Nothing in this revision has a writer yet.

``vendors`` carries ``state``, ``region`` and ``district`` as three real columns with
exactly those names, mirroring ``scans``. ``app.core.rbac.scope_to_jurisdiction`` reaches
them by ``getattr`` using the ``RoleTier`` member values, so the names are a contract with
that function and folding them into a document would make every scoped query raise. They are
nullable exactly as ``scans``' are: a NULL says the level was never recorded, and the two
tables have to agree about that or a query silently matches nothing.

``vendor_scans`` is three columns and takes ``scan_id`` as its primary key, so
"at most one vendor attribution per scan" is the key rather than a constraint beside it. It
deliberately holds nothing an evaluation could branch on — a vendor-submitted scan is an
ordinary scan carrying an attribution, not a second verdict path, and a column here that
could change how a scan is evaluated would make it one.

``complaints`` is append-only in shape, like ``reviews``: a transition is a new row whose
``supersedes_id`` names the one it replaces, and every row stays. It carries no
``resolved_at`` — on an append-only table a resolution is a new row carrying RESOLVED, so a
resolution timestamp would duplicate that row's own ``raised_at`` and could drift from it.

``product_reviews`` holds **no reviewer identity column of any kind**, and that is the
table's whole guarantee: no user id, no IP, no hash of one, no device fingerprint, no
session id, not "for deduplication". ``anonymous_token`` is a ``uuid`` and not a hex string
so it cannot hold a digest of something about the submitter without a column type change —
which is another migration, which is a review gate. Its uniqueness is not about collisions;
it is there so that reusing one token across a submitter's reports fails on the second
INSERT. ``published_at`` NULL means held pending threshold, and that is the entire
publication mechanism.

**Why this is hand-written.** Autogenerate created the three enum types implicitly inside
``create_table`` and emitted no ``DROP TYPE`` for any of them. A downgrade that left them
behind makes the next upgrade fail with ``type "vendor_type" already exists``, one command
after the one that actually caused it — the failure ``64a9392a6859`` recorded and
``a3f1d2e7b504`` works around the same way. The three types are therefore module-level
objects here and the downgrade drops each explicitly.

All three types are **new**, so none is referenced with ``create_type=False``: that form is
for a type an earlier revision created, as ``c16334c8d865`` does for ``verdict``. No member
is added to any existing enum by this revision, because ``alembic check`` does not compare
the *values* of a type that already exists — it passes clean and then fails at the first
insert with ``invalid input value for enum``.

Revision ID: 257f6bc96647
Revises: a3f1d2e7b504
Create Date: 2026-09-07 18:47:57.992455
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "257f6bc96647"
down_revision: str | None = "a3f1d2e7b504"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


vendor_type = sa.Enum(
    "godown",
    "supermarket",
    "kirana",
    name="vendor_type",
    create_constraint=True,
)

complaint_status = sa.Enum(
    "raised",
    "acknowledged",
    "resolved",
    "rejected",
    name="complaint_status",
    create_constraint=True,
)

consumer_safety_claim = sa.Enum(
    "safe",
    "unsafe",
    name="consumer_safety_claim",
    create_constraint=True,
)
"""Its own type, never ``verdict``. A consumer's report and the rule engine's
recommendation are different vocabularies, and the database refuses each in the other's
column."""

ENUM_TYPES = (vendor_type, complaint_status, consumer_safety_claim)
"""Every enum type this revision creates, in the order the downgrade drops them."""


def upgrade() -> None:
    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_identifier", sa.String(length=64), nullable=False),
        sa.Column("consumer_safety_claim", consumer_safety_claim, nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anonymous_token", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_reviews")),
        sa.UniqueConstraint("anonymous_token", name=op.f("uq_product_reviews_anonymous_token")),
    )
    op.create_index(
        op.f("ix_product_reviews_product_identifier"),
        "product_reviews",
        ["product_identifier"],
        unique=False,
    )

    op.create_table(
        "vendors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("vendor_type", vendor_type, nullable=False),
        sa.Column("state", sa.String(length=120), nullable=False),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vendors")),
    )
    op.create_index(
        "ix_vendors_state_region_district",
        "vendors",
        ["state", "region", "district"],
        unique=False,
    )

    op.create_table(
        "vendor_scans",
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("vendor_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name=op.f("fk_vendor_scans_scan_id_scans")
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"], ["vendors.id"], name=op.f("fk_vendor_scans_vendor_id_vendors")
        ),
        sa.PrimaryKeyConstraint("scan_id", name=op.f("pk_vendor_scans")),
    )
    op.create_index(op.f("ix_vendor_scans_vendor_id"), "vendor_scans", ["vendor_id"], unique=False)

    op.create_table(
        "complaints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("verdict_id", sa.Uuid(), nullable=False),
        sa.Column("manufacturer_name", sa.Text(), nullable=False),
        sa.Column("issue_summary", sa.Text(), nullable=False),
        sa.Column("status", complaint_status, nullable=False),
        sa.Column("raised_by_officer_id", sa.String(length=120), nullable=False),
        sa.Column(
            "raised_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["scans.id"], name=op.f("fk_complaints_scan_id_scans")
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["complaints.id"],
            name=op.f("fk_complaints_supersedes_id_complaints"),
        ),
        sa.ForeignKeyConstraint(
            ["verdict_id"], ["verdicts.id"], name=op.f("fk_complaints_verdict_id_verdicts")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_complaints")),
    )
    op.create_index(op.f("ix_complaints_scan_id"), "complaints", ["scan_id"], unique=False)
    op.create_index(
        "ix_complaints_scan_id_raised_at", "complaints", ["scan_id", "raised_at"], unique=False
    )


def downgrade() -> None:
    """Drop the four tables, including the enum types autogenerate would have left behind."""
    op.drop_index("ix_complaints_scan_id_raised_at", table_name="complaints")
    op.drop_index(op.f("ix_complaints_scan_id"), table_name="complaints")
    op.drop_table("complaints")

    op.drop_index(op.f("ix_vendor_scans_vendor_id"), table_name="vendor_scans")
    op.drop_table("vendor_scans")

    op.drop_index("ix_vendors_state_region_district", table_name="vendors")
    op.drop_table("vendors")

    op.drop_index(op.f("ix_product_reviews_product_identifier"), table_name="product_reviews")
    op.drop_table("product_reviews")

    bind = op.get_bind()
    for enum_type in ENUM_TYPES:
        enum_type.drop(bind, checkfirst=False)
