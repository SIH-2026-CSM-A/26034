# alembic

**Owner:** @Abhiram-0910

Database migrations. Every schema change ships as a migration — no hand-edited
databases, in any environment.

Not yet initialised; `alembic init` and the first revision are a separate ticket. Until
then this directory holds only `.gitkeep`.

Migrations read `DATABASE_URL` from the environment (see `../.env.example`). A migration
that touches a table owned by a module gets that module's owner on the PR.
