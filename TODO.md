# TODO.md — 26034

Read at session start. Updated at session end.
Tickets live in ClickUp, list `26034 Build`. This file is the shape of the work, not the
assignment record.

---

## Now

- [ ] **EXT-004** (Sitanshu). Not started.
- [ ] **VIS-003** (Akshaya). In rework.
- [ ] **DAT-001 — corpus** (Aashritha). In rework. Root cause diagnosed: fabricated
      annotations and empty-file placeholders. Plan is to rewrite the four real
      annotations from actual photo content, send images to Abhiram outside git, and close
      honestly at four real samples. No accuracy claim in the PRD is backed until this
      lands.
- [ ] **TAM-001** (Akshaya). Queued behind VIS-003.
- [ ] **`rules/` still carries its own `RuleDefinition` stand-in.** `app/modules/rules/`
      imports nothing from `app.contracts`; `models.py` says so in its own docstring. This
      is why `pipeline/rule_snapshot.py` has to exist as a translation layer. The swap is
      a rules-module ticket and was deliberately out of scope for RUL-002 and RUL-003.
      MEA-002's half of this item is done.

## Next

- [ ] **EVD-004 — report export**, PDF and editable format. Unblocked: `VerdictRecord`
      exists as of PIP-001. Also carries the `test_append_only_enforcement` fix below.
- [ ] **PIP-002 — ingestion and orchestration**, for both image and structured catalogue
      record. Blocked on EXT-004.
- [ ] **Frontend `npm audit` gate.** `npm ci` currently reports two moderate
      vulnerabilities and a deprecated `glob@11.1.0`. CI-002 builds the frontend but does
      not audit it.
- [ ] `core/` — SQLAlchemy engine and session factory, and a users table to replace the
      `OFFICERS` env list. Needs Alembic initialised first.
- [ ] `measurement/` — calibration, homography, ink extent, three-mode policy
- [ ] `fnt/` admin surface (Rohan) — rule-set draft, review and publish

## Later

- [ ] `tamper/` — field-localised detection, once the corpus can support training
- [ ] Copilot (F39) — hybrid retrieval, rerank, citations bound at generation time
- [ ] Offline sync and conflict resolution against the authoritative rule-set
- [ ] Admin console — rule-set draft → review → publish with diff view

## Bugs

- [ ] `claude.yml` re-triggers on Claude's own reply comments. Fix is an
      `github.actor != 'claude'` guard in the `if:` condition. Included in VP-CI-001.
- [ ] **`frontend` is a required status check but never reports on backend-only PRs.**
      `main-protection` requires contexts `backend` and `frontend`, while
      `.github/workflows/frontend.yml` is filtered to `paths: fnt/**`. A skipped-by-path
      workflow posts no status at all, so every backend-only PR sits at
      `mergeStateStatus: BLOCKED` on a check that can never arrive. Verified on #33, #32
      and #36 — all three show only `backend` in their rollup and all three were merged by
      hand. The protection is currently costing an override per PR and buying nothing. Two
      fixes: drop `frontend` from the required contexts, or remove the `paths:` filter and
      let the job skip internally so it still reports. Prefer the second — it keeps the
      gate real.
- [ ] **`test_append_only_enforcement` (EVD-003) passes vacuously.** It resolves
      `Path("app/modules/evidence")` relative to the working directory, so `rglob` yields
      nothing and `assert not found_violations` succeeds against an empty scan whenever
      pytest runs from anywhere but `bck/`. Fix belongs in **EVD-004**: resolve the path
      relative to the test file, and assert at least one file was actually scanned. A test
      that cannot fail is worse than no test, because it reads as coverage.

## Blocked / unresolved

*(Product name settled 2026-09-05: PCCS — Packaged Commodity Compliance System.
Applied across README, ARCHITECTURE, AGENTS and CLAUDE in CTR-002.)*

*(F18 unit sale price settled in COR-001: Rule 6(11) is a format rule prescribing the
unit basis, with no tolerance and no rounding increment. The ±₹0.01 and ±₹0.05 figures
were assumptions in earlier project documents, not law, and must not be encoded. See
`rules-corpus/README.md`.)*

- [ ] **MVP category priority** — packaged food is the volume answer and carries the
      heaviest FSSAI override risk.
