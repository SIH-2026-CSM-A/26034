# TODO.md — 26034

Read at session start. Updated at session end.
Tickets live in ClickUp, list `26034 Build`. This file is the shape of the work, not the
assignment record.

---

## Now

- [ ] **EXT-004 — span classification and spatial role binding** (Sitanshu). Turns OCR spans
      into identified Rule 6 declarations. Binds Manufactured-by / Marketed-by / Packed-by /
      Imported-by by geometry — keyword anchor, then nearest *downward* cluster containing a
      valid PIN — not reading order. **This is what unblocks PIP-002.**
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

## Next

- [ ] **EVD-004 — officer report export**, PDF and editable format, identical content
      (F28/F29). Unblocked now that `VerdictRecord` exists. Must also fix
      `test_append_only_enforcement`: it resolves `Path("app/modules/evidence")` against the
      cwd, so it scans nothing and passes vacuously if pytest ever runs from elsewhere.
      Resolve relative to the test file and assert at least one file was scanned.
- [ ] **PIP-002 — ingestion endpoints and orchestration.** `POST /scans` accepting an image
      or a structured catalogue record; composes vision → extraction → measurement → rules →
      evidence into a `VerdictRecord`. Blocked on EXT-004.
- [ ] **Frontend `npm audit` gate.** `npm ci` reports 2 moderate vulnerabilities and a
      deprecated `glob@11.1.0`. Not a build failure, so the current gate misses it.
- [ ] `core/` — SQLAlchemy engine and session factory, and a users table to replace the
      `OFFICERS` env list. Needs Alembic initialised first. Deliberately not built until a
      real caller exists.
- [ ] `pipeline/` — offline sync and re-validation against the authoritative rule set on
      reconnect (F51's second half).
- [ ] `fnt/` — admin surface (Rohan's, never started).

## Later

- [ ] Copilot (F39) — hybrid retrieval, rerank, citations bound at generation time.
- [ ] Admin console — rule-set draft → review → publish with diff view.
- [ ] Measurement depth — reference-object calibration (₹10 coin 27.0mm, EAN-13 **37.29mm**,
      50mm card). **Waits: Yashashvi unavailable and this is not reassigned.**

## Bugs

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
