# alembic

**Owner:** @Abhiram-0910

Database migrations. Every schema change ships as a migration — no hand-edited
databases, in any environment.

Run from `bck/`: `uv run alembic upgrade head`.

Migrations read `DATABASE_URL` through `app.core.config`, not from `alembic.ini` — there
is deliberately no `sqlalchemy.url` in the ini file, so a connection string is never
committed and there is no second copy to drift. A migration that touches a table owned by
a module gets that module's owner on the PR.

**Autogenerate does not write `DROP TYPE`.** A `sa.Enum` column creates a PostgreSQL type
implicitly on upgrade and autogenerate emits nothing to remove it on downgrade. A
downgrade that only drops tables leaves the types behind, and the *next* `upgrade head`
fails with `type "..." already exists` — one command after the one that caused it. Every
revision that adds an enum drops it explicitly, and `tests/persistence/` runs
upgrade → downgrade → upgrade to prove it.

`alembic check` runs in CI and fails on a model edited without a migration.

**Check which server you are migrating before you trust the result.** If a PostgreSQL
cluster already holds `127.0.0.1:5432` on your machine, it shadows the port
`docker-compose.yml` publishes. The container starts and reports healthy either way, but
`DATABASE_URL` then reaches the local cluster, and `alembic upgrade head` migrates that
instead of the container without saying so.

```
psql "$DATABASE_URL" -tAc "select version()"   # must report 16.x
```

To move off the clash, change the published port and the DSN **together**:

```
echo POSTGRES_PORT=5433 >> ../../.env     # repo root — compose reads this one
# and in ../.env:
DATABASE_URL=postgresql+psycopg://pccs:pccs@localhost:5433/pccs
```

They are two different files with nothing linking them. Compose reads `POSTGRES_PORT`
from the `.env` beside `docker-compose.yml` at the repo root; Alembic and the application
read `DATABASE_URL` from `bck/.env`, because `pydantic-settings` resolves
`env_file=".env"` against the working directory and every documented command runs from
`bck/`. Setting one and not the other publishes on one port and connects to another.
