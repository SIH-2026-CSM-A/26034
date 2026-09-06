# TODO.md — 26034

Read at session start. Updated at session end.
Tickets live in ClickUp, list `26034 Build`. This file is the shape of the work, not the
assignment record. Board state and per-PR remaining items are in `TICKETS.md`.

Last updated 2026-09-06, end of session 4, by Claude Code.

---

## Now

- [ ] **Close #34 DAT-001.** Superseded by DAT-002 + DAT-003, owner off the project, thirteen
      commits behind `main`. The last handoff recorded it as already closed; it is not.
      Salvage the four annotation defects into DAT-002 first (TICKETS.md lists them).
- [ ] **Land #42 MEA-004** (Yashashvi). One `uv run ruff format .` and a rebase. The red check
      is `ruff format --check`, not a test failure — `tests/modules/measurement` passes 14/14.
- [ ] **Land #45 VIS-003** (Akshaya). Both owed items are fixed. One thing left: the session
      log rewrite deleted her VIS-001 history instead of appending to it.
- [ ] **Decide the three merge-gate escalations.** #43 adds `pdfplumber` as a new dependency;
      #46 edits `app/contracts/enums.py` and `core/config.py`; #47 edits
      `app/contracts/measurement.py`. All three are other people editing Abhiram's directories.
      Each needs an explicit yes or a split, not a quiet merge.
- [ ] **Rebase sweep.** All six open PRs branched before today's four merges. Owners rebase
      their own branches; Yashashvi's three stack in one module and go oldest-first.
- [ ] **VIS-004 — OCR the detected panel, not the whole frame** (Akshaya). `detect_pdp`
      returns a bbox that nothing consumes: `extract_panel_text` is handed the full image, so
      every span's `region_id` of `"panel"` is a claim the chain has not established. The
      pipeline deliberately does **not** overwrite that field — doing so would stamp the
      panel's identity onto spans read off the whole photograph, a false provenance in the one
      field an evidence bundle uses to show an officer which crop a value came from. Fixing it
      means cropping to the detection before the OCR call *and* translating the returned
      polygons back into full-image coordinates, so an overlay still lines up. That is why it
      is vision's ticket and not a two-line change in `pipeline/`.
- [ ] **Wire `measure_margins` into the orchestrator.** #47 fixes the contract so a zero
      margin is expressible; `pipeline/` still never calls it, so Rule 8 free-space evaluation
      stays dark after that PR merges. Second ticket, and say so when #47 lands or it will
      read as fixed.
- [ ] **RUL-004 — `governs_declarations` on the rule store** (B.V. Yashwanth). Blocked on
      nothing now that PIP-002 has merged. This is what narrows 65 findings per scan, and it
      belongs in the rule store — **never as a filter in `pipeline/`.** RUL-003 is session 3's
      merged multi-piece ticket; do not reuse the number.
- [ ] **Swap the remaining local stand-in.** `app/modules/rules/` imports nothing from
      `app.contracts` and `models.py:21` still carries the RUL-001 stand-in comment. That is
      why `pipeline/rule_snapshot.py` exists as a translation layer. `measurement/`'s half is
      done.

## Next

- [ ] **EXT-005 then EXT-006** (Sitanshu). Unblocked by #44.
- [ ] **EVD-006 — accept a real `VerdictRecord` in `export_compliance_report`.** EVD-004's
      tests use mock record shapes, so the export has never been handed a real record.
- [ ] **DAT-002 then DAT-003** (Abhiram, from Aashritha). DAT-003 also corrects CODEOWNERS and
      AGENTS.md, which still name Aashritha on `datasets/` and Sitanshu on `extraction/`.
- [ ] **TAM-001 — conflicting MRP and sticker overlay** (Akshaya). Classical CV only, so not
      blocked on the corpus. `tamper/` is still an empty module.
- [ ] **Frontend `npm audit` gate.** `npm ci` reports 2 moderate vulnerabilities and a
      deprecated `glob@11.1.0`. Not a build failure, so the current gate misses it.
- [ ] **MinIO and Redis in `docker-compose.yml`.** Only Postgres is in it, so
      `tests/modules/evidence/test_minio_storage.py` skips on every machine including CI. One
      service each.
- [ ] `core/` — a users table to replace the `OFFICERS` env list. `Scan.officer_id` is a plain
      string until there is one to key against. Not built while officers are still config.
