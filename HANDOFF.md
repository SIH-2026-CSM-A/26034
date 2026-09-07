# HANDOFF.md — end of Session 14, 2026-09-07

Written from chat context. Everything else in project knowledge mirrors the repo; this file
does not. Read it first.

`main` is at `d9c44fa`. Verify the SHA rather than trusting any figure here, and measure the
baseline yourself — see **Infrastructure state**.

---

## How Abhiram works with you

- One task or question at a time. Give the next command, wait for output, then the next.
  Never a five-step sequence to work through alone.
- Exact pasteable commands with real values. Never a command described in prose.
- Anything outside the terminal — a settings panel, a form — every click, every field.
- Recommend one option and say why. Never hand him a menu.
- Say when something will not work instead of finding a way to agree.
- If you cannot verify a claim, say the claim is soft. He would rather know now than at a demo.
- Never claim a probability of winning.
- He executes; you decide.
- Every Claude Code prompt names the session, the exact `cd` command, and the branch he should
  see before pasting. **Never assume a session is still open** — Session 13 lost a turn pasting
  a CTR-006 prompt into a stale CORE-003 session. That session correctly refused to invent the
  context rather than guessing, which is the behaviour to keep.
- Tell him to close a Claude Code terminal the moment its PR merges. Idle sessions on deleted
  branches are how the wrong-session paste happens.
- Every prompt names the skill to invoke. `engineering-standards` for build tickets. `cplan`
  opens plan mode — use it, do not write "start in plan mode" in prose.
- Flag once past turn 30, again near 40. Flag immediately on repeating yourself, forgetting a
  decision, or re-asking something answered — that is the trigger to run HANDOFF-PROTOCOL.md.
- **Do not wind down until he says explicitly there are 24 hours left.** When a ticket closes,
  the next one is already there. When the board runs low, extend it from the PRD and feature
  spec and create the tickets yourself.
- **Never ask him to produce something before checking whether the repository already has it.**
  Session 14 asked him to photograph six packages without first listing
  `datasets/raw/_staging/`, which held fifteen staged captures. The standing rule under
  **Claims that turned out wrong** covers asking as well as asserting.

---

## What you can and cannot do (connector limits)

- **ClickUp MCP came back mid-Session 13** after being rate-limited for all of Session 6.
  Test once with a cheap `clickup_filter_tasks` before assuming it works.
- **Custom field writes are capped on this plan.** `clickup_update_task` with `custom_fields`
  returns *"Custom field usages exceeded for your plan"*. Name and status updates still work.
  FNT-003's branch field is consequently wrong on the board — it reads
  `fnt-001-generated-api-client`; the real branch was `fnt-003-generated-api-client`. Tell
  Vineeth verbally. The `Module 26034` UUID backfill is not happening on this plan.
- The `Module 26034` dropdown rejects a plain string; it needs an option UUID from
  `clickup_get_custom_fields`.
- ClickUp cannot post comments reliably. Information belongs in task descriptions.
- `done` is terminal. Nothing moves to `complete`.
- **There is no GitHub MCP connector.** `api.github.com` rate-limits within a few calls.
  Abhiram runs the command, uploads the `.md`, you read it.
- **PR reviews come back as ClickUp ticket-description text, never GitHub comments.** He owns
  GitHub entirely. **Never write a review into a ticket that is already `done`** — nobody reads
  those. Open the follow-up ticket instead.
- List ID `1300450000005736`. Custom fields: assignee `87d708c9-d795-41d5-bae7-be56090b3ff1`,
  branch `589b8355-8072-4ec7-b615-d78c6778bd87`, files in scope
  `21d1ae6f-d983-44db-b2ac-d390d30b6469`.

---

## The PR review protocol

1. **Check the head OID before spending a diff.** Unchanged since last review means the owed
   items are still owed — say so in one line and do not re-read. Corollary learned in Session
   14: **an OID that has changed invalidates the whole previous review, not just the parts you
   expect.** Both #63 and #66 moved between the review and the handoff, and in both cases the
   handoff's item list was wrong in both directions — items closed that it called open, and a
   worse defect it had no idea about.
2. **Read the file list and byte count before the diff.** A PR that should be three files and
   is four has something in it nobody asked for.
3. **Read the file-count deltas, not just the names.** `0/45` on a test file means forty-five
   lines deleted and nothing added. Session 13 caught VIS-004 deleting twelve OCR tests across
   two pushes while all three checks stayed green. **A suite with its guards removed passes
   easily.**
4. **A signature grep proves a test's name is back. It does not prove its body is.** This is
   the Session 14 lesson and it cost a wrong review. On #63,
   `gh api … | grep -E "^[-+]def test_"` showed `+def test_offline_guarantee_missing_tessdata_dir`
   and `+def test_arbitration_currency_normalization` and read as a restoration. The file at
   that head is twenty-seven lines: six functions, five with `pass` bodies and one
   `assert True`. **A deleted test and a hollowed test are identical to that grep.** When
   additions are a fraction of deletions — `+15/-187` here — open the file. Cheap greps are
   still right for deletions and for locating a string; they cannot answer "is this test real".
5. Under ~300 lines, paste in chat. Over, upload as `pr<n>-review.md`, then `-v2`. Never
   overwrite. `.md`, never `.diff`.
