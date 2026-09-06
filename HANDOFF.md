# HANDOFF.md

For a fresh Claude chat resuming as strategist / architect / engineering lead on PCCS
(SIH 2026, PS 26034). This is the fourth handoff in the project's history.

Read after `AGENTS.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `TODO.md`, `TICKETS.md` and
`RULES-CORPUS-INDEX.md`. This file carries only what is written down nowhere else.

Every line here exists because a session would behave differently without it. If it were
merely true, it was cut.

---

## How Abhiram works with you

Decide, don't offer menus. One recommendation with the tradeoff in one line. Exact
pasteable terminal commands, never a command described in prose, and **never a placeholder
like `<number>` inside a command** — substitute the real value every time. Chain
multi-step commands with `&&` when a later step depends on an earlier one; newline-
separated commands silently continue past a failure and that has already cost this project
a broken `uv.lock` and a git command run against the wrong branch.

For anything outside the terminal — a settings panel, a form — every click and every
field, assuming he has not seen the screen.

Say when something won't work instead of finding a way to agree. Mark unverifiable claims
soft. Never claim a probability of winning.

**One thing at a time when he asks for it.** He will say so explicitly. When he does, give
one question or one task per message and wait. Do not batch.

**Standing orders, verbatim in force:** don't ask how much time is left, don't wind down.
When a ticket closes the next one already exists; when the board runs low, extend it from
the PRD and feature spec yourself. Depth before breadth. He will say explicitly, 24 hours
before stopping — only then switch to wrapping up.

He runs Claude Code in WSL Ubuntu at `~/NewProjects/26034`. Windows paths are under
`/mnt/c/Users/drona/`.

---

## What you can and cannot do

**ClickUp connector works.** Create and update tickets directly; do not hand him ticket
text to paste unless it rate-limits again, in which case say so explicitly and switch to
pasteable blocks (title, assignee, status, priority, three custom fields, description).

The connector cannot: create or edit custom field *definitions*, create or edit statuses,
remove members, delete folders. **Posting comments prompts for approval each time and often
fails — put information in the task description, not a comment.**

**There is no GitHub MCP connector.** You read `api.github.com` directly from the sandbox:
public data only, unauthenticated, ~60 requests/hour from a rotating shared IP pool. **You
will hit that ceiling immediately** — it fired on the first call of the last session and
never recovered. Assume it is unavailable and use the PR review protocol below. Private
data returns 401. You cannot merge, comment, approve or push.

---

## The PR review protocol — use this, it works

1. He gives you a PR number. You give him this exact command shape:

```
cd ~/NewProjects/26034 && gh pr checks 29; gh pr view 29 --json headRefOid,updatedAt -q '.headRefOid + "  " + .updatedAt'; gh pr diff 29 > /mnt/c/Users/drona/Downloads/pr29.md; wc -l /mnt/c/Users/drona/Downloads/pr29.md
```

2. **Filename convention: `pr<number>.md`, then `pr<number>-v2.md`, `-v3.md` for reworks.**
   Never overwrite — retrieval will hand you a stale copy if two files share a name.
   **`.diff` files cannot be uploaded to project knowledge; `.md` can.** Always `.md`.
3. He uploads to project knowledge; you read it with `project_knowledge_search`.
4. **Always ask for the head OID.** Four times last session a teammate said they had pushed
   fixes and the diff was byte-identical — same blob hashes, only a rebase. Compare the OID
   *and* the blob hashes in the diff header before reviewing. If unchanged, say so in one
   line and don't re-review.
5. **Delete a PR's files from project knowledge once it merges.** Stale diffs compete with
   live ones during retrieval.
6. Under ~300 lines, pasting into chat is fine.

**Merge gate — recommend merge only if all hold:** checks green · one module · in ticket
scope · no migration · no auth or permission change · no shared-contract change · no new
dependency. Otherwise escalate with a recommendation. When a PR fails, comment the specific
fixes — never fix it yourself; the owner learns nothing and their branch diverges.

`session-log/<name>.md` in a diff is **not** an out-of-scope violation. AGENTS.md requires
it. Every ticket's Files field must include it — its absence produced false flags on every
review last session.

---

## The three failure patterns that recur — check for these first

**1. Tests that cannot fail.** This appeared in five separate PRs. A socket-isolation test
where the library under test is mocked, so nothing runs. A mutation test whose source object
is frozen all the way down. An adversarial test that stubs the verifier, calls the stub, and
asserts the stub returned what it was told to return. A directory scan resolving a relative
path that yields zero files and passes vacuously.

The instruction that works, in every ticket's pre-PR block: *"prove the test can fail —
introduce the defect it guards against, confirm red, revert."* Twice, Claude Code ran that
check on itself, found the guard was not load-bearing, and corrected the **claim** rather
than shipping a decorative test. That is the behaviour to reward.

**2. Fabricated ground truth.** Plausible-looking values written instead of read. Invented
MRP text, millimetre heights on uncalibrated photographs, samples hashing to the SHA-256 of
an empty file — `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Memorise
that string; it is the tell.

