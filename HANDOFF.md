# HANDOFF.md

For a fresh Claude chat resuming as strategist / architect / engineering lead on PCCS
(SIH 2026, PS 26034). Read this **after** `AGENTS.md`, `ARCHITECTURE.md`, `CLAUDE.md`,
`TODO.md` and `rules-corpus/README.md`, which are all on `main` — this file carries only
what is written down nowhere else.

---

## How Abhiram works with you

Decide, don't offer menus. One recommendation with the tradeoff in one line. Exact
pasteable terminal commands, never a command described in prose. For anything outside the
terminal — a settings panel, a form — every click and every field, assuming he has not
seen the screen.

Say when something won't work instead of finding a way to agree. Mark unverifiable claims
soft. Never claim a probability of winning.

**Standing orders, verbatim in force:** don't ask how much time is left, don't wind down.
When a ticket closes the next one already exists; when the board runs low, extend it from
the PRD and feature spec yourself. Depth before breadth. He will say explicitly, 24 hours
before stopping — only then switch to wrapping up.

He is running Claude Code in WSL Ubuntu at `~/NewProjects/26034`. Windows paths are under
`/mnt/c/Users/drona/`.

---

## What you can and cannot do

**ClickUp connector: rate-limited out for ~10 hours from 2026-09-05 afternoon.** Until it
clears, every board change goes to him as instructions to action manually. Give ticket
title, assignee, status, priority, the three field values, and the description as one
pasteable markdown block.

Even when working, the connector cannot: create or edit custom field *definitions*, create
or edit statuses, remove members, delete folders. Posting comments prompts him for approval
each time and often fails — **put information in the task description, not a comment.**

**There is no GitHub MCP connector.** You read `api.github.com` directly from the sandbox:
public data only, unauthenticated, ~60 requests/hour from a rotating shared IP pool. You
will hit that ceiling — it happened four times in one session. Private data returns 401.
You cannot merge, comment, approve or push.

**The PR review loop:** he gives you a PR number, you fetch the diff, you check it against
the ticket's acceptance criteria and the standing constraints, you return a verdict plus
the exact comment text. He pastes and merges. When the API is rate-limited, ask him to
upload the diff to project knowledge rather than paste it into chat — it keeps the context
window clean and you can search it.

**Merge gate — recommend merge only if all hold:** checks green · one module · in ticket
scope · no migration · no auth or permission change · no shared-contract change · no new
dependency. Otherwise escalate with a recommendation. When a PR fails, comment the specific
fixes — never fix it yourself, the owner learns nothing and their branch diverges.

---

## Infrastructure state, 2026-09-05

Org `SIH-2026-CSM-A`, shared with a second team. Repo `26034` public, `26167` is
Yashwanth's. Both public deliberately: **branch protection does not exist on private repos
under GitHub Free for organisations, and flipping a repo to private silently deactivates
protection with no warning.** Never propose making it private.

**Two stacked protections on `main`, both required.** The `main-protection` ruleset (PR
required, 1 approval, dismiss stale, code-owner review, no force push, linear history,
`backend` as required status check, repository-admin bypass) decides *whether* a PR is
mergeable. A classic rule restricting push to `Abhiram-0910` decides *who clicks merge* —
without it, two teammates approving each other is a complete path around him.

He cannot approve his own PRs, so his own tickets merge with
`gh pr merge N --squash --admin --delete-branch`. **`--admin` skips required checks too**
— it merged INF-001 with no CI run at all. Always have him verify locally after an
`--admin` merge.

All twelve org members are in the `Developers` team with push on both repos, zero pending
invitations. `ybaddam8-png` is an org Owner and therefore admin on `26034` as well —
deliberate, not a misconfiguration.

Claude GitHub App is installed **on the org**, scoped to `26034`, using
`CLAUDE_CODE_OAUTH_TOKEN` (subscription, no API billing). `@claude` in a PR or issue
*comment* triggers it; the PR description does not. Auto-review-on-every-PR was
deliberately declined.

ClickUp: space `SIH Team` (`1300450000003833`), list `26034 Build` (`1300450000005736`).
Fields `Module 26034`, `Files`, `Branch`. Statuses `to do` / `doubt` / `in progress` /
`review` / `done` / `complete`.

---

## Owners and usernames

| Person | GitHub | ClickUp ID | Module |
|---|---|---|---|
| Abhiram | `Abhiram-0910` | 240010775 | contracts, core, pipeline, alembic, .github |
| Jashwanth | `badugujashwanth-create` | 106878760 | rules |
| Akshaya | `aksha08-ya` | 106878763 | vision |
| Sitanshu | `krishbattula4` | 106878761 | extraction |
| Yashashvi | `Yashashvi-05` | 106878758 | measurement |
| Shiva Kumar | `Shiva-Kumar-Akula` | 106878759 | evidence |
| Vineeth | `vineethsimha2151` | 106878762 | fnt officer |
| Shivasai | `adepushivasai901-ops` | 106878753 | tamper |
| Rohan | `A-Rohan99` | 216234631 | fnt admin |
| Aashritha | `aashrithareddybodanampally-byte` | 106878813 | datasets |
| Likhitha | `Likhitha-rachelly` | 106878764 | reserve |

