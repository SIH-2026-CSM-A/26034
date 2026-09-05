# ARCHITECTURE.md — 26034 · Legal Metrology Packaged Commodities Compliance

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind, PWA | Authenticated internal tool — SSR buys nothing. Rejected Next.js: adds a Node server to Compose for no gain. Flutter deferred, not rejected. |
| Backend | Python 3.11 + FastAPI | The CV/OCR ecosystem decides it. Node/NestJS is defensible but forces a cross-language seam exactly where six of eleven people work. |
| Database | PostgreSQL 16 (self-hosted, Compose) + pgvector | Transactional integrity on the evidence chain; JSONB covers flexible fields; pgvector removes the need for a separate vector service. Rejected Supabase: free projects auto-pause after 7 days, and a DoCA deployment must land on MeitY GI Cloud / NIC MeghRaj. |
| Object store | MinIO (S3-compatible) | Offline-capable, sovereign, and swapping to a government bucket later is a config change. |
| Queue | Redis + arq | Async-native and light. Rejected Celery (sync-first, heavy) and RabbitMQ (a broker for a workload peaking at tens of jobs). |
| OCR | PaddleOCR PP-OCRv4 primary + character-whitelisted Tesseract re-OCR on MRP / net-quantity | Stronger on curved, glared, multi-script real-world labels. Cloud OCR is an opt-in escalation, never the default — see Decisions. |
| Detection | YOLO (ultralytics) — PDP localisation and tamper field localisation | Same family serves both; one weights pipeline to cache offline. |
| Rules | YAML rule store + deterministic Python evaluator | Must be inspectable by a domain expert who does not write code. Rejected a custom DSL, Drools and OPA as the most likely over-engineering trap in this project. |
| Copilot | LangGraph + hybrid retrieval (pgvector + Postgres FTS) + cross-encoder rerank, generation on Featherless | Grounded answers with clause-level attribution bound at generation time. LangGraph is confined to the copilot and never touches the verdict path. |
| Auth | OAuth2 password flow + JWT, RBAC on Controller → Deputy → Inspector with jurisdiction scoping | Rejected Auth0/Clerk: sovereignty, and neither works offline. |
| Deploy | Docker Compose, single VM. GCP mirror for a shareable link only. | Local Compose is the primary demo path and cloud the fallback, not the reverse. |

## Structure

```
bck/app/contracts/          Cross-module types. Imports nothing. Single source of truth
                            for the per-field state enum, verdict enum, rule schema, DTOs.
bck/app/core/               Auth, RBAC, jurisdiction scoping, config, cost ceilings.
bck/app/pipeline/           Ingestion endpoints, orchestration, offline sync. Composes
                            modules; modules never compose each other.
bck/app/modules/vision/         Preprocess, PDP detect, OCR providers.
bck/app/modules/extraction/     Spans -> Rule 6 field types, spatial binding, normalisation.
bck/app/modules/measurement/    Calibration, homography, ink extent, Rule 7 band lookup.
bck/app/modules/rules/          Rule store, evaluator, category routing, verdict assembly.
bck/app/modules/tamper/         Field-localised forgery detection.
bck/app/modules/evidence/       Hash chain, object store, BSA 63(4) Part A, exports.
bck/alembic/                Migrations. One owner, no exceptions.
fnt/                        React app. Officer surface and admin surface, separate route trees.
datasets/                   Labelled corpus and the eval harness. Contents gitignored.
rules-corpus/               Immutable source PDFs of the Act, Rules and every amendment.
session-log/                One file per person. Never a shared file.
```

**The import rule is the structure.** A module may import from `contracts` and `core` and
itself. Nothing else. `pipeline` composes modules. `contracts` imports nothing. This is
enforced by import-linter in CI, not by convention.

Layers nest *inside* each module (`router.py`, `service.py`, `repository.py`,
`schemas.py`) rather than as top-level directories. Deliberate deviation from the
horizontal layout in the engineering standards — with ten people owning directories, a
horizontal layout makes every ticket a three-way ownership collision.

## Data flow

A scan moves in one direction and every step writes provenance.

1. **Capture** — image upload, or a structured catalogue record from a listing. Both
   enter through `pipeline`; the listing path is a first-class input type, not a URL
   with an adapter bolted on, so ONDC later is an adapter rather than a rewrite.
2. **Quality gate** — blur, glare, completeness. Fails here return a capture instruction
   to the officer, never a verdict.
3. **Preprocess** — deskew, curvature remap for cylindrical substrates, glare mask and
   inpaint, CLAHE on the L channel only.
4. **PDP detection** — locates the principal display panel and yields the pixel area the
   Rule 7 band lookup needs.