**3. Stale branch bases.** `gh pr checks` reporting "no checks reported" almost always means
the branch is stale relative to `main`, not a CI outage. Check whether already-merged files
show as "new" in the diff before assuming anything else.

Also: **`gh pr checks --watch` is unreliable.** It reported "2 passed, 7 pending" against a
rollup containing exactly one check, twice. Read `statusCheckRollup` instead.

---

## Infrastructure state, 2026-09-06

`main` at `bc41ea5` plus the docs PR #37 and CI-003. **529 tests passing**, 3 import
contracts kept, 0 broken.

Org `SIH-2026-CSM-A`, shared with a second team. Repo `26034` public, `26167` is
Yashwanth's. **Both public deliberately: branch protection does not exist on private repos
under GitHub Free for organisations, and flipping a repo to private silently deactivates
protection with no warning. Never propose making it private.**

**Two stacked protections on `main`.** The `main-protection` ruleset (PR required, 1
approval, dismiss stale, code-owner review, no force push, linear history, `backend` and
`frontend` as required status checks, repository-admin bypass) decides *whether* a PR is
mergeable. A classic rule restricting push to `Abhiram-0910` decides *who clicks merge* —
without it, two teammates approving each other is a complete path around him.

**The ruleset lives at the repo level, not the org level:**
`github.com/SIH-2026-CSM-A/26034/settings/rules`. Org rulesets require GitHub Team and do
not exist here. Do not send him to the org settings page.

**`--admin` is the standard merge command for every PR, for every contributor.** CODEOWNERS
assigns exactly one owner per path and that owner is always the PR's author, so codeowner
review can never be satisfied. `--admin` also skips required checks, so always run
`gh pr checks` in the same breath. Abhiram cannot approve his own PRs — GitHub blocks it
outright; go straight to `gh pr merge N --squash --admin --delete-branch`.

**Worktrees.** `~/NewProjects/26034` on `main` (use this for all `gh` commands), plus
`26034-ci`, `26034-fnt`, `26034-rules` parked on detached HEAD as agent workspaces.
`git checkout main` fails in any worktree while another holds it — this caused three
confusing failures in one session. **Never run manual git commands in a folder a Claude Code
session has open**; use a separate worktree.

Claude GitHub App installed on the org, scoped to `26034`, `@claude` on mention only.
Auto-review on every PR was deliberately declined.

ClickUp: space `SIH Team` (`1300450000003833`), list `26034 Build` (`1300450000005736`).
Field IDs — `Module 26034` `87d708c9-d795-41d5-bae7-be56090b3ff1`, `Files`
`21d1ae6f-d983-44db-b2ac-d390d30b6469`, `Branch` `589b8355-8072-4ec7-b615-d78c6778bd87`.
Statuses `to do` / `doubt` / `in progress` / `review` / `done` / `complete`.
**`done` is the terminal status. Nothing goes to `complete`** — Abhiram decided this.

---

## Owners and usernames

