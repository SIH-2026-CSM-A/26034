# TODO.md — 2026-09-07, after the Session 14 handoff

Session numbering is read from `session-log/abhiram.md`, not from here — the last
`## Session N` heading in that file is authoritative. RUL-007 was Session 18 there. "Session 14"
in this PR's branch name is the *chat's* numbering and is a different sequence; do not reconcile
them, read the file.

---

## After Session 27 (2026-09-08, real ward + geographic map) — read this first

Merged #136: the dashboard heatmap is now a real GHMC ward choropleth, and the ward is a
persisted, officer-selected field (not a hash). Deployed to the VM; `--backfill-wards` ran
over the 81 seeded scans; browser-verified at 390 and 1280 with the network throttled.

1. **`verify1` is a temporary officer on the VM `.env`** (state-tier Telangana), added so
   the dashboard could be driven for browser verification. Either remove it after the demo
   or keep it as the read-only demo login — but it is a real credential on a public tunnel,
   so decide on purpose.
2. **`GET /scans` caps at 50**, so the dashboard aggregates the 50 most recent scans, not
   all 81 seeded. The map still shows all three bands, but a real dashboard would page or
   aggregate server-side rather than shading a sample.
3. **Ward is not validated against a district.** It is a free location tag finer than the
   RBAC tiers; there is no ward→district table, so an officer could record a ward outside
   their district. The dashboard shades only known GHMC wards and counts the rest aside.
4. **Six GHMC wards (3, 4, 11, 13, 31, 113) are absent** from the upstream DataMeet file and
   do not render. If a complete 150-ward map is wanted, assemble the missing five (119 too,
   from the fresher Overpass pull) from OSM relations and rebuild `ghmcWards.ts`.

---

## After Session 26 (2026-09-08, deployment night) — read this first

The VM serves `main` through a cloudflared quick tunnel; the hostname changes on every
cloudflared restart, so read it from `journalctl -u cloudflared-quick` on `pccs-vm`.

1. **opencv resolves to 4.10 or 5.0 at random** — three distributions share one `cv2`
   directory and the last unpacked wins; `test_coin_oblique_synthetic_geometry` fails under
   4.10 with height 259.93. Seven CI reruns tonight. Pin the three to one version or drop two.
2. **Evaluate in a one-worker process pool.** Paddle holds the interpreter lock for up to
   21 s inside inference, so every request stalls with it. The route tests patch the
   pipeline in-process, which is why it is a thread today; a process pool needs a seam.
3. **Barcode recall.** Two of ten corpus photographs decode; the rest are small, curled or
   absent barcodes. A library is the upgrade, and a dependency to ask for.
4. **Complaint transitions** have no endpoint; the UI's transitions stay local.
5. **Named tunnel** for a stable hostname: needs a domain on Cloudflare.
6. **Rate limiting** on `/consumer/scans/image`: none today; a per-IP limit at nginx.

---

## Now

1. **#63 VIS-004 — the OCR suite is hollow, and it is the one ticket between this project and a
   demonstrated pipeline.** `bck/tests/modules/vision/test_ocr.py` at head `7bc6307` is
   twenty-seven lines: five `pass` bodies and a `test_placeholder_ocr` asserting `True`. Main
   has twelve real tests there. Three checks green. Exact items in `TICKETS.md`. **No image has
   ever passed through this pipeline and this is the ticket that changes that** — it has now
   burned more than a day and has gone backwards.
