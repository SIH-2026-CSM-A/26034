# HANDOFF.md

For a fresh Claude chat resuming as strategist / architect / engineering lead on PCCS
(SIH 2026, PS 26034). This is the **fifth** handoff in the project's history.

Read after `AGENTS.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `TODO.md`, `TICKETS.md` and
`RULES-CORPUS-INDEX.md`. This file carries only what is written down nowhere else.

Every line here exists because a session would behave differently without it. If it were
merely true, it was cut.

---

## How Abhiram works with you

Decide, don't offer menus. One recommendation with the tradeoff in one line. Exact
pasteable terminal commands, never a command described in prose, and **never a placeholder
like `<number>` inside a command** — substitute the real value every time. Chain multi-step
commands with `&&` when a later step depends on an earlier one.

For anything outside the terminal — a settings panel, a form — every click and every field,
assuming he has not seen the screen.

Say when something won't work instead of finding a way to agree. Mark unverifiable claims
soft. Never claim a probability of winning.

**One thing at a time when he asks for it.** He will say so explicitly. Give one question or
one task per message and wait. Do not batch.

**Write teammate tickets as complete work orders.** This changed in session 5 and it
matters: teammates were spending hours per ticket because the tickets assumed context they
did not have. Exact files, exact signatures, commands in order, falsification steps spelled
out, an explicit out-of-scope list, and a "Before you raise the PR" block built from that
ticket's own failure modes. CI-004, DAT-004, DAT-005, MEA-007 and PIP-003 are the format.

**Standing orders, verbatim in force:** don't ask how much time is left, don't wind down.
When a ticket closes the next one already exists; when the board runs low, extend it from
the PRD and feature spec yourself. Depth before breadth. He will say explicitly, 24 hours
before stopping — only then switch to wrapping up.

He runs Claude Code in WSL Ubuntu at `~/NewProjects/26034`. Windows paths are under
`/mnt/c/Users/drona/`.

**On AI-generated images:** he has stated he uses them and does not want the objection
repeated. It was raised once in session 5 and dropped. Do not re-litigate it. Annotate
honestly per image — a garbled or illegible field annotates as `null`, whatever produced it.

---

## What you can and cannot do

**ClickUp connector — rate-limited 2026-09-06 19:30 for 600 minutes.** It worked for most of
session 5 and then hard-stopped. When limited, hand Abhiram each ticket as one pasteable
markdown block: title, assignee, status, priority, the three custom field values,
description. **Two status moves were owed when it hit: DAT-002 → done, CTR-004 → done.**

The connector cannot: create or edit custom field *definitions*, create or edit statuses,
remove members, delete folders. **Posting comments prompts for approval each time and often
fails — put information in the task description, not a comment.**

**The `Module 26034` dropdown rejects a plain string** — it needs an option UUID, which
`clickup_get_custom_fields` can fetch. Five tickets created in session 5 went in without it.

**There is no GitHub MCP connector.** You read `api.github.com` directly from the sandbox:
public data only, unauthenticated, ~60 requests/hour from a rotating shared IP pool. In
session 5 it worked for a handful of calls (a tree listing, a job step query) before
limiting. Assume it is unavailable and use the PR review protocol below. You cannot merge,
comment, approve or push.

**Abhiram handles all GitHub PR comments himself.** Give him draft text for ClickUp ticket
comments only.

---

## The PR review protocol — use this, it works

1. **Check the head OID before spending a diff.** He last saw head X; if it is unchanged, the
   owed items are still owed and you say so in one line rather than re-reading.

```
cd ~ && R=SIH-2026-CSM-A/26034 && gh pr view 46 --repo $R --json headRefOid,mergeable,changedFiles,additions,deletions -q '"head=\(.headRefOid[0:7]) \(.mergeable) files=\(.changedFiles) +\(.additions)/-\(.deletions)"'; gh pr checks 46 --repo $R
```

2. Then the full pull:

```
cd ~ && R=SIH-2026-CSM-A/26034 && D=/mnt/c/Users/drona/Downloads && N=46 && \
OUT=$D/pr$N-review.md && SHA=$(gh pr view $N --repo $R --json headRefOid -q .headRefOid) && \
{ echo "# PR #$N — head $SHA"; echo
  gh pr view $N --repo $R --json title,author,state,mergeable,additions,deletions,changedFiles,headRefName,updatedAt
  echo; echo "## Checks"; gh pr checks $N --repo $R 2>&1 || true
  echo; echo "## Files"; gh pr diff $N --repo $R --name-only
  echo; echo "## Diff"; echo '```diff'; gh pr diff $N --repo $R; echo '```'; } > "$OUT" && \
