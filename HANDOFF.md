# HANDOFF.md — end of Session 6, 2026-09-07

Written from chat context. Everything else in project knowledge is a mirror of the repo;
this file is not. Read it first.

---

## How Abhiram works with you

- One task or question at a time. Give the next command, wait for output, then the next.
  Never a five-step sequence to work through alone.
- Exact pasteable commands with real values. Never a command described in prose.
- Anything outside the terminal — a settings panel, a form — every click, every field.
- Recommend one option and say why. Never hand him a menu.
- Say when something will not work instead of finding a way to agree.
- If you cannot verify a claim, say the claim is soft. He would rather know now than at a
  demo.
- Never claim a probability of winning.
- He executes; you decide. He does not want choices, he wants the next action.
- Every Claude Code prompt names the session, the exact `cd` command, and the branch he
  should see before pasting. Never assume a session is still open.
- Most work is in `~/NewProjects/26034`. When a Claude Code session already holds the repo,
  use a worktree instead of a second clone.
- Every Claude Code prompt names which skill to invoke. `engineering-standards` for build
  tickets. `cplan` opens a session in plan mode — use it, do not write "start in plan mode"
  in prose.
- Flag once past turn 30, again near 40. Flag immediately on repeating yourself, forgetting
  a decision, or re-asking something answered — that is the trigger to run
  HANDOFF-PROTOCOL.md, not a warning.

---

## What you can and cannot do — connector limits

- **ClickUp MCP was rate-limited for the whole of Session 6.** A test mid-session reported
  537 minutes remaining. Test once with a cheap `clickup_filter_tasks` before assuming it
  works. While limited, hand each ticket over as one pasteable markdown block: title,
  assignee, status, priority, the three custom field values, description.
- The `Module 26034` dropdown rejects a plain string. It needs an option UUID from
  `clickup_get_custom_fields`. Several tickets still lack it.
- ClickUp cannot post comments reliably. Information belongs in task descriptions.
- `done` is terminal. Nothing moves to `complete`.
- **There is no GitHub MCP connector.** `api.github.com` rate-limits within a few calls.
  Abhiram runs the command, uploads the `.md`, you read it.
- **PR reviews come back as ClickUp ticket-comment drafts, never GitHub comments.** He
  pastes them; he owns GitHub entirely.
- List ID `1300450000005736`. Custom fields: assignee `87d708c9-d795-41d5-bae7-be56090b3ff1`,
  branch `589b8355-8072-4ec7-b615-d78c6778bd87`, files in scope
  `21d1ae6f-d983-44db-b2ac-d390d30b6469`. Statuses `to do` / `in progress` / `review` /
  `done`. Priorities `urgent` / `normal`.

---

## The PR review protocol

1. **Check the head OID before spending a diff.** Unchanged since last review means the owed
   items are still owed — say so in one line and do not re-read.
2. **Read the file list and byte count before the diff.** A PR that should be three files and
   is four has something in it nobody asked for. This caught #42's junk file, which passed
   both CI jobs.
3. Under ~300 lines, paste in chat. Over, upload as `pr<n>-review.md`, then `-v2`, `-v3`.
   Never overwrite. `.md`, never `.diff` — project knowledge rejects `.diff`.
4. Never more than two diffs at a time.
5. Read any migration in full.
6. **Merge gate:** checks green · one module · in ticket scope · no migration · no auth
   change · no shared-contract change · no new dependency. Otherwise escalate to Abhiram.
7. The gate is necessary, not sufficient. #55 passed every clause and still needed two
   rounds because its detector fired on any crop containing text.
8. For his own PRs, skip `gh pr review --approve` — GitHub blocks self-approval. Merge with
   `gh pr merge <n> --squash --admin --delete-branch`.
9. Delete review files from project knowledge once the PR merges.

**Check the check list, not just the colour.** A PR showing two checks where main produces
three has a base predating a merged workflow change. That is a stale base wearing a green tick.

---

## The recurring failure patterns

1. **A session log that describes work not in the branch.** Hit twice in Session 6.
   Akshaya's #55 log claimed a full rework at head `739c68f` where the three Python files
   were byte-identical to the previous head; only the log had changed. Sitanshu's #56 log
   claimed `मूल्य` and `अधिकतम राशी` were removed from `_DEVANAGARI_TOKEN_MAP` and a test
   added — both mappings were still present and the test existed only inside the log
   sentence. **Diff the code against the previous head before believing a rework claim.**
   The standing rule now: the session log records what is in the commit, never what was
   intended or run locally.