6. Never more than two diffs at a time.
7. Read any migration in full.
8. **Merge gate:** checks green · one module · in ticket scope · no migration · no auth change ·
   no shared-contract change · no new dependency. Otherwise escalate.
9. **Read the base OID as well as the head.** #46 carries three green checks on base `a95e8fb`,
   eleven merges behind `main`. "Require branches to be up to date" is deliberately off, so the
   tick is real and it verified a tree that predates CORE-003. Green on a stale base is not
   evidence about `main`.
10. For his own PRs, skip `gh pr review --approve` — GitHub blocks self-approval. Merge with
    `gh pr merge <n> --squash --admin --delete-branch`.

**Cheap targeted greps beat full diffs.** Session 13 settled three reviews without pulling a
diff at all:
- Lexicon claim: `gh api repos/$R/contents/<path>?ref=<sha> -q .content | base64 -d | grep -n`
- Deleted tests: `gh api repos/$R/pulls/<n>/files -q '.[]|select(.filename|endswith("x.py"))|.patch' | grep -E "^[-+]def test_"`
- Rebase artefacts: compare against `main`, not the old head. A three-dot compare from the old
  head shows everything main gained since branching, mixed in with the author's own work, and
  looks like scope creep when it is a clean rebase.

Read item 4 before you trust the second of those again.

---

## The recurring failure patterns

1. **A session log describing work not in the branch.** Diff the code against the previous head
   before believing a rework claim.
2. **Tests that cannot fail.** Session 13 added a species: **a test that fetches its own
   expectation.** RUL-005's marker and threshold tests read the value out of `rules.yaml` and
   compared it back against the store, so a same-length swap of `not for retail sale` →
   `not-for-retail-sale` left both green. Fixed by pinning corpus literals. **Watch for any test
   whose expected value is loaded rather than written.**
3. **A falsification that does not falsify.** RUL-005 first moved the scope check below the
   builders but left it winning the return — only four unrelated tests went red and both new
   ordering tests stayed green. That would have been a false confirmation. The real regression
   was the builder's result winning. **Check that the defect you inject is the defect the test
   claims to catch.**
4. **Deleting tests on the ticket that exists to prove they pass.** VIS-004, twice.
5. **Hollowing tests to `pass` bodies, which is the same failure wearing the names of the
   tests it replaced.** VIS-004 again, Session 14, and the worst instance so far: the entire
   OCR suite reduced to five `pass` bodies and a `test_placeholder_ocr` that asserts `True`,
   with all three checks green. `test_placeholder_ocr` is also a placeholder in committed code,
   which `AGENTS.md` forbids outright. **A green tick over a hollowed suite is indistinguishable
   from a green tick over a real one. Only reading the file separates them.**
6. **Modules merging with no caller.** Now six functions across five modules — the two artwork
   functions from #43 joined the list. Every such merge needs its wiring ticket created in the
   same breath.
7. **Stale bases and stale baselines.** The local test count moved four times in one day.
   **Measure the baseline on `origin/main` in the same session; never quote CLAUDE.md's figure,
   and never quote this file's.**
8. **Trusting a PR body or a commit message instead of the diff.** Cost two wrong review items
   on #43 (below), and commit `fa52a87` claimed "remove SVG" and "extract PT_TO_MM constant"
   and did neither. A commit message is a claim about a diff, not the diff.
9. **A document asserting a fact about the code with nothing checking it.** Three live examples
   found in one session: `rules-corpus/README.md`'s encoded-id list (thirteen discrepancies
   against the store, nothing in CI reads the file), `bck/tests/contracts/test_manifest_integrity.py`
   (loops a key the writer does not emit), and this file's own ARUCO_MARKER entry. **If a doc
   states a fact about the store or the schema, either a test pins it or it will drift.**

---

## Claims that turned out wrong, and who caught them

Four of these are Session 14's own, and all four were caught by a session that checked rather
than agreed. A handoff that records only successes teaches the next session to be confident
where this one was wrong.

- **I said #43's tests were mocks.** They are real `reportlab` round-trips —
  `bck/tests/modules/measurement/test_artwork.py` writes actual PDFs with `canvas.Canvas` at
  lines 19, 52, 75 and 108 and reads the dimensions back. I took it from the PR body instead
  of the code. Caught by the MEA-005 session.
- **I said #43's session log had been deleted.** It had been restored; the merged PR carries
  `session-log/abhiram.md +96/-0`. Same source, same error, same session caught it.
- **I said CI reports "~45 higher" than local, and told the next session to write that.** It is
  **30**, and it is 30 because there are exactly thirty postgres-marked tests that the runner
  un-skips. I wrote a CI delta from memory instead of deriving it — which is precisely the
  failure this file warns about two sections up. `CLAUDE.md` had it right the whole time.
  Measured: local `d9c44fa` 801/32; CI on the `rul-007` branch 835/2; `32 − 2 = 30`.
  **Derive the delta from the skip count. Never carry the number.**
- **I reported #63's five named OCR tests as partially restored.** All six functions in that
  file are `pass` stubs. I used a signature grep, which is blind to hollowing, and reported
  what it showed. See item 4 of the PR review protocol — the technique was the error, not the
  reading of its output.
