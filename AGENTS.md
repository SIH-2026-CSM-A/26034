# AGENTS.md

Cross-tool rules for PCCS — Packaged Commodity Compliance System, SIH 2026 PS 26034.
Read by Antigravity, Codex, Claude Code and any other AGENTS.md-aware agent at session start.

**This file holds standing rules, not session history.** Session history lives in
`session-log/<your-name>.md`.

---

## What this is

A compliance decision-support system for packaged commodities under the Legal Metrology
(Packaged Commodities) Rules, 2011. It extracts evidence and recommends. It never issues a
legal determination.

## Stack

Python 3.11, FastAPI, PostgreSQL 16 + pgvector, Redis + arq, MinIO, PaddleOCR, Tesseract,
YOLO (ultralytics), React 18 + TypeScript + Vite + Tailwind, Docker Compose. Dependencies
managed with `uv`.

## Commands

```
install:    cd bck && uv sync
dev:        cd bck && uv run uvicorn app.main:app --reload
test:       cd bck && uv run pytest
lint:       cd bck && uv run ruff check .
format:     cd bck && uv run ruff format --check .
imports:    cd bck && uv run lint-imports
frontend:   cd fnt && npm ci && npx tsc -b && npx vite build
```

All five backend commands must pass before a PR is opened. CI runs the same set, plus the
frontend build on every PR.

## Standing constraints

### The `__pycache__` purge — use the absolute path

```
/usr/bin/find . -name __pycache__ -type d -exec rm -rf {} +
```

Bare `find` is a shell function rerouting to `bfs`. A **single-line** command containing
`find ... -exec` is refused with `rtk: rtk find does not support compound predicates or
actions` and **exits 1**. The same line inside a multi-line command runs normally.

So `find ... && pytest` fails loudly and is safe. `find ... ; pytest` on one line silently
skips the purge and runs pytest against stale bytecode. Most falsifications on this project
are same-byte-length constraint edits (`gt=0` -> `ge=0`), which is exactly the shape a stale
`.pyc` hides.

Always use the absolute path, and assert the directory count is zero rather than trusting an
exit code.

`rtk` also intercepts `gh run view --job ... --log`, returning `rtk: Run ID required`. Use
`gh api repos/<owner>/<repo>/actions/jobs/<id>/logs` instead.
 — these never bend

1. **Verdicts are PASS / REVIEW / POTENTIAL VIOLATION.** Never "violation confirmed", never
   "non-compliant" as a finding, never "illegal". A human confirmation step sits between any
   output and any enforcement action. This applies to code, UI copy, logs, comments, fixture
   data and documentation.
2. **Never emit a millimetre font measurement from an uncalibrated photograph.** Three modes
   only: exact from pre-print artwork; a measurement with a stated confidence interval when a
   reference object is in frame; an explicit refusal otherwise, routed to human review. This
   applies to ground-truth annotations as much as to runtime output.
3. **Every legal, factual or statistical claim traces to `rules-corpus/` or
   `SIH26034_Research_And_References.md`.** If it is not there, do not assert it — not in
   code, not in a comment, not in a UI string, not in a test fixture.
4. **Rule numbers and thresholds are never written from memory.** They come from
   `rules-corpus/`. A rule with no resolvable `gazette_ref` fails to load.
5. **INSUFFICIENT_EVIDENCE is not FAIL.** "We could not read it" and "it is not there" are
   different findings with different legal consequences. Never collapse them, and never put
   them in the same branch of a conditional — including a set membership test.
6. **No stubs, placeholders, TODO comments or fake data in committed code.** Production-grade
   from the first commit.
7. **No LLM call and no agent loop anywhere in the verdict path.** Deterministic by design.
8. **Rebase onto `main`. Never merge `main` into your branch.** `git merge main` on a feature
   branch replays merged history as new work — it produced a 62-file, 6,398-addition diff on
   this repo that had to be thrown away and the two real files re-applied on a fresh branch.
   `git fetch origin && git rebase origin/main && git push --force-with-lease`, run by the
   branch's own owner. **Never rebase someone else's branch for them.** If you have stacked
   branches in one module, rebase them oldest-first or the later ones replay conflicts you
   already resolved.
9. **`session-log/<your-name>.md` is appended to, never rewritten.** Four PRs in one
   session destroyed an earlier ticket's history. Nothing above your new dated heading
   changes — not to reword it, not to improve it.
10. **Run `git status -sb` before every commit.** A commit message containing `(` or `"`
   will do surprising things in bash: one PR landed a 12 KB file at the repo root named
   from the tail of its own commit message. A filename containing `"` cannot be checked
   out on Windows, and it passed both CI jobs.
11. **Migrations are Abhiram's alone.** If your ticket needs a schema change, stop and say
   so — it gets split into two tickets. `alembic/` files can never be edited after merge.
12. **Confidence numbers need a source.** If you cannot cite one, name the value as a
   module-level constant and document it as an uncalibrated prior. Honest and unsourced
   beats confident and unsourced. Two PRs have destroyed
   history in one: #44 deleted `session-log/sitanshu.md` outright, #45 replaced an earlier
   ticket's entries with the current one's. Add a dated section; leave what is above it alone.

## Module ownership is absolute

You own directories. Nobody else edits them, and you edit nobody else's.

