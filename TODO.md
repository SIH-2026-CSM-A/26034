# TODO.md — 26034

Read at session start. Updated at session end.
Tickets live in ClickUp, list `26034 Build`. This file is the shape of the work, not the
assignment record. Board state and per-PR remaining items are in `TICKETS.md`.

Last updated 2026-09-06, end of session 5, by Claude Chat.

---

## Now

- [ ] **DAT-005 — annotate the six real captures.** Fifteen images are staged at
      `~/26034-dat/datasets/raw/_staging/` (gitignored). Six SKUs, each with a calibrated
      angle carrying a ₹10 coin, an uncalibrated angle, three with a third angle. The corpus
      is otherwise **empty** — DAT-002 deleted four fabricated annotations. This is the
      single highest-value piece of work on the board: nothing about vision, measurement or
      tamper can be evaluated until it exists, and every PRD accuracy figure depends on it.
      **Check Rule 26 against the corpus before writing ground truth for the 2 g Maggi
      sachet** — packages of 10 g or less are exempt, so most Rule 6(1) obligations may be
      `NOT_APPLICABLE` rather than required, and a ground truth that marks them FAIL trains
      the eval set to punish correct behaviour.
- [ ] **Review #46 EVD-005.** Head moved to `e510224` after the session-5 review; re-pull
      before reading. The false-attestation defect is the blocker.
- [ ] **Land the `asset_type` column and its migration** (Abhiram). Split out of #46:
      `alembic/` is single-owner and a migration cannot be edited after merge. #46 rebases
      onto it. Shiva does not write this.
- [ ] **#47 MEA-006, then #43 MEA-005** (Yashashvi). Both touch `services.py`, which #42
      rewrote. #47 first.
- [ ] **CI-004 — `datasets/` has never been executed by CI**, and `datasets/eval/test_harness.py`
      cannot even be collected (`ModuleNotFoundError: No module named 'datasets'`). The
      schema guards added in DAT-002 are equally invisible. Separate job, **no `paths:`
      filter**, and do not make it required until it has reported once. Also carries a
      repo-hygiene step: #42 landed a file named from a shell quoting accident, containing a
      `"`, which cannot be checked out on Windows and passed both CI jobs.
- [ ] **PIP-003 — wire the category proposal.** `propose_category` merged in #52 with no
      caller and is not exported from `extraction/__init__.py`. Same shape as
      `EvidenceEntryRow` shipping with no writer. **A proposal must never write itself into
      `Scan.product_category`** — that is an officer's act, and letting it through would
      silently unmask the six tests the sector gate masks.
- [ ] **DAT-004 — reference-object vocabulary.** `datasets/schema.py` says `coin_inr_10` /
      `credit_card_id1` / `ean_13`; `measurement/services.py` takes `coin_10` / `id_card` /
      `ean_13`. Nothing can hand an annotation to measurement. Decision made: measurement's
      names win, schema adopts them, plus a cross-module test so they cannot drift again.
- [ ] **DAT-003 — ownership corrections and the manifest.** CODEOWNERS and AGENTS.md still
      name Aashritha on `datasets/`. `ingest_images.py` requires a Google Drive folder ID and
      raises without one, which is why `manifest.json` is `{"records": []}` — rebuild it to
      walk `datasets/raw/`. The demo has to survive the venue network failing.
- [ ] **Ask Sitanshu where EXT-006 stands.** His session log claimed it built, including a
      new `evidence.py` defining a second `ExtractionResult`; that claim vanished from #52
      and the branch `ext-006-bilingual-declarations` is pushed with no PR. **A second
      `ExtractionResult` must not be created** — `binder.py` owns it.
- [ ] **Ask Akshaya about TAM-001.** Branch `feat/tam-001-dual-mrp-sticker-detection` is
      pushed with no PR. `tamper/` was an empty module at last check.

## Next

