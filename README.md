# 26034 — PCCS

**PCCS — Packaged Commodity Compliance System.** Compliance decision-support for
packaged commodities under the Legal Metrology (Packaged Commodities) Rules 2011.
SIH 2026, problem statement 26034.

Monorepo: `bck/` is the FastAPI backend, `fnt/` is the frontend (not yet scaffolded).

Read [AGENTS.md](AGENTS.md) before your first PR — it has the ownership map, the import
rule, and the branching conventions this repo uses instead of the T4 defaults.

## Setup

Requires Python 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:Abhiram-0910/26034.git
cd 26034/bck
uv sync --all-groups
cp .env.example .env     # then fill it in
```

`uv sync` creates `bck/.venv` and installs the backend in editable mode. You do not need
to activate it — prefix commands with `uv run`.

## Run

No application entrypoint yet; `app/` holds the package skeleton only. Once
`app/pipeline/` has an ASGI app it starts with:

```bash
uv run uvicorn app.main:app --reload
```

## Test

From `bck/`. This is exactly what CI runs on every PR:

```bash
uv run ruff check .
uv run ruff format --check .
uv run lint-imports
uv run pytest
```

## Environment variables

Every variable the backend reads is listed in [`bck/.env.example`](bck/.env.example) with
a comment saying what it is for. `.env` is git-ignored; never commit real values.

`DATABASE_URL` is the only one with no usable default — the rest have sensible local
values. It is read by both SQLAlchemy and Alembic.

## Troubleshooting

**`lint-imports` fails with "not allowed to import".** Working as intended. A module may
import `app.contracts`, `app.core`, and itself — nothing else. See the import rule in
AGENTS.md; the fix is to move the shared piece down into `contracts` or `core`, not to
widen the contract.

**`pytest` fails in `test_import_boundaries.py`.** You added a package under
`app/modules/` without adding it to the independence contract in `bck/pyproject.toml`.
Add it there and to `.github/CODEOWNERS`.

**`ModuleNotFoundError: app`.** You ran outside `uv run`, or from the repo root. Backend
commands run from `bck/`.

**`uv sync --locked` fails in CI but works locally.** You changed a dependency without
committing the regenerated `bck/uv.lock`.

## Layout

| Path | Holds |
|---|---|
| `bck/app/contracts/` | Shared types crossing module boundaries. Imports nothing. |
| `bck/app/core/` | Settings, database session, logging, shared exceptions. |
| `bck/app/modules/` | One vertical slice per capability, one owner each. |
| `bck/app/pipeline/` | The only place modules are composed. |
| `bck/alembic/` | Migrations. |
| `bck/tests/` | Tests, mirroring the package layout. |
| `fnt/` | Frontend. Separate ticket. |
| `datasets/` | Local image/label data. Git-ignored contents. |
| `rules-corpus/` | Machine-readable Legal Metrology rules. Tracked. |
| `session-log/` | One file per person. Never a shared log. |