| Person | GitHub | ClickUp ID | Module |
|---|---|---|---|
| Abhiram | `Abhiram-0910` | 240010775 | contracts, core, pipeline, alembic, .github, **rules**, **fnt officer** |
| Jashwanth | `badugujashwanth-create` | 106878760 | rules — **unavailable** |
| Akshaya | `aksha08-ya` | 106878763 | vision, **tamper** |
| Sitanshu | `krishbattula4` | 106878761 | extraction |
| Yashashvi | `Yashashvi-05` | 106878758 | measurement — **unavailable** |
| Shiva Kumar | `Shiva-Kumar-Akula` | 106878759 | evidence |
| Vineeth | `vineethsimha2151` | 106878762 | fnt officer — **unavailable** |
| Shivasai | `adepushivasai901-ops` | 106878753 | tamper — never engaged, reassigned |
| Rohan | `A-Rohan99` | 216234631 | fnt admin — never started |
| Aashritha | `aashrithareddybodanampally-byte` | 106878813 | datasets |
| Likhitha | `Likhitha-rachelly` | 106878764 | reserve |

Jashwanth runs Codex; everyone else Antigravity + Gemini Pro; Abhiram Claude Code.

**B.V. Yashwanth (`ybaddam8-png`, ClickUp 240010980) is not on the team** — he leads 26167
and is an org Owner, therefore admin on `26034` too. That is deliberate, not a
misconfiguration. Never assign him work. FNT-001 was a one-time explicit exception for
Vineeth's absence and does not extend to anyone else. He is a different person from
Yashashvi; the near-identical names are a real hazard when assigning by ID.

### Ownership shifts — recorded, not violations

- **`rules/`** — Jashwanth unavailable. RUL-002 reassigned to Abhiram mid-session, RUL-003
  built by him. He owns it for now.
- **`fnt/` officer surface** — Vineeth unavailable. Abhiram builds it directly rather than
  handing another person's module to a third party.
- **`tamper/`** — Shivasai never received a ticket and never worked. Directory transferred
  to Akshaya (TAM-001); she now owns `vision/` and `tamper/`.
- **`measurement/`** — Yashashvi unavailable. **No new measurement work is assigned and none
  should be forced onto someone else.** Reference-object calibration (₹10 coin at 27.0mm via
  Circle Hough, EAN-13 at **37.29mm not 31.35mm**, 50mm printable card) is the remaining
  depth there and it waits. If it is still waiting near demo, scenario 4 (calibrated font
  measurement) drops from the demo set and scenarios 5 (the refusal) and 8 (artwork mode)
  carry that story instead. Say that out loud rather than quietly cutting it.
- **Known unfixed bug in `measurement/`:** `measure_margins` raises on a zero margin, because
  `MeasurementExact.value` and `MeasurementCalibrated.value` are `gt=0`. A declaration flush
  against ink or the crop edge crashes instead of measuring. Logged, not lost, owner away.

CODEOWNERS still reflects the original map. If these shifts persist past another ticket or
two, change CODEOWNERS rather than letting the file lie.

---

## Legal findings — expensive to rediscover

**Rule 7 is a single Table-I banded by PDP area** since 01.01.2018 (G.S.R. 629(E)). Normal
print: ≤50 cm² → 1.0mm · 50–100 → 1.5 · 100–500 → 2.5 · 500–2500 → 4.0 · >2500 → 6.0.
**There is no 2.0mm or 3.0mm band.** Table-II no longer exists. Rule 7(3): width not less
than one third of height, except the numeral "1" and the letters i, I, l. A flat 1mm/2mm and
a 1.7mm figure both appear in older project documents — **`SIH26034_PSR.md` §3 is the
offender and is not a source for rule facts.**

**Rule 6(11) is a FORMAT rule, not a tolerance.** It prescribes the unit basis — `Rs. per g`
below 1 kg, `Rs. per kg` at or above; `per cm`/`per metre`; `per ml`/`per litre`;
`per number` by count. It contains no tolerance, no rounding increment, no permitted
difference. **The ±₹0.01 and ±₹0.05 figures in project documents are assumptions, not law,
and must never be encoded.** F18 is two checks: is a unit sale price declared, and is it on
the correct unit basis for the net quantity.

**Rounding increment ≠ tolerance.** "Rounded to nearest ₹0.05" transforms in steps; "±₹0.05"
accepts a difference. They diverge at boundaries. The schema expresses both separately, and
a tolerance without a `tolerance_basis` fails to construct — `Decimal("0.05")` alone is
either five paise or five percent.