- [ ] **MEA-007 — ellipse-fit coin homography** (Yashashvi, low). #42 settled the coin path
      honestly: scale only, `h_matrix = None`, because a circle under perspective has no
      corner correspondences. The gap it leaves is real — a coin-calibrated measurement on an
      oblique capture is not perspective-corrected and the 5% prior does not cover it.
- [ ] **EVD-006** — export takes a real `VerdictRecord`; EVD-004's tests use mock shapes.
- [ ] **Wire `measure_margins` into the orchestrator.** #47 fixes the contract; `pipeline/`
      still never calls it, so Rule 8 free-space evaluation stays dark after it merges.
- [ ] **Frontend `npm audit` gate.** 2 moderate vulnerabilities, deprecated `glob@11.1.0`.
- [ ] **Seven `UP042` findings in `datasets/schema.py`** (`str, Enum` → `StrEnum`).
      Pre-existing; converting a schema that serialises to JSON is its own change.
- [ ] **MinIO and Redis in `docker-compose.yml`.** Only Postgres is in it, so
      `tests/modules/evidence/test_minio_storage.py` skips on every machine including CI.
- [ ] **A unique constraint on `reviews.supersedes_id`.** Nothing stops two rows sharing one,
      which forks the correction chain. **Do it before any review data exists.**
