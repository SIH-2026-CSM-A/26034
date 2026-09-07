# HANDOFF.md — end of Session 13, 2026-09-07

Written from chat context. Everything else in project knowledge mirrors the repo; this file
does not. Read it first.

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

---

## What you can and cannot do — connector limits

- **ClickUp MCP came back mid-Session 13** after being rate-limited for all of Session 6.
  Test once with a cheap `clickup_filter_tasks` before assuming it works.
- **Custom field writes are capped on this plan.** `clickup_update_task` with `custom_fields`
  returns *"Custom field usages exceeded for your plan"*. Name and status updates still work.
  FNT-003's branch field is consequently wrong on the board — it reads
  `fnt-001-generated-api-client`; the real branch is `fnt-003-generated-api-client`. Tell
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
   items are still owed — say so in one line and do not re-read.
2. **Read the file list and byte count before the diff.** A PR that should be three files and
   is four has something in it nobody asked for.
3. **Read the file-count deltas, not just the names.** `0/45` on a test file means forty-five
   lines deleted and nothing added. Session 13 caught VIS-004 deleting twelve OCR tests across
   two pushes while all three checks stayed green. **A suite with its guards removed passes
   easily.**
4. Under ~300 lines, paste in chat. Over, upload as `pr<n>-review.md`, then `-v2`. Never
   overwrite. `.md`, never `.diff`.
5. Never more than two diffs at a time.
6. Read any migration in full.
7. **Merge gate:** checks green · one module · in ticket scope · no migration · no auth change ·
   no shared-contract change · no new dependency. Otherwise escalate.
8. For his own PRs, skip `gh pr review --approve` — GitHub blocks self-approval. Merge with
   `gh pr merge <n> --squash --admin --delete-branch`.

**Cheap targeted greps beat full diffs.** Session 13 settled three reviews without pulling a
diff at all:
- Lexicon claim: `gh api repos/$R/contents/<path>?ref=<sha> -q .content | base64 -d | grep -n`
- Deleted tests: `gh api repos/$R/pulls/<n>/files -q '.[]|select(.filename|endswith("x.py"))|.patch' | grep -E "^[-+]def test_"`
- Rebase artefacts: compare against `main`, not the old head. A three-dot compare from the old
  head shows everything main gained since branching, mixed in with the author's own work, and
  looks like scope creep when it is a clean rebase.

---

## The recurring failure patterns

1. **A session log describing work not in the branch.** Diff the code against the previous head
   before believing a rework claim.
2. **Tests that cannot fail.** Now at seven instances. Session 13 added a new species: **a test
   that fetches its own expectation.** RUL-005's marker and threshold tests read the value out
   of `rules.yaml` and compared it back against the store, so a same-length swap of
   `not for retail sale` → `not-for-retail-sale` left both green. Fixed by pinning corpus
   literals. **Watch for any test whose expected value is loaded rather than written.**
3. **A falsification that does not falsify.** RUL-005 first moved the scope check below the
   builders but left it winning the return — only four unrelated tests went red and both new
   ordering tests stayed green. That would have been a false confirmation. The real regression
   was the builder's result winning. **Check that the defect you inject is the defect the test
   claims to catch.**
4. **Deleting tests on the ticket that exists to prove they pass.** VIS-004, twice.
5. **Modules merging with no caller.** Four so far. Every such merge needs its wiring ticket
   created in the same breath.
6. **Stale bases and stale baselines.** The local test count moved twice in one session.
   **Measure the baseline on `origin/main` in the same session; never quote CLAUDE.md's figure.**

---

## Claims that turned out wrong, and who caught them

- **I said `ARUCO_MARKER` was deleted from `ReferenceObjectType`** and used it as the precedent
  for the member-consumer deletion rule. It is still at `datasets/schema.py:55` with
  `RULER_SCALE` and `CHECKERBOARD`, none of which have `REF_DIMS` entries. ARCHITECTURE.md and
  HANDOFF.md both say they were deleted. **There is no enforced member-consumer guard anywhere
  in the repo.** The rule is still right; it is applied fresh, not inherited. Caught by the
  CORE-003 session. **Still unresolved — open item.**
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