**Rule 8 governs placement, Rule 9 governs manner.** Distinct rules, never one check. Now
encoded as four: `R8-1-PDP-PLACEMENT`, `R8-1-FREE-SPACE`, `R9-1-MANNER`,
`R9-3-OUTER-CONTAINER`. Rule 8(1)'s proviso requires clear space above and below of at least
the **numeral's** height and left and right of at least twice it — **derive it from
`numeral_height_mm`, not `letter_height_mm`**; they are distinct measurements on a real
package and only coincide by accident in fixtures.

**Rule 7(4) PDP area:** rectangular = height × width; cylindrical = **40%** of (height ×
circumference); other = 40% of total surface area, **OR an area considered to be the
principal display panel**. That second limb is the answer for irregular shapes — measure the
identified panel through the homography rather than refusing. Refuse only when no panel can
be identified or it is not adequately planar. Excludes tops, bottoms, can flanges, and the
shoulder and neck of bottles and jars.

**Medical devices are a carve-out, not a stricter path.** G.S.R. 778(E) (23.10.2025, in force
from publication 24.10.2025) routes numeral and letter height to MDR 2017 via a rule 2(h)
proviso, disapplies the Rule 33 relaxation, and makes PDP declaration non-mandatory.
**Table-I is not universal.** `SIH26034_TI.md` §5 uses "Medical Device" as its routing
example without knowing this.

**Rule 6(1)(aa) vs Rule 6(10A).** 6(1)(aa) is the package declaration of country of origin.
6(10A), inserted by G.S.R. 128(E) (13.02.2026), is a *separate* obligation on e-commerce
platforms to provide a searchable country-of-origin filter, evaluated against a
`CatalogueRecord`, not a package scan. G.S.R. 128(E) does not touch Rule 6(1) at all.
G.S.R. 312(E) substitutes that sub-rule effective **01.07.2027** — encode with
`effective_from: 2027-07-01` rather than omitting it.

**Combination (2(ka)) and Group (2(kb)) packages** — G.S.R. 722(E), in force 01.01.2024.
**Multi-piece package (2(kc))** and its food proviso — same instrument, encoded in RUL-003
as `R2-KC-MULTI-PIECE-FOOD` with `package_type` scoping. G.S.R. 722(E) paragraph 4's Rule
6(11) unit-sale-price exemption is deliberately **not** encoded; a test asserts the rule
store excludes it.

**"multi-piece package" occurs three times in the entire corpus, all inside G.S.R. 722(E),
and that instrument does not amend rule 9.** So no multi-piece/Rule 9(3) interaction is
encoded, and `test_the_gazette_states_no_multi_piece_outer_wrapper_rule` asserts the absence.
Do not invent one.

**Sector overrides:** Rule 6(1)(a) Explanation III routes the manufacturer declaration for
food to FSSA 2006. Rule 6(1)(d) third proviso routes the date declaration for cosmetics to
the Drugs and Cosmetics Rules 1945. Neither states a separate commencement in the
compilation; both inherit their parent clause's committed date, documented in a YAML comment.

**Two evidence gaps, recorded not papered over.** The DoCA consolidated e-book returns
Access denied — no consolidated text covering Nov 2021 to Oct 2023. The 11.11.2025 DoCA FAQ
is not captured; two claims in EXT-001 (both `₹` and `Rs.` acceptable; "Marketed by" /
"Brand Owner" satisfies Rule 6(1)(a)) rest on three secondary sources and are marked
**[SOURCED], not [VERIFIED]**.

**LMPC applies to packages intended for retail sale in India.** An EU export pack carries no
INR MRP obligation — the correct field state is `NOT_APPLICABLE`, not FAIL and not a
`known_issue`. *(The scope limb itself is soft — verify against the corpus before encoding it
as a rule rather than an annotation convention.)*

**G.S.R. 778(E) says "rule 33 shall be numbered as sub-rule (1)" while the Maharashtra
compilation already shows a 33(1) and 33(2).** That is a semi-official compilation artefact.
Encode what the gazette says and cite the gazette.

