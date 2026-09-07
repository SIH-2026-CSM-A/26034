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

### CI

`datasets` is a required status check. Three checks report on every PR. **"Require branches to be up to date before merging" is deliberately unchecked** — turning it on would force five people to rebase on every merge. The cost is that a stale base can carry a green tick past the gate, which is why you read the check list rather than the colour.

**An empty grep of a CI log for `FAILED|^E |assert` means the failure is not a test.** It is usually `ruff format --check`, which runs *before* Lint, Import boundaries and Tests — so a format failure means nothing in the PR has been verified by CI. Grep for `Process completed with exit code` instead.

Three checks report on every PR: `CI/backend`, `CI/datasets`, `Frontend/frontend`. A PR
showing two has a base predating #60 — that is a stale base wearing a green tick, not a CI
problem. Rebase before reading anything into it.

`ci.yml` has no `paths:` filter and must never gain one. `paths:` is a workflow-level trigger
filter; a job cannot carry its own, so adding one silences every job at once. A workflow
skipped by path posts no status and a required context waits on it forever — the deadlock
that blocked #32, #33, #36 and #37. An `if:` on a job is the same deadlock in a different
costume.

The `datasets` job deliberately has no ruff step: `datasets/` carries seven pre-existing
UP042 findings and one format diff under `bck`'s config, so adding one turns the job red on
arrival.

**Do not quote a test count from this file. Measure it.** The local baseline moved
three times in Session 13 alone (731 -> 739 -> 741 -> 772) and this line was stale all
session. Measure on `origin/main` in your own session, with a clean tree and bytecode
purged, before claiming a delta. CI reports roughly 30 higher because it un-skips the
postgres-marked tests.

The historical figures were 737 passed / 2 skipped on the runner and 707 / 32 locally. The
difference is the 30 postgres-marked tests, which CI un-skips because it provides a Postgres
service. Both numbers are correct.

Session-log numbering in `session-log/abhiram.md`: 10 = CORE-003, 11 = CTR-006,
12 = PIP-004, 13 = RUL-005. Next is Session 14. Resolve conflicts in that file by reconstruction — take main's version verbatim
and append your block — never by editing conflict markers. Prove it with
`git diff --numstat origin/main -- session-log/abhiram.md` showing zero deletions.


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
  the venue network failing. `bck/.env` does not currently exist; the four required settings
  are `PDP_WEIGHTS_PATH` (a file), `OCR_DET_MODEL_DIR`, `OCR_REC_MODEL_DIR` and
  `TESSERACT_TESSDATA_DIR` (directories). Blank is treated as unset.
- **There is no PDP-trained YOLO model, and pointing `PDP_WEIGHTS_PATH` at stock weights is
  worse than leaving it unset.** `detect_pdp` takes `boxes.conf.argmax()` of whatever it is
  given, so `yolov8n.pt` returns a COCO box as the principal display panel and its area
  feeds the Rule 7 band lookup. Its empty-detection branch returns the **whole image** with
  `confidence 0.0`, overestimating area and biasing toward POTENTIAL VIOLATION.
- **paddleocr is 3.7.0.** The 2.x API (`det_model_dir`, `use_gpu`, `show_log`,
  `ocr(cls=False)`) does not construct. Use `text_detection_model_dir`,
  `text_recognition_model_dir`, `use_textline_orientation`, `device`, and `ocr.predict()`,
  which returns `dt_polys` / `rec_texts` / `rec_scores`. `tesseract` is not installed on the
  dev machine at all.
- **Cloud OCR is off by default** with a daily page cap of `0` in config. Turning it on is a
  deliberate act, not a fallback that fires on its own.
- **`main` may be checked out in another worktree.** `git checkout main` will fail with
  "already used by worktree at …". Detach that worktree first rather than fighting it.
- **A duplicate SVG pattern `id` across breakpoint variants** resolves `url(#…)` to the
  hidden element and paints nothing. Scope with `useId`. Only a real browser at two widths
  catches this.
- **`/tmp` is a 3.9 GB tmpfs on this machine.** Anything unpacking paddle, torch or
  ultralytics into it runs out of space, and the failure surfaces as a file-copy error rather
  than "out of space", so it reads like a permissions or checksum problem. Set `TMPDIR` under
  `~` before a large `uv sync` or a model download. Relatedly, `uv cache prune` blocks on a
  concurrent `uv` — do not `--force` it while another session is syncing.
- **`alembic check` fails immediately after a test run, and it is not drift.** The persistence
  suite downgrades to base when it finishes, so the database is empty and `check` reports
  exactly what real drift reports. Run `uv run alembic upgrade head` first, then check.
  Separately, `alembic check` does **not** detect a change to the *values* of an existing enum
  — adding a member to `contracts.DeclarationField` passes clean and then fails at the first
  insert with `invalid input value for enum`. That needs a hand-written
  `ALTER TYPE ... ADD VALUE`, which cannot run inside a transaction.
- **Compose reads the port from two different `.env` files.** `POSTGRES_PORT` comes from the
  repo-root `.env`; `DATABASE_URL` comes from `bck/.env`. Nothing links them, so changing one
  publishes on one port and connects to another with no error. A local Postgres cluster
  already on `127.0.0.1:5432` shadows the container entirely — the container reports healthy
  and the DSN quietly reaches the local cluster. Change both files together.
- **Grepping a CI log for `ERROR` always returns three lines, and all three are passing
  tests.** They are Postgres server logs dumped under the "Stop containers" step: the
  `field_state` enum-drift guard firing on `"PROBABLY_FINE"`, and the two uniqueness tests
  hitting `uq_evidence_entries_scan_id_sequence` and
  `uq_field_findings_verdict_id_field_rule_id`. Read the step name and the conclusion.

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
- Rebase onto `main`; never `git merge main` into a feature branch. It replays merged history
  as new files — it cost this repo a 62-file diff that had to be thrown away.
- Append to `session-log/<name>.md`. Never rewrite it: two PRs have already destroyed an
  earlier ticket's history in one.

---

## Prove your tests can fail

Before claiming a guard works, introduce the defect it guards against and confirm the test
goes red, then revert. **Run `/usr/bin/find . -name __pycache__ -type d -exec rm -rf {} +` first.**
Python's `.pyc` staleness check is mtime-and-size, and a falsification edit is usually exactly
the shape that defeats it — one string swapped for another of the same byte length
(`"medical_device"` → `"MEDICAL_DEVICE"`). Stale bytecode reports a green pass over a real
defect. Five separate PRs on this project shipped tests that could not fail:
a network-isolation test with the library mocked, a mutation test against a frozen object, an
adversarial test asserting a stub returned what it was told, a directory scan resolving a
relative path to nothing.

If a test genuinely cannot be made to fail, **correct the claim, not the code.** Rename it to
say what it actually proves and put the reason in its docstring. That is a better outcome
than a decorative green tick, and it is explicitly the behaviour wanted here.

If it cannot be made to fail **and** there is no true claim left to rename it to, delete it.
`not isinstance(proposal, ProductCategory)` restated the type system — a `StrEnum` with
members cannot be subclassed — so there was nothing to rename it to.

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
