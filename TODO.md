# TODO.md — end of Session 6, 2026-09-07

---

## Now

1. **PIP-004** — route a contested declaration to REVIEW_REQUIRED. CTR-006 landed
   `CompetingReadings` and `ExtractionResult.disagreements`; nothing reads them yet, so once
   EXT-007 populates the collection a contested obligation lands in **INSUFFICIENT_EVIDENCE**,
   which the constraints forbid — both readings were read perfectly well. Four edit points:
   (a) `EvidenceContext`, `bck/app/pipeline/rule_findings.py:60-93`, a field carrying the
   contested obligations; (b) `_one_declaration`, same file `:167-197`, a REVIEW_REQUIRED
   branch **above** the `if values:` test — its own branch, never sharing an expression with
   INSUFFICIENT_EVIDENCE or FAIL, and no set membership test; (c) `orchestrator.py:240`, the
   image path, fed from `extraction.disagreements`, including `field_providers` at `:256`
   which is `dict.fromkeys(declared, …)` and would otherwise omit a contested obligation that
   now carries a finding; (d) `orchestrator.py:295`, the catalogue path, passes empty — a
   listing supplies one value per obligation key.
   **Not optional polish.** `verdict.py:56-59` tests REVIEW_REQUIRED and INSUFFICIENT_EVIDENCE
   one at a time and both return `Verdict.REVIEW`, so the package verdict is the same either
   way. What PIP-004 buys is the correct *reason string* on the officer surface: without it
   the system tells an officer "the evidence needed could not be obtained" about a label it
   read perfectly, twice. **Merges before EXT-007** so the forbidden state never reaches main.
2. **DAT-005** — annotate the fifteen staged captures. The single highest-value item on the
   board; every accuracy figure in the PRD depends on it and none is currently defensible.
3. **Send the three review drafts** — MEA-006 to Yashashvi (unblocked by #58), EXT-006 to
   Sitanshu, EVD-005 to Shiva.

## Next

4. Add `datasets` as a required status check in the `main-protection` ruleset. It has now
   reported once, which is the precondition.
5. **Docs PR — the `rtk` gotcha.** CLAUDE.md and AGENTS.md document the unsafe purge form.
   Load-bearing for every falsification on this project.
6. **DAT-003, ownership only.** CODEOWNERS still assigns `datasets/` to someone off the
   project, and `measurement/README.md` names the wrong owner.
7. **PIP-003** — wire `propose_category` into the orchestrator as a proposal that can never
   write itself into the confirmed category.
8. Create TAM-002 and MEA-008 on the board. EXT-007 and PIP-004 are both on it now.

## Later

9. **TAM-002** once DAT-005 exists — wiring plus the false-positive rate on real labels.
10. **EVD-004 / EVD-006** — the report export takes mock shapes and needs a real
    `VerdictRecord`. Shiva's, and unblocked; he should be on it rather than idle.
11. The seven UP042 findings in `datasets/schema.py`. Converting a schema that serialises to
    JSON is its own change, and until it happens the datasets job cannot gain a ruff step.
12. The officer surface's presentation of 65 findings per scan. RUL-004 established this is a
    presentation problem, not a rule-store one.

## Bugs

- **`measure_margins` raises on a flush declaration on both paths.** Pre-existing on the
  artwork path; now also on the calibrated path since `MeasurementMarginCalibrated`
  constrains `confidence_interval` to `gt=0`. MEA-006 (#47) fixes it in `services.py`.
- **`max(0, dist_px)` swallows overlap.** Ink intruding into the Rule 8(1) free space reads as
  a margin of exactly zero — flush and overlapping become the same reading. In MEA-006's scope.
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