`consumeraffairs.gov.in`, `doca.gov.in` and `egazette.gov.in` all refuse automated access.
**Do not build a fetcher.** The corpus is updated by hand.

---

## Hard nos — do not re-propose

- **Supabase** — free projects auto-pause after 7 days; sovereignty.
- **Cloud-primary OCR** — makes the offline path a second, weaker extraction implementation
  and puts product images outside the sovereign boundary. Self-hosted PaddleOCR primary;
  cloud is opt-in per request, disabled by default, daily page cap 0.
- **A custom rules DSL / Drools / OPA** — versioned YAML plus a deterministic evaluator.
  This is the project's most likely over-engineering failure.
- **A separate vector database** — pgvector in the same Postgres.
- **Next.js** — SSR buys nothing for an authenticated internal tool.
- **Two repositories** — monorepo with CODEOWNERS and import-linter.
- **Python 3.12** — 3.11, because PaddlePaddle and CV wheels lag.
- **Horizontal layer directories** — layers nest *inside* modules.
- **Empty `router.py`/`service.py` stubs per module** — 24 stubs, breaks the no-stubs rule.
- **Auto-review on every PR** — burns quota, trains people to scroll past Claude.
- **A develop chain** — `main` plus feature branches. T4's `develop` references superseded.
- **Making the repo private** — kills branch protection silently.
- **Lightening the frontend focus tint to fix contrast** — a focus signal at 1.04:1 against
  the ground is not a signal. Unfilled chips ground on Field Paper instead.
- **An `if:` guard to skip the frontend CI job** — a skipped job posts no status and a
  required context then waits forever. Same bug as the `paths:` filter, different costume.
- **Fixing PIP-001's "unfalsifiable" deepcopy test** — it is documented as unfalsifiable
  under the current annotation, on purpose.

---

## Constraints discovered the hard way

- **`--ours`/`--theirs` mean opposite things in `git rebase` versus `git merge`.** Rebase:
  `--ours` = the branch being rebased *onto* (main), `--theirs` = the commit being replayed.
  Merge: the reverse. State which operation is in play every time before giving either flag.
- **Never hand-resolve conflict markers in `uv.lock`.** Delete it and run `uv lock` fresh
  once `pyproject.toml` is confirmed correct.
- **A required status check plus a `paths:` filter on its workflow is a deadlock.** A
  workflow skipped by path posts no status, so the required context never arrives. This
  blocked #32, #33, #36 and #37 and was misread as the review requirement. Fixed in CI-003
  by removing the filter so the workflow always runs and always reports.
- **Required status checks cannot be added before the check has run once.**
- **import-linter needs `include_external_packages = true`** for a forbidden contract on a
  module outside `root_package`.
- **A forbidden contract that matches nothing looks identical to one that works.** Prove a
  new contract by adding a deliberate violation and confirming exit 1 — in both directions.
- **Check exit codes directly, not through a pipe.** `lint-imports | tail` reports `tail`'s
  status, which is always 0.
- **Deleting the ClickUp list destroyed all ten tickets and Trash was unavailable.** Be
  precise about "folder" versus "list".
- **Custom fields are workspace-level and shared with the other team.** Prefix new fields
  with the problem statement number.
- **A ClickUp assignee filter silently hides everyone else's tickets.** The sidebar count is
  the truth.
- **`git branch` does not switch to the branch.** Run `git status -sb` before every commit.
- **`mv /mnt/c/.../*.pdf`** moved an entire Downloads folder into the repo. Name files
  explicitly.
- **A duplicate SVG pattern `id` across two breakpoint variants** resolves `url(#…)` to the
  `display:none` element and paints nothing. Renders perfectly at the width you test and
  silently fails at the other. Scope with `useId`. No build step or unit test catches this —
  only driving a real browser at two widths does.
- **Before any `git reset --hard` or `checkout --ours/--theirs`, run `git status` first.**

---

## Decisions this session — do not re-litigate