2. **Tests that cannot fail.** Six PRs in a row. `test_tamper_result_zero_bounds` asserted a
   `ge=0.0` field accepts `0.0`. `test_unpaired_span_conservation` used a fixture built from
   the word list added three lines away in the same diff. `test_detect_sticker_hard_edge`
   asserted `probability > 0.0` against a hardcoded `0.85`.
3. **Fixtures that do not resemble the input.** #55's sticker tests contained no rendered
   text at all, on a detector that runs on OCR crops which always contain glyphs.
4. **Modules merging with no caller.** `EvidenceEntryRow`, `propose_category`,
   `measure_margins`, and now `tamper/`. Four. An uncalled function is invisible to CI and
   to review. Every such merge needs its wiring ticket created in the same breath.
5. **Stale bases.** Teammates push, main moves, the PR reports a suite count from a base
   forty tests behind. Require the count from the rebased base, in the PR body.

---

## Claims that turned out wrong, and who caught them

- **I said every falsification on this project may have run against stale bytecode**, because
  `rtk` intercepts `find -exec`. Lane C proved it **exits 1**, so `find … && pytest` fails
  loudly and cannot silently pass. Real exposure is only single-line `find … ; pytest` with a
  semicolon. Narrower than I claimed.
- **I predicted the suite count would move** when #58 rebased onto #60. Lane A showed it does
  not: #60 touched no file under `bck/tests/`, and `testpaths = ["tests"]` means the datasets
  tests never enter that count.
- **I said `pipeline/` discriminates on `MeasurementExact` / `MeasurementCalibrated`.** A grep
  showed nothing outside `contracts/` does an `isinstance` on them. The Liskov problem was
  latent, not active. The fix was still right; the reason I gave was not.
- **My CTR-005 ticket assumed `confidence_interval` was `gt=0`.** It is `ge=0`, deliberately,
  with a documented zero-variance contrast-ratio case. Lane A caught it before writing code.
- **Claude Code was wrong twice about the `rtk` mechanism** — first "first token of the
  command", then corrected to line structure — and said so both times rather than leaving the
  first claim standing.
- Session 5's lesson still holds: a session was told a PR was merged when it was not, checked
  `mergedAt`, found it open, and corrected. That is the behaviour to keep.

---

## Infrastructure state, dated 2026-09-07

- **`main` is past #59.** Verify the SHA rather than trusting any figure written here.
- **`CI/datasets` exists** as of #60 and reports on every PR. It runs a repo-hygiene step and
  `uv run pytest ../datasets` with `working-directory: bck`. **It is not yet a required
  status check** — it has now reported, so it can be added at
  `github.com/SIH-2026-CSM-A/26034/settings/rules` → `main-protection` → Require status
  checks → `+ Add checks` → `datasets` → Save.
- **`ci.yml` has no `paths:` filter and must never gain one.** A workflow skipped by path
  posts no status and a required context waits forever — the deadlock that blocked #32, #33,
  #36 and #37. An `if:` on a job is the same deadlock in a different costume.
- **`datasets/` is not ruff-clean** under `bck`'s config: seven pre-existing UP042 findings
  (every enum in `schema.py` is `(str, Enum)`) and one format diff. The datasets job has no
  ruff step for exactly that reason. Adding one turns it red on arrival.
- Backend on the runner reports **737 passed, 2 skipped**; locally **707 passed, 32 skipped**.
  The difference is the 30 postgres-marked tests, which CI un-skips because it provides a
  Postgres service. Both numbers are correct. Do not treat the gap as a defect.
- Datasets job: 28 collected, 26 passed, 2 skipped.
- **Worktree paths — HANDOFF was wrong on these.** `26034-ci`, `26034-fnt` and `26034-rules`
  live under `~/NewProjects/`, not `~`. `~/26034-ctr`, `~/26034-dat` and `~/26034-docs` are
  under `~`. Confirm with `git -C ~/NewProjects/26034 worktree list` before creating one.
- Session-log numbering in `session-log/abhiram.md`: 7 = CI-004, 8 = CTR-005, 9 = DAT-004.
  **Next is Session 10.** Two rebases in Session 6 collided on this file. Resolve by
  reconstruction — take main's file verbatim, append your block — never by editing conflict
  markers, and prove it with `git diff --numstat` showing zero deletions.

