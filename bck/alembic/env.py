"""Alembic's entry point: where the DSN and the target metadata come from.

Two deliberate choices.

**The DSN comes from ``app.core.config``, not from ``alembic.ini``.** One setting, read
from the environment, used by the application and by migrations alike. There is no
``sqlalchemy.url`` in the ini file, so a connection string cannot be committed by
accident and there is no second copy to fall out of step.

**Migrations run synchronously against that same string.** The application opens it with
``create_async_engine``; here it is opened with ``create_engine``. SQLAlchemy picks the
mode from the constructor rather than from the URL, so ``postgresql+psycopg://`` serves
both and neither side has to rewrite the other's scheme.

``Base`` is imported from ``app.core.models`` rather than from the ``app.core`` package
surface on purpose: a migration has no business dragging in FastAPI, PyJWT and bcrypt
just to learn the shape of four tables.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.core.config import get_settings
from app.core.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """The DSN, or a failure that names the setting that is missing."""
    database_url = get_settings().database_url
    if database_url is None:
        raise RuntimeError(
            "DATABASE_URL is not set; alembic has no database to migrate. See bck/.env.example."
        )
    return database_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it, for a reviewed hand-applied change."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect and run the migrations.

    ``compare_type=True`` so ``alembic check`` notices a column whose type changed in
    the models and not in a migration — the drift a schema picks up when a model edit
    ships without one.
    """
    connectable = create_engine(_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