- [ ] **`SIH26034_TI.md` §5 is stale on medical devices.** It uses "Medical Device" as a
      routing example without knowing about G.S.R. 778(E). Not a source for rule facts;
      `rules-corpus/` is. Left here so nobody re-derives the old behaviour from it.

## Cut

- **Automated Claude review on every PR** — cut because ten agents opening PRs
  continuously would burn subscription quota and train everyone to scroll past the
  output. `@claude` on mention is kept.
- **Two repositories (`-bck` / `-fnt`)** — cut because it doubles branch protection and
  CI and creates a cross-repo type-sync problem policed by hand. CODEOWNERS plus
  import-linter gives directory-level isolation in one repo.
- **Custom DSL for rules** — cut because a small YAML interpreter is correct for MVP and
  a DSL is this project's most likely over-engineering failure.
- **Separate vector database** — cut because the corpus is a few hundred pages and
  pgvector handles it without adding a service.
- **Supabase** — cut because free projects auto-pause after 7 days and a DoCA deployment
  must be sovereign.
- **Cloud-primary OCR** — cut because it makes the offline verdict path a second, weaker
  extraction implementation and puts product images outside the sovereign boundary.
  Retained as an opt-in per-request escalation, disabled by default.

## Deferred, and what it costs

- **Flutter native app** — PWA ships instead. Costs true on-device offline capture and
  camera guidance. Acceptable while the demo runs on a laptop; not acceptable for a
  field pilot.
- **Kubernetes on MeitY GI Cloud / NIC MeghRaj** — Compose ships instead. Costs
  horizontal scaling and the sovereignty story being demonstrable rather than described.
  Mitigated by keeping every service S3- and Postgres-compatible.
- **Live ONDC integration** — the ingestion interface accepts a structured catalogue
  record as a first-class type, so this stays an adapter. Deferring the live connection
  costs a demo talking point, not an architecture change.
- **Bhashini output localisation** — costs the multilingual story. Note it is output
  localisation only; conflating it with regional-script OCR is a technical error a judge
  can challenge.
- **DigiLocker** — costs an integration talking point. No architectural dependency.
- **Component tests and web performance work** — costs regression safety in the frontend.
  Accepted deliberately given the timeline.

## Done

- [x] GitHub org `SIH-2026-CSM-A`, repos `26034` and `26167` — 2026-09-05
- [x] Branch protection on `main`: ruleset + push restriction + squash-only — 2026-09-05
- [x] Claude GitHub App installed on the org, `@claude` on-mention workflow — 2026-09-05
- [x] ClickUp list `26034 Build` with statuses and Module / Files / Branch fields — 2026-09-05
- [x] **VP-CI-001 repo scaffold** — 2026-09-05. Includes the `claude.yml` actor guard.
- [x] **Rule corpus** committed to `rules-corpus/` — 2026-09-05. Eight documents. Two
      known gaps recorded in its README: the consolidated e-book, and the 11.11.2025 DoCA
      FAQ (two clauses sourced from secondary reports, marked [SOURCED] not [VERIFIED]).
- [x] **CTR-002 contracts v1** — 2026-09-05.
- [x] **CORE-001** auth, JWT, RBAC, jurisdiction scoping — 2026-09-06 (#25).
- [x] **PIP-001** verdict assembly and rule parameter snapshot adapter — 2026-09-06 (#28).
- [x] **CI-002** frontend build gate on `fnt/**` — 2026-09-06 (#30).
- [x] **CTR-003** deep-copy rule parameters into the snapshot — 2026-09-06 (#33).
- [x] **RUL-002** Rule 8 placement and free space, Rule 9 manner, sector override
      dispatch, medical device carve-out, Combination and Group packages — 2026-09-06
      (#32). Closes the two rule bullets formerly in this file and in `ARCHITECTURE.md`.
- [x] **FNT-002** officer design system, verdict detail, review queue — 2026-09-06 (#35).
- [x] **RUL-003** multi-piece package 2(kc) and its food proviso, package-type scoping on
      the sector dispatch — 2026-09-06 (#36).
- [x] **EVD-003** hash chain verification and append-only enforcement — 2026-09-06 (#31).
      See Bugs: its append-only test currently passes vacuously.
- [x] **MEA-002's local measurement union dropped** for the real `app.contracts` imports
      — 2026-09-06.
- [x] **CI added as required status checks** on the `main-protection` ruleset —
      2026-09-06. Contexts: `backend`, `frontend`. See Bugs: `frontend` is required but
      path-filtered.
