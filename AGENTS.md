# AGENTS.md

Cross-tool rules for 26034. Read by Antigravity, Codex, Claude Code and any other
AGENTS.md-aware agent at session start.

**This file holds standing rules, not session history.** Session history lives in
`session-log/<your-name>.md`.

---

## What this is

A compliance decision-support system for packaged commodities under the Legal Metrology
(Packaged Commodities) Rules, 2011. It extracts evidence and recommends. It never issues
a legal determination.

## Stack

Python 3.11, FastAPI, PostgreSQL 16 + pgvector, Redis + arq, MinIO, PaddleOCR,
Tesseract, YOLO (ultralytics), React 18 + TypeScript + Vite + Tailwind, Docker Compose.
Dependencies managed with `uv`.

## Commands

```
install:    cd bck && uv sync
dev:        cd bck && uv run uvicorn app.main:app --reload
test:       cd bck && uv run pytest
lint:       cd bck && uv run ruff check .
format:     cd bck && uv run ruff format --check .
imports:    cd bck && uv run lint-imports
```

All five must pass before a PR is opened. CI runs the same set.

## Standing constraints — these never bend

1. **Verdicts are PASS / REVIEW / POTENTIAL VIOLATION.** Never "violation confirmed",
   never "non-compliant" as a finding. A human confirmation step sits between any output
   and any enforcement action. This applies to code, UI copy, logs and documentation.
2. **Never emit a millimetre font measurement from an uncalibrated photograph.** Three
   modes only: exact from pre-print artwork; a measurement with a stated confidence
   interval when a reference object is in frame; an explicit refusal otherwise, routed
   to human review.
3. **Every legal, factual or statistical claim traces to `SIH26034_Research_And_References.md`.**
   If it is not in that file, do not assert it — not in code, not in a comment, not in a
   UI string.
4. **Rule numbers and thresholds are never written from memory.** They come from the
   files in `rules-corpus/`. A rule with no gazette reference does not ship.
5. **No stubs, no placeholders, no TODO comments, no fake data in committed code.**
   Production-grade from the first commit.

## Module ownership is absolute

You own directories. Nobody else edits them, and you edit nobody else's.

| Directory | Owner |
|---|---|
| `bck/app/contracts/` | Abhiram |
| `bck/app/core/` | Abhiram |
| `bck/app/pipeline/` | Abhiram |
| `bck/alembic/` | Abhiram |
| `.github/` | Abhiram |
| `bck/app/modules/rules/` | Jashwanth |
| `bck/app/modules/vision/` | Akshaya |
| `bck/app/modules/extraction/` | Sitanshu |
| `bck/app/modules/measurement/` | Yashashvi |
| `bck/app/modules/evidence/` | Shiva Kumar |
| `bck/app/modules/tamper/` | Shivasai |
| `fnt/` officer surface | Vineeth |
| `fnt/` admin surface | Rohan |
| `datasets/` | Aashritha |

If a ticket would make you edit outside your directory, that is a ticket bug. Say so and
stop. It gets split into two tickets with a contract between them.

## The import rule

A module may import from `contracts` and `core` and itself. **Nothing else.**
`pipeline` composes modules. `contracts` imports nothing.

Two modules never import each other. When they need to exchange something, it becomes a
type in `contracts/` and `pipeline` passes it.

CI enforces this with import-linter. A cross-module import fails the build before it
reaches a pull request.

## Contracts are not yours to change

Only Abhiram edits `bck/app/contracts/`. If you need a field added or a type changed,
comment on your ClickUp ticket. Do not add it locally and do not work around it.

## Deny rules

- Never modify an existing migration — write a new one.
- Never commit `.env` or any file containing a secret.
- Never add AI-attribution trailers to commit messages.
- Never call a paid API without the cost ceiling in `core/config.py` in the loop.
- Never put an LLM or an agent loop in the verdict path. It is deterministic by design.
- Never widen a verdict enum or a per-field state enum locally.

## Files not to touch

- `fnt/src/services/generated/` — regenerated from the backend OpenAPI schema.
- `rules-corpus/` — immutable source PDFs. Add, never edit.
- Anyone else's module directory.

## Git

- Branch base is `main`. The four-branch develop chain in the shared GitHub doc is
  superseded for this project.
- One ticket = one branch = one PR. Branch name comes pre-written on the ticket.
- Squash merge only. Never merge to `main` yourself — only Abhiram merges.
- Commit incrementally with messages that name the change and its trigger. Evaluators
  read commit history.
- Set your commit email to your GitHub no-reply alias
  (`ID+username@users.noreply.github.com`, found at github.com/settings/emails).
  The repository is public and author emails are scraped.

## Multi-agent

More than one agent works this project — Claude Code, Antigravity and Codex, across
eleven people. Before starting:

1. Read your ClickUp ticket. It names your module, the files you may edit, the branch
   name, and the acceptance criteria.
2. Work on your own branch. Never share a working tree.
3. Record what you did in `session-log/<your-name>.md`, including which agent you are.
   Never write to a shared session log.

## Skills and tools

- Skills load on demand — `engineering-standards` for structure and standards,
  `genai-project` for anything calling a model or a paid API, `frontend-work` for UI.
- MCP config: `.mcp.json`
- Ticket board: ClickUp, list `26034 Build`.