**PIP-001.** `derive_verdict(findings)` and `assemble_verdict(...)` are two functions, not
one, because `VerdictRecord.findings` is `min_length=1` and "zero findings returns REVIEW"
cannot produce a record. The contract won; the spec bent. Derivation uses four separate
`any()` passes with `is` comparisons and no set membership anywhere — `REVIEW_REQUIRED` and
`INSUFFICIENT_EVIDENCE` reach the same verdict but never through the same expression, because
collapsing them into one `in {...}` is one edit away from a set that also contains `FAIL`.
The timestamp is a parameter, never a clock read.

**The rule-snapshot adapter lives in `pipeline/`**, not `rules/` or `contracts/`.
`rules.RuleDefinition` / `RuleCondition` are the **permanent internal shape** of that module,
legitimately richer than what contracts exposes, because no other module needs to introspect
a rule's condition *shape* — only that a snapshot exists.
`conditions.model_dump(mode="json")` is mandatory, not stylistic: Table-I bands are `Decimal`
and `Decimal` is not a `JsonValue`. A `NumericConstraint` carrying a bare tolerance with no
basis raises rather than being carried through.

**CTR-003.** The deepcopy in `RuleParameterSnapshot.from_rule` is **not** what provides
isolation today — pydantic's `JsonValue` re-validation rebuilds every container. It ships as
*annotation-independence* against a future widening to `dict[str, Any]`. The test pins the
property and **cannot fail under the current annotation**; that is stated in its own
docstring, with a falsification matrix in the PR body.

**RUL-002.** `Rule7Route` generalised from `MEDICAL_DEVICES_RULES_2017` to
`LMPC_TABLE_I` / `SECTOR_FRAMEWORK` — a route enum carrying one sector's answer is an
if/else chain in disguise. The medical-device guard moved into `minimum_character_height()`
rather than the two evaluator callsites, because the sector-blind public lookup was the
actual bug. Sector dispatch is a table built by reading the store; adding a sector is a YAML
rule plus an enum member, touching no existing logic. Schema split three ways to stay under
300 lines: `base.py` (vocabulary) → `conditions.py` (obligation shapes) → `models.py` (the
record), plus `results.py`. One direction, no cycle.

**RUL-003.** `rule_33_relaxation_applies` and the dispatch collapsed onto one `_applicable()`
— two copies of an applicability check is how a scoped override fires in one reader and not
the other. `package_type` defaults to `None` meaning any package type, so RUL-002's three
overrides fire unchanged; three tests hold that down.

**Every new rule gets its own condition kind rather than `declaration_required`**, because
`bck/tests/pipeline/test_rule_snapshot.py` asserts exact equality between `DECLARATION_FIELDS`
and the strings encoded in `rules.yaml`. Do not edit that assertion to make room for a rule.

**CORE-001 shape.** Officer credentials are config-seeded (`OFFICERS` env var, JSON list of
username/bcrypt-hash/tier/jurisdiction) — no `User` model, no migration, no DB store yet.
`core/db.py` was deliberately **not** built: no real caller exists to tell a session-scope
decision right, and building it speculatively is exactly what the Hard Nos exist to catch.
`RoleTier` is an ordered `StrEnum` (`STATE`/`REGIONAL`/`DISTRICT`); designations configurable
via `ROLE_DESIGNATIONS`, default Controller of Legal Metrology / Deputy Controller / Legal
Metrology Inspector. **The pilot state is still not chosen and this will very likely change.**

**Measurement contracts.** `MeasurementResult`'s variants keep Yashashvi's original names
(`MeasurementExact` / `MeasurementCalibrated` / `MeasurementRefusal`).
`MeasurementCalibrated.confidence_interval` is `ge=0`, not `gt=0` — a zero-variance
contrast-ratio measurement is a genuine result. Do not re-litigate either.

**Cloud providers.** Featherless is the sole copilot generation provider. An OpenAI
query-rewriting/retrieval-expansion step ahead of hybrid retrieval was proposed but **not
confirmed** — don't build against it. AWS is unallocated reserve: no product data, no
evidence records, ever.

**No AI-attribution trailer on commit messages *or* PR bodies.** The rule names commits, but
the reason behind it is that the repo is public and scraped, and a PR body is as public as a
commit message.

---

## The frontend design system — settled, in `fnt/DESIGN.md`