---

## Infrastructure state, dated 2026-09-07

- **`main` is past #69.** Verify the SHA rather than trusting any figure here.
- **Local baseline moved twice in Session 13:** 731/32 → 739/32 (#65) → 741/32 (#67) → 772/32
  (#68). CI reports ~30 higher because it un-skips the postgres-marked tests. **CLAUDE.md's
  707/32 was stale all session.** Measure, do not quote.
- **`datasets` is already a required status check.** Confirmed in the ruleset UI. Three checks
  report on every PR: `backend`, `datasets`, `frontend`. Two means a stale base.
- **"Require branches to be up to date before merging" is deliberately unchecked.** Turning it
  on would force five people to rebase on every merge. The cost is that a stale base can carry a
  green tick past the gate — which is why you read the check *list*, not just the colour.
- **`ci.yml` has no `paths:` filter and must never gain one.** An `if:` on a job is the same
  deadlock in a different costume.
- **`datasets/` is not ruff-clean** — seven pre-existing UP042 findings. The datasets job has no
  ruff step for that reason.
- **Worktrees:** `26034-ci`, `26034-fnt`, `26034-rules` under `~/NewProjects/`; `26034-ctr`,
  `26034-dat`, `26034-docs` under `~`. Confirm with `git -C ~/NewProjects/26034 worktree list`
  before creating one. Several sit on merged branches and need a fresh cut from `origin/main`.
- **Session-log numbering in `session-log/abhiram.md`: 10 = CORE-003, 11 = CTR-006,
  12 = PIP-004, 13 = RUL-005. Next is Session 14.** Resolve conflicts by reconstruction — take
  main's file verbatim, append your block — never by editing markers, and prove it with
  `git diff --numstat` showing zero deletions.

---

## Owners and usernames

| Person | GitHub | ClickUp | Owns |
|---|---|---|---|
| Abhiram | `Abhiram-0910` | 240010775 | contracts, pipeline, core, alembic, datasets, CI, rules. Sole merger. |
| Akshaya | `aksha08-ya` | 106878763 | vision, tamper |
| Shiva Kumar | `Shiva-Kumar-Akula` | 106878759 | evidence |
| Sitanshu | `krishbattula4` | 106878761 | extraction |
| Yashashvi | `Yashashvi-05` | 106878758 | measurement |
| Vineeth | — | 106878762 | frontend (FNT-003) |

- **Aashritha is off the project. Assign her nothing.** CODEOWNERS now reassigns `datasets/` to
  Abhiram (#64).
- **The `fnt/` officer surface stays with Abhiram** even though Vineeth is available again. It
  is on the demo path and Abhiram drives it on stage. Vineeth gets bounded frontend work under
  Abhiram's merge, not his module back.
- **B.V. Yashwanth (240010980, not on the team), Jashwanth Badugu (106878760, unavailable) and
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
  encode with `effective_from`, do not omit.
- **Rule 6(11)** is a format rule with zero tolerance. The ±₹0.01 / ±₹0.05 figures in older
  project docs are assumptions, not law.
- **Rule 26** exempts packages of 10 g / 10 ml or less, except tobacco. Two staged samples fall
  under it: a 2 g Maggi sachet and a 6 ml Dove sachet. **An exempt obligation is NOT_APPLICABLE
  even when the label satisfies it voluntarily — not PASS.**
- **Rule 3** (new, RUL-005) — Chapter II applicability, three limbs: (a) more than 25 kg or
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
  EAN-13 is 37.29 mm.
- `SIH26034_PSR.md` §3 carries a **wrong Rule 7 figure**. Not a source for rule facts.

---

## Hard nos — do not re-propose

- Margin measurement types as **subclasses** of the strict types. Settled: siblings off private
  bases.
- Moving `ExtractionResult` into `contracts/`. ARCHITECTURE.md records it as tidy-up, and
  PIP-002's `contracts/binding.py` was dropped from history so it would not be recreated.
- A `paths:` filter or an `if:` on any job in `ci.yml`.
- A ruff step on the datasets job before the seven UP042 findings are fixed.
- Re-adding a `ReferenceObjectType` member without its `REF_DIMS` entry and detector branch in
  the same PR.
- The ₹5 coin at 25.0 mm, under any spelling. Do not invent `coin_5`.
- An LLM or agent loop anywhere in the verdict path.
- **Generated or AI-synthesised label images in `datasets/`.** Proposed in Session 13 and
  refused. The corpus already died once from fabrication; a synthetic PDP feeding a Rule 7 band
  lookup produces accuracy figures about generated images. **Also refused: inpainting the coin
  out of a calibrated capture** — it leaves visible radial artefacts and destroys the very
  declarations being annotated. Both were tried and both failed on inspection.
- Millimetre measurements from uncalibrated photographs, including in ground-truth annotations.

---

## Constraints discovered the hard way

- **`rtk` intercepts `find … -exec`** and **exits 1**. `find … && pytest` fails loudly and is
  safe; `find … ; pytest` on one line silently skips the purge. **Always `/usr/bin/find`, and
  assert the directory count is zero** rather than trusting an exit code. Both CLAUDE.md and
  AGENTS.md now document the safe form (#64).
- **`rtk` also intercepts `gh run view --job … --log`** → use
  `gh api repos/<r>/actions/jobs/<id>/logs`.
- **An empty grep of a CI log for `FAILED|^E |assert` means the failure is not a test.** It is
  usually `ruff format --check`, which runs *before* Lint, Import boundaries and Tests — so a
  format failure means **nothing in the PR has been verified by CI**. Grep for
  `Process completed with exit code` instead.
- **Same-length string edits run stale bytecode.** This is why the purge is load-bearing.
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

**CORE-003 (#62, merged).** `asset_type` on the evidence entry: required, no default, on model
and column; folded into `compute_entry_hash`. Three members — `PRODUCT_IMAGE`, `PERSONAL_DATA`,
`AUDIT_LOG` — in `contracts/enums.py`, because `core` may not import from `modules`.
`FIELD_VERDICT` deleted (no consumer); `GEOLOCATION` merged into `PERSONAL_DATA` (same retention
window, no branch distinguished them). **`DERIVED_ARTEFACT` deliberately excluded** — no
retention branch consumes it; adding it later needs a non-transactional `ALTER TYPE`, which is
Abhiram's to write when EVD-006 lands the branch.

**CTR-006 (#65, merged).** `CompetingReadings` (frozen, `readings` tuple `min_length=2`,
`reason`) and `DisagreementReason` with **one member**, `BILINGUAL_VALUE_MISMATCH`, whose
docstring deliberately spans both limbs of the binder's `or` — value and unit. A second member
for the unit limb has no consumer. `ExtractionResult` gained `disagreements` plus a
`model_validator` refusing any `field_type` in both collections — **structural, because a test
asserting disjointness over real `bind_spans` output would be vacuously true until EXT-007.**
Authorised crossing into `modules/extraction/`, this ticket only, not precedent.

**PIP-004 (#67, merged).** `contested: Mapping[DeclarationField, tuple[CompetingReadings, ...]]`
on `EvidenceContext` — a tuple, because two spatial pairs against one obligation can each
disagree. `REVIEW_REQUIRED` produced as a **literal**, not through `FIELD_STATE_FROM_VERDICT`:
the round-trip computes a constant, and it would hand the branch the FAIL branch's exact
expression shape, one token from rerouting. The branch sits **above `if values:`** and that
ordering is pinned by `test_a_contested_declaration_outranks_a_resolved_one`.

**RUL-005 (#68) and its docs (#69, both merged).** `R3-CHAPTER-II-SCOPE` in the store; new
`ChapterScopeCondition`; new `scope.py` sibling to `sector.py`; callsite is `build_findings`,
once per scan, **before** the sector check. Order that survives:
**scope → sector → contested → `if values:`**. `ScopeStatus` is `GOVERNED` / `EXCLUDED` /
`UNCERTAIN`; the marker produces `UNCERTAIN`, never `EXCLUDED`; **absence infers nothing** and
all 739 pre-existing tests pass unchanged with the gate in place, which is that property
demonstrated rather than asserted. `derive_verdict` gained an all-`NOT_APPLICABLE` → REVIEW pass
— previously it fell through to **PASS**, which would have been a new wrong answer shipped by
the PR fixing the old one. Officer confirmation is a request field
(`institutional_or_industrial_confirmed`, default `False`), **not persisted** — that needs a
contracts enum and a migration and is raised, not added.

**MEA-006 (#47, merged).** Zero margin permitted; interval floored at one pixel's mm equivalent
as a documented uncalibrated prior. She also rewrote the slicing so each direction scans only
its own half-plane with perpendicular bands masked — fixing an unticketed bug where ink far to
the left could register as the *above* margin.

**`pdfplumber` approved for MEA-005.** Pure Python over `pdfminer.six`, no system libraries.
Artwork mode is the only path yielding an exact millimetre figure. **Scoped to PDF; SVG is its
own ticket if it ever arrives.**

**DAT-005 parked, deliberately.** All six staged "uncalibrated" captures have ₹10 coins in
frame, so the uncalibrated half of the set does not exist and the refusal path has no sample.
Cropping the coin out destroyed the declaration block; inpainting left visible starbursts. **The
fix is a phone and a real package, not image processing.** Corpus stands at zero and **no
accuracy figure is quoted anywhere**.

---

## The frontend design system

Light-ground and light-first — a state enforcement tool read in daylight, not a dark dashboard.
Eight states (five field, three verdict) separable in greyscale, colour last of four channels.
Tokens and the two contrast findings are in `fnt/DESIGN.md`. The officer surface still runs
entirely on `fnt/src/fixtures/`; `fnt/src/services/generated/` holds only a README. FNT-003
lands the generated client and moves exactly one screen onto it.

---

## Where the board stands, 2026-09-07

**Merged this session:** #62 CORE-003 · #56 EXT-006 · #64 DAT-003 docs · #47 MEA-006 ·
#65 CTR-006 · #67 PIP-004 · #68 RUL-005 · #69 docs.

**Open PRs:**

| PR | Owner | Ticket | State |
|---|---|---|---|
| #63 | Akshaya | VIS-004 | **Blocked.** Twelve OCR tests deleted across two pushes, five restored. Five still missing, including both offline-guarantee tests and the provider-arbitration test. Plus `px_to_cm_ratio` / `area_cm2` must come off `PDPResult`; empty-detection must refuse; the `DetectionResult`→`PDPResult` rename is held. |
| #66 | Sitanshu | EXT-008 | Two changes owed: remove the "Page 9" citation (a pdftotext artefact), and actually separate recognised-but-unnormalisable from noise — Tamil and Bengali were added but Telugu and `"12345 !!!"` still share `NEITHER`. |
| #46 | Shiva | EVD-005 | **Red on Format check**, so nothing is CI-verified. Needs `ruff format .`, then a rebase onto CORE-003. The six review items stand; the `storage_key` false attestation is the blocker. |
| #43 | Yashashvi | MEA-005 | Unblocked — `pdfplumber` approved. Needs a rebase; main moved many times. |

**Abhiram's queue:** MEA-009 (contract half) → RUL-006 → PIP-003 → DAT-005 when photos exist.

**EXT-007 is unblocked** — both CTR-006 and PIP-004 are on main. Sitanshu should finish or park
#66 first; never two branches in one module.

**On the board and not started:** TAM-002 (blocked on DAT-005), MEA-007, MEA-008, MEA-009,
RUL-006, PIP-003, EXT-007, FNT-003.

**Open items nobody owns yet:** the `ARUCO_MARKER` discrepancy; persisting the Rule 3(c) officer
flag; the seven UP042 findings; `TODO.md`'s stale header.

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

**Correcting your own claim.**
BAD: leave the docstring saying the binder leaves the marker unclassified, because the code works anyway.
GOOD: measure it, find it binds to `COMMON_OR_GENERIC_NAME`, fix the sentence, and find the fixture where the claim *is* true.