---

## Owners and usernames

| Person | GitHub | ClickUp | Owns |
|---|---|---|---|
| Abhiram | `Abhiram-0910` | 240010775 | contracts, pipeline, core, alembic, datasets, CI. Sole merger. |
| Akshaya | `aksha08-ya` | — | vision, tamper (transferred from Shivasai) |
| Shiva Kumar | `Shiva-Kumar-Akula` | — | evidence |
| Sitanshu | `krishbattula4` | 106878761 | extraction |
| Yashashvi | `Yashashvi-05` | 106878758 | measurement |

- **Aashritha is off the project. Assign her nothing.** `datasets/` ownership in CODEOWNERS
  and the AGENTS.md table still names her — DAT-003 fixes that.
- **B.V. Yashwanth (240010980, not on the team), Jashwanth Badugu (106878760, unavailable)
  and Yashashvi (106878758, active) are three different people.** Check the ClickUp ID, never
  the name.
- `bck/app/modules/measurement/README.md` names `@Abhiram-0910` as owner; CODEOWNERS and
  AGENTS.md give measurement to Yashashvi. DAT-003 fixes this too.

---

## Legal findings — expensive to rediscover

- Rule 7 letter-height is a **PDP-area-banded Table-I (1.0–6.0 mm)** per G.S.R. 629(E), in
  force 1 January 2018. Not a flat figure.
- Rule 7(4) "other shapes" has a **second limb** enabling homography-based measurement.
- Rule 8 governs placement; Rule 9 governs manner. **Rule 9(4)** permits Hindi in Devanagari
  or English, with other languages in addition — the basis for EXT-006.
- **Rule 6(1)(aa)** is the correct citation for country-of-origin package declaration.
- **Rule 6(10A)**, inserted by G.S.R. 128(E), is a separate e-commerce platform obligation.
- **Rule 6(11)** is a format rule with zero tolerance. Any ±₹ figures in project docs are
  assumptions, not law. Below 1 litre or 1 kg the unit price is per ml or per g; at or above,
  per litre or per kg.
- **Rule 26** exempts packages of 10 g / 10 ml or less, except tobacco. This matters
  immediately: the staged 2 g Maggi sachet. Read the corpus before writing its ground truth —
  a ground truth marking exempt obligations FAIL trains the eval set to punish correct
  behaviour.
- The medical-devices carve-out, **G.S.R. 778(E)**, means Rule 7 Table-I is not universal.
  `SIH26034_TI.md` §5 uses "Medical Device" as a routing example without knowing this.
- **The only sourced coin dimension on this project is the ₹10 coin at 27.0 mm** (RBI-confirmed,
  `SIH26034_TI.md` §15). ID-1 card is 85.60 × 53.98 mm; EAN-13 is 37.29 mm.
- `SIH26034_PSR.md` §3 carries a **wrong Rule 7 figure**. It is not a source for rule facts.
- `मूल्य` is generic price, used in the corpus inside `अजधकतम खुिरा मूल्य` — **not** a
  statutory synonym for MRP. `अधिकतम राशी` has no statutory support at all.

---

## Hard nos — do not re-propose

- Margin measurement types as **subclasses** of the strict types. Settled: siblings off two
  private bases. Rejected alternatives, with reasons: subclassing violates Liskov and makes
  existing `isinstance` assertions pass vacuously; a flat layout duplicates two long field
  docstrings that then drift; chaining the two bases forces one `rule_limb` docstring to cover
  both Rule 7(4) and Rule 7(2).
- A `paths:` filter or an `if:` on any job in `ci.yml`.
- A ruff step on the datasets job before the seven UP042 findings are fixed.
- Re-adding `aruco_marker`, `ruler_scale` or `checkerboard` to `ReferenceObjectType` without
  its `REF_DIMS` entry and detector branch **in the same PR**. The guard carries no exemption
  list by design.
- The ₹5 coin at 25.0 mm, under any spelling. Do not invent `coin_5` either — an identifier
  that exists nowhere is the same defect as an unreachable enum member.
- `coin_inr_10` / `credit_card_id1` — the schema now uses measurement's names.
- A duplicate `ExtractionResult`, or a new `app/modules/extraction/evidence.py`.
- An LLM or agent loop anywhere in the verdict path.
- A further rule-store ticket to reduce the 65-findings-per-scan count. RUL-004 established
  that Rule 7(2) and 7(3) genuinely govern every declaration; `governs_declarations: None`
  records that honestly. The remaining fix is a presentation problem on the officer surface.