- [ ] Drop `ix_reviews_scan_id` — `ix_reviews_scan_id_created_at` leads with the same column.
- [ ] `core/` — a users table to replace the `OFFICERS` env list.
- [ ] `fnt/` — admin surface (Rohan's, never started), and a generated client from the
      OpenAPI schema. The frontend still runs entirely on fixtures.
- [ ] `pipeline/` — offline sync and re-validation on reconnect (F51's second half).

## Later

- [ ] Copilot (F39) — hybrid retrieval, rerank, citations bound at generation time.
- [ ] Admin console — rule-set draft → review → publish with diff view.
- [ ] Dashboard aggregates (F32). `rule_id` was promoted to a typed column specifically so
      violation-rate-by-clause is queryable when this is built.
- [ ] Pan masala (G.S.R. 881(E)) not encoded.

## Bugs

- [ ] **The image path has never run with real model weights. P0, and it is on the demo
      path.** No YOLO or PaddleOCR weights on the dev machine; `main.py` refuses to boot
      without four paths that do not exist locally. `bck/.env` **does not exist at all**.
      The four settings are `PDP_WEIGHTS_PATH` (a file), `OCR_DET_MODEL_DIR`,
      `OCR_REC_MODEL_DIR`, `TESSERACT_TESSDATA_DIR` (directories); blank is treated as unset
      and each is checked for existence at boot.
      **Two blockers found in session 5, one now fixed.** `ocr.py` on `main` was written
      against the PaddleOCR 2.x API while 3.7.0 is installed — it could not construct a
      `PaddleOCR` at all. #45 fixed that. Still open: **there is no PDP-trained YOLO model.**
      `detect_pdp` takes `boxes.conf.argmax()` of whatever weights it is given, so stock
      `yolov8n.pt` returns a COCO box as the principal display panel and its area feeds the
      Rule 7 band lookup. Its empty-detection branch returns the **whole image** with
      `confidence 0.0`, which overestimates area and biases toward POTENTIAL VIOLATION.
      **Do not point `PDP_WEIGHTS_PATH` at stock weights to make boot succeed.** Decide
      deliberately: train a detector, or use the documented fallback (largest coherent
      printed-text region) and say so.
      Also: `tesseract` is not installed on the dev machine at all.
- [ ] **`measure_margins` raises on a zero margin** — #47 fixes the contract; orchestrator
      wiring is a second ticket.
- [ ] **`tesseract_tessdata_dir` is checked at boot but never called.**
- [ ] **No `relationship()` anywhere in `core/models.py`** — the explicit parent flush in
      `pipeline/repository.add_verdict` is the pattern to copy. Adding relationships trades
      it for `MissingGreenlet` on an async mapper.
- [ ] **65 findings per scan.** RUL-004 narrowed `R9-1-MANNER` to retail sale price and net
      quantity, but the corpus audit confirmed Rule 7(2) and 7(3) **genuinely govern every
      declaration** — so the rule store has no honest way to remove those pairings. **The
      remaining reduction is a presentation problem for the officer surface, not a rule-store
      problem.** Do not raise another rule-store ticket for it.
- [ ] `test_append_only_enforcement` (evidence) resolves a relative path against the cwd and
      passes vacuously if it scans zero files.
- [ ] `test_annotation_image_sha256_matches_manifest` iterates `manifest.get("records", [])`
      — with an empty manifest it passes vacuously. DAT-005 owns the fix with the rebuild.
- [ ] `gh pr checks --watch` reports phantom pending checks. Read `statusCheckRollup`, and
      note that `gh pr checks` returns a **stale rollup** for ~90s after a push.

## Blocked / unresolved

- [ ] **Pilot state not chosen.** `ROLE_DESIGNATIONS` will change.
- [ ] **DoCA FAQ of 11.11.2025 not captured.** Two EXT-001 claims are [SOURCED], not [VERIFIED].
- [ ] **No consolidated LMPC text covering Nov 2021 – Oct 2023.**
- [ ] **OpenAI query-rewriting scope unconfirmed.** Do not build against it.
- [ ] **The offline path (F51, P0) does not exist.** Neither half.
- [ ] **ClickUp connector rate-limited 2026-09-06 19:30, 600 minutes.** Hand Abhiram
      pasteable ticket blocks until it clears. **DAT-002 and CTR-004 still need moving to
      `done` by hand.**

## Done — session 5, 2026-09-06

- [x] **CTR-004** `RuleStatus` unified with contracts; `Verdict` and `Severity` corrected to
      `POTENTIAL_VIOLATION`; 17 yaml lines (not 18) — #54
- [x] **DAT-002** fabricated corpus removed, ground-truth schema hardened — #53
- [x] **EXT-005** deterministic category proposal — #52
- [x] **RUL-004** `governs_declarations` on the rule store — #51
- [x] **VIS-003** PaddleOCR 3.x parser, strict confidence, arbitration — #45
- [x] **MEA-004** homography before scale, per-method confidence priors — #42

## Cut

- **Automated Claude review on every PR** · **Two repositories** · **Custom DSL for rules** ·
  **Separate vector database** · **Supabase** · **Cloud-primary OCR** · **A multi-piece /
  Rule 9(3) interaction** · **G.S.R. 722(E) para 4's Rule 6(11) exemption** · **PyMuPDF**
  (AGPL-3.0) · **`BoundDeclaration` / `DeclarationRole` / `contracts/binding.py`**
- **The `coin_10` bounding-box homography** — #42 removed it. A circle under perspective is
  an ellipse with no corner correspondences; any matrix from its bounding box maps arbitrary
  points. Do not rebuild it; MEA-007 is the correct approach.
- **`coin_inr_1` / `coin_inr_2` / `coin_inr_5` in the dataset schema** — dimensions written
  from memory. Only the ₹10 at 27.0 mm is sourced.

## Deferred, and what it costs

- **Flutter native app** — PWA ships. Costs true on-device offline capture.
- **Kubernetes on MeitY GI Cloud** — Compose ships. Costs horizontal scaling and a
  sovereignty story; mitigated by staying S3- and Postgres-compatible.
- **Live ONDC integration** — the ingestion interface accepts a structured catalogue record,
  so this stays an adapter.
- **Bhashini output localisation** — costs the multilingual story. **Output localisation
  only; conflating it with regional-script OCR is a technical error a judge can challenge.**
- **DigiLocker** — a talking point, no architectural dependency.
- **Component tests and web performance work** — costs frontend regression safety.
- **Scenario 4 of the demo set (calibrated font measurement)** — carried by scenarios 5 (the
  refusal) and 8 (artwork mode) if reference-object calibration is still unbuilt near the
  demo. Say it out loud rather than quietly cutting it.
