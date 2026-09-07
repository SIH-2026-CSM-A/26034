# TODO.md — end of Session 14, 2026-09-07

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
2. **DAT-005** — annotate the fifteen staged captures. The single highest-value item on the
   board; every accuracy figure in the PRD depends on it and none is currently defensible.
3. **MEA-009 Part B** (Yashashvi) — replace the overlap refusal in `measure_margins` with
   `MeasurementMarginOverlapExact` / `MeasurementMarginOverlapCalibrated`. Part A landed the
   contract. Two things to know: the `dist_mm < 0` branch sits **above** the `is_artwork`
   split, so both shapes must be constructed there; and margins are still not wired into
   `pipeline/orchestrator.py` at all (it omits `measure_margins` pending EXT-004's declaration
   bounding box), so this changes what the function returns without changing any scan yet.
4. **Send the three review drafts** — MEA-006 to Yashashvi (unblocked by #58), EXT-006 to
   Sitanshu, EVD-005 to Shiva.

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
   Load-bearing for every falsification on this project.
9. **DAT-003, ownership only.** CODEOWNERS still assigns `datasets/` to someone off the
   project, and `measurement/README.md` names the wrong owner.
10. **PIP-003** — wire `propose_category` into the orchestrator as a proposal that can never
   write itself into the confirmed category.
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

## Blocked

- **#46 EVD-005** on CORE-003. Shiva has EVD-006 available and should not be idle.
- **#47 MEA-006** — no longer blocked; #58 merged. Needs the rebase.
- **EXT-007** — no longer blocked; #56 merged and CTR-006 landed the contract. Sequenced
  after PIP-004. One correction for it: at `binder.py:604` the value check runs *before*
  `_are_spans_spatially_adjacent` at 607, so as ordered the branch cannot tell two scripts
  disagreeing about one declaration from two unrelated declarations elsewhere on the panel.
  Move the adjacency check above the value check first.
- **TAM-002** on DAT-005.
- **#43 MEA-005** on a decision about the `pdfplumber` dependency.
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
