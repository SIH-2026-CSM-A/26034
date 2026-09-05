# TODO.md — 26034

Read at session start. Updated at session end.
Tickets live in ClickUp, list `26034 Build`. This file is the shape of the work, not the
assignment record.

---

## Now

- [ ] **VP-CI-001 — repo scaffold** (Abhiram). Built, uncommitted. Reconcile against the
      six template files, commit, push, merge.
- [ ] **Add the CI check as a required status check** on the `main-protection` ruleset.
      Could not be added earlier because the check did not exist.
- [ ] **Rule corpus** (Abhiram). Download and commit to `rules-corpus/`: the consolidated
      LMPC e-book, G.S.R. 629(E) 2017, the 6 Oct 2023 amendment, the Oct 2025
      medical-devices amendment, G.S.R. 128(E) and G.S.R. 312(E) 2026. Immutable source
      PDFs. Every encoded rule cites one of these.
- [x] **`contracts/` v1** (Abhiram, CTR-002) — 2026-09-05. Per-field state enum,
      verdict enum, rule schema, ExtractedSpan, NormalisedField, MeasurementResult,
      VerdictRecord, CatalogueRecord.
- [ ] **Swap the local stand-ins for the real imports.** Two are outstanding:
      RUL-001 (Jashwanth) drops his local `RuleDefinition`; MEA-002 (Yashashvi, PR #13,
      changes requested) drops the local union in
      `bck/app/modules/measurement/schemas.py`. The contracts variants match hers field
      for field, so it is a delete-and-import. One behaviour change to know about:
      `confidence_interval` is now `gt=0`, so a degenerate zero-width interval raises
      instead of being emitted as a measurement.
- [ ] **Corpus collection starts** (Aashritha). Real Indian packaging photographs across
      categories, plus the labelling schema and the eval harness. No accuracy claim in
      the PRD is currently backed by anything.
- [ ] **Collect the six missing GitHub usernames** — Jashwanth, Yashashvi, Vineeth,
      Rohan, Aashritha, Likhitha. Each needs an org invite and a CODEOWNERS line.

## Next

- [ ] `core/` — auth, JWT, RBAC on Controller → Deputy → Inspector, jurisdiction scoping
- [ ] `pipeline/` — ingestion endpoints for both image and structured catalogue record
- [ ] `vision/` — preprocessing chain, PDP detection, PaddleOCR provider
- [ ] `extraction/` — field classification, spatial binding, normalisation
- [ ] `rules/` — YAML store, evaluator, Rule 6 and Rule 7 encoded from the corpus
- [ ] `measurement/` — calibration, homography, ink extent, three-mode policy
- [ ] `evidence/` — hash chain, object store, BSA 63(4) Part A generation
- [ ] `fnt/` — Vite scaffold and `DESIGN.md` before any component exists

## Later

- [ ] `tamper/` — field-localised detection, once the corpus can support training
- [ ] Copilot (F39) — hybrid retrieval, rerank, citations bound at generation time
- [ ] Offline sync and conflict resolution against the authoritative rule-set
- [ ] Admin console — rule-set draft → review → publish with diff view

## Bugs

- [ ] `claude.yml` re-triggers on Claude's own reply comments. Fix is an
      `github.actor != 'claude'` guard in the `if:` condition. Included in VP-CI-001.

## Blocked / unresolved

*(Product name settled 2026-09-05: PCCS — Packaged Commodity Compliance System.
Applied across README, ARCHITECTURE, AGENTS and CLAUDE in CTR-002.)*

- [ ] **F18 unit sale price tolerance** — ±₹0.01 in one document, ±₹0.05 in another.
      Needs a read of Rule 6(11)'s rounding language. Blocks encoding F18.
- [ ] **Medical devices carve-out** — Amendment Rules 2025 route numeral and letter
      height to the Medical Devices Rules 2017 and disapply the Rule 33 relaxation and
      PDP declaration. Rule 7 Table-I is not universal. Not yet in the sector-override
      set, and `SIH26034_TI.md` §5 uses "Medical Device" as its routing example without
      knowing this.
- [ ] **Combination Package and Group Package** — defined by the Amendment Rules 2023,
      absent from every project document and from the rule schema.
- [ ] **MVP category priority** — packaged food is the volume answer and carries the
      heaviest FSSAI override risk.

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
