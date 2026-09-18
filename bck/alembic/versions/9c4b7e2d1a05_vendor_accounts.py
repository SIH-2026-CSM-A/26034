"""``vendor_accounts``: a login per registered premises, for vendor self-scan.

Vendors at godowns, supermarkets and kirana shops scan their own stock; the scan reaches
the officer whose jurisdiction covers the premises. That needs a vendor to be able to log
in, and this is where the credential lives — one row per vendor, keyed on the vendor, with
a bcrypt hash produced by ``app.core.auth.hash_password`` and a unique username.

A separate table rather than two nullable columns on ``vendors``: a premises written by
scan attribution alone has no login, and "no login" is the absence of a row here rather
than a NULL that every reader of the register has to remember to check.

Revision ID: 9c4b7e2d1a05
Revises: 7d2e9a41c3b8
Create Date: 2026-09-18 00:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9c4b7e2d1a05"
down_revision: str | None = "7d2e9a41c3b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendor_accounts",
        sa.Column("vendor_id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"], ["vendors.id"], name=op.f("fk_vendor_accounts_vendor_id_vendors")
        ),
        sa.PrimaryKeyConstraint("vendor_id", name=op.f("pk_vendor_accounts")),
        sa.UniqueConstraint("username", name=op.f("uq_vendor_accounts_username")),
    )


def downgrade() -> None:
    op.drop_table("vendor_accounts")
