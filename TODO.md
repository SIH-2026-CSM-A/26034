# TODO.md — end of Session 19, 2026-09-07

---

## Now

1. **EXT-007** (Sitanshu) — populate `ExtractionResult.disagreements` from the non-pairing
   branch at `binder.py:604`. **Now unblocked on both sides:** CTR-006 (#65) landed the
   contract and PIP-004 (Session 12) landed the pipeline, so a contested obligation already
   routes to REVIEW_REQUIRED the moment the collection is non-empty. **Move
   `_are_spans_spatially_adjacent` (607) above the value check (604)** — as ordered, the
   branch cannot tell "two scripts disagreeing about one declaration" from "two unrelated
   declarations elsewhere on the panel", and EXT-007 would record disagreements that are not
   disagreements. `tests/modules/extraction/test_bilingual_declarations.py:185` pins today's
   two-record behaviour and is the test EXT-007 changes.
2. ~~**DAT-005** — annotate the captures.~~ **Done, Session 19.** Not the fifteen staged
   files: those all carry a ₹10 coin, which is why the ticket was parked. Twelve new real
   captures landed — six SKUs, front and back, no reference object in any frame — and are
   annotated at `datasets/annotations/{food,cosmetics}/` with a twelve-record
   `datasets/manifest.json`. All twelve are `uncalibrated`, `reference_object.present` false,
   `pdp.is_measurable` false, every height field null, verdict `REVIEW`. `_staging/` untouched
   and still unannotated — its provenance is unconfirmed and that is a separate decision.
   **TAM-002 is unblocked.**
3. **MEA-011 / MEA-009 Part B** (Yashashvi) — replace the overlap refusal in `measure_margins` with
   `MeasurementMarginOverlapExact` / `MeasurementMarginOverlapCalibrated`. Part A landed the
   contract. Two things to know: the `dist_mm < 0` branch sits **above** the `is_artwork`
   split, so both shapes must be constructed there; and margins are still not wired into
   `pipeline/orchestrator.py` at all (it omits `measure_margins` pending EXT-004's declaration
   bounding box), so this changes what the function returns without changing any scan yet.
   **RUL-007 (Session 18) landed the consuming shape:** `SideOverlap` on
   `FreeSpaceMeasurement`, so an overlap now has somewhere to go the moment this returns one.
   No adapter exists between them yet — see item 4a.
4. **Send the three review drafts** — MEA-006 to Yashashvi (unblocked by #58), EXT-006 to
   Sitanshu, EVD-005 to Shiva.

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

5. Add `datasets` as a required status check in the `main-protection` ruleset. It has now
   reported once, which is the precondition.
6. **Correct the test-count gotcha in CLAUDE.md.** It says backend reports 707 passed / 32
   skipped locally and 737 / 2 on the runner. Both are now stale by five merges. Measured on
   `origin/main`: **739 / 32** at a95e8fb and **741 / 32** at d1114af in Session 13, and
   **772 / 32** at 2817c6b in Session 14. Every
   session that reads the documented figure as a baseline starts from a wrong number, and
   #68 nearly reported a delta of +29 against a baseline that had moved underneath it. Fix
   the local figure, re-derive the runner figure alongside it, and say in the gotcha that a
   baseline is to be measured rather than quoted — the number will go stale again.
7. **Persist the Rule 3(c) officer confirmation, or decide not to.** RUL-005 passes it as a
   plain `bool` down to `EvidenceContext` and deliberately does not store it: that would need
   a `contracts` enum, a `scans` column, a migration and a `ScanSummary` field, and
   `contracts/` is single-owner. It is auditable today only through the `reason` text on the
   findings it produced. Decide whether an officer needs to filter scans by it.
8. **Docs PR — the `rtk` gotcha.** CLAUDE.md and AGENTS.md document the unsafe purge form.
   Load-bearing for every falsification on this project. **Fold in two more corrections:**
   CLAUDE.md's test baseline says 707/32 and `origin/main` @ `acc0815` measures **780/32** —
   six merges stale; and `ARCHITECTURE.md:247` and `:296` still say `propose_category` has
   no caller, which PIP-003 (Session 15) fixed.
9. **DAT-003, ownership only.** CODEOWNERS still assigns `datasets/` to someone off the
   project, and `measurement/README.md` names the wrong owner.
10. **PIP-003 landed (Session 15).** `propose_category` has a caller, an export and a test
   that goes red the moment a proposal routes anything — confirming `food` rather than
   proposing it takes the gate-settled count from 30 to 0, which is what the test pins. Two
   follow-ups it deliberately did not take: **(a)** the proposal is **not persisted** —
   present on the POST response and `None` on a GET re-read, because the `scans` row has no
   column for it. A column plus its migration is a ticket of its own, and it is the thing
   that decides whether an officer can act on a proposal after reloading the page.
   **(b)** the catalogue path proposes nothing; `propose_category` takes an
   `ExtractionResult` that a listing never builds. Decide whether a listing should propose.
11. Create TAM-002 and MEA-008 on the board. EXT-007 and PIP-004 are both on it now.

## Later

12. **TAM-002** once DAT-005 exists — wiring plus the false-positive rate on real labels.
13. **EVD-004 / EVD-006** — the report export takes mock shapes and needs a real
    `VerdictRecord`. Shiva's, and unblocked; he should be on it rather than idle.
14. The seven UP042 findings in `datasets/schema.py`. Converting a schema that serialises to
    JSON is its own change, and until it happens the datasets job cannot gain a ruff step.
15. The officer surface's presentation of 65 findings per scan. RUL-004 established this is a
    presentation problem, not a rule-store one.

## Bugs

- **`measure_margins` raises on a flush declaration on both paths.** Pre-existing on the
  artwork path; now also on the calibrated path since `MeasurementMarginCalibrated`
  constrains `confidence_interval` to `gt=0`. MEA-006 (#47) fixes it in `services.py`.
- **An overlap is still reported as a refusal.** MEA-006 (#47) stopped `max(0, dist_px)`
  collapsing overlap into a flush margin, but replaced it with
  `MeasurementRefusal(reason="Margin overlaps active ink region.")` — which
  `pipeline/measurement_findings.py:37` maps to INSUFFICIENT_EVIDENCE. So ink intruding into
  the Rule 8(1) free space now reads as "we could not measure it" rather than as the finding.
  MEA-009 Part A landed the two outcome types; **Part B (Yashashvi) returns them.**
- **`FreeSpaceMeasurement` cannot carry an overlap, or a flush margin.**
  `modules/rules/results.py:82` types all four clearances as `PositiveDecimal`, so
  `evaluate_rule8_free_space` rejects `0.0` as well as any intrusion. Pre-existing, surfaced by
  MEA-009; needs its own ticket in `modules/rules/`.
- **Port-shadowing.** `POSTGRES_PORT` in the repo-root `.env`, `DATABASE_URL` in `bck/.env`,
  nothing linking them. Setting one without the other connects to the wrong server silently.
- **`rtk` refuses single-line `find … -exec`** and exits 1. `find … ; pytest` on one line
  skips the purge and runs on stale bytecode. Use `/usr/bin/find` and assert the directory
  count.
- **`rtk` refuses `gh run view --job … --log`.** Use `gh api repos/<r>/actions/jobs/<id>/logs`.
- **`datasets/` is not ruff-clean** under `bck`'s config: seven UP042 plus one format diff.
- **`test_manifest_integrity.py` is unfalsifiable, and it guards the corpus.** Raised in
  Session 19, three defects that compound. `bck/tests/contracts/test_manifest_integrity.py:16`
  and `:41` both iterate `manifest.get("records", [])`, but a manifest produced by
  `datasets/ingest_images.py:47-52` has a **`samples`** key — so both tests loop over an empty
  list and pass green against any manifest at all. The seventh unfalsifiable test on this
  project and the first guarding the corpus. DAT-005's manifest uses `records`, so the two
  tests now assert something for the first time; the key mismatch in `ingest_images.py` is
  unfixed and will silently re-vacuum them the moment anyone regenerates the manifest with it.
  Needs a ticket: fix `ingest_images.py` to emit `records`, or fix the tests to fail on an
  empty manifest, or both.
- **`ingest_images.py` cannot do what its README says.** `sync_manifest` raises without a
  Google Drive folder ID (`:18-19`), while `datasets/README.md:72` says the manifest is built
  by walking `datasets/raw/` and is deliberately not synced from Drive — "the demo has to
  survive the venue network failing". Same ticket as above.
- **`ingest_images.py` globs `*.jpg` only** — `RAW_DIR.glob("**/*.[jJ][pP][gG]")` (`:24`) — so
  any PNG in the tree is invisible to it. Twelve of the fifteen `_staging/` files are PNG.
  Same ticket.
- **`datasets/README.md` is stale as of Session 19.** Its status section still says the corpus
  is empty and "Nothing in this directory may be treated as ground truth until real captures
  land." Twelve annotations now exist. Its `declared: false` definition at `:66-68` also
  contradicts what the schema can express — see the next item. Docs PR.
- **`declared` conflates a pack fact with an image fact.** Raised in Session 19 and decided
  with Abhiram: `declared` is scoped to the photographed face, so `declared: false` now means
  either "absent from the pack" or "present but not in frame". `expected_field_state`
  distinguishes them (`INSUFFICIENT_EVIDENCE` versus the rest); the bool alone does not, and
  `datasets/README.md:66-68` states the opposite intent. Needs a `NOT_IN_FRAME` third state or
  a `visible_in_image` bool — a `datasets/schema.py` change, so its own ticket. The affected
  entries are listed in `session-log/abhiram.md`, Session 19.

## Blocked

- **#46 EVD-005** on CORE-003. Shiva has EVD-006 available and should not be idle.
- **#47 MEA-006** — no longer blocked; #58 merged. Needs the rebase.
- **EXT-007** — no longer blocked; #56 merged and CTR-006 landed the contract. Sequenced
  after PIP-004. One correction for it: at `binder.py:604` the value check runs *before*
  `_are_spans_spatially_adjacent` at 607, so as ordered the branch cannot tell two scripts
  disagreeing about one declaration from two unrelated declarations elsewhere on the panel.
  Move the adjacency check above the value check first.
- ~~**TAM-002** on DAT-005.~~ **Unblocked, Session 19** — twelve annotated captures exist.
  Read the note under item 2: all twelve are uncalibrated, so a false-positive rate measured
  against them is a real number, but nothing in the set can support a Rule 7 finding.
- ~~**#43 MEA-005** on a decision about the `pdfplumber` dependency.~~ Merged as `2f915f4`.
  It adds `pdfplumber` and `pdfminer-six`; **run `uv sync` before measuring any baseline**,
  or you are measuring against a stale venv.
- **PIP-002** on EXT-004.

## Done — Session 6, 2026-09-07

- **#60 CI-004** — `datasets/` runs in CI for the first time. 27 tests that had never
  executed once now do. Repo-hygiene step gates tracked filenames.
- **#55 TAM-001** — tamper detection, two review rounds. Merged with uncalibrated thresholds
  and no caller, deliberately and on the record.
- **#58 CTR-005** — margin measurement types as siblings off private bases.
- **#59 DAT-004** — schema adopts measurement's reference-object vocabulary; cross-module
  guard now executes in CI.
- Corpus provenance closed: one commit ever added annotations, all eight from the same batch.
  Nothing real was lost; DAT-005 does not change shape.

## Cut / deferred, and what it costs

- **Sticker-overlay detection may yet be cut to conflicting-MRP only.** Its threshold is
  uncalibrated and its behaviour depends on where a neighbouring text line falls relative to
  the two comparison bands. If it fires on clean labels once the corpus exists, cut it. Cost:
  demo scenario for physical tampering shrinks to price-conflict only, which is still real.
- **PDP detector.** There is no PDP-trained model. Pointing `PDP_WEIGHTS_PATH` at stock
  `yolov8n.pt` is worse than leaving it unset — stock COCO weights return a confident wrong
  box that feeds the Rule 7 Table-I band lookup. Empty detection returns the whole image at
  confidence 0.0, overestimating PDP area and biasing toward POTENTIAL VIOLATION. This is a
  decision — train one, or use the documented largest-coherent-text-region fallback and say so
  — not a download. **Cost: the image path has still never run with real weights.**
- **50 mm calibration card.** Deferred to MEA-008 and may close as a finding rather than an
  implementation. Cost: the manufacturer self-check flow (F2) has no reference object.
- **UP042 conversion.** Cost: the datasets CI job cannot lint.