- Millimetre measurements from uncalibrated photographs — including in ground-truth
  annotations. Requirements may carry millimetres; observations may not.

---

## Constraints discovered the hard way

- **`rtk` intercepts `find … -exec`.** A single-line command containing it is refused with
  `rtk: rtk find does not support compound predicates or actions` and **exits 1**. The same
  line inside a multi-line command runs normally. `/usr/bin/find` always works. So
  `find … && pytest` fails loudly and is safe; `find … ; pytest` on one line silently skips
  the purge and runs pytest on stale bytecode. **Always `/usr/bin/find`, and assert the
  directory count is zero rather than trusting an exit code.** `type -t find` reports
  `function` in both shapes; the mechanism is a shell function rerouting to `bfs`.
- **`rtk` also intercepts `gh run view --job … --log`** → `rtk: Run ID required`. Use
  `gh api repos/<r>/actions/jobs/<id>/logs` instead.
- **Same-length string edits run stale bytecode.** This is why the purge is load-bearing:
  `gt=0` → `ge=0` does not change file size or mtime granularity enough to invalidate a
  `.pyc`. Most falsifications on this project are exactly that shape.
- `git ls-files -z | tr '\0' '\n'` reintroduces the hole it closes — a filename containing a
  newline splits across two innocent-looking lines. Plain `git ls-files` quotes such names
  onto one line, where the `"` trips the check.
- **Port-shadowing:** Docker Compose reads `POSTGRES_PORT` from the repo-root `.env` while
  `DATABASE_URL` lives in `bck/.env` with nothing linking them. Setting one without the other
  silently connects to the wrong server.
- `--ours` / `--theirs` mean opposite things in rebase vs merge.
- Never hand-resolve `uv.lock` conflict markers — delete and regenerate.
- Chain multi-step commands with `&&`, not bare newlines.
- `gh pr checks` reporting "no checks reported" almost always means a stale branch needing a
  rebase, not a CI problem.
- Never run manual git commands in a folder a Claude Code session has open. Use a worktree.
- Editing a model test to pass an Alembic drift check is falsification. Fix the constraint.
- `pytest.raises(DBAPIError)` is not proof of enum rejection — assert the specific constraint.

---

## Decisions this session — do not re-litigate

