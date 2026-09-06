# TICKETS.md — board state, 2026-09-06 (end of session 5)

ClickUp list `26034 Build` (`1300450000005736`), space `SIH Team` (`1300450000003833`).
Fields: `Module 26034` (dropdown) · `Files` (text) · `Branch` (text).
Statuses: `to do` · `doubt` · `in progress` · `review` · `done` · `complete`.

**`done` is the terminal status. Nothing moves to `complete`.**

**The ClickUp connector rate-limited at 19:30 on 2026-09-06 with a 600-minute lockout.**
Until roughly 05:30 on 2026-09-07, hand Abhiram each ticket as one pasteable markdown block
— title, assignee, status, priority, the three custom field values, description — instead
of writing directly. Two status moves were still owed when the limit hit and must be made
by hand in the UI: **DAT-002 → done** and **CTR-004 → done**.

Also: the `Module 26034` dropdown rejects a plain string. It needs an option UUID, which
`clickup_get_custom_fields` can fetch. Five tickets created this session went in without it.

`main` is at `5ff81d0`. **686 tests pass locally**, 32 skip without MinIO, Redis and a local
Postgres. 3 import contracts kept, 109 files analysed — not the silent no-op.

**PR state below was read from GitHub on 2026-09-06 at 19:33.** Check `gh pr list` before
trusting any line in this file.

---

## Merged in session 5 — six PRs

| PR | Ticket | Owner | What landed |
|---|---|---|---|
| #42 | MEA-004 | Yashashvi | Homography before scale; `coin_10` returns scale only with `h_matrix = None`; per-method confidence priors |
| #45 | VIS-003 | Akshaya | **PaddleOCR 3.x parser** — the version on `main` could not construct a `PaddleOCR` at all |
| #51 | RUL-004 | B.V. Yashwanth | `governs_declarations` on the rule store, corpus-audited |
| #52 | EXT-005 | Sitanshu | Deterministic category proposal |
| #53 | DAT-002 | Abhiram | Fabricated corpus removed, ground-truth schema hardened |
| #54 | CTR-004 | Abhiram | `RuleStatus` unified with contracts, drifted verdict spelling corrected |