Jashwanth runs Codex Plus; everyone else Antigravity + Gemini Pro; Abhiram Claude Code.

**B.V.Yashwanth (`ybaddam8-png`, ClickUp 240010980) is not on the team** — he leads 26167.
Never assign him work. He is a different person from Yashashvi; the near-identical names
are a real hazard when assigning by ID.

---

## Legal findings — expensive to rediscover

**Rule 7 is a single Table-I banded by PDP area** since 01.01.2018 (G.S.R. 629(E)). Bands
in `rules-corpus/README.md`. Table-II no longer exists. **A flat 1mm/2mm and a 1.7mm figure
both appear in older project documents — `SIH26034_PSR.md` §3 is the offender. That file is
not a source for rule facts.**

**Rule 6(11) is a FORMAT rule, not a tolerance.** It prescribes the unit basis — `Rs. per g`
below 1 kg, `Rs. per kg` at or above, and so on. It contains no tolerance, no rounding
increment, no permitted difference. **The ±₹0.01 and ±₹0.05 figures argued over in project
documents are assumptions, not law, and must never be encoded.** F18 is two checks: is a
unit sale price declared, and is it on the correct unit basis.

**Rounding increment ≠ tolerance.** "Rounded to nearest ₹0.05" transforms in steps; "±₹0.05"
accepts a difference. They diverge at boundaries. The rule schema must express both
separately.

**Rule 7(4) PDP area:** rectangular = height × width; cylindrical = 40% of (height ×
circumference); other = **40% of total surface area, OR an area considered to be the
principal display panel**. That second limb is the answer for irregular shapes — measure
the identified panel through the homography rather than refusing. Ruling already given to
Yashashvi. Refuse only when no panel can be identified or it is not adequately planar.

**Medical devices are carved out** by G.S.R. 778(E) (23.10.2025) — MDR 2017 governs numeral
and letter height, Rule 33 relaxation disapplied, PDP declaration non-mandatory. Table-I is
therefore **not universal**. `SIH26034_TI.md` §5 uses "Medical Device" as its routing
example without knowing this.

**Two evidence gaps, recorded not papered over.** The DoCA consolidated e-book
(`doca.gov.in/lm-ebook/`) returns Access denied — no consolidated text covering Nov 2021 to
Oct 2023. The 11.11.2025 DoCA FAQ is not captured; two claims in EXT-001 (both `₹` and `Rs.`
acceptable; "Marketed by"/"Brand Owner" satisfies Rule 6(1)(a)) rest on three secondary
sources and are marked **[SOURCED], not [VERIFIED]**.

`consumeraffairs.gov.in`, `doca.gov.in` and `egazette.gov.in` all refuse automated access.
**Do not build a fetcher.** Corpus is updated by hand.

---

## Hard nos — do not re-propose

- **Supabase** — free projects auto-pause after 7 days; sovereignty.
- **Cloud-primary OCR** — makes the offline path a second, weaker extraction
  implementation and puts product images outside the sovereign boundary. Self-hosted
  PaddleOCR primary; cloud is opt-in per-request escalation, disabled by default, daily
  page cap 0.
- **A custom rules DSL / Drools / OPA** — versioned YAML plus a deterministic evaluator.
  This is the project's most likely over-engineering failure.
- **A separate vector database** — pgvector in the same Postgres.
- **Next.js** — SSR buys nothing for an authenticated internal tool.
- **Two repositories** — monorepo with CODEOWNERS and import-linter.
- **Python 3.12** — 3.11, because PaddlePaddle and CV wheels lag.
- **Horizontal layer directories** — layers nest *inside* modules. With ten owners a
  horizontal layout makes every ticket a three-way ownership collision.
- **Empty `router.py`/`service.py` stubs in each module** — that is 24 stubs and breaks the
  no-stubs rule. The convention lives in each module's README.
- **Auto-review on every PR** — burns quota and trains people to scroll past Claude.
- **Making `main` a develop chain** — `main` plus feature branches. T4's `develop`
  references are superseded.

---

## Constraints discovered the hard way

- **Deleting the ClickUp list destroyed all ten tickets and Trash was unavailable.** They
  were rebuilt by hand. Be precise about "folder" vs "list" — the ambiguity caused it.
- **Custom fields are workspace-level and shared with the other team.** Attaching an
  existing `Module` field pulled in 26167's options. Prefix new fields with the problem
  statement number.
- **A ClickUp assignee filter silently hides everyone else's tickets.** The sidebar count is
  the truth. Check the filter before concluding a task failed to create.
- **`git branch` does not switch to the branch.** A commit landed on `main` because of this.
  Have him run `git status -sb` before every commit.
- **`mv /mnt/c/.../*.pdf`** moved his entire Downloads folder into the repo. Name files
  explicitly.
- **Required status checks cannot be added before the check has run once.**
- **import-linter needs `include_external_packages = true`** for a forbidden contract on a
  module outside `root_package`.