**CTR-005 (#58, merged).** Four public measurement types, none deriving from another:

| Type | `mode` | `value` | `confidence_interval` |
|---|---|---|---|
| `MeasurementExact` | `exact` | `gt=0` | — |
| `MeasurementMarginExact` | `margin_exact` | `ge=0` | — |
| `MeasurementCalibrated` | `calibrated` | `gt=0` | `ge=0` |
| `MeasurementMarginCalibrated` | `margin_calibrated` | `ge=0` | **`gt=0`** |

Zero **value** is a physical fact — a declaration flush against the panel edge. Zero
**interval** is a false-precision claim about a distance carrying pixel quantisation and
reference-object localisation error. Different questions; only the second is constrained.
`MeasurementCalibrated` keeps `ge=0` because a zero-variance contrast-ratio crop genuinely has
no spread. Tightening on a child is the safe direction — it guarantees strictly more than its
base.

**DAT-004 (#59, merged).** Measurement's vocabulary wins: `coin_10` / `id_card` / `ean_13`.
Rejected renaming inside measurement — that touches merged, reviewed code, and
`orchestrator.py`'s `Calibration.reference_type` docstring already declared measurement
authoritative. The schema was the outlier. The guard
`TestMeasurementCanConsumeEveryOfferedObject` asserts every offered value is a `REF_DIMS` key.

**CI-004 (#60, merged).** A separate `datasets` job, not an extension of `backend` — that job
is scoped to the `bck` package and carries a Postgres service this one has no use for. Plus a
repo-hygiene step failing on quotes, backticks, leading hyphens, and unlisted root files.

**TAM-001 (#55, merged).** Merged with uncalibrated thresholds and no caller, deliberately.
`CV_STEP_DISCONTINUITY_THRESHOLD=35.0`, `PRIOR_STICKER_OVERLAY_PROBABILITY=0.85`,
`PRIOR_CONFLICTING_MRP_PROBABILITY=0.95` are all unsourced. **Tamper detection must not be
described as working until it has run against real annotated labels.** TAM-002 carries wiring
and calibration.

**CORE-003 — decided, in flight, not yet written.** Two calls a fresh session cannot derive
from the code:
- `asset_type` is **required with no default**, on both model and column. Precedent:
  `ReferenceObject.object_type`. A default lets an entry carry a disposition nobody chose,
  and this field decides when evidence is destroyed.
- `asset_type` **is folded into `compute_entry_hash`**. Outside the hash, an entry can be
  relabelled from original capture to derived thumbnail, become purgeable under a different
  retention rule, and chain verification still reports the chain intact — a tamper vector on
  the one structure whose purpose is detecting tampering. It changes every existing entry
  hash; there are no entries, so the cost is zero now and unpayable later.

**EVD-005 legal hold — decided, and the shipped code has it inverted.** HOLD on any
`POTENTIAL_VIOLATION` with no review row; HOLD on `CONFIRM` or `OVERRIDE`; RELEASE only on
`REJECT`. An unreviewed potential violation is the evidence most worth keeping.

**DAT-003 rescoped to ownership only.** Its original body is stale and its setup step is now
**dangerous** — it unzips `dat001-raw-corpus.zip` into `datasets/raw/`, re-importing the four
fabricated catalogue renders that DAT-002 deleted. Do not run it. The `manifest.json` rebuild
moved into DAT-005.

**The corpus provenance question is closed.** Exactly one commit ever added a file under
`datasets/annotations/` — `da8278f` (#8, DAT-001), eight files, one author, one batch. The
four proven fabricated and the eight never reviewed share that provenance. Nothing real was
lost. ARCHITECTURE.md's "Technical debt" section is stale on this: the corpus is **zero**
samples, not four, and fifteen real captures are staged and unannotated.

---

## Where the board stands, 2026-09-07

**Merged this session:** #60 (CI-004), #55 (TAM-001), #58 (CTR-005), #59 (DAT-004).

**Open PRs:**

| PR | Owner | Ticket | State |
|---|---|---|---|
| #46 | Shiva | EVD-005 | Blocked on CORE-003. Format check red. Carries three Abhiram-owned files. Four review items unconfirmed. |
| #47 | Yashashvi | MEA-006 | **Unblocked by #58.** Must rebase, drop both `contracts/` files, floor the confidence interval. |
| #56 | Sitanshu | EXT-006 | Two fixes owed: the uncommitted lexicon removal, and a triplicated module docstring. |
| #43 | Yashashvi | MEA-005 | Untouched in Session 6. Still blocked on a new `pdfplumber` dependency. |

**In flight:** CORE-003 in Lane A (`~/NewProjects/26034`), plan stage.

**Abhiram's queue, in order:** CORE-003 → **DAT-005** → CI/datasets required check → DAT-003
(ownership only) → PIP-003.

**DAT-005 is the highest-value item on the board.** Nothing about vision, measurement or
tamper can be evaluated until it exists, and every PRD accuracy figure depends on it.

**New tickets created in Session 6, not all on the board yet:** CTR-005 (done), CORE-003,
TAM-002, MEA-008, EXT-007.

---

## Golden examples

**Falsifying a guard — the second falsification is the one that matters.**
BAD: rename `coin_10` to `coin_ten`, confirm the guard goes red. That only proves it catches a
renamed member.
GOOD: also re-add `ARUCO_MARKER` with no `REF_DIMS` entry and confirm **only** the new guard
goes red. That proves the claim the docstring actually makes — a new member without a
dimension is rejected.

**Correcting your own claim.**
BAD: leave a comment saying rootdir resolves to `bck/` because the code works anyway.
GOOD: read the CI log, find rootdir is the repo root with no configfile, fix the sentence and
say so in the PR body. Fix the claim, not the code.

**A rework claim.**
BAD: read the session log's rework entry and review against it.
GOOD: `git diff <old-head> <new-head> --stat`. Twice in Session 6 the log described work that
was not in the branch.

**A test that cannot fail.**
BAD: `assert results[0].probability > 0.0` against a hardcoded `0.85`.
GOOD: assert the exact prior constant, and separately assert `ValidationError` on `-0.1` and
`1.1`.

**Splitting a ticket at an ownership boundary.**
BAD: ask the module owner to write the migration their ticket needs.
GOOD: land the column and migration yourself, tell them explicitly not to write one, and have
them rebase. Shiva correctly refused to edit `tests/core/test_persistence.py` and said so —
that is the behaviour to reinforce.
