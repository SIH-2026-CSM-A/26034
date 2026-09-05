# Session log — Abhiram

### 2026-09-05 — VP-CI-001 repo scaffold — Claude Code

**Done**
- `bck/` package skeleton: `contracts`, `core`, `pipeline`, and six module packages under
  `modules/`. Every directory has a README naming its owner.
- `bck/pyproject.toml` — Python 3.11, uv, FastAPI stack, dev group, ruff (line 100,
  py311, E/F/I/N/UP/B/SIM), and the two import-linter contracts.
- `.github/workflows/ci.yml` — ruff check, ruff format --check, lint-imports, pytest on
  every PR, with uv cached against `bck/uv.lock`.
- `.github/CODEOWNERS`, `.gitignore`, `bck/.env.example`, `AGENTS.md`, root `README.md`.
- Fixed `.github/workflows/claude.yml` re-triggering on its own replies
  (`github.actor != 'claude'` guard around the existing condition).
- Verified the boundary rather than assuming it: added
  `from app.modules import rules` to `vision/__init__.py`, `lint-imports` exited 1 naming
  the violation, removed it, re-ran the full set green. Also confirmed
  `test_import_boundaries.py` fails when a module package exists without a contract entry.

**Decided**
- Layers nest inside each module (`router.py`/`service.py`/`repository.py`/`schemas.py`),
  not as top-level `api/`/`services/`/`repositories/`. Deviation from T3 §4, recorded in
  AGENTS.md. Reason: ten owners; horizontal layers make every ticket a three-way
  ownership collision. Rejected the T3 layout for that reason — do not re-propose it.
- Base branch is `main`. T4's develop→staging→release→production chain is superseded here;
  one environment does not justify a four-branch promotion chain.
- No empty `router.py`/`service.py` files. The ticket bars stubs, so the layer convention
  is documented in each module README instead of pre-created as empty files.
- `bck` is installed as a real package (hatchling) rather than relying on cwd being on
  `sys.path` — `lint-imports` is a console script and would not have found `app` otherwise.
- Rejected a `docs/` directory (T3 §3 checklist) for now — nothing to put in it yet, and
  an empty one is exactly the placeholder the ticket rules out.

**Incomplete**
- Alembic not initialised — `bck/alembic/` is `.gitkeep` + README. Separate ticket.
- No application entrypoint; `uv run uvicorn app.main:app` in the README is the target,
  not something that runs today.
- GitHub usernames unconfirmed for `measurement` and `rules`; both fall back to
  @Abhiram-0910 in CODEOWNERS and AGENTS.md. Update both files together when known.
- Branch protection on `main` (PR-only, CI green) is a GitHub settings change, not a file
  — still needs doing in the repo settings.
