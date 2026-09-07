# TODO.md — 2026-09-07, after the Session 14 handoff

Session numbering is read from `session-log/abhiram.md`, not from here — the last
`## Session N` heading in that file is authoritative. RUL-007 was Session 18 there. "Session 14"
in this PR's branch name is the *chat's* numbering and is a different sequence; do not reconcile
them, read the file.

---

## Now

1. **#63 VIS-004 — the OCR suite is hollow, and it is the one ticket between this project and a
   demonstrated pipeline.** `bck/tests/modules/vision/test_ocr.py` at head `7bc6307` is
   twenty-seven lines: five `pass` bodies and a `test_placeholder_ocr` asserting `True`. Main
   has twelve real tests there. Three checks green. Exact items in `TICKETS.md`. **No image has
   ever passed through this pipeline and this is the ticket that changes that** — it has now
   burned more than a day and has gone backwards.
2. **#77 DAT-005 — review and merge.** Twelve annotated captures, uncalibrated throughout,
   plus a populated `datasets/manifest.json`. This is the item every accuracy figure in the PRD
   depends on and none has been defensible without it. `declared` is per-image, not pack-level.
   Read `datasets/manifest.json` against `ingest_images.py` before merging — see Bugs.
3. **#66 EXT-008 — one item.** `MIXED` now means any two of five scripts, so the statutory
   Devanagari-plus-Latin pair is the one distinction it no longer expresses. Narrow it or rename
   it, and pin the choice. Everything else on that PR is closed.
