# CLAUDE.md — PCCS (26034)

**PCCS — Packaged Commodity Compliance System.** Compliance decision-support for packaged commodities under the Legal Metrology
(Packaged Commodities) Rules, 2011. Used by Legal Metrology officers — Controller,
Deputy, Inspector — to scan a package or a listing and get evidence-backed findings.

**Stack:** FastAPI + PostgreSQL + PaddleOCR + React, all in Docker Compose
**Run:** `cd bck && uv run uvicorn app.main:app --reload` · **Test:** `cd bck && uv run pytest` · **Lint:** `cd bck && uv run ruff check . && uv run lint-imports`

---

## Gotchas

- **`bck` installs as a real package** (hatchling, `packages = ["app"]`). `lint-imports`
  is a console script, so `sys.path[0]` is the venv's `bin/`, not the working directory.
  Without the installed package it cannot import `app` and the contracts silently
  analyse nothing and report success. If `lint-imports` passes suspiciously fast, check
  the install first.
- **Modules have no empty layer files.** There is no blank `router.py` / `service.py` /
  `repository.py` / `schemas.py` in each module — that would be twenty-four stubs. The
  naming convention is documented in each module's README instead. Create the file when
  you have something to put in it.
- **`contracts/` is single-owner.** If a type you need is missing, stop and raise it.
  Adding it locally will pass your tests and break someone else's merge.
- **Rule parameters are snapshotted into the verdict record**, not joined from the rules
  table. Do not "fix" this by normalising it — replaying an old verdict against today's
  rules is exactly the bug the snapshot prevents.
- **INSUFFICIENT_EVIDENCE is not FAIL.** "We could not read it" and "it is not there" are
  different findings with different legal consequences. Never collapse them.
- **Python is 3.11, not 3.12** — PaddlePaddle and several CV wheels lag.
- **Model weights are gitignored and must be pre-cached locally.** The demo has to
  survive the venue network failing.
- **Cloud OCR is off by default** with a daily page cap of `0` in config. Turning it on
  is a deliberate act, not a fallback that fires on its own.

---

## Constraints

- No new dependencies without asking. Every addition is a package a teammate has to
  install and CI has to build.
- No LLM call and no agent loop anywhere in the verdict path. Deterministic by design.
- Every paid-API call sits inside a cost ceiling read from `core/config.py`.
- Tailwind only in the frontend, no CSS-in-JS.
- No stubs, placeholders, TODO comments or fake data in committed code.
- Rule numbers and thresholds come from `rules-corpus/` and
  `SIH26034_Research_And_References.md`. Never from memory, including yours.

---

## Files Claude should not touch

- `bck/alembic/versions/` — hand-reviewed only; write a new migration, never edit one.
- `fnt/src/services/generated/` — regenerated from the backend OpenAPI schema.
- `rules-corpus/` — immutable source gazettes. Add files, never edit them.
- Any module directory not owned by the person in this session. See `AGENTS.md`.

---

## Session start

Read `SESSION-LOG.md` (what happened before), `TODO.md` (what's next),
`ARCHITECTURE.md` (how it's built). Then state the plan before writing code.

Use `cplan` for anything non-trivial. Load `engineering-standards` for structural work,
`genai-project` for anything touching a model or a paid API, `frontend-work` for UI.

`AGENTS.md` holds the cross-tool rules shared with Antigravity and Codex — module
ownership, the import rule, and the standing constraints that never bend.

## Session end

Tests pass, ruff clean, `lint-imports` clean, `SESSION-LOG.md` and `TODO.md` updated —
noting which agent did the work.