Palette: Gazette Ink `#101A24` · Field Paper `#DCDFDB` · Attest Green `#14603C` · Query Ochre
`#845605` · Seal Vermilion `#A32A1E` · Slate Void `#4A5560`. Hairlines `#A8AFAC`, focus tint
`#C9CEC9`. IBM Plex Sans for language, IBM Plex Mono for anything measured, cited or
timestamped — the mono is tabular, and measured-over-required must align digit over digit.
17px base, read at arm's length in glare. Scale 44/600 · 27/600 · 21/500 · 17/400 · 15/400 ·
13/500. Sentence case; verdicts in capitals because they are quoted verbatim in the report.

**Query Ochre was `#8A5A05` and failed at 4.43:1 on Field Paper. It is `#845605` at 4.77:1.**
Two further contrast findings are recorded in DESIGN.md: ochre at 3.97:1 on the focus tint
(fixed by grounding unfilled chips on Field Paper) and the hatch at 3.4:1 where a stroke
crosses a letter (fixed with an inset plate).

Five field states, four independent channels, colour last: PASS filled + tick · FAIL unfilled
+ cross + 5px vermilion left edge · REVIEW REQUIRED dashed + `?` + ochre · NOT APPLICABLE
lightest weight + em dash + slate · INSUFFICIENT EVIDENCE 45° hatch + hollow ring + dotted
slate border. **FAIL and INSUFFICIENT EVIDENCE share no channel.** INSUFFICIENT EVIDENCE rows
always carry Request recapture; FAIL rows never do — **the remedy tells the officer which one
they are looking at before the label does.**

Three verdicts distinguished by rule weight at banner scale: PASS solid, REVIEW dashed,
POTENTIAL VIOLATION double and the heaviest object on screen. A verdict must never render
identically to a field state.

Layout: masthead as permanent furniture (inspection id, rule-set version, capture timestamp,
offline marker), findings ledger in ruled rows with no cards, the package photo as a pinned
second register that follows row focus, officer actions at thumb reach behind a heavy rule.
Row focus is a 4px ink left bar plus a tint shift, never a shadow lift. The machine's column
and the officer's column never share a background.

Fixtures live in `fnt/src/fixtures/` and cite `rules.yaml` on `main`, not ticket text — the
encoded rule set is authoritative. Fonts are vendored OFL `.woff2` in `fnt/public/fonts/`;
no Google Fonts link, because it would fail at exactly the moment F51 exists to survive.
`AppShell` is shared with Rohan's admin surface and is not restyled by officer work.

---

## Where the board stands, 2026-09-06

**Merged this session (8 PRs):** #28 PIP-001 · #30 CI-002 · #33 CTR-003 · #32 RUL-002 ·
#35 FNT-002 · #36 RUL-003 · #31 EVD-003 · #37 docs. CI-003 (frontend always reports) in
flight at handoff time.

**Open, in rework:**

- **#29 VIS-003 (Akshaya)** — four pushes, all byte-identical to the first (`ef2dd9d..5587ce4`).
  Five items open: a socket test that can't fail because PaddleOCR is mocked; no synthetic-crop
  test for 8/B, 0/O, 5/S, 1/l; `ArbitrationResult` carries no `EvidenceProvider`;
  `arbitrate_mrp` has no caller so the constrained pass is disconnected; the whitelist
  `"0123456789.Rskgmlg/-"` excludes `₹` and has no `M` or `P`. **Do not re-review until the
  blob hashes change.** Separately: the PaddleOCR constructor uses 3.x kwargs
  (`text_detection_model_dir`, `use_textline_orientation`, `device="cpu"`) while the call site
  is `ocr.ocr(image, cls=False)`, the 2.x signature — a runtime crash no mocked test can catch.
