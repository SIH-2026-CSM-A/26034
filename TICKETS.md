# TICKETS.md — board state, 2026-09-06 (end of session 4)

ClickUp list `26034 Build` (`1300450000005736`), space `SIH Team` (`1300450000003833`).
Fields: `Module 26034` (dropdown) · `Files` (text) · `Branch` (text).
Statuses: `to do` · `doubt` · `in progress` · `review` · `done` · `complete`.

**`done` is the terminal status. Nothing moves to `complete`.**

The ClickUp connector works — create and update tickets directly. If it rate-limits again,
stop and give Abhiram each ticket as one pasteable markdown block: title, assignee, status,
priority, the three custom field values, description.

`main` is at `9f68683`. **637 tests pass locally**, 33 skip without MinIO, Redis and a local
Postgres. 3 import contracts kept, 0 broken.

**PR state below was read from GitHub on 2026-09-06, not carried forward from the last
handoff.** The previous handoff recorded MEA-004 (#42) as merged and DAT-001 (#34) as closed.
Neither is true. Check `gh pr list` before trusting any line in this file.

---

## Status

| Ticket | Owner | Status | PR |
|---|---|---|---|
| CI-001 scaffold | Abhiram | done | #3 |
| COR-001 rule corpus | Abhiram | done | #6 |
| INF-001 CODEOWNERS + import guard | Abhiram | done | #7 |
| INF-002 handoff | Abhiram | done | #10 |
| INF-003 gh auth login steps | Abhiram | done | #11 |
| CTR-002 contracts v1 | Abhiram | done | #17 |
| CORE-001 auth, RBAC, jurisdiction scoping | Abhiram | done | #25 |
| PIP-001 verdict assembly + rule snapshot adapter | Abhiram | done | #28 |
| CI-002 frontend build gate *(no ClickUp ticket)* | Abhiram | done | #30 |
| CTR-003 snapshot deep copy *(no ClickUp ticket)* | Abhiram | done | #33 |
| RUL-002 Rule 8/9, sector overrides, Combination/Group | Abhiram *(from Jashwanth)* | done | #32 |
| FNT-002 officer design system, verdict detail, review queue | Abhiram *(Vineeth's module)* | done | #35 |
| RUL-003 multi-piece package 2(kc) + food proviso *(no ClickUp ticket)* | Abhiram | done | #36 |
| EVD-003 hash chain verification + append-only | Shiva Kumar | done | #31 |
| docs: session log, TODO, tickets *(no ClickUp ticket)* | Abhiram | done | #37 |
| CI-003 frontend always reports *(no ClickUp ticket)* | Abhiram | done | #38 |
| **CORE-002 persistence, async session, Alembic, Postgres CI** | Abhiram | **done** | **#40** |
| **EVD-004 officer report export, PDF + editable** | Shiva Kumar | **done** | **#41** |
| **EXT-004 span classification + spatial role binding** | B.V. Yashwanth *(from Sitanshu)* | **done** | **#44** |
| **PIP-002 HTTP surface, orchestration, scan endpoints** | Abhiram | **done** | **#48** |
| EXT-001 | Sitanshu | done | #4 |
| EXT-002 country of origin | Sitanshu | done | #18 |
| EXT-003 name, dimensions, unit price | Sitanshu | done | #24 |
| RUL-001 | Jashwanth | done | #21 |
| VIS-001 | Akshaya | done | #5 |
| VIS-002 PDP detection + OCR | Akshaya | done | #20 |
| MEA-001 | Yashashvi | done | #9 |
| MEA-002 artwork mode + Rule 9 contrast | Yashashvi | done | #13 |
| MEA-003 ratio + margins | Yashashvi | done | #22 |
| EVD-001 | Shiva Kumar | done | #12 |
| EVD-002 MinIO + BSA report | Shiva Kumar | done | #23 |
| FNT-001 | B.V. Yashwanth *(one-time exception)* | done | #14 |
| **MEA-004 homography before scale, distinct confidence intervals** | Yashashvi | **review — red** | **#42 open** |
| **MEA-005 artwork vector ingest** | Yashashvi | **review — changes requested** | **#43 open** |
| **VIS-003 constrained re-OCR, arbitration, offline** | Akshaya | **review — near merge** | **#45 open** |
| **EVD-005 retention and purge** | Shiva Kumar | **review — escalate** | **#46 open** |
| **MEA-006 permit zero-margin results** | Yashashvi | **review — escalate** | **#47 open** |
| **DAT-001 corpus, labelling schema, eval harness** | Aashritha | **close as superseded** | **#34 open** |
| **VIS-004 OCR the detected panel, not the whole frame** | Akshaya | **to do** | — |
| **EXT-005, EXT-006** | Sitanshu | **to do** | — |
| **EVD-006 accept a real `VerdictRecord` in export** | Shiva Kumar | **to do** | — |
| **DAT-002, DAT-003** | Abhiram *(from Aashritha)* | **to do** | — |
| **RUL-004 `governs_declarations` on the rule store** | B.V. Yashwanth | **to do** | — |
| **TAM-001 conflicting MRP + sticker overlay** | Akshaya *(from Shivasai)* | **to do — never started** | — |

**Off the project:** Aashritha. **Unavailable:** Jashwanth, Vineeth. **Never started:**
`fnt-admin` (Rohan), `tamper/` (Akshaya). **Reserve:** Likhitha.

**RUL-003 is session 3's merged multi-piece ticket (#36).** The `governs_declarations`
narrowing ticket is **RUL-004**. Do not reuse the number.

---

## Every open PR is on a stale base

All six branched before today's four merges — between 2 and 13 commits behind `main`:

| PR | Branch | Base | Commits behind `main` |
|---|---|---|---|
| #42 | `mea-004-homography-calibration-confidence` | `5613944` | 4 |
| #43 | `mea-005-artwork-vector-ingest` | `5613944` | 4 |
| #45 | `vis-003-reocr-clean` | `266b00b` | 2 |
| #46 | `evd-005-retention-purge` | `5613944` | 4 |
| #47 | `mea-006-zero-margin` | `266b00b` | 2 |
| #34 | `feature/26034-DAT-001-corpus-images` | `23d224f` | 13 |

The fix is the owner's, not yours:

```
git fetch origin && git rebase origin/main && git push --force-with-lease
```

**Never rebase someone else's branch for them.** Yashashvi has three stacked branches in one
module — rebase them **oldest-first** (#42, then #43, then #47), or the later ones replay
conflicts already resolved in the earlier ones.

**A stale base does not reliably show as red.** #45 and #47 are green on bases two commits
behind. A green check on a stale branch is evidence about the base it ran on and nothing else.

---

## Open PRs — exact remaining items

### #42 MEA-004 homography before scale — Yashashvi

Head `83e3979`. Files: `bck/app/modules/measurement/services.py`,
`bck/tests/modules/measurement/test_measurement.py`, `session-log/yashashvi.md`.

**The red check is not a test failure.** `ruff check .` passes; `uv run ruff format --check .`
fails on a re-wrapped comment in `services.py` (around line 444, "the scale error cancels
between the numerator and denominator"). `tests/modules/measurement` passes 14/14 on a
rebase. Two items:

1. `cd bck && uv run ruff format .`, commit the result.
2. Rebase onto `origin/main` and force-with-lease.

Nothing about the code is in dispute. This is the cheapest PR on the board to close out.

### #43 MEA-005 artwork vector ingest — Yashashvi

Head `e3c87f2`. `CONFLICTING`. Files: `bck/app/modules/measurement/artwork.py`,
`services.py`, `bck/pyproject.toml`, `bck/tests/modules/measurement/test_artwork.py`,
`bck/uv.lock`.

1. **A missing library returns `MeasurementRefusal`.** That renders a deployment fact — the
   package is not installed — as a finding about the *package under inspection*. An officer
   reading the refusal cannot tell the two apart. A missing import must fail loudly at
   startup, the way the model-weight check does.
2. **The tests inject `sys.modules["pdfplumber"] = MagicMock()`**, so real pdfplumber output
   is never parsed and the ingest path has never run. `reportlab` is **already a dependency**
   (EVD-004 uses it) and can generate a genuine vector PDF fixture with known dimensions.
   Build the fixture, parse it, assert the millimetre values.
3. **New dependency: `pdfplumber` in `pyproject.toml` and `uv.lock`.** Merge-gate
   escalation — it needs Abhiram's explicit yes before merge, not after.
4. **No `session-log/yashashvi.md` in the diff.** AGENTS.md requires it on every ticket.
5. Rebase; the branch conflicts.

**Do not merge this before #42.** They both touch `services.py`.

### #45 VIS-003 constrained re-OCR — Akshaya

Head `01f109e`. Green on both checks. Files: `bck/app/modules/vision/ocr.py`,
`bck/tests/modules/vision/test_ocr.py`, `session-log/akshaya.md`.

**Both previously-owed items are fixed.** `_extract_numeric_value` now returns `""` for
`"150.00.5"` instead of silently repairing it to `"150.005"`, and there is a test for it.
`session-log/akshaya.md` is in the diff. One item remains:

1. **The session log rewrite deleted her VIS-001 history** — nine lines replaced with seven,
   removing the `remap_curvature` vectorisation entry, the performance regression test entry
   and the rebase notes. Same defect as #44 deleting `session-log/sitanshu.md`. Ask her to
   **append** the new section and restore the old one; the log is append-only in spirit for
   the same reason the evidence chain is in fact.

Then rebase and it is mergeable. This is the closest PR to done.

### #46 EVD-005 retention and purge — Shiva Kumar

Head `7e1c5cb`. `CONFLICTING`, **no checks have run at all**. Files include
`bck/app/contracts/enums.py` (+22), `bck/app/core/config.py` (+10),
`bck/app/modules/evidence/{chain,domain,retention,storage}.py`,
`bck/tests/modules/evidence/test_retention_purge.py` (+255), `session-log/shiva-kumar.md`.

1. **It edits `bck/app/contracts/enums.py` and `bck/app/core/config.py`.** Both are Abhiram's,
   and AGENTS.md says contracts are not the module owner's to change. **Merge-gate
   escalation: shared-contract change.** Either Abhiram lands the enum members in a separate
   contracts commit first, or this PR is split in two.
2. **It also modifies `chain.py` (+63/-21) and two existing chain tests.** A retention ticket
   rewriting hash-chain code and its tests is the shape that hides a weakened guard. Read
   `test_chain_verification.py` and `test_hash_chain.py` line by line and ask what the changed
   assertions no longer catch.
3. **No CI has run.** Rebase and push so the checks report before any review conclusion.
4. Purge must not be able to break the chain. Ask explicitly: after a purge, does
   `verify_chain` still pass, and if an entry is removed, what does the sequence gap do to
   `(scan_id, sequence)`? The answer belongs in the PR body with a test behind it.

### #47 MEA-006 permit zero-margin results — Yashashvi

Head `b5fb09b`. Green on both checks. **One file:** `bck/app/contracts/measurement.py` (+17/-1).

The shape is right — `MeasurementMarginExact` and `MeasurementMarginCalibrated` as distinct
discriminated variants at `ge=0`, with every other measurement (area, height, ratio) left at
`gt=0` so a zero there still surfaces as an upstream detection failure. The PR body says
`test_zero_margin_is_valid` was falsified against the old constraint before the fix, which is
the standard this project asks for.

1. **It edits `bck/app/contracts/measurement.py`, which is Abhiram's.** Merge-gate escalation:
   shared-contract change. The fix is correct and the ownership still has to be resolved
   explicitly rather than waved through because the diff is small.
2. **No test file in the diff** and **no `session-log/yashashvi.md`**. The PR body names
   `test_zero_margin_is_valid`; it is not in the changed files. Ask where it lives.
3. **The contract change alone does not restore Rule 8.** `pipeline/` still never calls
   `measure_margins`. Wiring the orchestrator to call it is a second ticket, and Rule 8
   free-space evaluation stays dark until that lands. Say so when this merges, or it will
   read as fixed.

### #34 DAT-001 corpus — Aashritha

Head `47fa16d`. Red, thirteen commits behind `main`. **Aashritha is off the project and this
is superseded by DAT-002 + DAT-003.**

**Close it. Do not merge it, and do not review it a fifth time.**

Closing it is an action nobody has taken — the last handoff recorded it as already closed and
it is not. Before closing, salvage these four into DAT-002, because they are real defects in
the annotations regardless of who finishes them:

1. `cosmetics_himalaya_face_wash_100ml_001` appears **twice** in the manifest — once `.jpg`,
   once `.png`, same `sample_id` and `annotation_path`, different `sha256`. Keep the `.jpg`,
   which is what the annotation's `image_filename` points at.
2. `food_parle_g_biscuits_001` has `reference_object.present: false` with every height nulled,
   but its notes still claim a "calibrated coin reference target". Delete the sentence or
   supply the reference object.
3. **The Himalaya MRP question, unanswered after four rounds.** Both files are tagged
   `export_pack` and `non_domestic` while declaring `MRP Rs. 180.00`.
4. Manifest `image_path` and annotation `image_filename` use **two different path schemes**,
   so nothing downstream can resolve an image from an annotation.

Written review has failed four times here. The next move is a fifteen-minute call with one
annotation open beside the actual photograph.

---

## Merge order

1. **#42** — one `ruff format` run and a rebase. No judgement required.
2. **#45** — restore the deleted VIS-001 log history, rebase, merge.
3. **#47** — resolve the contracts ownership, get the test file named, merge.
4. **#43** — after #42, and only once the `pdfplumber` dependency is agreed and the
   `MagicMock` fixture is replaced with a real one.
5. **#46** — after the contracts split, and after CI has actually run once.
6. **#34** — close, do not merge.

**Merge gate, unchanged:** checks green · one module · in ticket scope · no migration · no
auth or permission change · no shared-contract change · no new dependency. #43, #46 and #47
each fail that gate on one clause and need an explicit decision rather than a quiet merge.

`gh pr merge N --squash --admin --delete-branch`, with `gh pr checks N` in the same breath —
`--admin` skips required checks as well as the unsatisfiable code-owner review.

---

## Owed on every future ticket

- A personalised **"Before you raise the PR"** block built from that ticket's own acceptance
  criteria and its specific failure modes — including *"prove the test can fail: introduce
  the defect it guards against, confirm red, revert."*
- The `Files` field must include the matching test path **and** `session-log/<name>.md`.
  Omitting the session log produced false out-of-scope flags on an earlier session's reviews.
  Three of the six open PRs are missing one, so the ticket text is still not carrying it.
- **`session-log/<name>.md` is appended to, never rewritten.** Two PRs have now destroyed
  history in one: #44 deleted `sitanshu.md` outright, #45 replaced Akshaya's VIS-001 entries.
  Put it in the ticket text.
- A rebase instruction placed **immediately before opening the PR**, not before starting
  work. Every one of the six open PRs is on a stale base.