echo "$OUT $(wc -c < "$OUT")"
```

3. **Filename convention: `pr<n>-review.md`, then `-v2`, `-v3`.** Never overwrite —
   retrieval hands you a stale copy if two files share a name. **`.diff` cannot be uploaded
   to project knowledge; `.md` can.**
4. **Read the file list and byte count BEFORE the diff.** This caught a real defect in
   session 5: #42 came back as 4 files when it should have been 3, and the fourth was a 12 KB
   junk file at the repo root named from a shell quoting accident. The list told us in one
   line what the diff would have buried.
5. **Never ask for more than two diffs at a time.**
6. **Read the migration in full for any PR that adds one** — it can never be edited after merge.
7. **Delete a PR's files from project knowledge once it merges.**
8. Under ~300 lines, pasting into chat is fine.
9. `gh pr diff` takes **no pathspec** — `gh pr diff N -- path` fails.

**Merge gate — recommend merge only if all hold:** checks green · one module · in ticket
scope · no migration · no auth or permission change · no shared-contract change · no new
dependency. Otherwise escalate with a recommendation. When a PR fails, comment the specific
fixes — never fix it yourself.

`session-log/<n>.md` in a diff is **not** an out-of-scope violation. AGENTS.md requires it.

---

## The failure patterns that recur — check for these first

**1. Tests that cannot fail.** Five PRs in session 4; **five of five PRs in session 5**
shipped at least one. Session 5's crop: a socket-isolation test that patched both providers
so nothing ran under the block; a glyph test whose mock was told the answer and asserted it
got it back; a directory scan over four candidate paths that always skipped; a confidence
test asserting `(scale * 0.05) / scale == 0.05`; a falsification test asserting a
three-element tuple is not contained in a one-element tuple, both written as literals three
lines above.

The instruction that works, in every ticket: *"prove the test can fail — introduce the defect
it guards against, confirm red, revert."* **Assume a green suite proves nothing until someone
has introduced the defect and watched it go red.**

**2. Fabricated ground truth.** Session 5 found this was not four bad annotations but a
fabricated corpus end to end — see "Decisions this session". Memorise
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, the SHA-256 of an empty
file; it is the tell.

**3. Stale branch bases.** `gh pr checks` reporting "no checks reported" almost always means
a stale branch. Also: **`gh pr checks` returns a stale rollup for roughly 90 seconds after a
push** — it showed a 47-second-old failure on a branch that had just been fixed. Read
`statusCheckRollup` with `startedAt` and confirm the head OID matches.

**4. Session logs rewritten instead of appended.** Four PRs in session 5 destroyed an earlier
ticket's history. It only stopped when the instruction went into the ticket text with the
exact lines to restore.

---

## Claims that turned out wrong, and who caught them

- **I repeated the handoff's line that #42 was "the cheapest PR on the board, nothing about
  the code in dispute."** That came from reading the check status, not the diff. Reading it
  properly found a fabricated coin homography and three unsourced confidence figures. **One
  of the four review rounds on #42 was mine.** Read the diff before characterising a PR.
- **I told Abhiram CTR-004 needed no yaml change** because `rules.Severity` was
  rules-internal. Wrong: `rule_findings.py:194` does `Verdict(rule.severity.value)`, so the
  two enums are value-coupled and the yaml had to change with them. Found by grepping
  `app/pipeline/` before writing the ticket.
- **I said 18 `severity:` lines.** There are 17. Claude Code checked and corrected it.
- **I guessed #53's lint failure was `E402` in my own new file.** It was a pre-existing
  `E501` in `tests/contracts/test_manifest_integrity.py`. Read the log, don't guess.
- A previous session told the PIP-002 session that EXT-004 was merged when it was not.
  **Verify claims about repository state against the repository — including this file's.**

---

## Infrastructure state, 2026-09-06

**`main` at `5ff81d0`. 686 tests pass locally**, 32 skip without MinIO, Redis and a local
Postgres. 3 import contracts kept, 109 files analysed.

**What has never run: the image path with real models.** Two blockers were found in session
5. The first is fixed: `ocr.py` on `main` was written against the PaddleOCR **2.x** API
(`det_model_dir`, `use_gpu`, `show_log`, `ocr(cls=False)`) while **3.7.0** is installed, so
`extract_panel_text` could not construct a `PaddleOCR` at all — downloading weights would
only have moved the failure from boot to first call. #45 fixed it.

The second is open and is a **decision, not a download**: there is no PDP-trained YOLO model.
`detect_pdp` takes `boxes.conf.argmax()` of whatever weights it is handed, so stock
`yolov8n.pt` returns a COCO bounding box as the principal display panel, and its area feeds
the Rule 7 Table-I band lookup. Its empty-detection branch returns the **whole image** with
`confidence 0.0`, overestimating area and biasing toward POTENTIAL VIOLATION. **Do not point
`PDP_WEIGHTS_PATH` at stock weights to make boot succeed.**

`bck/.env` **does not exist**. The four required settings are `PDP_WEIGHTS_PATH` (a file),
`OCR_DET_MODEL_DIR`, `OCR_REC_MODEL_DIR`, `TESSERACT_TESSDATA_DIR` (directories). Blank is
treated as unset; each is checked for existence at boot. `tesseract` is not installed on the
dev machine. Installed and current: ultralytics 8.4.142, paddleocr 3.7.0, paddle, pytesseract, cv2.

Org `SIH-2026-CSM-A`, shared with a second team. Repo `26034` public, `26167` is B.V.
Yashwanth's. **Both public deliberately: branch protection does not exist on private repos
under GitHub Free for organisations. Never propose making it private.**

**Two stacked protections on `main`.** The `main-protection` ruleset (PR required, 1
approval, dismiss stale, code-owner review, no force push, linear history, `backend` and
`frontend` as required checks, repository-admin bypass) decides *whether* a PR is mergeable.
A classic rule restricting push to `Abhiram-0910` decides *who clicks merge*. The ruleset is
at the **repo** level: `github.com/SIH-2026-CSM-A/26034/settings/rules`. Org rulesets need
GitHub Team and do not exist here.

**`--admin` is the standard merge command for every PR.** CODEOWNERS assigns exactly one
owner per path and that owner is always the PR's author, so codeowner review can never be
satisfied. `--admin` also skips required checks, so always run `gh pr checks` in the same
breath. Abhiram cannot approve his own PRs.

**Worktrees.** `~/NewProjects/26034` (use for `gh` commands), plus `26034-ci`, `26034-fnt`,
`26034-rules` parked on detached HEAD, `26034-dat` on `dat-002-corpus-annotations`, and
`26034-docs` on `docs-session-5-handoff`. `git checkout main` fails in any worktree while
another holds it. **Never run manual git commands in a folder a Claude Code session has open.**

ClickUp: space `SIH Team` (`1300450000003833`), list `26034 Build` (`1300450000005736`).
Field IDs — `Module 26034` `87d708c9-d795-41d5-bae7-be56090b3ff1`, `Files`
`21d1ae6f-d983-44db-b2ac-d390d30b6469`, `Branch` `589b8355-8072-4ec7-b615-d78c6778bd87`.
**`done` is the terminal status. Nothing goes to `complete`.**

---

## Owners and usernames

| Person | GitHub | ClickUp ID | Module |
|---|---|---|---|
| Abhiram | `Abhiram-0910` | 240010775 | contracts, core, pipeline, alembic, .github, **rules**, **fnt officer**, **datasets** |
| Jashwanth | `badugujashwanth-create` | 106878760 | rules — **unavailable** |
| Akshaya | `aksha08-ya` | 106878763 | vision, **tamper** |
| Sitanshu | `krishbattula4` | 106878761 | extraction |
| Yashashvi | `Yashashvi-05` | 106878758 | measurement |
| Shiva Kumar | `Shiva-Kumar-Akula` | 106878759 | evidence |
| Vineeth | `vineethsimha2151` | 106878762 | fnt officer — **unavailable** |
| Shivasai | `adepushivasai901-ops` | 106878753 | tamper — never engaged, reassigned |
| Rohan | `A-Rohan99` | 216234631 | fnt admin — never started |
| Aashritha | `aashrithareddybodanampally-byte` | 106878813 | datasets — **off the project** |
| Likhitha | `Likhitha-rachelly` | 106878764 | reserve |

Jashwanth runs Codex; everyone else Antigravity + Gemini Pro; Abhiram Claude Code.

**B.V. Yashwanth (`ybaddam8-png`, ClickUp 240010980) is not on the team** — he leads 26167
and is an org Owner, therefore admin on `26034` too. Never assign him work. FNT-001, EXT-004
and RUL-004 were explicit exceptions. **B.V. Yashwanth, Jashwanth Badugu and Yashashvi are
three different people** — check the ClickUp ID, not the name.

CODEOWNERS still names Aashritha on `datasets/`; DAT-003 corrects it and is unmerged, so the
file currently lies.

---

## Legal findings — expensive to rediscover

**Rule 7 is a single Table-I banded by PDP area** since 01.01.2018 (G.S.R. 629(E)). Normal
print: ≤50 cm² → 1.0mm · 50–100 → 1.5 · 100–500 → 2.5 · 500–2500 → 4.0 · >2500 → 6.0.
**There is no 2.0mm or 3.0mm band.** Table-II no longer exists. Rule 7(3): width not less
than one third of height, except the numeral "1" and the letters i, I, l. A flat 1mm/2mm and
a 1.7mm figure both appear in older project documents — **`SIH26034_PSR.md` §3 is the
offender and is not a source for rule facts.**

**Rule 6(11) is a FORMAT rule, not a tolerance.** `Rs. per g` below 1 kg, `per kg` at or
above; `per cm`/`per metre`; `per ml`/`per litre`; `per number` by count. **The ±₹0.01 and
±₹0.05 figures in project documents are assumptions, not law, and must never be encoded.**

**Rounding increment ≠ tolerance.** A tolerance without a `tolerance_basis` fails to
construct — `Decimal("0.05")` alone is either five paise or five percent.

**Rule 8 governs placement, Rule 9 governs manner.** Encoded as four: `R8-1-PDP-PLACEMENT`,
`R8-1-FREE-SPACE`, `R9-1-MANNER`, `R9-3-OUTER-CONTAINER`. Rule 8(1)'s proviso derives from
`numeral_height_mm`, **not** `letter_height_mm`.

**Rule 7(4) PDP area:** rectangular = height × width; cylindrical = **40%** of (height ×
circumference); other = 40% of total surface area, **OR an area considered to be the
principal display panel** — that second limb is the answer for irregular shapes.

**Medical devices are a carve-out, not a stricter path.** G.S.R. 778(E) routes numeral and
letter height to MDR 2017, disapplies the Rule 33 relaxation, and makes PDP declaration
non-mandatory. **Table-I is not universal.** A false medical-device classification therefore
removes Rule 7 from evaluation entirely — which is why EXT-005's regex anchoring matters.

**Rule 6(1)(aa) vs Rule 6(10A).** 6(1)(aa) is the package declaration of country of origin.
6(10A), inserted by G.S.R. 128(E), is a *separate* obligation on e-commerce platforms,
evaluated against a `CatalogueRecord`. G.S.R. 312(E) substitutes that sub-rule effective
**01.07.2027** — encode with `effective_from: 2027-07-01`.

**Rule 26 — packages of 10 g or 10 ml or less are exempt, except tobacco products.** This
became live in session 5: the first real capture is a **2 g** Maggi sachet. Read the corpus
before writing its ground truth; if the exemption applies, most Rule 6(1) obligations are
`NOT_APPLICABLE`, not `FAIL`, and marking them FAIL trains the eval set to punish correct
behaviour.

**Combination (2(ka)), Group (2(kb)), Multi-piece (2(kc))** — G.S.R. 722(E), in force
01.01.2024. Paragraph 4's Rule 6(11) exemption is deliberately **not** encoded.

**"multi-piece package" occurs three times in the corpus, all inside G.S.R. 722(E), and that
instrument does not amend rule 9.** No multi-piece/Rule 9(3) interaction is encoded and a
test asserts the absence. Do not invent one.

**Two evidence gaps.** The DoCA consolidated e-book returns Access denied. The 11.11.2025
DoCA FAQ is not captured; two EXT-001 claims rest on secondary sources and are marked
**[SOURCED], not [VERIFIED]**.

**LMPC applies to packages intended for retail sale in India.** An export pack carries no INR
MRP obligation — `NOT_APPLICABLE`, not FAIL. *(The scope limb itself is [SOFT].)*

`consumeraffairs.gov.in`, `doca.gov.in` and `egazette.gov.in` all refuse automated access.
**Do not build a fetcher.**

---

## Hard nos — do not re-propose

- **Supabase** · **Cloud-primary OCR** · **A custom rules DSL / Drools / OPA** · **A separate
  vector database** · **Next.js** · **Two repositories** · **Python 3.12** · **Horizontal
  layer directories** · **Empty stub files per module** · **Auto-review on every PR** ·
  **A develop chain** · **Making the repo private**
- **Lightening the frontend focus tint to fix contrast.**
- **An `if:` guard to skip the frontend CI job** — a skipped job posts no status.
- **Fixing PIP-001's "unfalsifiable" deepcopy test** — documented as unfalsifiable on purpose.
- **An LLM call or an agent loop anywhere in the verdict path.**
- **Pipeline-side filtering of findings.**
- **`relationship()` on the async schema** — `MissingGreenlet` mid-serialisation.
- **`BoundDeclaration` / `DeclarationRole` / `app/contracts/binding.py`** — EXT-004's shape won.
- **A second `ExtractionResult`.** `binder.py` owns it. Sitanshu's EXT-006 log claimed a new
  `evidence.py` defining one; that must not be created.
- **PyMuPDF** — AGPL-3.0.
- **An AI-attribution trailer on a commit or a PR body.**
- **A millimetre figure from an uncalibrated photograph**, in output **or** in ground-truth
  annotations. `null` is a correct annotation.
- **`coin_inr_5` at 25.0 mm**, and now `coin_inr_1` / `coin_inr_2` — all written from memory.
  The ₹10 at 27.0 mm is the only sourced coin dimension.
- **EAN-13 nominal width at 31.35 mm** — it is **37.29 mm**, and a regression test pins it.
- **Keeping a test that cannot fail because it is green.** It gets deleted, not shipped.
- **The `coin_10` bounding-box homography.** #42 removed it: a circle under perspective is an
  ellipse with no corner correspondences, so any matrix from its bounding box maps arbitrary
  points. `coin_10` returns scale only with `h_matrix = None`. MEA-007 is the correct fix.
- **Another rule-store ticket to reduce the 65 findings.** RUL-004's corpus audit confirmed
  Rule 7(2) and 7(3) genuinely govern every declaration. It is a presentation problem now.
- **Asking a module owner to write a migration.** `alembic/` is single-owner. Split the ticket.

---

## Constraints discovered the hard way

- **`--ours`/`--theirs` mean opposite things in `git rebase` versus `git merge`.** State which
  operation is in play every time before giving either flag.
- **Never hand-resolve conflict markers in `uv.lock`.** Delete it and run `uv lock` fresh.
- **A required status check plus a `paths:` filter on its workflow is a deadlock.**
- **Required status checks cannot be added before the check has run once.**
- **import-linter needs `include_external_packages = true`** for a forbidden contract on a
  module outside `root_package`. If `lint-imports` finishes suspiciously fast it is analysing
  nothing — check the file count in its output.
- **A falsification can run against stale bytecode and report a green pass over a real
  defect.** Always `find . -name __pycache__ -type d -exec rm -rf {} +` first. CTR-004's edit
  — `"POTENTIAL VIOLATION"` → `"POTENTIAL_VIOLATION"` — is the same byte length.
- **Check exit codes directly, not through a pipe.**
- **A guard on a database constraint is only falsified by editing the migration.**
- **`alembic check` does not detect changes to the values of an existing enum type.**
- **`pytest.raises(DBAPIError)` is almost never a proof.**
- **A published container port is shadowed by any local server already on it.**
  `POSTGRES_PORT` (repo-root `.env`) and `DATABASE_URL` (`bck/.env`) must change together.
- **Deleting the ClickUp list destroyed all ten tickets and Trash was unavailable.**
- **`git branch` does not switch to the branch.** Run `git status -sb` before every commit —
  it would have caught #42's junk file immediately.
- **A commit message containing `(` or `"` will do surprising things in bash.** #42 landed a
  12 KB file at the repo root named `urement): implement rule 7 ratio and rule 8 margin
  measurements"`. A filename containing `"` **cannot be checked out on Windows**. It passed
  both CI jobs, because nothing checks what files exist. CI-004 adds that check.
- **Before any `git reset --hard` or `checkout --ours/--theirs`, run `git status` first.**
- **`git merge main` into a feature branch destroyed a PR.** Rebase onto main, never merge in.
- **`alembic check` fails immediately after a test run** because the persistence suite
  downgrades to base. Run `upgrade head` first.
- **The unconfirmed-category sector gate silently masks tests.** It masked six.
  `tests/pipeline/sector_gate.findings_for_rule` is the only sanctioned selector.
- **`EvidenceEntryRow` shipped in CORE-002 with no writer.** A merged table — or function —
  with no caller is invisible to CI and to review. `propose_category` is currently in that
  state; PIP-003 fixes it.
- **`/tmp` is a 3.9 GB tmpfs.** Work in `~`. `uv cache prune` blocks on a concurrent `uv`.
- **Grepping a CI log for `ERROR` on this repo always returns three lines, all passing tests.**
  They are Postgres server logs from the "Stop containers" step. **Read the step name and
  conclusion:** `gh api repos/$R/actions/jobs/<id> -q '.steps[] | "\(.conclusion)  \(.name)"'`
  names the failing step in one line. `gh run view --log-failed` returns the job tail, which
  on this repo is teardown noise.
- **`gh pr checks` returns a stale rollup for ~90 seconds after a push.** Confirm the head OID
  and read `startedAt`.
- **`gh pr view --repo` requires a PR number argument.** `gh pr diff` takes no pathspec.
- **A `gh pr checks` non-zero exit breaks an `&&` chain** — use `;` between check calls.
- **`datasets/` has never been executed by CI.** The backend job is `working-directory: bck`
  with `testpaths = ["tests"]`. `datasets/eval/test_harness.py` cannot even be collected.

---

## Decisions this session — do not re-litigate

**The corpus was fabricated end to end, and is now empty.** Session 4 recorded four
annotation defects. Opening the four annotations beside their photographs, and running them
through `schema.py` for the first time, found something else: **4 of 4 failed their own
schema**, and none of the four annotations described its own image.

- Both Himalaya annotations described a 100 ml Indian retail tube, MRP ₹180.00, Bengaluru
  manufacturer. The images are two **different** EU export products, 150 ml, country of
  origin UAE, UK responsible-person address, **no MRP, no unit sale price, no Indian
  consumer-care declaration**. They shared one `sku_id` while being different products.
- Both Parle-G annotations declared 55 g. The packs read `55g+10g EXTRA=65g` and
  `110g+20g EXTRA=130g`. The consumer-care number was wrong. The unit sale price was computed
  (5.00 ÷ 55), not read; Parle-G wrappers carry none.
- One claimed a calibration reference object that is not in the frame.
- All eight declaration bboxes were byte-identical across all four files.
- None were photographs; all four were e-commerce catalogue renders.

**Why four written review rounds missed it: nobody opened an image or ran the validator,
including me until session 5.** `datasets/README.md` described a 14-SKU corpus that never
existed, with a Drive folder ID still set to the literal placeholder and an absolute WSL path
on a former teammate's machine — it read like a corpus existed. `SELF_TEST_REPORT.md`
reported 1.0000 across eight samples and nine difficulty tags the corpus never had.

All of it is deleted (#53). Fifteen real captures are staged at
`~/26034-dat/datasets/raw/_staging/`, six SKUs, gitignored. **DAT-005 owns annotating them.**

**`schema.py` is hardened so the fabrication is unrepresentable.** `ReferenceObject` refuses
`present: true` without an identified object of known size, and `present: false` carrying a
dimension or bbox. Six guards, each falsified against a real fabrication shape before
committing. `object_type` is required with no default — a default lets an incoherent
calibration claim pass review silently.

**CTR-004: the drift was the value, not the duplicate vocabulary.** `rules.Verdict` stays —
`rules/` is allowed its own internal vocabulary and `rule_snapshot.py` argues that well.
`rules.RuleStatus` was deleted and re-exports the contracts one. **`rules.Severity` is NOT
merged into `contracts.RuleSeverity`** — they answer different questions and `SEVERITY_ROUTING`
maps between them deliberately.

**The most important falsification of the session:** re-adding a duplicate `RuleStatus` inside
`rules/` left the whole suite green. `RuleParameterSnapshot.status` is typed to the contracts
enum, and a `StrEnum` member from the duplicate arrives at validation as the plain string
`"VERIFIED"`, which pydantic coerces straight back. The duplication CTR-004 removes could
have been reintroduced and nothing would notice until the enums diverged — on a live scan.
`test_the_rules_module_names_the_contracts_rule_status_and_not_a_copy` guards it.

**RUL-004 cannot deliver the reduction its ticket promised.** The corpus audit confirmed Rule
7(2) and 7(3) genuinely govern every declaration. Only `R9-1-MANNER` narrowed, to retail sale
price and net quantity, per Rule 9(1)(b)'s contrasting-colour requirement. **The remaining 65
findings are a presentation problem for the officer surface.**

**The `asset_type` migration for EVD-005 is Abhiram's, split out of #46.** Shiva does not
write it. The column lands first, then #46 rebases onto it.

**EVD-005 legal hold, decided:** hold on any POTENTIAL_VIOLATION with **no** review row, and
on any with CONFIRM or OVERRIDE. Release only on REJECT. The shipped code is inverted.

**MEA-004's coin path:** scale only, no homography, `h_matrix = None`, callers guard on it.
The 5% prior does **not** cover the resulting oblique error, and the docstring says so.

**MEA-006's contracts edit (#47):** my position is to approve it as a recorded exception
rather than re-cut a seventeen-line diff already reviewed as correct — conditional on a real
falsified test appearing.

**EXT-005's confidence scores** (0.95 / 0.80 / 0.98) are named constants documented as
uncalibrated priors. Same for MEA-004's 1% / 5% / 10%. Neither has a source; both say so.

---

## The frontend design system — settled, in `fnt/DESIGN.md`

Palette: Gazette Ink `#101A24` · Field Paper `#DCDFDB` · Attest Green `#14603C` · Query Ochre
`#845605` · Seal Vermilion `#A32A1E` · Slate Void `#4A5560`. Hairlines `#A8AFAC`, focus tint
`#C9CEC9`. IBM Plex Sans for language, IBM Plex Mono for anything measured, cited or
timestamped. 17px base. Scale 44/600 · 27/600 · 21/500 · 17/400 · 15/400 · 13/500.

**Query Ochre was `#8A5A05` and failed at 4.43:1. It is `#845605` at 4.77:1.**

Five field states, four independent channels, colour last: PASS filled + tick · FAIL unfilled
+ cross + 5px vermilion left edge · REVIEW REQUIRED dashed + `?` + ochre · NOT APPLICABLE
lightest weight + em dash + slate · INSUFFICIENT EVIDENCE 45° hatch + hollow ring + dotted
slate border. **FAIL and INSUFFICIENT EVIDENCE share no channel.** INSUFFICIENT EVIDENCE rows
always carry Request recapture; FAIL rows never do.

Three verdicts by rule weight at banner scale: PASS solid, REVIEW dashed, POTENTIAL VIOLATION
double and heaviest. A verdict must never render identically to a field state.

Fixtures cite `rules.yaml` on `main`, not ticket text. Fonts are vendored OFL `.woff2`; no
Google Fonts link. `AppShell` is shared with Rohan's admin surface.

---

## Where the board stands, 2026-09-06 (end of session 5)

**Merged in session 5:** #42 MEA-004 · #45 VIS-003 · #51 RUL-004 · #52 EXT-005 · #53 DAT-002
· #54 CTR-004. `main` carries nothing of Abhiram's unfinished.

**Open PRs — all three are teammate rework:** #43 MEA-005 · #46 EVD-005 (head moved to
`e510224` after review; re-pull) · #47 MEA-006.

**Branches pushed with no PR:** `ext-006-bilingual-declarations` (Sitanshu),
`feat/tam-001-dual-mrp-sticker-detection` (Akshaya). Ask both where they stand.

**Never started:** `fnt-admin`. The offline path (F51, P0) does not exist. Dashboard
aggregates (F32) do not exist. The frontend still runs on fixtures with no generated client.

**Biggest unmanaged risk is still the corpus** — but its character changed. It is no longer
"four thin samples"; it is **zero samples and fifteen unannotated images**, with the schema
and guards now in place to make the next attempt honest. DAT-005 is the unblock.

---

## Golden examples from this project

**A test that passes and proves nothing.** PIP-001's deepcopy mutation test could not be made
to fail. Claude Code found that, corrected the docstring rather than the code, and renamed the
tests to state what they actually prove. *Reward this.*

**CI passing on a PR that breaks the architecture.** PR #5 was green; a `bck.*` import path
defeated the module contracts silently.

**A rule figure appearing in two documents with different values.** Neither was law.

**Two options presented, both wrong.** The right answer was a third path written into Rule
7(4) itself. Read the primary source before choosing between someone's options.

**Deleting your own work because the source doesn't support it.** Sitanshu was asked to cite
the corpus for EXT-005's commodity word lists. He went to the PDFs and **removed** the terms
he could not source — `TEA`, `COFFEE`, `BISCUITS`, `MILK`, `PAN MASALA` — keeping only what
cites a file and page. *That is the standard, and it is rare.*

**Writing the proof that your own code is wrong.** Yashashvi's MEA-004 docstring stated that
the coin path cannot recover a true homography — while the code built one anyway. The
docstring was right. When someone documents a limitation honestly, read it as a finding.

**A file list catching what a diff would have buried.** #42 came back as 4 files when 3 were
expected; the fourth was a junk file from a shell quoting accident. Check the list first.