- [ ] **A unique constraint on `reviews.supersedes_id`.** Nothing stops two rows sharing one,
      which forks the correction chain. It would make single-successor structural, the way
      `(scan_id, sequence)` does for evidence. **Do it before any review data exists.**
- [ ] Drop `ix_reviews_scan_id` — `ix_reviews_scan_id_created_at` leads with the same column.
- [ ] `pipeline/` — offline sync and re-validation against the authoritative rule set on
      reconnect (F51's second half).
- [ ] `fnt/` — admin surface (Rohan's, never started).
- [ ] `fnt/` — generated client from the backend OpenAPI schema. The frontend still runs
      entirely on fixtures.

## Later

- [ ] Copilot (F39) — hybrid retrieval, rerank, citations bound at generation time.
- [ ] Admin console — rule-set draft → review → publish with diff view.
- [ ] Dashboard aggregates (F32). Does not exist; `rule_id` was promoted to a typed column
      specifically so violation-rate-by-clause is queryable when this is built.
- [ ] Measurement depth — reference-object calibration (₹10 coin 27.0mm, EAN-13 **37.29mm**,
      50mm card). Yashashvi is active again, so this is assignable; it is behind her three
      open PRs.
- [ ] Pan masala (G.S.R. 881(E)) not encoded.

## Bugs

- [ ] **The image path has never run with real model weights. P0, and it is on the demo
      path.** There are no YOLO or PaddleOCR weights on the dev machine. Every image-path
      verification to date substituted `detect_pdp` and `extract_panel_text`; everything
      downstream of them is real and verified live, and the app now refuses to boot without
      four model paths that do not exist locally. **This is the largest gap between "the tests
      pass" and "the system works".** Cache the weights and run one real photograph end to
      end before anything else is called demo-ready. `ultralytics` is already a runtime
      dependency, so the YOLO stack ships with the backend.
- [ ] **`measure_margins` raises on a zero margin**, so Rule 8(1)'s proviso is never called
      from the orchestrator and the chain reports INSUFFICIENT_EVIDENCE instead of measuring.
      #47 fixes the contract; the orchestrator wiring is still outstanding.
- [ ] **`tesseract_tessdata_dir` is checked at boot but never called.** The constrained re-read
      needs a bound MRP crop to run against. A required config path with no reader is a boot
      failure waiting for a machine that does not have it.
- [ ] **No `relationship()` anywhere in `core/models.py`.** SQLAlchemy orders dependent inserts
      from relationships, not from `ForeignKey` columns, so a parent and its children added in
      one flush can be inserted child-first. `pipeline/repository.add_verdict` flushes the
      parent explicitly. Adding relationships is *not* the fix: on an async mapper they
      lazy-load on attribute access and raise `MissingGreenlet` mid-serialisation. If more
      parent/child writes appear, the explicit flush is the pattern to copy.
- [ ] **65 findings per scan**, most INSUFFICIENT_EVIDENCE, because Rule 7 and Rule 9 govern
      every declaration the store requires and each pairing is its own finding. Correct but
      heavy for an officer to read. Narrowing belongs in the rule store as
      `governs_declarations` (RUL-004), not as a filter in `pipeline/`.
- [ ] `test_append_only_enforcement` (evidence) resolves a relative path against the cwd and
      passes vacuously if it scans zero files. EVD-004 was meant to fix it — confirm it did.
- [ ] `gh pr checks --watch` reports phantom pending checks against a single-check rollup.
      Read `statusCheckRollup` instead. Tooling issue, not ours to fix.

## Blocked / unresolved

- [ ] **No usable labelled corpus — four samples, not the 8–12 planned.** Every accuracy
      figure in the PRD carries that sample size. Vision, measurement and tamper cannot be
      evaluated at all. DAT-003 is unmerged. **This is the largest single risk in the
      project**, and written review has now failed four times on it; the next move is a
      fifteen-minute call with one annotation open beside the actual photograph.
- [ ] **Pilot state not chosen.** `ROLE_DESIGNATIONS` defaults to Controller of Legal
      Metrology / Deputy Controller / Legal Metrology Inspector, and nomenclature varies by
      state. This will change.
- [ ] **DoCA FAQ of 11.11.2025 not captured.** Two EXT-001 claims rest on secondary sources
      and are marked [SOURCED], not [VERIFIED].
- [ ] **No consolidated LMPC text covering Nov 2021 – Oct 2023.** The DoCA e-book refuses
      automated access.
- [ ] **OpenAI query-rewriting scope unconfirmed.** Do not build against it.
- [ ] **The offline path (F51, P0) does not exist.** Neither half — no on-device run, no
      re-validation on reconnect.

## Done

- [x] **PIP-002** HTTP surface, scan orchestration, four scan endpoints, `reviews` table,
      `Scan.product_category`, migration `c16334c8d865` — #48, 2026-09-06
- [x] **EXT-004** span classification and spatial role binder — #44, 2026-09-06
      *(moved Sitanshu → B.V. Yashwanth, never started, delivered same day)*
- [x] **EVD-004** officer report export, PDF and editable — #41, 2026-09-06
- [x] **CORE-002** persistence: async engine and session factory, `Scan` / `VerdictRow` /
      `FieldFindingRow` / `EvidenceEntryRow`, Alembic, Postgres 16 + pgvector in Compose and
      a `postgres` service in CI — #40, 2026-09-06
- [x] **CI-003** frontend gate runs on every PR so the required context always reports —
      #38, 2026-09-06
- [x] **PIP-001** verdict assembly + rule parameter snapshot adapter — #28, 2026-09-06
- [x] **CI-002** frontend build gate on `fnt/**` — #30, 2026-09-06
- [x] **CTR-003** deep-copy rule parameters into the snapshot — #33, 2026-09-06
- [x] **RUL-002** Rule 8 placement and free space, Rule 9 manner, sector override dispatch,
      medical device carve-out, Combination and Group packages — #32, 2026-09-06
- [x] **FNT-002** officer design system, verdict detail, review queue — #35, 2026-09-06
- [x] **RUL-003** multi-piece package 2(kc) and its food proviso, package-type scoping —
      #36, 2026-09-06
- [x] **EVD-003** hash chain verification and append-only enforcement — #31, 2026-09-06
- [x] `frontend` added as a required status check on `main-protection` — 2026-09-06
- [x] `contracts/` v1 — CTR-002, 2026-09-05
- [x] `core/` auth, JWT, RBAC, jurisdiction scoping — CORE-001, 2026-09-05
- [x] GitHub org, repos, branch protection, Claude App, ClickUp board — 2026-09-05

## Cut

- **Automated Claude review on every PR** — burns quota, trains people to scroll past it.
- **Two repositories** — doubles branch protection and CI, creates a cross-repo type-sync
  problem policed by hand.
- **Custom DSL for rules** — the project's most likely over-engineering failure.
- **Separate vector database** — pgvector handles a few hundred pages.
- **Supabase** — free projects auto-pause after 7 days.
- **Cloud-primary OCR** — makes the offline verdict path a second, weaker implementation.
- **A multi-piece / Rule 9(3) interaction** — the gazette does not amend rule 9. A test
  asserts the absence.
- **G.S.R. 722(E) paragraph 4's Rule 6(11) exemption** — deliberately not encoded.
- **PyMuPDF** — AGPL-3.0, and its network clause would attach to the whole work.
  `pdfplumber` instead.
- **`BoundDeclaration` / `DeclarationRole` / `app/contracts/binding.py`** — EXT-004's
  `bind_spans` → `ExtractionResult` shape won. The contracts commit was dropped from history,
  not reverted. Do not recreate them.

## Deferred, and what it costs

- **Flutter native app** — PWA ships instead. Costs true on-device offline capture and camera
  guidance. Acceptable on a laptop demo; not for a field pilot.
- **Kubernetes on MeitY GI Cloud / NIC MeghRaj** — Compose ships instead. Costs horizontal
  scaling and a demonstrable sovereignty story. Mitigated by staying S3- and
  Postgres-compatible.
- **Live ONDC integration** — the ingestion interface accepts a structured catalogue record as
  a first-class type, so this stays an adapter. Costs a talking point, not architecture.
- **Bhashini output localisation** — costs the multilingual story. **Output localisation only;
  conflating it with regional-script OCR is a technical error a judge can challenge.**
- **DigiLocker** — a talking point, no architectural dependency.
- **Component tests and web performance work** — costs frontend regression safety. Accepted.
- **Scenario 4 of the demo set (calibrated font measurement)** — costs the strongest
  measurement story. Carried by scenarios 5 (the refusal) and 8 (artwork mode) instead if
  reference-object calibration is still unbuilt near the demo. Say it out loud rather than
  quietly cutting it.