2. ~~**DAT-005** — annotate the captures.~~ **Merged as #77.** **Not** the fifteen `_staging/`
   files: those all carry a ₹10 coin, which is why the ticket was parked. Twelve new real
   captures landed — six SKUs, front and back, no reference object in any frame — annotated at
   `datasets/annotations/{food,cosmetics}/` with a twelve-record `datasets/manifest.json`. All
   twelve are `uncalibrated`, `reference_object.present` false, `pdp.is_measurable` false, every
   height field null, verdict `REVIEW`. `_staging/` is untouched and still unannotated; its
   provenance is unconfirmed and that is a separate decision.

   **Both `TestCommittedAnnotationsLoad` guards now execute, for the first time ever.**
   `datasets/tests/test_schema_guards.py:121` and `:128` each open with
   `if not files: pytest.skip("corpus is empty pending real captures (DAT-002)")`. From DAT-002
   until #77 they skipped every run, including every CI run since #60 put `datasets/` in the
   pipeline. Verified three ways. Locally with the twelve annotations present both pass;
   locally with `datasets/annotations/{food,cosmetics}/` removed both report
   `SKIPPED … corpus is empty pending real captures (DAT-002)`; and in CI the `datasets` job
   went from **26 passed / 2 skipped** on #76 and #66 to **28 passed / 0 skipped** on #77 — the
   two that stopped skipping are these two. They run in the `datasets` job, not `backend`:
   `bck/pyproject.toml:56` is `testpaths = ["tests"]`, so `cd bck && uv run pytest` has never
   collected `datasets/tests/` and the backend count says nothing about them.
   `test_every_annotation_validates` now validates all twelve against `LabelledSample`, and
   `test_no_annotation_claims_a_millimetre_height` now asserts on all twelve that an
   uncalibrated capture carries no `numeral_height_mm` and no `letter_height_mm`. **That second
   guard is what enforces Constraint 2 on ground truth**, and this is the first run in which it
   has had a sample to enforce it against.

   **It does not make an accuracy figure available.** Every capture is uncalibrated, so nothing
   in the set can support a Rule 7 finding. No accuracy figure is quoted anywhere and none
   should be until a calibrated set exists.

   **Superseded by DAT-008 (Session 24).** All twelve of those annotations described images
   that do not exist, and the four real JPEGs on disk were named by no record — thirteen
   guards passed over it. The twelve were deleted and four were written by hand from the
   photographs. The `cosmetics/` and `food/` directories were swapped, and the names also
   carried a net quantity the packs contradict, so there are now four SKUs at one image each:
   Parle-G Gluco Biscuits at 65 g and at 130 g, and two Himalaya face wash tubes at 150 ml.
   Still uncalibrated, still `REVIEW`, still no accuracy figure. Two open items came out of
   it: the cosmetics half is two EU/UK-market packs that were never placed on the Indian
   market, and none of the four is a field capture — all are catalogue images on seamless
   white. Both are recorded in `datasets/README.md` and in the DAT-008 PR body.
3. **EXT-009 — `MIXED` no longer marks the pair Rule 9(4) turns on.** #66 merged with this open.
   `bck/app/modules/extraction/binder.py:190` returns `MIXED` for any two of five scripts, so
   Tamil-plus-Bengali and Devanagari-plus-Latin are now the same value — and the second is the
   distinction EXT-006 pairs on and EXT-007 routes disagreements from. Narrow `MIXED` back to
   the statutory pair and give the general case its own member, or rename it and say in its
   docstring what it now means. Pin it with a test. **Open EXT-009; do not write a review into
   the `done` EXT-008 ticket.**