| Directory | Owner |
|---|---|
| `bck/app/contracts/` | Abhiram |
| `bck/app/core/` | Abhiram |
| `bck/app/pipeline/` | Abhiram |
| `bck/alembic/` | Abhiram |
| `.github/` | Abhiram |
| `bck/app/modules/rules/` | Abhiram *(from Jashwanth, unavailable)* |
| `bck/app/modules/vision/` | Akshaya |
| `bck/app/modules/tamper/` | Akshaya *(from Shivasai)* |
| `bck/app/modules/extraction/` | Sitanshu |
| `bck/app/modules/measurement/` | Yashashvi |
| `bck/app/modules/evidence/` | Shiva Kumar |
| `fnt/` officer surface | Abhiram *(Vineeth's module, he is unavailable)* |
| `fnt/` admin surface | Rohan |
| `datasets/` | Abhiram *(from Aashritha, off the project)* |

Reassignments are recorded, not silent. If a ticket would make you edit outside your
directory, that is a ticket bug. Say so and stop — it gets split into two tickets with a
contract between them.

**Recorded shifts, 2026-09-06.** `datasets/` moved off Aashritha to Abhiram — she is off the
project, DAT-001 is superseded by DAT-002 + DAT-003, assign her nothing. `extraction/` is
**Sitanshu's**: EXT-004 was a one-off exception delivered by B.V. Yashwanth because Sitanshu
had never started it, and it does not extend past that ticket — EXT-005 and EXT-006 are his.
`measurement/` is Yashashvi's and she is active again. CODEOWNERS still names Aashritha on
`datasets/`; DAT-003 corrects it and is unmerged, so the file currently lies.

## The import rule

A module may import from `contracts` and `core` and itself. **Nothing else.** `pipeline`
composes modules and is the one package permitted to import from `app.modules.*`.
`contracts` imports nothing.

Two modules never import each other. When they need to exchange something, it becomes a type
in `contracts/` and `pipeline` passes it.

CI enforces this with import-linter — three contracts: layer order, module independence, and
no `bck.*` import path. Import from `app.…`, never `bck.app.…`; the second creates a parallel
import path that defeats the contracts silently.

## Contracts are not yours to change

Only Abhiram edits `bck/app/contracts/`. If you need a field added or a type changed, comment
on your ClickUp ticket. Do not add it locally and do not work around it.

Import from the package, never from a file inside it:

```python
from app.contracts import DeclarationField, FieldState, MeasurementResult, VerdictRecord
```

If you are carrying a local stand-in for one of these, delete it and import the real one.

## Testing

- **Every guard needs a test that can fail.** Before you claim a test proves something,
  introduce the defect it guards against and confirm the test goes red, then revert. A test
  that passes against a broken implementation is worse than no test — it is a false
  assurance that survives review.
- If a test cannot be made to fail, say so and **correct the claim**, not the code. Rename it
  to state what it actually proves and put the reason in its docstring.
- Mocking the library under test and then asserting the mock behaved is not a test.

## Deny rules

- Never modify an existing migration — write a new one.
- Never commit `.env` or any file containing a secret.
- **Never add AI-attribution trailers to commit messages or PR bodies.** The repo is public
  and scraped.
- Never call a paid API without the cost ceiling in `core/config.py` in the loop.
- Never widen a verdict enum or a per-field state enum locally.
- Never add a dependency without flagging it in the PR description first.

## Files not to touch

- `fnt/src/services/generated/` — regenerated from the backend OpenAPI schema.
- `rules-corpus/` — immutable source PDFs. Add, never edit.
- `fnt/src/layout/AppShell.tsx` — shared with the admin surface.
- Anyone else's module directory.

## Git

- Branch base is `main`. The four-branch develop chain in the shared GitHub doc is superseded.
- One ticket = one branch = one PR. Branch name comes pre-written on the ticket.
- Squash merge only. Never merge to `main` yourself — only Abhiram merges.
- Commit incrementally with messages that name the change and its trigger. Evaluators read
  commit history.
- Set your commit email to your GitHub no-reply alias
  (`ID+username@users.noreply.github.com`). The repository is public and author emails are
  scraped.
- **`git branch` does not switch to the branch.** Run `git status -sb` before every commit.
- **`--ours` and `--theirs` mean opposite things in rebase versus merge.** Know which
  operation you are in before using either.

## Multi-agent

More than one agent works this project — Claude Code, Antigravity and Codex, across eleven
people. Before starting:

1. Read your ClickUp ticket. It names your module, the files you may edit, the branch name,
   and the acceptance criteria.
2. Work on your own branch. **Never share a working tree** — use `git worktree add` if you
   need a second checkout, and never run manual git commands in a folder another agent has
   open.
3. Record what you did in `session-log/<your-name>.md`, including which agent you are. Never
   write to a shared session log.

## Skills and tools

- `engineering-standards` for structure and standards · `genai-project` for anything calling
  a model or a paid API · `frontend-work` and `hallmark` for UI · `playwright-cli` for
  verifying a UI in a real browser, which is the only thing that catches breakpoint-specific
  rendering failures.
- MCP config: `.mcp.json` · Ticket board: ClickUp, list `26034 Build`.

## Before opening any PR

**Rebase onto `main` immediately before opening, every time**, even if you don't suspect
drift. Branches created early and pushed late are the recurring cause of stale-base conflicts
and missing CI runs on this project. If `gh pr checks` says "no checks reported", that is a
rebase signal, not a CI outage.
