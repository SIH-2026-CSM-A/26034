# CLAUDE.md — PCCS (26034)

**PCCS — Packaged Commodity Compliance System.** Compliance decision-support for packaged
commodities under the Legal Metrology (Packaged Commodities) Rules, 2011. Used by Legal
Metrology officers — Controller, Deputy, Inspector — to scan a package or a listing and get
evidence-backed findings.

**Stack:** FastAPI + PostgreSQL + PaddleOCR + React, all in Docker Compose
**Run:** `cd bck && uv run uvicorn app.main:app --reload` · **Test:** `cd bck && uv run pytest`
· **Lint:** `cd bck && uv run ruff check . && uv run lint-imports`

---

## Gotchas

- **`bck` installs as a real package** (hatchling, `packages = ["app"]`). `lint-imports` is a
  console script, so `sys.path[0]` is the venv's `bin/`, not the working directory. Without
  the installed package it cannot import `app`, and the contracts silently analyse nothing
  and report success. If `lint-imports` passes suspiciously fast, check the install first.
- **Check exit codes directly, not through a pipe.** `lint-imports | tail` reports `tail`'s
  status, which is always 0.
- **Modules have no empty layer files.** There is no blank `router.py` / `service.py` /
  `repository.py` / `schemas.py` in each module — that would be twenty-four stubs. The naming
  convention is documented in each module's README instead. Create the file when you have
  something to put in it.
- **`contracts/` is single-owner.** If a type you need is missing, stop and raise it. Adding
  it locally will pass your tests and break someone else's merge.
- **`pipeline/` is the only package allowed to import `app.modules.*`.** That is what
  "pipeline composes modules" means. Modules still never import each other.
- **Rule parameters are snapshotted into the verdict record**, not joined from the rules
  table. Do not "fix" this by normalising it — replaying an old verdict against today's rules
  is exactly the bug the snapshot prevents.
- **`RuleParameterSnapshot.from_rule`'s deepcopy is documented as not load-bearing today** —
  pydantic's `JsonValue` re-validation already rebuilds every container. It ships as
  annotation-independence. Its test says in its own docstring that it cannot fail under the
  current annotation. Do not "repair" that test.
- **Every new rule needs its own condition kind, not `declaration_required`.**
  `bck/tests/pipeline/test_rule_snapshot.py` asserts exact equality between
  `DECLARATION_FIELDS` and the strings in `rules.yaml`. Do not edit that assertion to make
  room for a rule.
- **INSUFFICIENT_EVIDENCE is not FAIL.** Never collapse them, and never put them in the same
  branch — including a set membership test, which is one edit away from also containing FAIL.
- **Python is 3.11, not 3.12** — PaddlePaddle and several CV wheels lag.
- **Model weights are gitignored and must be pre-cached locally.** The demo has to survive
  the venue network failing.
- **Cloud OCR is off by default** with a daily page cap of `0` in config. Turning it on is a
  deliberate act, not a fallback that fires on its own.
- **`main` may be checked out in another worktree.** `git checkout main` will fail with
  "already used by worktree at …". Detach that worktree first rather than fighting it.
- **A duplicate SVG pattern `id` across breakpoint variants** resolves `url(#…)` to the
  hidden element and paints nothing. Scope with `useId`. Only a real browser at two widths
  catches this.

---

## Constraints

- No new dependencies without asking. Every addition is a package a teammate has to install
  and CI has to build.
- No LLM call and no agent loop anywhere in the verdict path. Deterministic by design.
- Every paid-API call sits inside a cost ceiling read from `core/config.py`.
- Tailwind only in the frontend, no CSS-in-JS.
- No stubs, placeholders, TODO comments or fake data in committed code.
- Rule numbers and thresholds come from `rules-corpus/` and
  `SIH26034_Research_And_References.md`. Never from memory, including yours.
- No AI-attribution trailer on a commit message or a PR body. The repo is public and scraped.

---

## Prove your tests can fail

Before claiming a guard works, introduce the defect it guards against and confirm the test
goes red, then revert. Five separate PRs on this project shipped tests that could not fail:
a network-isolation test with the library mocked, a mutation test against a frozen object, an
adversarial test asserting a stub returned what it was told, a directory scan resolving a
relative path to nothing.

If a test genuinely cannot be made to fail, **correct the claim, not the code.** Rename it to
say what it actually proves and put the reason in its docstring. That is a better outcome
than a decorative green tick, and it is explicitly the behaviour wanted here.

---

## Files Claude should not touch

- `bck/alembic/versions/` — hand-reviewed only; write a new migration, never edit one.
- `fnt/src/services/generated/` — regenerated from the backend OpenAPI schema.
- `rules-corpus/` — immutable source gazettes. Add files, never edit them.
- `fnt/src/layout/AppShell.tsx` — shared with the admin surface.
- Any module directory not owned by the person in this session. See `AGENTS.md`.

---

## Session start

Read `session-log/<name>.md` (what happened before), `TODO.md` (what's next),
`ARCHITECTURE.md` (how it's built). Then state the plan before writing code.

Use `cplan` for anything non-trivial. Load `engineering-standards` for structural work,
`explore-codebase` to navigate via the knowledge graph rather than scanning files,
`genai-project` for anything touching a model or a paid API, `frontend-work` plus `hallmark`
for UI, and `playwright-cli` before claiming a UI works.

`AGENTS.md` holds the cross-tool rules shared with Antigravity and Codex — module ownership,
the import rule, and the standing constraints that never bend.

## Session end

Tests pass, ruff clean, `lint-imports` clean, `session-log/<name>.md` and `TODO.md` updated —
noting which agent did the work. Doc updates go in their own PR, not folded into a code
ticket whose Files field excludes them.
