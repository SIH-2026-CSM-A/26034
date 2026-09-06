"""The declarative base and the column plumbing every table here is built from.

Split out of :mod:`app.core.models` when a second module needed the same helpers. What
lives here is the machinery — the naming convention, the dialect-portable JSON type, the
column widths and the enum-column factory — and what lives there is the schema itself.
Nothing in this file knows what a Legal Metrology declaration is, which is the line
``core/README.md`` draws and the reason the tables are allowed to sit in ``core`` at all.

``alembic/env.py`` imports :class:`Base` from here rather than from the ``app.core``
package surface, so a migration learns the shape of the tables without dragging in
FastAPI, PyJWT and bcrypt to do it.
"""

from enum import StrEnum

from sqlalchemy import JSON, Enum, MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
"""Names every constraint and index deterministically. Without it SQLAlchemy emits
unnamed constraints, autogenerate cannot refer to them, and a downgrade has nothing to
drop."""

Json = JSON().with_variant(JSONB(), "postgresql")
"""``jsonb`` on PostgreSQL, ``JSON`` on anything else. One annotation, both dialects."""

JURISDICTION_LEVEL_LENGTH = 120
"""Column width for a state, region or district name."""

SHA256_HEX_LENGTH = 64
"""A SHA-256 digest as :func:`hashlib.sha256().hexdigest` renders it."""


def enum_column(python_enum: type[StrEnum], name: str) -> Enum:
    """A closed vocabulary the database enforces.

    A native ``TYPE`` on PostgreSQL and a ``VARCHAR`` with a ``CHECK`` elsewhere.
    ``values_callable`` stores each member's *value*; SQLAlchemy stores names by default,
    which for the enums here whose name and value differ would put the wrong string on
    disk.
    """
    return Enum(
        python_enum,
        name=name,
        create_constraint=True,
        values_callable=lambda enum: [member.value for member in enum],
    )


class Base(DeclarativeBase):
    """Declarative base for every table in this schema. Alembic reads its metadata."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