- **I said `ARUCO_MARKER` was deleted from `ReferenceObjectType`, then corrected myself to say
  it was still present. The first claim was right.** The correction, which stood in this file
  from Session 13 to Session 14 and is repeated in `rules-corpus/README.md`, said the members
  were "still at `datasets/schema.py:55` with `RULER_SCALE` and `CHECKERBOARD`" and that
  "there is no enforced member-consumer guard anywhere in the repo". Both false at `d9c44fa`.
  `ReferenceObjectType` has four members — `NONE`, `COIN_10`, `ID_CARD`, `EAN_13`; DAT-004
  (#59) deleted the three markers; and the guard is real and executes in CI —
  `datasets/tests/test_schema_guards.py:89-112` asserts `offered <= set(REF_DIMS)`, running
  since #60 put `datasets/` into CI. **The rule is enforced. Closed, not open.**
  One caveat to carry: `offered <= set(REF_DIMS)` is a subset assertion, the exact shape
  RUL-006 deleted `test_rule_store_contains_only_ticket_authorized_scopes` for. It is green
  against an empty enum. It is not vacuous today because the enum has four members.
- **I said hotels, hospitals, airlines and railways were the institutional consumers in the
  corpus.** They appear nowhere in it. Rule 3(c) says "packaged commodities meant for industrial
  consumers or institutional consumers" and names no institutions. Caught by the RUL-005
  research pass.
- **I said the export limb rested on the retail-sale scope.** It is Rule 25, Chapter IV, and it
  points the other way: an export package may not be sold in India *unless* re-labelled to
  Chapter II. Citing it for "missing MRP is NOT_APPLICABLE" cites a rule for a proposition it
  does not carry. `export package` is undefined in the compilation. Caught by RUL-005.
- **I predicted #47's failure was the confidence-interval floor.** It was a pre-existing test
  asserting `MeasurementExact` on a margin result, which is `MeasurementMarginExact` after
  CTR-005. The test was wrong, not her code.
- **I told Abhiram to rebase #68 when it had already opened and rebased itself.** Wasted a turn.
- **A Claude Code session was sent a prompt for a ticket it had never seen** and refused to
  write a plan from a summary rather than inventing the context. Keep that.

> **Standing rule: verify against the repository before asserting anything about it, or asking
> anyone — including Abhiram — to produce anything. A prose claim is not evidence. A PR body is
> not evidence. A commit message is not evidence. This file is not evidence.**

---

## Infrastructure state, dated 2026-09-07

- **`main` is at `d9c44fa`** (RUL-006, #75). Verify the SHA rather than trusting this line.
- **The local `main` branch in `~/NewProjects/26034` is at `49a6a87` and is behind
  `origin/main`.** A branch cut from local `main` starts stale. Cut from `origin/main`.
- **Baseline: measure it, do not read it.** `origin/main` measured **801 / 32** at `d9c44fa`,
  **820 / 32** at `a4e462c` and **829 / 32** at `19c7966` — one afternoon, about ninety minutes,
  clean tree and bytecode purged each time. **That number will be wrong by the next merge, and
  it went stale twice while this very sentence was being written.** The CI delta is **+30 passed and −30
  skipped, and it is 30 because there are exactly thirty postgres-marked tests the runner
  un-skips because it provides a Postgres service.** Derive it from the skip count; do not carry
  the figure. CI on the `rul-007` branch reported 835/2 against a local 801/32 plus RUL-007's
  four new tests, which is the derivation checking out.
- **One test in the suite asserts against a wall clock and flakes under load.**
  `tests/modules/vision/test_preprocess.py:147` asserts `elapsed < 0.5` for a 3000x4000
  `remap_curvature`. It takes 0.16 s in isolation and measured 1.26 s during a full run on a
  loaded machine, failing the build. If a run goes red on that test alone, re-run it in
  isolation before believing your diff caused it.
- **Do not write a CI count into a file that ships in the same commit.** It is stale on the
  next merge. Write the mechanism, not the number.
- **`uv sync` before measuring a baseline.** MEA-005 added `pdfplumber`. A baseline against a
  stale venv is not one.
- **`datasets` is a required status check.** Confirmed in the ruleset UI. Three checks report
  on every PR: `backend`, `datasets`, `frontend`. Two means a stale base.
- **"Require branches to be up to date before merging" is deliberately unchecked.** Turning it
  on would force five people to rebase on every merge. The cost is that a stale base can carry a
  green tick past the gate — which is why you read the check *list* and the *base OID*, not just
  the colour. #46 is the live example.
- **`ci.yml` has no `paths:` filter and must never gain one.** An `if:` on a job is the same
  deadlock in a different costume.
- **`datasets/` is not ruff-clean** — seven pre-existing UP042 findings plus one format diff
  under `bck`'s config. The datasets job has no ruff step for that reason.
- **Worktrees:** `26034-ci`, `26034-fnt`, `26034-rules` under `~/NewProjects/`; `26034-ctr`,
  `26034-dat`, `26034-docs` under `~`. Confirm with `git -C ~/NewProjects/26034 worktree list`
  before creating one. Several sit on merged branches and need a fresh cut from `origin/main`.
- **`datasets/raw/_staging/` exists only in `~/26034-dat`.** It is gitignored, so it is absent
  from every other worktree including the primary one. Fifteen captures: twelve `.png`, three
  `.jpg`, six of them `_uncalibrated`. Do not conclude from an empty `datasets/raw/` that the
  captures do not exist.
- **Session-log numbering is read from `session-log/abhiram.md`, never assumed and never
  carried in a doc.** Read the last `## Session N` heading in the file. It has gone stale in
  `CLAUDE.md` four times. Sessions 14–17 are MEA-009, PIP-003, MEA-005 and RUL-006. Resolve
  conflicts by reconstruction — take main's file verbatim, append your block — never by editing
  markers, and prove it with `git diff --numstat` showing zero deletions.
- **`session-log/abhiram.md` is a serialisation bottleneck.** It forced a rebase on every PR
  merged today and RUL-006 renumbered its session three times. The fix is per-ticket log files.
  Ticket not yet written; it is in `TODO.md`.

---

## Owners and usernames, with ownership shifts recorded

| Person | GitHub | ClickUp | Owns |
|---|---|---|---|
| Abhiram | `Abhiram-0910` | 240010775 | contracts, pipeline, core, alembic, datasets, CI, rules. Sole merger. |
| Akshaya | `aksha08-ya` | 106878763 | vision, tamper |
| Shiva Kumar | `Shiva-Kumar-Akula` | 106878759 | evidence |
| Sitanshu | `krishbattula4` | 106878761 | extraction |
| Yashashvi | `Yashashvi-05` | 106878758 | measurement |
| Vineeth | `vineethsimha2151` | 106878762 | frontend (FNT-003 landed as #72; FNT-004 next) |

**Vineeth's GitHub username is `vineethsimha2151`.** This file recorded it as `—` through
Session 13. He is a repo collaborator, he is named in CODEOWNERS, and he authored #72.

**Shifts recorded in CODEOWNERS, Session 14.** Both were already recorded in `AGENTS.md`'s
ownership table and only CODEOWNERS was lying:
- `bck/app/modules/rules/` and `bck/tests/modules/rules/` moved off `@badugujashwanth-create`
  (Jashwanth Badugu, off the project) to `@Abhiram-0910`.
- `bck/app/modules/tamper/` and `bck/tests/modules/tamper/` moved off `@adepushivasai901-ops`
  (never engaged) to `@aksha08-ya`, following TAM-001.
- `session-log/yashashvi.md`, `session-log/vineeth.md` and `session-log/shiva-kumar.md` gained
  entries. All three files existed with no owner.

**Aashritha is off the project. Assign her nothing.** CODEOWNERS reassigned `datasets/` to
Abhiram in #64 and that entry is correct — do not re-raise it.

**`/fnt/` ownership has three different answers and is unresolved.** `.github/CODEOWNERS:29`
assigns all of `/fnt/` to `@vineethsimha2151`; this file has said the officer surface stays with
Abhiram because it is on the demo path and he drives it on stage; `AGENTS.md:120` says
"Abhiram *(Vineeth's module, he is unavailable)*" — and he is demonstrably available, having
shipped #72. **Three sources, three positions, none of them wrong on its own terms.** Decide it
deliberately; do not let a CODEOWNERS edit decide it silently.

**B.V. Yashwanth (240010980, not on the team), Jashwanth Badugu (106878760, unavailable) and
Yashashvi (106878758, active) are three different people.** Check the ClickUp ID, never the name.

---

## Legal findings — expensive to rediscover

- Rule 7 letter-height is a **PDP-area-banded Table-I (1.0–6.0 mm)** per G.S.R. 629(E), in force
  01.01.2018. Five bands. There is no 2.0 mm or 3.0 mm normal-print band.
- Rule 7(4) "other shapes" has a **second limb** enabling homography-based measurement.
- Rule 8 governs placement; Rule 9 governs manner. **Rule 9(4)** permits Hindi in Devanagari or
  English, with other languages **in addition** — the basis for EXT-006 and EXT-008.
- **Rule 6(1)(aa)** is country-of-origin on the package. **Rule 6(10A)** (G.S.R. 128(E)) is a
  separate e-commerce obligation. **G.S.R. 312(E)** substitutes it effective **01.07.2027** —
  encode with `effective_from`, do not omit. Both are encoded, as `R6-10A-GSR-128E` and
  `R6-10A-GSR-312E`. There has never been a rule called `R6-10A-ECOMMERCE-FILTER`.
- **Rule 6(11) is a format rule with zero tolerance, and it is deliberately NOT encoded.** The
  ±₹0.01 / ±₹0.05 figures in older project docs are assumptions, not law.
  `bck/tests/modules/rules/test_loader.py:124` asserts the store excludes it. Do not add it to
  the rule store or to the encoded-id list without a ticket that says why.
- **Rule 26** exempts packages of 10 g / 10 ml or less, except tobacco. Two staged samples fall
  under it: a 2 g Maggi sachet and a 6 ml Dove sachet. **An exempt obligation is NOT_APPLICABLE
  even when the label satisfies it voluntarily — not PASS.**
- **Rule 3** (RUL-005) — Chapter II applicability, three limbs: (a) more than 25 kg or
  25 L; (b) cement, fertilizer, agricultural farm produce in bags above 50 kg; (c) packaged
  commodities meant for industrial or institutional consumers. **3(b) is subsumed by 3(a)** —
  every package it names exceeds 50 kg and therefore already exceeds 25 kg.
- **Rule 2(bb) and 2(bc) as substituted** require an industrial/institutional package to bear
  *"not for retail sale"*. That marker is the only limb of 3(c) a label can evidence. **The
  compilation does not name the notification that made the substitution.** Semi-official source,
  stated not laundered.
- **The corpus names no institutions.** Hotels, hospitals, airlines, railways are secondary
  commentary only.
- **Rule 25 does not support an export-scope exclusion.** It restricts selling an export package
  in India *unless* re-labelled to Chapter II. `export package` is undefined in the compilation.
  The export limb stays **[SOFT]**.
- The only sourced coin dimension is the **₹10 coin at 27.0 mm**. ID-1 card is 85.60 × 53.98 mm;
  EAN-13 is 37.29 mm. These three are the whole of `REF_DIMS`.
- `SIH26034_PSR.md` §3 carries a **wrong Rule 7 figure**. Not a source for rule facts.
- **The rule store holds 28 rules.** Read the ids out of
  `bck/app/modules/rules/data/rules.yaml`; do not read them out of a document.

---

## Hard nos — do not re-propose

- Margin measurement types as **subclasses** of the strict types. Settled: siblings off private
  bases.
- **A single measurement type with nullable calibration fields.** It makes an artwork-derived
  figure and a photograph-derived one indistinguishable at the type level, which is the shape
  `measurement.py` exists to make unrepresentable.
- Moving `ExtractionResult` into `contracts/`. ARCHITECTURE.md records it as tidy-up, and
  PIP-002's `contracts/binding.py` was dropped from history so it would not be recreated.
- A `paths:` filter or an `if:` on any job in `ci.yml`.
- A ruff step on the datasets job before the seven UP042 findings are fixed.
- Re-adding a `ReferenceObjectType` member without its `REF_DIMS` entry and detector branch in
  the same PR. This is now enforced by `datasets/tests/test_schema_guards.py`, not just agreed.
- The ₹5 coin at 25.0 mm, under any spelling. Do not invent `coin_5`.
- An LLM or agent loop anywhere in the verdict path.
- **Generated or AI-synthesised label images in `datasets/`.** Proposed in Session 13 and
  refused. The corpus already died once from fabrication; a synthetic PDP feeding a Rule 7 band
  lookup produces accuracy figures about generated images. **Also refused: inpainting the coin
  out of a calibrated capture** — it leaves visible radial artefacts and destroys the very
  declarations being annotated. Both were tried and both failed on inspection.
- Millimetre measurements from uncalibrated photographs, including in ground-truth annotations.
- **Building an adapter with no producer.** Five modules have already shipped with no caller and
  MEA-005 made it six functions. The wiring ticket goes on the board in the same breath.
- **A stub, a placeholder or a `pass` body in a committed test.** #63 is the reason this is
  listed as a hard no rather than a review item.

---

## Constraints discovered the hard way

- **`rtk` intercepts `find … -exec`** and **exits 1**. `find … && pytest` fails loudly and is
  safe; `find … ; pytest` on one line silently skips the purge. **Always `/usr/bin/find`, and
  assert the directory count is zero** rather than trusting an exit code. Both CLAUDE.md and
  AGENTS.md document the safe form (#64).
- **`rtk` also intercepts `gh run view --job … --log`** → use
  `gh api repos/<r>/actions/jobs/<id>/logs`.
- **An empty grep of a CI log for `FAILED|^E |assert` means the failure is not a test.** It is
  usually `ruff format --check`, which runs *before* Lint, Import boundaries and Tests — so a
  format failure means **nothing in the PR has been verified by CI**. Grep for
  `Process completed with exit code` instead.
- **`-x` produces false confirmations.** With `-x`, pytest reports whichever test comes first in
  file order, not the one the injected defect targets. Reproduced independently by three
  sessions. **Always falsify without `-x`, and confirm the test that went red is the one the
  defect aims at.**
- **`git checkout -- <file>` wipes real edits alongside the injected defect.** Happened three
  times in one day. Keep a scratchpad copy and restore from that.
- **Same-length string edits run stale bytecode.** This is why the purge is load-bearing.
- **Check exit codes directly, never through a pipe.** `lint-imports | tail` reports `tail`'s
  status, which is always 0.
- **Port-shadowing:** `POSTGRES_PORT` in repo-root `.env`, `DATABASE_URL` in `bck/.env`, nothing
  linking them.
- `--ours` / `--theirs` mean opposite things in rebase vs merge.
- Never hand-resolve `uv.lock` conflict markers — delete and regenerate.
- Never run manual git commands in a folder a Claude Code session has open. Use a worktree.
- **`alembic check` does not detect a change to the *values* of an existing enum.** Adding a
  member passes clean then fails at first insert. Needs `ALTER TYPE … ADD VALUE`, which cannot
  run inside a transaction.

---

## Decisions this session — do not re-litigate

**MEA-009 Part A (#73, merged).** Two overlap types — `MeasurementMarginOverlapExact` and
`MeasurementMarginOverlapCalibrated` — siblings off the private bases, field named `overlap`
not `value`, `gt=0`. **Rejected:** a single type with a nullable `confidence_interval` and
`reference_object`, because it makes an artwork-derived overlap and a photograph-derived one
indistinguishable at the type level. **`overlap` rather than `value` because**
`pipeline/measurement_findings.py:59` formats `f"{result.value} {result.unit}"` for any
non-refusal result, so a `value=2.0` overlap would reach an officer as the identical string a
2 mm clearance produces. Named `overlap`, that line raises instead of lying.

**PIP-003 (#74, merged).** `propose_category` wired into `pipeline/orchestrator.py:283` as a
proposal that never writes itself into the confirmed category. **`CategoryProposal` is not
exported from `extraction/__init__.py`** — only `propose_category` is. **Rejected:** exporting
both, because `CategoryProposal` is a contracts type and a second import path for it is the same
defect class as the `bck.*` path the third import-linter contract forbids. **Also rejected:** a
deep `from app.modules.extraction.category import …`, which reaches past the module's public
surface. Crossing into Sitanshu's `__init__.py` was authorised **for that ticket only**.
Two follow-ups deliberately not taken: the proposal is **not persisted** (present on the POST
response, `None` on a GET re-read — the `scans` row has no column), and the catalogue path
proposes nothing because `propose_category` takes an `ExtractionResult` a listing never builds.

**RUL-006 (#75, merged).** `applies_to` **removed, not deprecated**. Verified by grep: zero
readers, and the six scope tokens appear nowhere in `bck/app/` except `rules.yaml`. **The
ticket said fourteen rules; it was 28** — every rule in the store, because `applies_to` was
`Field(min_length=1)`. 29 tokens, 6 distinct, 22 of them `retail_packages`. **The replay hazard
was checked by running the actual read-back, not reasoned about:** `applies_to` was a key inside
`parameters` (`dict[str, JsonValue]`), and `extra="forbid"` governs model fields, not dict keys,
so historical rows re-validate unchanged. No migration, no backfill.
`test_rule_store_contains_only_ticket_authorized_scopes` was **deleted, not adapted** — a `<=`
subset assertion is green against the empty set, and it stayed green while a whole rule was
deleted. **Do not re-raise it as an unfalsifiable test needing a ticket; it is gone.**
`contracts.RuleDefinition.applies_to` survives at `contracts/rules.py:60`, defaulting to `()`,
reachable only through `RuleParameterSnapshot.from_rule`, which nothing in `bck/app/` calls.
Recorded as a follow-up, not an oversight.

**RUL-007 (#76, open).** Two side variants, not three. `SideClearance` (`distance_mm`,
`NonNegativeDecimal`, `0.0` == flush) and `SideOverlap` (`overlap_mm`, `PositiveDecimal`), as a
discriminated union. **Rejected:** widening the numeric type and letting the sign carry meaning
— `modules/rules/placement.py` is one generator expression doing `observed < required` and would
report a 2 mm overlap and a 2 mm clearance identically. **Rejected:** a third `SideFlush`
variant — contracts models flush as a margin of `0.0`, and admitting `0.0` to overlap would give
one physical fact two representations. `Rule8FreeSpaceEvaluation` gains `overlapping_sides`
separate from `deficient_sides`.

**MEA-005 (#43, merged).** Finished on Yashashvi's own branch with commits on top and
`--force-with-lease`, **not a new PR**. Her authorship on `artwork.py` is intact and her commits
keep their original messages. **SVG stripped and moved to MEA-010** because it means parsing
untrusted XML from an outside manufacturer and `xml.etree.ElementTree` is vulnerable to entity
expansion — MEA-010 requires `defusedxml` and a billion-laughs test that must go red when
swapped for the stdlib parser. `PT_TO_MM` extracted from two inline copies to
`artwork.py:9`. `pdfplumber` approved: pure Python over `pdfminer.six`, no system libraries.
**Artwork mode is the only path yielding an exact millimetre figure.**

**DAT-005 — `declared` is per-image, not pack-level.** A scan is one image. A back-panel
declaration annotated on the front image is `declared: false` + `INSUFFICIENT_EVIDENCE`.
**Rejected:** pack-level `true`, which asserts evidence the system never had and makes the
harness score a correct refusal as a miss. This leaves a real schema gap — `declared: false` now
means both "absent from the pack" and "not in frame", which contradicts `datasets/README.md`.
Needs a `NOT_IN_FRAME` state or a `visible_in_image` bool. Ticket is in `TODO.md`.

**Carried from Session 13, still binding:**

**CORE-003 (#62).** `asset_type` on the evidence entry: required, no default, on model and
column; folded into `compute_entry_hash`. Three members — `PRODUCT_IMAGE`, `PERSONAL_DATA`,
`AUDIT_LOG` — in `contracts/enums.py`, because `core` may not import from `modules`.
`FIELD_VERDICT` deleted (no consumer); `GEOLOCATION` merged into `PERSONAL_DATA` (same retention
window, no branch distinguished them). **`DERIVED_ARTEFACT` deliberately excluded** — no
retention branch consumes it; adding it later needs a non-transactional `ALTER TYPE`, which is
Abhiram's to write when EVD-006 lands the branch.

**CTR-006 (#65).** `CompetingReadings` (frozen, `readings` tuple `min_length=2`, `reason`) and
`DisagreementReason` with **one member**, `BILINGUAL_VALUE_MISMATCH`, whose docstring
deliberately spans both limbs of the binder's `or` — value and unit. A second member for the
unit limb has no consumer. `ExtractionResult` gained `disagreements` plus a `model_validator`
refusing any `field_type` in both collections — **structural, because a test asserting
disjointness over real `bind_spans` output would be vacuously true until EXT-007.**

**PIP-004 (#67).** `contested: Mapping[DeclarationField, tuple[CompetingReadings, ...]]` on
`EvidenceContext` — a tuple, because two spatial pairs against one obligation can each disagree.
`REVIEW_REQUIRED` produced as a **literal**, not through `FIELD_STATE_FROM_VERDICT`: the
round-trip computes a constant, and it would hand the branch the FAIL branch's exact expression
shape, one token from rerouting. The branch sits **above `if values:`** and that ordering is
pinned by `test_a_contested_declaration_outranks_a_resolved_one`.

**RUL-005 (#68, #69).** `R3-CHAPTER-II-SCOPE` in the store; new `ChapterScopeCondition`; new
`scope.py` sibling to `sector.py`; callsite is `build_findings`, once per scan, **before** the
sector check. Order that survives: **scope → sector → contested → `if values:`**. `ScopeStatus`
is `GOVERNED` / `EXCLUDED` / `UNCERTAIN`; the marker produces `UNCERTAIN`, never `EXCLUDED`;
**absence infers nothing**. `derive_verdict` gained an all-`NOT_APPLICABLE` → REVIEW pass —
previously it fell through to **PASS**, which would have been a new wrong answer shipped by the
PR fixing the old one. Officer confirmation is a request field
(`institutional_or_industrial_confirmed`, default `False`), **not persisted**.

**MEA-006 (#47).** Zero margin permitted; interval floored at one pixel's mm equivalent as a
documented uncalibrated prior. She also rewrote the slicing so each direction scans only its own
half-plane with perpendicular bands masked — fixing an unticketed bug where ink far to the left
could register as the *above* margin.

**EXT-007 (#71, merged).** Landed on `binder.py`, populating `ExtractionResult.disagreements`.

---

## The frontend design system

Light-ground and light-first — a state enforcement tool read in daylight, not a dark dashboard.
Eight states (five field, three verdict) separable in greyscale, colour last of four channels.
Tokens and the two contrast findings are in `fnt/DESIGN.md`.

**FNT-003 landed as #72.** `fnt/src/services/generated/schema.d.ts` is now a real generated
artefact, not a README placeholder, produced by `fnt/scripts/generate-api.mjs`;
`fnt/src/services/apiClient.ts` wraps it and `fnt/src/officer/ReviewQueue.tsx` is the one screen
moved onto it. Everything else still runs on `fnt/src/fixtures/`.

`fnt/src/services/generated/` is regenerated from the backend OpenAPI schema and is not to be
hand-edited. **FNT-004 must run `npm run generate:api` first** — PIP-003 changed the schema.

**A duplicate SVG pattern `id` across breakpoint variants** resolves `url(#…)` to the hidden
element and paints nothing. Scope with `useId`. Only a real browser at two widths catches this.

---

## Where the board stands, dated 2026-09-07

**`main` is at `19c7966`, and it moved four times while this file was being written.** #76
RUL-007, #46 EVD-005 and #78 FNT-004 merged within nine minutes; #66 EXT-008 followed; #77
DAT-005 opened; #63's head moved twice. Every OID below is a timestamp, not a fact — re-read
before acting. **The findings were re-verified against each new head and none of them changed**,
which is the useful half: an OID moving is not evidence that anything was addressed.

**Merged 2026-09-07:** #62 CORE-003 · #56 EXT-006 · #64 DAT-003 docs · #47 MEA-006 · #65 CTR-006
· #67 PIP-004 · #68 RUL-005 · #69 docs · #70 docs · #71 EXT-007 · #73 MEA-009 Part A ·
#72 FNT-003 · #74 PIP-003 · #43 MEA-005 · #75 RUL-006 · #76 RUL-007 · #46 EVD-005 · #78 FNT-004
· #66 EXT-008.

**Open PRs:**

| PR | Owner | Ticket | Head | Base | State |
|---|---|---|---|---|---|
| #77 | Abhiram | DAT-005 | `6a2e9fa` | `a4e462c` | Open, three checks green. Twelve annotated captures, uncalibrated throughout, and a populated manifest. **The highest-value item on the board.** Read it against `ingest_images.py` first — the manifest uses `records`, the writer writes `samples`. |
| #63 | Akshaya | VIS-004 | `71147c9` | `19c7966` | **Blocked.** `test_ocr.py` is 27 lines: five `pass` bodies and a `test_placeholder_ocr`. Three checks green over a hollow suite. Head has moved twice; that file is byte-identical at every one of them. |

**#66 EXT-008 merged with its last item open.** `binder.py:190` on `main` is
`if len(matching_scripts) > 1: return ScriptType.MIXED`, so `MIXED` means any two of five scripts
and no longer marks the Devanagari/Latin pair Rule 9(4) turns on — the pair EXT-006 and EXT-007
both key off. Opened as **EXT-009**. Do not write it into the `done` EXT-008 ticket; nobody reads
those.

**#46 merged with half its blocker fixed.** The false attestation is closed —
`retention.py:106` aborts on a storage miss instead of writing an audit entry. The key
derivation still differs from the CAS write path (`payload_hash` vs `sha256(image_bytes)`), and
whether they coincide depends on what a caller passes as `payload` — **and retention has no
caller**. Undetermined at runtime, untestable today, and it will be settled by whoever wires it.
Tracked as EVD-007. Do not write it into the `done` EVD-005 ticket.

**Sessions running at handoff — ask Abhiram for both outputs before acting:**
`DAT-005` in `~/26034-dat` on `dat-005-annotate-staged-captures`, annotating the staged captures;
`RUL-007` in `~/26034-ctr`, now open as #76.

**To do:** MEA-010 and MEA-011 (Yashashvi, both unblocked by #43) · MEA-007 (Yashashvi, in
progress, needs a rebase — `services.py` changed) · MEA-008 · MEA-009 Part B (Yashashvi) ·
FNT-004 (Vineeth, unblocked, `npm run generate:api` first) · TAM-002 (Akshaya, genuinely blocked
on DAT-005 landing) · EVD-006 (Shiva).

**Open items nobody owns yet:** the seven UP042 findings; persisting the Rule 3(c) officer flag;
the `/fnt/` three-way ownership disagreement; the seven identified-not-written tickets in
`TODO.md`.

**The ARUCO_MARKER discrepancy is closed.** Do not re-raise it.

---

## The gap that matters more than any ticket

**No image has ever passed through this pipeline.** `main.py` will not boot without model
weights that exist on no machine. Every one of the ~800 tests is a unit test against mocks or
synthetic spans. `measure_margins` is not wired to the orchestrator (blocked on EXT-004), tamper
detection is not wired, the corpus has no validated annotations, and `ReviewQueue.tsx` calls an
API nobody has watched respond.

Module code is roughly 70% built. The assembled system is 0% demonstrated. That gap is one
ticket wide — VIS-004 (#63), which has now burned more than a day and has gone backwards.

---

## Abhiram's mentor changes

He has changes from his SIH mentor and guide that he is deliberately holding until the current
board is finished. They may touch the rule store or the verdict path. **Do not raise this
repeatedly — he has been told twice and has decided.** Ask once when the board clears.

---

## Golden examples

**A test that fetches its own expectation.**
BAD: `assert parameters.not_for_retail_sale_marker == rule_by_id(ID).conditions.not_for_retail_sale_marker` — the store compared against itself; a same-length swap leaves it green.
GOOD: `assert parameters.not_for_retail_sale_marker == "not for retail sale"` — the corpus literal, written in the test.

**A falsification that does not falsify.**
BAD: move the scope check below the builders but leave it winning the return — four unrelated tests go red, both ordering tests stay green, and you call it confirmed.
GOOD: inject the regression the test actually claims to catch — the builder's result winning — and confirm both go red.

**Reviewing a rebased PR.**
BAD: three-dot compare from the old head, see twenty files, conclude scope creep.
GOOD: compare against `main`. Three files, one module, clean rebase.

**Deleted coverage behind a green tick.**
BAD: three checks pass, merge it.
GOOD: read `0/45` on a test file and ask what went. Twelve tests deleted, five restored, five never replaced.

**Hollowed coverage behind a green tick.**
BAD: grep the patch for `^[-+]def test_`, see the names come back, report them restored.
GOOD: read `+15/-187`, notice additions are a twelfth of deletions, open the file, find six functions with `pass` bodies and one `assert True`.

**A document asserting a fact nothing checks.**
BAD: someone notices `R6-1-C` is missing from the encoded-id list, so add `R6-1-C`.
GOOD: diff the whole list against `rules.yaml`. Eleven ids missing, two listed that never existed, and no test anywhere reads the file. Regenerate the list from the store and say that nothing pins it.

**Deriving a number versus carrying one.**
BAD: "CI reports ~45 higher" — written from memory, wrong, and copied forward into the next session's instructions.
GOOD: "CI reports +30 passed and −30 skipped, because thirty tests are postgres-marked and the runner provides Postgres." The mechanism survives the next merge; the number does not.

**Correcting your own claim.**
BAD: leave the docstring saying the binder leaves the marker unclassified, because the code works anyway.
GOOD: measure it, find it binds to `COMMON_OR_GENERIC_NAME`, fix the sentence, and find the fixture where the claim *is* true.

**Correcting a correction.**
BAD: this file said `ARUCO_MARKER` was deleted, then "corrected" itself to say it was still present, and carried the false correction as an open item across two sessions and into two other documents.
GOOD: open `datasets/schema.py`, count the four enum members, find the guard at `test_schema_guards.py:89`, and record that the original claim was right and the correction was the error.