4. **MEA-011 / MEA-009 Part B** (Yashashvi) — replace the overlap refusal in `measure_margins`
   with `MeasurementMarginOverlapExact` / `MeasurementMarginOverlapCalibrated`. Part A (#73)
   landed the contract. Two things to know: the `dist_mm < 0` branch sits **above** the
   `is_artwork` split, so both shapes must be constructed there; and margins are still not wired
   into `pipeline/orchestrator.py` at all (it omits `measure_margins` pending EXT-004's
   declaration bounding box), so this changes what the function returns without changing any
   scan yet. **RUL-007 (#76, Session 18) landed the consuming shape:** `SideOverlap` on
   `FreeSpaceMeasurement`, so an overlap now has somewhere to go the moment this returns one.
   No adapter exists between them yet — see item 4a.

4a. **Wire Rule 8(1)'s proviso into the pipeline — a new ticket, blocked twice.** RUL-007 (#76)
   left `evaluate_rule8_free_space` correct and unreached. It needs (i) EXT-004's declaration
   bounding box, so `orchestrator.py` can call `measure_margins` at all, and (ii) MEA-011, so
   an overlap arrives as an overlap rather than a refusal. Two further things the writer needs
   to know. `context.measurements` is keyed one result per condition kind and `measure_margins`
   returns four, so `free_space` needs a shape that is not one `MeasurementResult`. And
   `measurement_findings.py`'s non-Table-I branch formats `f"{result.value} {result.unit}"` —
   an overlap type has no `.value`, deliberately, per the MEA-009 docstring. Unreachable today;
   an `AttributeError` on the first real overlap the day it is wired.

## Next

5. **Write the seven tickets below.** They are specified, not vague; each has a file, a defect
   and a consequence. Until they are on the board they are invisible.
6. **Create MEA-010, MEA-011, EVD-007 and EXT-009 on the board.** MEA-010 and MEA-011 are
   unblocked and Yashashvi is idle; EVD-007 is Shiva's and followed #46 onto `main`; EXT-009 is
   Sitanshu's and followed #66. FNT-004 landed as #78 — do not create it. **Three tickets in one
   afternoon have merged with one item still open. That is the pattern to watch, not any one of
   them: the follow-up ticket has to be created in the same breath as the merge, or the item is
   lost the moment the ticket goes `done`.**
7. **Persist the Rule 3(c) officer confirmation, or decide not to.** RUL-005 passes it as a
   plain `bool` down to `EvidenceContext` and deliberately does not store it: that would need a
   `contracts` enum, a `scans` column, a migration and a `ScanSummary` field, and `contracts/`
   is single-owner. It is auditable today only through the `reason` text on the findings it
   produced. Decide whether an officer needs to filter scans by it.
8. **Persist the category proposal and the display category, or decide not to.** PIP-003 (#74)
   left the proposal present on the POST response and `None` on a GET re-read, because the
   `scans` row has no column for it. PIP-006 (#112) puts `display_category` in exactly the same
   position, for exactly the same reason — **two fields now, one migration.** A column plus its
   migration is a ticket of its own, and it is the thing that decides whether an officer can
   act on either after reloading the page.

   Note what this does *not* block: the officer dashboard's category filter already works off
   `product_category` (`fnt/src/officer/dashboard/index.tsx:172`), the officer's confirmed
   legal category. Persisting these two would add a *presentation* axis beside it, not repair
   a broken filter. Putting `display_category` on `ScanSummary` without a column was considered
   in PIP-006 and refused: always-`None` reads as working.

   Separately: the catalogue path proposes and classifies nothing, because both
   `propose_category` and `classify_display_category` take an `ExtractionResult` that a listing
   never builds. Decide whether a listing should.
9. **Resolve `/fnt/` ownership.** Three sources give three answers — `.github/CODEOWNERS:29`
   assigns all of `/fnt/` to `@vineethsimha2151`; `HANDOFF.md` says the officer surface stays
   with Abhiram because it is on the demo path; `AGENTS.md:120` says Abhiram *"(Vineeth's
   module, he is unavailable)"* and he is demonstrably available, having shipped #72. This was
   deliberately **not** decided by the Session 14 CODEOWNERS edit. Decide it on purpose.

## Later

10. **TAM-002 — unblocked by #77, and it should start.** Wiring plus the false-positive rate on
    real labels; the first ticket on the board that can run against annotated images. One thing
    to carry from DAT-005: **all twelve captures are uncalibrated**, so a false-positive rate
    measured against them is a real number, but nothing in the set can support a Rule 7 finding.
    Do not let a tamper figure be read as an accuracy figure for the measurement path.
11. **EVD-004 / EVD-006 / EVD-007** — the report export takes mock shapes and needs a real
    `VerdictRecord`; EVD-007 single-sources the evidence storage key. All three are Shiva's and
    all three are unblocked now that #46 has merged.
12. **MEA-007, MEA-008.** MEA-007 needs a rebase — `services.py` changed under it in #43.
    MEA-008 may legitimately close as a finding that the 50 mm card does not exist.
13. **The seven UP042 findings in `datasets/schema.py`.** Converting a schema that serialises to
    JSON is its own change, and until it happens the datasets job cannot gain a ruff step.
14. **The officer surface's presentation of 65 findings per scan.** RUL-004 established this is
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

**DAT-008 picked the convention, not the schema change.** A declaration not in the frame is
`declared: false` with `expected_field_state: INSUFFICIENT_EVIDENCE`, and `datasets/README.md`
now says the *state* is what separates "not shown here" from "absent from the pack" — never
`declared` on its own, because absence from a pack would have to be `FAIL` and no single panel
establishes it. All four DAT-008 annotations follow that. This does **not** close the item: the
harness still cannot tell the two apart from `declared` alone, and the enum question is
untouched. It only means the corpus is now annotated consistently while the decision is made.

**2-4. `ingest_images.py` — RESOLVED in DAT-008 by deleting the script.** All three items
(the `samples`/`records` key mismatch, the Google Drive ID the offline-demo design forbids,
and the silent `.png` skip) were defects in one sixty-line file that had never produced a
correct manifest and could destroy one. It was deleted rather than fixed: nothing imported
it, and four records maintained by hand do not need a writer. `datasets/manifest.json` is
now written by hand and `datasets/README.md` says so under "Building the manifest".

The assertion item 2 asked for — the one that makes an empty manifest fail — is DAT-007's
`_records()` and it is in. Four guards now run in
`bck/tests/contracts/test_manifest_integrity.py`, including
`test_the_manifest_hash_is_the_hash_of_the_image_on_disk`, which compares the recorded hash
to the file's bytes rather than to the other document. Forging manifest and annotation to
agree with each other still fails it.

**New, from DAT-008 — the corpus can only be verified where the images are.** `datasets/raw/`
is gitignored, so on a fresh clone two of those four guards fail. DAT-008 force-added its four
JPEGs (524,541 bytes) over the ignore so CI can hash them; `raw/` stays ignored, so a new
capture still has to be `git add -f`ed deliberately. **Anyone landing DAT-007 on its own
should know its guard is red on a tree without images**, and that `ruff format --check` exits
1 on `test_manifest_integrity.py:51` as that branch stands — which under this repo's CI
ordering means nothing on it has been verified by Lint, Import boundaries or Tests.

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

- **`test_remap_curvature_performance_at_realistic_resolution` is a wall-clock assertion and it
  flakes under load.** `bck/tests/modules/vision/test_preprocess.py:147` asserts
  `elapsed < 0.5` for a 3000x4000 `remap_curvature`. In isolation it takes 0.16 s, three runs
  out of three. During a full suite run on a loaded machine it measured 1.26 s and failed the
  build. **Why it matters:** a timing assertion turns an unrelated background process into a red
  CI run, and the next person to see it red will assume their diff caused it. The intent — catch
  a per-pixel Python loop, which would take 10 s+ — is served just as well by a budget an order
  of magnitude above the vectorised time and well below the naive one. Raise it, or assert
  against a shape-scaling ratio instead of a clock.
- **The officer screens have never been watched against a running backend.** #72 and #78 moved
  `ReviewQueue`, `VerdictDetail` and the new `ScanSubmission` onto the generated client, and
  `main.py` does not boot without model weights. Verify at two widths in a real browser before
  any demo.

**Closed since the last revision of this file:**

- ~~`measure_margins` raises on a flush declaration on both paths.~~ Fixed by MEA-006 (#47).
- ~~An overlap is reported as a refusal.~~ Part A landed the types (#73); Part B returns them.
- ~~`FreeSpaceMeasurement` cannot carry an overlap or a flush margin~~ —
  `modules/rules/results.py:82` typed all four clearances as `PositiveDecimal`. Fixed by
  RUL-007 (#76, merged).
- ~~`purge_evidence` writes an immutable chain entry attesting a destruction that never
  happened.~~ Fixed by EVD-005 (#46, merged): `retention.py:106` aborts on a storage miss. The
  key derivation still differs from the write path — that is EVD-007, and it is a different
  defect.

---

## Blocked

- **`measure_margins` orchestrator wiring** (item 4a) on EXT-004's declaration bounding box
  *and* on MEA-011. Blocked twice.
- **PIP-002** on EXT-004.

**No longer blocked** — these came off the list and the reason is recorded so nobody re-adds
them: #43 MEA-005 (`pdfplumber` approved, merged), #47 MEA-006 (#58 merged), EXT-007 (#65 and
#67 landed the contract and the pipeline; merged as #71), PIP-004 (merged), MEA-010 and MEA-011
(unblocked by #43), FNT-004 (merged as #78), EVD-005 (merged as #46), RUL-007 (merged as #76),
EVD-006 and EVD-007 (Shiva is free), **TAM-002 — unblocked, DAT-005 merged as #77** — and
DAT-005 itself, which was blocked on a phone and six real packages, not on code.

---

## Done — with dates

**2026-09-07, later** — #76 RUL-007 (15:02) · #46 EVD-005 (15:06) · #78 FNT-004 (15:11) ·
#66 EXT-008 · **#77 DAT-005**. Five merges while this file was being rewritten, three of them
inside nine minutes.

**#77 is the one that changes what this project can claim.** The corpus is no longer zero,
`TestCommittedAnnotationsLoad` stops skipping, and TAM-002 becomes runnable — the first ticket
on this board that can be measured against real labels rather than synthetic spans.

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
  `yolov8n.pt` is worse than leaving it unset — `detect_pdp` selects `boxes.conf.argmax()`, the
  highest-confidence box — of whatever it is given, so stock COCO weights still return a
  confident wrong box (a COCO class, not a panel) whose area feeds the
  Rule 7 Table-I band lookup. This is a decision — train one, or use the documented
  largest-coherent-text-region fallback and say so — not a download. **Cost: the image path has
  still never run with real weights.** (#63 has since made empty detection refuse rather than
  return the whole image at confidence 0.0, which removes the other half of this hazard.)
- **The 50 mm calibration card.** Deferred to MEA-008 and may close as a finding rather than an
  implementation. **Cost:** the manufacturer self-check flow (F2) has no reference object.
- **`test_coin_oblique_synthetic_geometry` is flaky on CI** (`measurement/`, Yashashvi's).
  Same commit, two CI runs: green (1003 passed), then
  `Height 259.93 deviates from 200.0 by >5%` on a tree differing only in one markdown file,
  then green again on a bare re-run. Passes 5/5 locally. Found during PIP-006 (#112) and
  raised there; not diagnosed. There is no RNG in `measurement/services.py` — the path is
  `Canny` → `findContours` → `max(key=contourArea)` → `fitEllipse`. **Cost:** a red tick on
  an unrelated PR that costs someone a bisect, and a measurement guard that cannot be trusted
  to mean what it says until it is deterministic.
- **`test_independence_contract_lists_the_eight_modules` pins nine modules**
  (`bck/tests/test_import_boundaries.py:67`). #101 renamed it from seven to eight; #104 added
  `complaints` to the list without renaming again. **Cost:** cosmetic today — a name that
  miscounts what it pins is a name the next person distrusts.
- **UP042 conversion in `datasets/schema.py`.** **Cost:** the datasets CI job cannot gain a ruff
  step, so that directory is linted by nobody.
- **Rule 6(11) encoding.** Deliberately not in the rule store;
  `bck/tests/modules/rules/test_loader.py:124` asserts its absence. **Cost:** F18 — is a unit
  sale price declared, and on the correct unit basis for the net quantity — is unevaluated. The
  extraction side exists (`bck/app/modules/extraction/unit_sale_price.py`); the rule does not.
- **Persisting the Rule 3(c) officer flag, the PIP-003 category proposal and the PIP-006 display
  category.** All three need a column and a migration, all three are `contracts`-owned.
  **Cost:** none of them survives a page reload, so an officer cannot act on any after leaving
  the scan. Three fields, one migration — worth doing as one ticket rather than three.

- **FNT-verdict-detail** — Antigravity. Removed the fabricated geometry overlay from the VerdictDetail and CapturePlate components, since no geometry data is exposed by the API and compliance rules forbid fake measurements. PR opened.
