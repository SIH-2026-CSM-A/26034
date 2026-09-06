# TODO.md — 26034

Read at session start. Updated at session end.
Tickets live in ClickUp, list `26034 Build`. This file is the shape of the work, not the
assignment record.

---

## Now

- [ ] **VIS-004 — OCR the detected panel, not the whole frame** (Akshaya, new). `detect_pdp`
      returns a bbox that nothing consumes: `extract_panel_text` is handed the full image,
      so every span's `region_id` of `"panel"` is a claim the chain has not established.
      The pipeline deliberately does **not** overwrite that field — doing so would stamp the
      panel's identity onto spans read off the whole photograph, which is a false provenance
      in the one field an evidence bundle uses to show an officer which crop a value came
      from. Fixing it properly means cropping to the detection before the OCR call *and*
      translating the returned polygons back into full-image coordinates, so an overlay
      still lines up — which is why it is vision's ticket and not a two-line change in
      `pipeline/`.
- [ ] **VIS-003 rework** (Akshaya). Five items open, listed in TICKETS.md. Four pushes so far
      have been byte-identical.
- [ ] **DAT-001 rework** (Aashritha). Two blockers plus the Himalaya MRP contradiction.
- [ ] **TAM-001 — conflicting MRP and sticker overlay** (Akshaya, behind VIS-003). Classical
      CV only, so not blocked on the corpus.
- [ ] **Swap the remaining local stand-in.** `app/modules/rules/` imports nothing from
      `app.contracts` and `models.py:21` still carries the RUL-001 stand-in comment. That is
      why `pipeline/rule_snapshot.py` exists as a translation layer. `measurement/`'s half is
      done.
- [ ] **CI-003** — remove the `paths:` filter from `frontend.yml` so the required `frontend`
      context always reports. In flight.
- [x] **EXT-004 consumed by the pipeline** (Claude Code). The image path binds for real:
      `bind_spans` replaces the old adapter, stages 4 and 5 are one call, and every span
      reaches the evidence record with the unplaced ones named inside the hash. **The
      branch requires PR #44 to merge first** — it was open, not merged, when this was
      written.
- [x] **PIP-002 — HTTP surface and orchestration** (Claude Code, this session). `app/main.py`
      with a lifespan that refuses to start without the vision weights; `pipeline/`
      orchestrator, router, repository and the four-way split of the findings logic; the
      four scan endpoints; `reviews` table and `Scan.product_category`; migration
      `c16334c8d865`; `rule_set_version` on the rule store. 621 tests pass. The image path
      is built to the EXT-004 seam and refuses there by name; the catalogue path works end
      to end.
- [x] **CORE-002 — persistence** (Claude Code, this session). `core/db.py` (async engine,
      session factory, one request-scoped `get_session`; the caller commits), `core/models.py`
      (`Scan`, `VerdictRow`, `FieldFindingRow`, `EvidenceEntryRow`), Alembic initialised with
      one hand-reviewed revision, `docker-compose.yml` with Postgres 16 + pgvector, and a
      `postgres` service added to `ci.yml`. Jurisdiction scoping proved against the real
      `Scan` table; every guard was made to fail before it was claimed.

## Next

- [ ] **EVD-004 — officer report export**, PDF and editable format, identical content
      (F28/F29). Unblocked now that `VerdictRecord` exists. Must also fix
      `test_append_only_enforcement`: it resolves `Path("app/modules/evidence")` against the
      cwd, so it scans nothing and passes vacuously if pytest ever runs from elsewhere.
      Resolve relative to the test file and assert at least one file was scanned.
- [ ] **Frontend `npm audit` gate.** `npm ci` reports 2 moderate vulnerabilities and a
      deprecated `glob@11.1.0`. Not a build failure, so the current gate misses it.
- [ ] `core/` — a users table to replace the `OFFICERS` env list. `Scan.officer_id` is a
      plain string until there is one to key against. Not built while officers are still
      configuration.
- [ ] **MinIO and Redis in `docker-compose.yml`.** Only Postgres is in it, so
      `tests/modules/evidence/test_minio_storage.py` skips on every machine including CI.
      One service each; not folded into CORE-002 because it is not that ticket.
- [ ] `pipeline/` — offline sync and re-validation against the authoritative rule set on
      reconnect (F51's second half).
- [ ] `fnt/` — admin surface (Rohan's, never started).

## Later

- [ ] Copilot (F39) — hybrid retrieval, rerank, citations bound at generation time.
- [ ] Admin console — rule-set draft → review → publish with diff view.
- [ ] Measurement depth — reference-object calibration (₹10 coin 27.0mm, EAN-13 **37.29mm**,
      50mm card). **Waits: Yashashvi unavailable and this is not reassigned.**

## Bugs

- [ ] **`measure_margins` raises on a zero margin**, so Rule 8(1)'s proviso is never called
      from the orchestrator — the chain reports INSUFFICIENT_EVIDENCE for it instead of
      measuring. `MeasurementExact.value` and `MeasurementCalibrated.value` are `gt=0`, and a
      declaration flush against ink or the crop edge crashes. Owner unavailable; needs its
      own ticket rather than a workaround in `pipeline/`.
- [ ] **No `relationship()` anywhere in `core/models.py`.** SQLAlchemy orders dependent
      inserts from relationships, not from `ForeignKey` columns, so a parent and its children
      added in one flush can be inserted child-first. `pipeline/repository.add_verdict`
      flushes the parent explicitly. Adding relationships is *not* the fix: on an async
      mapper they lazy-load on attribute access and raise `MissingGreenlet` mid-serialisation.
      If more parent/child writes appear, the explicit flush is the pattern to copy.
- [ ] **65 findings per scan**, most INSUFFICIENT_EVIDENCE, because Rule 7 and Rule 9 govern
      every declaration the store requires and each pairing is its own finding. Correct but
      heavy for an officer to read. Narrowing it belongs in the rule store as a
      `governs_declarations` field, not as a filter in `pipeline/`.
- [ ] `test_append_only_enforcement` (evidence) resolves a relative path against the cwd and
      passes vacuously if it scans zero files. Fix in EVD-004.
- [ ] `measure_margins` raises on a zero margin — `MeasurementExact.value` and
      `MeasurementCalibrated.value` are `gt=0`, so a declaration flush against ink or the crop
      edge crashes instead of measuring. Owner unavailable.
- [ ] `gh pr checks --watch` reports phantom pending checks against a single-check rollup.
      Read `statusCheckRollup` instead. Tooling issue, not ours to fix.

## Blocked / unresolved

- [ ] **Pilot state not chosen.** `ROLE_DESIGNATIONS` defaults to Controller of Legal
      Metrology / Deputy Controller / Legal Metrology Inspector, and nomenclature varies by
      state. This will change.
- [ ] **DoCA FAQ of 11.11.2025 not captured.** Two EXT-001 claims rest on secondary sources
      and are marked [SOURCED], not [VERIFIED].
- [ ] **No consolidated LMPC text covering Nov 2021 – Oct 2023.** The DoCA e-book refuses
      automated access.
- [ ] **OpenAI query-rewriting scope unconfirmed.** Do not build against it.

## Done

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