Session 4 merged four before them: EVD-004 (#41) · CORE-002 (#40) · EXT-004 (#44) ·
PIP-002 (#48), plus CTR-003 (#50) and a docs PR (#49).

---

## Status

| Ticket | Owner | Status | PR |
|---|---|---|---|
| CI-001 · COR-001 · INF-001/2/3 · CTR-002 · CORE-001 | Abhiram | done | #3 #6 #7 #10 #11 #17 #25 |
| EXT-001/2/3 | Sitanshu | done | #4 #18 #24 |
| VIS-001/2 | Akshaya | done | #5 #20 |
| MEA-001/2/3 | Yashashvi | done | #9 #13 #22 |
| EVD-001/2/3 | Shiva Kumar | done | #12 #23 #31 |
| RUL-001 | Jashwanth | done | #21 |
| FNT-001 | B.V. Yashwanth *(one-time exception)* | done | #14 |
| PIP-001 · CI-002 · CTR-003 · RUL-002 · FNT-002 · RUL-003 · CI-003 | Abhiram | done | #28 #30 #33 #32 #35 #36 #38 |
| CORE-002 | Abhiram | done | #40 |
| EVD-004 | Shiva Kumar | done | #41 |
| EXT-004 | B.V. Yashwanth *(from Sitanshu)* | done | #44 |
| PIP-002 | Abhiram | done | #48 |
| **MEA-004** | Yashashvi | **done** | **#42** |
| **VIS-003** | Akshaya | **done** | **#45** |
| **RUL-004** | B.V. Yashwanth | **done** | **#51** |
| **EXT-005** | Sitanshu | **done** | **#52** |
| **DAT-002** | Abhiram | **done** *(move by hand — connector rate-limited)* | **#53** |
| **CTR-004** | Abhiram | **done** *(move by hand — connector rate-limited)* | **#54** |
| DAT-001 | Aashritha | closed as superseded | #34 closed |
| **MEA-005** artwork vector ingest | Yashashvi | **in progress** | **#43 open** |
| **EVD-005** retention and purge | Shiva Kumar | **in progress** | **#46 open, reworked** |
| **MEA-006** zero margin | Yashashvi | **in progress** | **#47 open** |
| **EXT-006** bilingual declarations | Sitanshu | **in progress** | branch pushed, no PR |
| **TAM-001** conflicting MRP + sticker | Akshaya | **in progress** | branch pushed, no PR |
| **CI-004** datasets/ never runs in CI | Abhiram | **to do** | — |
| **DAT-003** ownership + manifest off disk | Abhiram | **to do** | — |
| **DAT-004** reference-object vocabulary | Abhiram | **to do** | — |
| **DAT-005** annotate the six real captures | Abhiram | **to do, urgent** | — |
| **PIP-003** wire the category proposal | Abhiram | **to do** | — |
| **EVD-006** export takes a real VerdictRecord | Shiva Kumar | **to do** | — |
| **MEA-007** ellipse-fit coin homography | Yashashvi | **to do, low** | — |

**Off the project:** Aashritha. **Unavailable:** Jashwanth, Vineeth. **Never started:**
`fnt-admin` (Rohan). **Reserve:** Likhitha.

**Number reuse to be aware of.** #50 merged under the label CTR-003, which is already #33.
#51's branch is `rul-003-governs-declarations` but the ticket is RUL-004; RUL-003 is #36.
Neither was renamed. Read the ticket, not the branch.

---

## Open PRs — exact remaining items

### #46 EVD-005 retention and purge — Shiva Kumar

**Head moved to `e510224` after the session-5 review; the diff below has NOT been re-read.**
Re-pull it before reviewing. The items below are from head `1b1b15a`.

**The migration is Abhiram's, not Shiva's.** `asset_type` needs a column on
`EvidenceEntryRow` and a migration; `alembic/` is single-owner and a migration can never be
edited after it merges. Split it: Abhiram lands the column and migration first, then #46
rebases onto it. **Do not ask Shiva to write a migration** — an earlier review comment did,
and it was wrong.

1. **A purge that finds nothing reports success and writes an audit record claiming the
   asset was destroyed.** `storage_key = f"evidence/{entry.payload_hash}"` uses the payload
   hash, but the CAS client keys on image bytes. When they differ, `purge_image` takes its
   not-found branch, `purge_evidence` returns `True`, and `append_purge_entry` writes an
   immutable chain entry attesting a destruction that did not happen. Derive the key from
   what `store_image` returned, and make `purge_image` report whether it found anything so a
   no-op purge writes no audit record. **A false attestation in the evidence chain is worse
   than a failed purge.**
2. **`asset_type` is not in `compute_entry_hash`.** The field that decides when evidence is
   destroyed can be relabelled without breaking verification. Either fold it into the hash —
   which changes every existing entry hash and is its own decision — or document why it is
   deliberately outside.
3. **`is_purged` reads `payload.get("type")`, but persisted payloads are JSON strings**, so
   it returns `False` for everything on the database path. Purge detection is memory-only.
4. **`test_chain_verification_tampered_purge` proves nothing about purging.** Remove the
   purge and it passes identically — the tampering alone causes `payload_hash_mismatch`.
5. `purge_evidence(e0, e0, ...)` passes an entry as its own predecessor in several tests.
6. **No `session-log/shiva-kumar.md`** in the head reviewed.
7. `S3ContentAddressedStorageClient.purge_image` catches bare `Exception` and returns, so a
   permissions failure reads as "already purged".

**Legal hold — decided, build to this:** hold on any POTENTIAL_VIOLATION with **no** review
row, and on any with CONFIRM or OVERRIDE. Release only on REJECT. The shipped code has it
inverted — an unreviewed potential violation is currently purgeable, and that is the
evidence most worth keeping. The docstring describes the opposite of what the code does.

### #43 MEA-005 artwork vector ingest — Yashashvi

Not re-reviewed since session 4. Items from then:

1. A missing library returns `MeasurementRefusal` — a deployment fact rendered as a finding
   about the package under inspection. A missing import must fail loudly at startup.
2. Tests inject `sys.modules["pdfplumber"] = MagicMock()`, so real pdfplumber output is
   never parsed. `reportlab` is already a dependency and can generate a genuine vector PDF
   fixture with known dimensions.
3. **New dependency: `pdfplumber`.** Merge-gate escalation — needs an explicit yes.
4. No `session-log/yashashvi.md` in the diff.
5. Rebase; it is well behind.

**Do not merge before #47** — both touch `services.py`, and #42 already rewrote it.

### #47 MEA-006 permit zero-margin results — Yashashvi

Went red after `contracts/` moved under it when #50 merged. Not re-checked since.

1. **Edits `bck/app/contracts/measurement.py`, which is Abhiram's.** Merge-gate escalation.
   My position: approve as a recorded exception rather than re-cutting a seventeen-line diff
   already reviewed as correct — conditional on item 2 producing a real falsified test.
2. The PR body names `test_zero_margin_is_valid`; it is not in the changed files.
3. No `session-log/yashashvi.md`.
4. **The contract change alone does not restore Rule 8.** `pipeline/` still never calls
   `measure_margins`. Say so when it merges or it will read as fixed.

---

## Merge order

1. **#47** — resolve contracts ownership, get the test file named, rebase.
2. **#43** — after #47; needs the `pdfplumber` decision and a real fixture.
3. **#46** — after Abhiram lands the `asset_type` column and migration.

**Merge gate, unchanged:** checks green · one module · in ticket scope · no migration · no
auth or permission change · no shared-contract change · no new dependency. All three fail it
on at least one clause and need an explicit decision rather than a quiet merge.

`gh pr merge N --squash --admin --delete-branch`, with `gh pr checks N` in the same breath.

---

## Owed on every future ticket

Session 5's lesson: teammates were spending hours per ticket on under-specified
instructions. **Write tickets as complete work orders** — exact files, exact signatures, the
commands in order, the falsification steps spelled out, and an explicit out-of-scope list.
The five tickets created this session (CI-004, DAT-004, DAT-005, MEA-007, PIP-003) are the
format to copy.

- A personalised **"Before you raise the PR"** block from that ticket's own failure modes,
  including *"prove the test can fail — introduce the defect it guards against, confirm red,
  revert"* and *"run `find . -name __pycache__ -type d -exec rm -rf {} +` first"*.
- The `Files` field must include the matching test path **and** `session-log/<n>.md`.
- **`session-log/<n>.md` is appended to, never rewritten.** Four PRs destroyed history this
  session before the instruction started landing.
- **Run `git status -sb` before every commit.** #42 committed a 12 KB junk file at the repo
  root named from a shell quoting accident; it passed both CI jobs.
- A rebase instruction placed **immediately before opening the PR**.