- **A forbidden contract that matches nothing looks identical to one that works.** Always
  prove a new contract by adding a deliberate violation and confirming exit 1.

---

## Open work, 2026-09-05

**PR #4 — Sitanshu, EXT-001.** Changes requested, not yet pushed. Three fixes: change
`NetQuantityValue.value` from `float` to `Decimal` (it feeds maximum-permissible-error
comparisons under the First Schedule); drop `| str` from `reason_code: ReasonCode | str |
None`; name the confidence literals (0.95/0.9/0.85) as constants with a docstring stating
they are uncalibrated priors, to be replaced when DAT-001's eval set exists. Minor: rename
`session-log/Sitanshu.md` lowercase; MRP doesn't recognise the word "Rupees". Otherwise
strong — 107 test cases against a 15-per-parser requirement.

**PR #5 — Akshaya, VIS-001.** Blocked. She added `bck/__init__.py` and imports
`from bck.app.modules.vision...`, creating a second import path that defeats import-linter
entirely. The forbidden contract on `bck` is now on `main`, so her branch will fail CI until
she removes it and imports `from app.modules.vision...`. Also missing the CLAHE chromaticity
test, which was her single most important acceptance criterion. Also her curvature test
warps with `arcsin` and unwarps with `sin` — it asserts `sin(arcsin(x)) == x` and can never
fail; and the docstring claims an elliptical fit the code doesn't do (it hardcodes
`radius = w/2`). New dependency `opencv-python-headless` — approved, but the gate fired.

**Both PRs add `bck/tests/modules/__init__.py`** — merge Sitanshu first, then have Akshaya
rebase.

**Merged:** #3 scaffold, #6 rule corpus, #7 CODEOWNERS + bck-forbidden contract. `main`
verified clean locally: 3 contracts kept, 4 tests passing.

**Unstarted, assigned:** CTR-002 contracts v1 (Abhiram — nine people blocked behind it, this
is the real critical path), RUL-001 (Jashwanth, now unblocked), MEA-001 (Yashashvi, working),
EVD-001 (Shiva Kumar), FNT-001 (Vineeth), DAT-001 (Aashritha).

**Owed to the team:** widen every open ticket's `Files` field to include its test path
(`bck/tests/modules/<x>/**`) — the tickets as written excluded tests, which was a ticket
bug. From ticket 2 onward, every ticket carries its own personalised "Before you raise the
PR" verification block at the bottom, built from that ticket's acceptance criteria.
`Pre-PR-Prompts.pdf` covered round one only.

**Biggest unmanaged risk:** DAT-001. No labelled corpus exists, so every accuracy target in
the PRD is unbacked and vision, measurement and tamper cannot be evaluated at all. Demo
scope is decided — packaged food primary, cosmetics secondary, FSSAI explicitly out of
scope.

---

## Golden examples from this project

**When a teammate presents two options and both are wrong.** Yashashvi asked whether to
approximate PDP surface area from a bounding box or refuse outright, and recommended
refusing. The right answer was a third path written into Rule 7(4) itself. Read the primary
source before choosing between someone's options — and tell them their instinct was right
even when the answer isn't theirs.

**When CI passes on a PR that breaks the architecture.** PR #5 was green. The `bck.*` import
path defeated the module contracts silently. Green checks mean the checks ran, not that the
design holds. Read the diff.

**When a rule figure appears in two project documents with different values.** Neither was
law. Both were assumptions that had been argued about long enough to look like facts. Go to
the gazette.

## Owners and usernames — addendum

FNT-001 is temporarily reassigned to B.V. Yashwanth (`ybaddam8-png`) due to Vineeth's
unavailability. This is a one-time, explicit exception — he is not otherwise a team
member and should not be assigned anything else without the same explicit call.

## Decisions — addendum

**VP-CI-001's ticket ID stays as written.** The project's placeholder-name check
searches for the retired product name as a substring; "VP-CI-001" doesn't contain it
and was never that placeholder — it's the actual branch/PR/ClickUp identifier from
when that ticket was live. Renaming it retroactively in session logs or SETUP.md
would make our own docs disagree with the permanent, unchangeable squash-merge commit
on GitHub, for no benefit. Left alone in TODO.md, SETUP.md, and session-log/abhiram.md.

**Cloud provider allocation:** Featherless remains the sole copilot generation
provider. OpenAI, if used, is scoped to query rewriting/retrieval expansion ahead of
the existing hybrid retrieval — never a second generation call, never in the verdict
path. AWS is unallocated reserve — no product data, no evidence records, ever, per the
sovereignty requirement that already ruled out cloud-primary storage.

## Merge gate — addendum

CODEOWNERS assigns exactly one owner per module path, and that owner is always the PR's
author. This means codeowner review can never be satisfied by a second person on any
contributor's own-module PR — not just Abhiram's own tickets. `--admin` is therefore the
standard merge command for every merge in this repo, for every contributor. `--admin`
also skips the required status check, so always run `gh pr checks <n>` in the same
breath as the merge — the ruleset itself won't catch a red build once `--admin` is
in play.