4. **MEA-011 / MEA-009 Part B** (Yashashvi) — replace the overlap refusal in `measure_margins`
   with `MeasurementMarginOverlapExact` / `MeasurementMarginOverlapCalibrated`. Part A (#73)
   landed the contract. Two things to know: the `dist_mm < 0` branch sits **above** the
   `is_artwork` split, so both shapes must be constructed there; and margins are still not wired
   into `pipeline/orchestrator.py` at all (it omits `measure_margins` pending EXT-004's
   declaration bounding box), so this changes what the function returns without changing any
   scan yet. **RUL-007 (#76, Session 18) landed the consuming shape:** `SideOverlap` on
   `FreeSpaceMeasurement`, so an overlap now has somewhere to go the moment this returns one.
   No adapter exists between them yet — see item 4a.

4a. **Wire Rule 8(1)'s proviso into the pipeline — a new ticket, blocked twice.** RUL-007
   left `evaluate_rule8_free_space` correct and unreached. It needs (i) EXT-004's declaration
   bounding box, so `orchestrator.py` can call `measure_margins` at all, and (ii) MEA-011, so
   an overlap arrives as an overlap rather than a refusal. Two further things the writer needs
   to know. `context.measurements` is keyed one result per condition kind and `measure_margins`
   returns four, so `free_space` needs a shape that is not one `MeasurementResult`. And
   `measurement_findings.py`'s non-Table-I branch formats `f"{result.value} {result.unit}"` —
   an overlap type has no `.value`, deliberately, per the MEA-009 docstring. Unreachable today;
   an `AttributeError` on the first real overlap the day it is wired.

## Next

7. **Write the seven tickets below.** They are specified, not vague; each has a file, a defect
   and a consequence. Until they are on the board they are invisible.
8. **Create MEA-010, MEA-011 and FNT-004 on the board.** All three are unblocked and all three
   have owners idle or nearly idle.
9. **Persist the Rule 3(c) officer confirmation, or decide not to.** RUL-005 passes it as a
   plain `bool` down to `EvidenceContext` and deliberately does not store it: that would need a
   `contracts` enum, a `scans` column, a migration and a `ScanSummary` field, and `contracts/`
   is single-owner. It is auditable today only through the `reason` text on the findings it
   produced. Decide whether an officer needs to filter scans by it.
10. **Persist the category proposal, or decide not to.** PIP-003 (#74) leaves it present on the
    POST response and `None` on a GET re-read, because the `scans` row has no column for it. A
    column plus its migration is a ticket of its own, and it is the thing that decides whether
    an officer can act on a proposal after reloading the page. Separately: the catalogue path
    proposes nothing, because `propose_category` takes an `ExtractionResult` that a listing
    never builds. Decide whether a listing should propose.
11. **Resolve `/fnt/` ownership.** Three sources give three answers — `.github/CODEOWNERS:29`
    assigns all of `/fnt/` to `@vineethsimha2151`; `HANDOFF.md` says the officer surface stays
    with Abhiram because it is on the demo path; `AGENTS.md:120` says Abhiram *"(Vineeth's
    module, he is unavailable)"* and he is demonstrably available, having shipped #72. This was
    deliberately **not** decided by the Session 14 CODEOWNERS edit. Decide it on purpose.

## Later

12. **TAM-002** once DAT-005 exists — wiring plus the false-positive rate on real labels.
13. **EVD-004 / EVD-006** — the report export takes mock shapes and needs a real
    `VerdictRecord`. Shiva's, and unblocked; he should be on it rather than idle.
14. **MEA-007, MEA-008.** MEA-007 needs a rebase — `services.py` changed under it in #43.
    MEA-008 may legitimately close as a finding that the 50 mm card does not exist.
15. **The seven UP042 findings in `datasets/schema.py`.** Converting a schema that serialises to
    JSON is its own change, and until it happens the datasets job cannot gain a ruff step.
16. **The officer surface's presentation of 65 findings per scan.** RUL-004 established this is
    a presentation problem, not a rule-store one.

---

## Identified this session, not yet written as tickets

Seven, each with the file, the defect, and why it matters. They are not one-liners because none
of them is obvious from the code alone.

**1. `NOT_IN_FRAME` — the ground-truth schema cannot say "not in this photograph".**
`datasets/schema.py:212` has `declared: bool` on `DeclarationField`, and
`FieldComplianceState` (`schema.py:92-99`) has exactly five members: `PASS`, `FAIL`,
`REVIEW_REQUIRED`, `NOT_APPLICABLE`, `INSUFFICIENT_EVIDENCE`. A scan is one image, and DAT-005
settled that `declared` is per-image. So `declared: false` now carries two different facts —
"this declaration is absent from the package" and "this declaration is on a panel the camera
did not see" — and nothing distinguishes them. **Why it matters:** the evaluation harness scores
a correct `INSUFFICIENT_EVIDENCE` refusal as a miss against a ground truth that says the field
was undeclared, so the system is penalised for the exact behaviour Constraint 2 requires of it.
It also contradicts `datasets/README.md`. Needs a `NOT_IN_FRAME` state or a `visible_in_image`
bool, and a decision about which — a state changes the enum and therefore needs an
`ALTER TYPE ... ADD VALUE` if it ever reaches Postgres.

**2. `test_manifest_integrity` guards nothing, and the manifest it guards is a stub.**
`bck/tests/contracts/test_manifest_integrity.py:16` and `:41` both loop
`manifest.get("records", [])`. `datasets/ingest_images.py:47-52` writes a `"samples"` key. The
committed `datasets/manifest.json` is nineteen bytes — `{"records": []}` — and was not produced
by that writer at all: it has no `manifest_version` and no `total_samples`. So both loops get
`[]` twice over. Worse, `test_annotation_image_sha256_matches_manifest` has **no assertion
outside its loop**, so it passes against any JSON object whatsoever. **Why it matters:** two
green tests claim the annotation hashes match the images. Nothing is compared. This is the
eighth unfalsifiable test on this project and the first where the fixture is also fake.

**3. `ingest_images.py` demands a Google Drive ID the design explicitly forbids.**
`datasets/ingest_images.py:18-19` raises `ValueError("A valid Google Drive folder ID must be
provided to sync the manifest.")` on a missing or placeholder id, read from a hand-rolled
`sys.argv` at `:60-66` (there is no argparse). `datasets/README.md:72-73` says the manifest
"is **not** synced from Google Drive; the demo has to survive the venue network failing". The id
is used for nothing but being stamped into the JSON at `:49` — no network call exists anywhere
in the file. **Why it matters:** the script cannot be run at the venue, or by anyone who does
not have the folder id, to produce a manifest it does not need the id for. Either the guard goes
or the README does; they cannot both be right.

**4. `ingest_images.py` silently skips twelve of the fifteen staged captures.**
`datasets/ingest_images.py:24` is `RAW_DIR.glob("**/*.[jJ][pP][gG]")`. The character class
already handles `.JPG`, so that is not the problem. `.png` is. Twelve of the fifteen files in
`~/26034-dat/datasets/raw/_staging/` are `.png` — every capture numbered 01 to 05. **Why it
matters:** this is the input to DAT-005. A run against the staged set would produce a manifest
of three files and report success, and nothing anywhere would say twelve were dropped.

**5. Per-ticket session logs.** `session-log/abhiram.md` is 137 KB and every PR appends to it,
so every PR conflicts with every other PR. It forced a rebase on **every** PR merged on
2026-09-07, and RUL-006 renumbered its session three times during review as concurrent work
landed. **Why it matters:** it is a serialisation bottleneck on a five-person board, and the
conflict-resolution procedure is delicate — reconstruction, never marker-editing, proved with
`git diff --numstat` showing zero deletions — because two PRs have already destroyed an earlier
ticket's history in this file. Split to `session-log/abhiram/<ticket>.md` or equivalent;
`.github/CODEOWNERS` follows the split.

**6. Two artwork measurement functions merged with no caller.**
`bck/app/modules/measurement/artwork.py:65` (`measure_artwork_ink_extent`) and `:79`
(`calculate_artwork_pdp_area`). Every other reference in the repository is in
`bck/tests/modules/measurement/test_artwork.py`. Neither is in `measurement/__init__.py`'s
`__all__`, and nothing in `bck/app/` imports from `.artwork`. **Why it matters:** they are the
fifth and sixth functions to ship uncalled on this project, and artwork mode is the *only* path
that yields an exact millimetre figure — the one measurement that never needs a refusal. It is
built and unreachable. Tracked as MEA-011; this entry is the specification.

**7. Two ceremonial `deepcopy` calls, and a decision to make about both.**
`RuleParameterSnapshot.from_rule` — `bck/app/contracts/records.py:83` — and `snapshot_from_rule`
— `bck/app/pipeline/rule_snapshot.py:209`. Only the second has a live caller
(`pipeline/rule_findings.py:154`); the first is reachable from nothing in `bck/app/`. Both
docstrings already concede the copy is not load-bearing: pydantic's `JsonValue` re-validation
walks the mapping and rebuilds every container, so the snapshot is isolated with or without it.
`bck/tests/contracts/test_contracts.py:721` says in its own docstring that it cannot fail
against the annotation as it stands. **Why it matters:** the decision is whether the copy stays
as annotation-independence (documented, deliberate) or goes. It is **not** to "repair" the test
— `CLAUDE.md` forbids that by name. And the dead `from_rule` path is a separate question that
`applies_to`'s survival at `contracts/rules.py:60` also hangs off.

**Not a ticket, recorded so it is not re-raised:**
`test_rule_store_contains_only_ticket_authorized_scopes` was flagged as unfalsifiable — a `<=`
subset assertion green against the empty set. **RUL-006 already deleted it** in `d9c44fa`. It is
gone, not outstanding.

---

## Bugs

- **`rules-corpus/README.md`'s encoded-rule-id list is wrong in thirteen places and nothing
  pins it.** It listed nineteen ids against a twenty-eight-rule store: eleven real ids missing
  (`R3-CHAPTER-II-SCOPE`, `R6-1-B`, `R6-1-C`, `R6-1-D-GSR-722E`, `R6-1-DA`, `R6-1-E`, `R6-1-F`,
  `R6-1-G`, `R7-5-OTHER-LAW`, `R6-10A-GSR-128E`, `R6-10A-GSR-312E`) and two listed that have
  never existed in code (`R6-11`, `R6-10A-ECOMMERCE-FILTER` — the latter entering in a docs
  commit, `756462b`, and only ever there). The list is regenerated from the store in this PR.
  **The defect is that nothing in CI reads that file.** `bck/tests/modules/rules/test_loader.py:133`
  pins `rules.yaml` against a hardcoded 28-entry mapping and would catch a store change; a wrong
  README ships green. A test that compares the README list against `load_rules(...)` would have
  caught all thirteen. Same species as bug 2 above.
- **`test_placeholder_ocr` is a placeholder in a committed test file** on #63. `AGENTS.md:78`
  and `CLAUDE.md` forbid stubs and placeholders in committed code outright. Listed here as well
  as on the PR because it is a constraint breach, not only a review item.
- **`measure_margins` is not wired into `pipeline/orchestrator.py`** at all — it omits
  `measure_margins` pending EXT-004's declaration bounding box. So MEA-006, MEA-009 and RUL-007
  all change what the measurement layer *returns* without changing any scan.
- **Port-shadowing.** `POSTGRES_PORT` in the repo-root `.env`, `DATABASE_URL` in `bck/.env`,
  nothing linking them. Setting one without the other connects to the wrong server silently. A
  local Postgres cluster on `127.0.0.1:5432` shadows the container entirely — the container
  reports healthy and the DSN quietly reaches the local cluster.
- **`rtk` refuses single-line `find … -exec`** and exits 1. `find … ; pytest` on one line skips
  the purge and runs on stale bytecode. Use `/usr/bin/find` and assert the directory count is
  zero.
- **`rtk` refuses `gh run view --job … --log`.** Use `gh api repos/<r>/actions/jobs/<id>/logs`.
- **`datasets/` is not ruff-clean** under `bck`'s config: seven UP042 plus one format diff.
- **`alembic check` does not detect a change to the *values* of an existing enum.** Adding a
  member passes clean and then fails at the first insert with `invalid input value for enum`.
  Needs a hand-written `ALTER TYPE ... ADD VALUE`, which cannot run inside a transaction.

**Closed since the last revision of this file:**

- ~~`measure_margins` raises on a flush declaration on both paths.~~ Fixed by MEA-006 (#47).
- ~~An overlap is reported as a refusal.~~ Part A landed the types (#73); Part B returns them.
- ~~`FreeSpaceMeasurement` cannot carry an overlap or a flush margin~~ —
  `modules/rules/results.py:82` typed all four clearances as `PositiveDecimal`. RUL-007 (#76)
  fixes it and is in review.

---

## Blocked

- **TAM-002** on DAT-005 landing. Genuinely blocked; Akshaya has #63 in the meantime.
- **`measure_margins` orchestrator wiring** on EXT-004's declaration bounding box.
- **PIP-002** on EXT-004.

**No longer blocked** — these came off the list and the reason is recorded so nobody re-adds
them: #43 MEA-005 (`pdfplumber` approved, merged), #47 MEA-006 (#58 merged), EXT-007 (#65 and
#67 landed the contract and the pipeline; merged as #71), PIP-004 (merged), MEA-010 and MEA-011
(unblocked by #43), FNT-004 (unblocked by #72), #46 EVD-005 (CORE-003 merged as #62 — Shiva
owes the rebase, he is not blocked on anyone).

---

## Done — with dates

**2026-09-07, Session 14** — #71 EXT-007 · #72 FNT-003 · #73 MEA-009 Part A · #74 PIP-003 ·
#43 MEA-005 · #75 RUL-006 · #70 docs.

**2026-09-07, Session 13** — #62 CORE-003 · #56 EXT-006 · #64 DAT-003 docs · #47 MEA-006 ·
#65 CTR-006 · #67 PIP-004 · #68 RUL-005 · #69 docs.

**2026-09-07, Session 6** — #60 CI-004, `datasets/` runs in CI for the first time and 27 tests
that had never executed once now do; repo-hygiene step gates tracked filenames. #55 TAM-001,
tamper detection, two review rounds, merged with uncalibrated thresholds and no caller,
deliberately and on the record. #58 CTR-005, margin measurement types as siblings off private
bases. #59 DAT-004, schema adopts measurement's reference-object vocabulary and the cross-module
guard now executes in CI — this is the change that deleted `aruco_marker`, `ruler_scale` and
`checkerboard` from `ReferenceObjectType` and put `datasets/tests/test_schema_guards.py:89-112`
in the way of their return.

**Corpus provenance closed, 2026-09-06.** One commit ever added annotations, all eight from the
same batch. Nothing real was lost; DAT-005 does not change shape.

---

## Cut

- **`applies_to`.** Removed, not deprecated, by RUL-006 (#75). It was a required non-empty tuple
  of scope tokens on all 28 rules, enforced by a vocabulary test, copied into every persisted
  verdict snapshot, and read by nothing. 22 rules asserted `retail_packages` while the thing
  that decides retail-vs-not is `chapter_ii_scope`, and `medical_device_packages` restated a
  sector override that is executable code. Cost: none. It decided nothing.
- **SVG artwork ingest, out of MEA-005.** Cut from #43 and re-opened as MEA-010, because it
  means parsing untrusted XML with an entity-expansion-vulnerable stdlib parser. Cost: exact
  millimetre figures are available from PDF artwork only until MEA-010 lands.
- **Generated or AI-synthesised label images in `datasets/`.** Refused in Session 13. A
  synthetic PDP feeding a Rule 7 band lookup produces accuracy figures about generated images.
  Inpainting the coin out of a calibrated capture was also tried and refused — visible radial
  artefacts, and it destroys the declarations being annotated. Cost: the corpus needs real
  photographs and cannot be manufactured.

## Deferred — and what it costs

- **Sticker-overlay detection may yet be cut to conflicting-MRP only.** Its threshold is
  uncalibrated and its behaviour depends on where a neighbouring text line falls relative to the
  two comparison bands. If it fires on clean labels once the corpus exists, cut it. **Cost:** the
  demo scenario for physical tampering shrinks to price-conflict only, which is still real.
- **The PDP detector.** There is no PDP-trained model. Pointing `PDP_WEIGHTS_PATH` at stock
  `yolov8n.pt` is worse than leaving it unset — `detect_pdp` takes `boxes.conf.argmax()` of
  whatever it is given, so stock COCO weights return a confident wrong box whose area feeds the
  Rule 7 Table-I band lookup. This is a decision — train one, or use the documented
  largest-coherent-text-region fallback and say so — not a download. **Cost: the image path has
  still never run with real weights.** (#63 has since made empty detection refuse rather than
  return the whole image at confidence 0.0, which removes the other half of this hazard.)
- **The 50 mm calibration card.** Deferred to MEA-008 and may close as a finding rather than an
  implementation. **Cost:** the manufacturer self-check flow (F2) has no reference object.
- **UP042 conversion in `datasets/schema.py`.** **Cost:** the datasets CI job cannot gain a ruff
  step, so that directory is linted by nobody.
- **Rule 6(11) encoding.** Deliberately not in the rule store;
  `bck/tests/modules/rules/test_loader.py:124` asserts its absence. **Cost:** F18 — is a unit
  sale price declared, and on the correct unit basis for the net quantity — is unevaluated. The
  extraction side exists (`bck/app/modules/extraction/unit_sale_price.py`); the rule does not.
- **Persisting the Rule 3(c) officer flag and the PIP-003 category proposal.** Both need a
  column and a migration, both are `contracts`-owned. **Cost:** neither survives a page reload,
  so an officer cannot act on either after leaving the scan.