- **#34 DAT-001 (Aashritha)** — four rounds, genuine progress each time. **Fixed:** all
  `letter_height_mm` and `numeral_height_mm` nulled on uncalibrated packs; stale `pdp` block
  removed from the Himalaya files; `pdp_geometry` correct at 56.0 cm² in the 50–100 band at
  1.5mm; manifest cut from 89 lines to 53 with **every empty-file hash gone**; placeholder
  `drive_folder_id` removed; `schema.py` cites Rule 6(1)(aa) alone. The Tata Salt annotation
  correctly derives `Rs. per kg` from a ≥1 kg net quantity under Rule 6(11) and says so in its
  notes — she is now reasoning from the rule rather than pattern-matching, which is the change
  that matters.

  **Four remaining:** (1) `cosmetics_himalaya_face_wash_100ml_001` appears twice in the
  manifest, once `.jpg` and once `.png`, same `sample_id` and `annotation_path`, different
  `sha256` — the harness would double-load it and the hashes disagree about which file it is;
  (2) `food_parle_g_biscuits_001` has `reference_object.present: false` with all heights
  nulled, but its notes still claim a "calibrated coin reference target" — a note asserting a
  calibration the annotation denies; (3) the Himalaya MRP question is **still unanswered after
  four rounds** — both files tagged `export_pack` and `non_domestic` while declaring
  `MRP Rs. 180.00`; (4) manifest `image_path` uses
  `datasets/raw/cosmetics/cosmetics_himalaya_face_wash_100ml_001/…` while the annotations'
  `image_filename` says `datasets/raw/cosmetics/himalaya_face_wash_100ml/001.jpg` — two path
  schemes, so nothing downstream can resolve an image from an annotation.

**To do, not started:** EXT-004 (Sitanshu, span classification and spatial role binding —
this is what unblocks PIP-002), TAM-001 (Akshaya, behind VIS-003).

**Not ticketed yet:** EVD-004 (report export in PDF and editable format, unblocked now that
`VerdictRecord` exists; must also fix EVD-003's `test_append_only_enforcement`, which resolves
`Path("app/modules/evidence")` against the cwd and passes vacuously if it scans nothing —
resolve relative to the test file and assert at least one file was scanned), PIP-002
(ingestion endpoints + orchestration, blocked on EXT-004), a frontend `npm audit` gate
(2 moderate vulns, deprecated `glob@11.1.0`).

**`rules/` imports nothing from `contracts`** and `models.py:21` still carries a stand-in
comment — that is why `rule_snapshot.py` exists as a translation layer. Live work, in TODO.

**Biggest unmanaged risk remains DAT-001.** After three review rounds the corpus is a handful
of genuinely-annotated Indian retail samples, mostly packaged food; cosmetics has effectively
nothing behind it. Every accuracy target in the PRD is unbacked and vision, measurement and
tamper cannot be evaluated at all. **Written review has failed three times here.** The next
move is a fifteen-minute call opening one annotation beside the actual photograph, not a
fourth written round. Demo scope stays: packaged food primary, cosmetics secondary, FSSAI
explicitly out of scope.

---

## Golden examples from this project

**A test that passes and proves nothing.** The deepcopy mutation test specified for PIP-001
could not be made to fail — the source `RuleDefinition` is frozen all the way down. Claude
Code found that, corrected the docstring rather than the code, and renamed the tests to state
what they actually prove. *Reward this. It is worth more than the test that was asked for.*

**CI passing on a PR that breaks the architecture.** PR #5 was green. A `bck.*` import path
defeated the module contracts silently. Green checks mean the checks ran, not that the design
holds. Read the diff.

**A rule figure appearing in two documents with different values.** Neither was law. Both were
assumptions argued about long enough to look like facts. Go to the gazette.

**Two options presented, both wrong.** Yashashvi asked whether to approximate PDP area from a
bounding box or refuse outright, and recommended refusing. The right answer was a third path
written into Rule 7(4) itself. Read the primary source before choosing between someone's
options — and tell them their instinct was right even when the answer isn't theirs.

**A confident claim not verified.** The last session told Abhiram to add `frontend` as a
required check and separately endorsed its `paths:` filter. Each is right alone; together they
deadlock every backend-only PR. The resulting `BLOCKED` was then attributed to the review
requirement without checking. Claude Code found it. *Check before attributing a cause, and say
so plainly when you were wrong.*

**Deleting a test rather than repairing it.** Shiva Kumar's adversarial-verifier file was
asked to be rewritten; he deleted it instead and moved the falsification into the PR
description where it belonged. That took more judgement than patching would have.