5. **OCR** — PaddleOCR over the panel; whitelisted Tesseract re-pass on MRP and
   net-quantity crops. Emits spans with polygons and per-span confidence.
6. **Extraction** — spans classified to Rule 6(1) declaration fields, spatially bound
   (Manufactured-By vs Marketed-By), values normalised to units, ISO dates, decimal MRP.
7. **Measurement** — only if a reference object is in frame or pre-print artwork was
   supplied. Otherwise the field is marked INSUFFICIENT_EVIDENCE and routed to review.
   A millimetre figure is never emitted from an uncalibrated photograph.
8. **Rule evaluation** — deterministic. Takes a normalised field set plus a rule-set
   version, returns a per-field state. Rule parameters are snapshotted into the record
   at evaluation time, never foreign-keyed to a mutable table.
9. **Tamper** — field-localised, scored per region, attached as evidence rather than as
   a verdict input.
10. **Verdict assembly** — PASS / REVIEW / POTENTIAL VIOLATION. Never "violation
    confirmed".
11. **Evidence record** — immutable, hash-chained to the previous entry, containing image
    hash, model versions, rule-set version, measured-vs-required values, OCR provider per
    field, and confidence.
12. **Human confirmation** — an officer confirms, overrides or annotates. Only then can
    anything reach an enforcement workflow.

Offline: steps 1–7 plus a cached rule-set subset run on device. Results queue locally and
re-validate against the authoritative rule-set on reconnect.

## Decisions

- **Self-hosted OCR primary; cloud as opt-in escalation** — cloud-primary would make the
  offline verdict path a second, weaker implementation of extraction, and would put
  consumer-product images outside the sovereign boundary a DoCA deployment requires.
  A cloud provider implements the same interface and can be enabled per request when
  online and local confidence is low. Rejected cloud-primary-with-local-fallback.
  The accuracy cost of self-hosted primary is **unmeasured** until the eval set exists.
- **Monorepo named `26034`, folders `bck/` and `fnt/`** — two repos would give harder
  isolation but double branch protection, double CI, and create a cross-repo type-sync
  problem policed by hand. Rejected. Ownership is enforced by CODEOWNERS paths and
  import-linter instead.
- **LangGraph confined to the copilot** — an agent loop anywhere in the verdict path
  destroys reproducibility. Rejected agentic rule evaluation outright.
- **Rules as versioned data, parameters snapshotted per verdict** — rejected
  foreign-keying verdicts to a live rules table, which would silently re-adjudicate
  history whenever a rule changed.
- **Citations bound at generation time** — the copilot binds claims to `rule_id` via a
  strict output schema rather than appending citations post-hoc. Post-hoc is cheaper
  today and cannot be upgraded without rebuilding the generation path.
- **Five per-field states, not four** — PASS / FAIL / REVIEW_REQUIRED / NOT_APPLICABLE /
  INSUFFICIENT_EVIDENCE. Collapsing INSUFFICIENT_EVIDENCE into FAIL conflates "we could
  not see it" with "it is not there", which is a wrongful-flag liability.
- **Python 3.11, not 3.12** — PaddlePaddle and several CV wheels lag on newer releases.

## Technical debt

- [ ] No labelled corpus yet. Every accuracy target in the PRD is currently unbacked.
      Blocks vision, measurement and tamper from being evaluated at all.
- [ ] Rule 7 Table-I is encoded as a universal lookup. The Amendment Rules 2025 carve out
      medical devices to the Medical Devices Rules 2017 for numeral and letter height —
      not yet modelled in the sector-override set.
- [ ] Combination Package and Group Package (Amendment Rules 2023) are absent from the
      rule schema entirely.
- [ ] F18 unit-sale-price tolerance is ±0.01 in one document and ±0.05 in another.
      Unresolved; blocks encoding F18.
- [ ] Product name is a placeholder across the whole document set.
- [ ] `26167` in the same org has no branch protection. Write access there is direct-push.

---

## Standards

This project follows the full engineering standards: repository structure, layer
boundaries, dependency direction, file/function limits, naming, branching, SemVer,
API design, deployment gates, logging, and backend specifics.

They live in the `engineering-standards` skill and load on demand — ask for them by
name, or they trigger automatically on repo setup, structural work, releases, code
review, and anything heading to production.

**Overrides for this project:**

- Branch base is `main` plus feature branches, not the four-branch develop chain.
  Eleven people, one merger, no staging environment.
- Layers nest inside modules, not modules inside layers. Ownership isolation.
- Repository is named `26034` with no client-project-layer prefix and no `-bck` / `-fnt`
  suffix, because it is a monorepo.
- `.env.example`, not `.env-example`.
