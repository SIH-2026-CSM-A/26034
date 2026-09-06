# ARCHITECTURE.md — PCCS · Packaged Commodity Compliance System

SIH 2026, problem statement 26034. Legal Metrology (Packaged Commodities) Rules 2011.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind, PWA | Authenticated internal tool — SSR buys nothing. Rejected Next.js: adds a Node server to Compose for no gain. Flutter deferred, not rejected. |
| Backend | Python 3.11 + FastAPI | The CV/OCR ecosystem decides it. Node/NestJS is defensible but forces a cross-language seam exactly where six of eleven people work. |
| Database | PostgreSQL 16 (self-hosted, Compose) + pgvector | Transactional integrity on the evidence chain; JSONB covers flexible fields; pgvector removes the need for a separate vector service. Rejected Supabase: free projects auto-pause after 7 days, and a DoCA deployment must land on MeitY GI Cloud / NIC MeghRaj. |
| Object store | MinIO (S3-compatible) | Offline-capable, sovereign; swapping to a government bucket later is a config change. |
| Queue | Redis + arq | Async-native and light. Rejected Celery (sync-first, heavy) and RabbitMQ (a broker for a workload peaking at tens of jobs). |
| OCR | PaddleOCR PP-OCRv4 primary + character-whitelisted Tesseract re-OCR on MRP / net-quantity | Stronger on curved, glared, multi-script real-world labels. The constrained second pass exists because 8-for-B is tolerable on an address and not on a price. Cloud OCR is an opt-in escalation, never the default. |
| Detection | YOLO (ultralytics) — PDP localisation and tamper field localisation | Same family serves both; one weights pipeline to cache offline. |
| Rules | YAML rule store + deterministic Python evaluator | Must be inspectable by a domain expert who does not write code. Rejected a custom DSL, Drools and OPA as the most likely over-engineering trap in this project. |
| Copilot | LangGraph + hybrid retrieval (pgvector + Postgres FTS) + cross-encoder rerank, generation on Featherless | Grounded answers with clause-level attribution bound at generation time. LangGraph is confined to the copilot and never touches the verdict path. |
| Auth | OAuth2 password flow + JWT, RBAC on Controller → Deputy → Inspector with jurisdiction scoping | Rejected Auth0/Clerk: sovereignty, and neither works offline. |
| Deploy | Docker Compose, single VM. GCP mirror for a shareable link only. | Local Compose is the primary demo path and cloud the fallback, not the reverse. |

## Structure

```
bck/app/contracts/          Cross-module types. Imports nothing. Single source of truth for
                            the per-field state enum, verdict enum, rule schema, DTOs.
                            FieldState, Verdict, DeclarationField, EvidenceProvider,
                            ExtractedSpan, NormalisedField, MeasurementResult,
                            RuleDefinition, RuleSetVersion, RuleParameterSnapshot,
                            FieldFinding, VerdictRecord, CatalogueRecord.
bck/app/core/               Auth, RBAC, jurisdiction scoping, config, cost ceilings.
bck/app/pipeline/           Verdict assembly, rule-snapshot adapter, and (next) ingestion
                            endpoints and orchestration. The only package permitted to
                            import app.modules.* — this is what "composes modules" means.
bck/app/modules/vision/         Preprocess, PDP detect, OCR providers.
bck/app/modules/extraction/     Spans -> Rule 6 field types, spatial binding, normalisation.
bck/app/modules/measurement/    Calibration, homography, ink extent, Rule 7 band lookup.
bck/app/modules/rules/          base -> conditions -> models -> results, plus evaluator,
                                loader, sector dispatch, placement. Rule store in data/.
bck/app/modules/tamper/         Field-localised forgery detection. Not started.
bck/app/modules/evidence/       Hash chain, verification, object store, BSA 63(4) Part A.
bck/alembic/                Migrations. One owner, no exceptions. Not initialised yet.
fnt/                        React app. Officer and admin surfaces, separate route trees.
                            DESIGN.md holds the design system and its contrast findings.
datasets/                   Labelled corpus and the eval harness. Contents gitignored.
rules-corpus/               Immutable source PDFs of the Act, Rules and every amendment.
session-log/                One file per person. Never a shared file.
```

**The import rule is the structure.** A module may import from `contracts` and `core` and
itself. Nothing else. `pipeline` composes modules. `contracts` imports nothing. Enforced by
import-linter in CI with three contracts — layer order, module independence, and no `bck.*`
import path — not by convention. Each contract has been proved to bite by introducing a
deliberate violation in both directions.

Layers nest *inside* each module (`router.py`, `service.py`, `repository.py`, `schemas.py`)
rather than as top-level directories. Deliberate deviation from the horizontal layout in the
engineering standards — with ten people owning directories, a horizontal layout makes every
ticket a three-way ownership collision.

## Data flow

A scan moves in one direction and every step writes provenance.

1. **Capture** — image upload, or a structured catalogue record from a listing. Both enter
   through `pipeline`; the listing path is a first-class input type, so ONDC later is an
   adapter rather than a rewrite.
2. **Quality gate** — blur, glare, completeness. Fails here return a capture instruction to
   the officer, never a verdict.
3. **Preprocess** — deskew, curvature remap for cylindrical substrates, glare mask and
   inpaint, CLAHE on the L channel only.
4. **PDP detection** — locates the principal display panel and yields the pixel area the
   Rule 7 band lookup needs.
5. **OCR** — PaddleOCR over the panel; whitelisted Tesseract re-pass on MRP and net-quantity
   crops. Emits spans with polygons, per-span confidence and the provider that produced them.
   Providers that disagree on a numeric field surface both readings rather than arbitrating.
6. **Extraction** — spans classified to Rule 6(1) declaration fields, spatially bound
   (Manufactured-By vs Marketed-By, by keyword anchor plus nearest downward PIN-bearing
   cluster), values normalised to units, ISO dates, decimal MRP.
7. **Measurement** — only if a reference object is in frame or pre-print artwork was
   supplied. Otherwise INSUFFICIENT_EVIDENCE, routed to review. A millimetre figure is never
   emitted from an uncalibrated photograph.
8. **Rule evaluation** — deterministic. Sector overrides dispatch on confirmed product
   category before general evaluation; a medical device carves out of Table-I rather than
   being evaluated more strictly against it.
9. **Tamper** — field-localised, scored per region, attached as evidence rather than as a
   verdict input.
10. **Verdict assembly** — any FAIL → POTENTIAL VIOLATION; else any REVIEW_REQUIRED or
    INSUFFICIENT_EVIDENCE → REVIEW; else PASS. Zero findings → REVIEW, never PASS. Rule
    parameters are deep-copied into the record at this point, never referenced.
11. **Evidence record** — immutable, hash-chained to the previous entry. Verification detects
    a mutated payload, reordered entries, a deletion, an insertion, and a recomputed-hash
    attack, and names the first broken index and the reason.
12. **Human confirmation** — an officer confirms, overrides or annotates. Only then can
    anything reach an enforcement workflow.

Offline: steps 1–7 plus a cached rule-set subset run on device. Results queue locally and
re-validate against the authoritative rule-set on reconnect.

## Decisions

- **Self-hosted OCR primary; cloud as opt-in escalation** — cloud-primary would make the
  offline verdict path a second, weaker implementation of extraction, and would put
  consumer-product images outside the sovereign boundary. The accuracy cost of self-hosted
  primary is **unmeasured** until the eval set exists.
- **Monorepo named `26034`, folders `bck/` and `fnt/`** — two repos would double branch
  protection and CI and create a cross-repo type-sync problem policed by hand. Ownership is
  enforced by CODEOWNERS paths and import-linter instead.
- **LangGraph confined to the copilot** — an agent loop anywhere in the verdict path destroys
  reproducibility. Rejected agentic rule evaluation outright.
- **Rules as versioned data, parameters snapshotted per verdict** — rejected foreign-keying
  verdicts to a live rules table, which would silently re-adjudicate history.
- **The rule-snapshot adapter lives in `pipeline/`** — `rules.RuleDefinition` is the permanent
  internal shape of that module, richer than what contracts exposes, because no other module
  needs to introspect a rule's condition *shape*, only that a snapshot exists.
- **Sector overrides as a table read from the rule store, not an if/else chain** — adding a
  sector is a YAML rule plus an enum member and touches no existing logic. `Rule7Route` was
  generalised from a member naming one sector to `LMPC_TABLE_I` / `SECTOR_FRAMEWORK` for the
  same reason.
- **Five per-field states, not four** — PASS / FAIL / REVIEW_REQUIRED / NOT_APPLICABLE /
  INSUFFICIENT_EVIDENCE. Collapsing INSUFFICIENT_EVIDENCE into FAIL conflates "we could not
  see it" with "it is not there", which is a wrongful-flag liability.
- **A tolerance is stored with its basis** — the First Schedule states maximum permissible
  error as a percentage of declared quantity, while a money tolerance is absolute.
  `Decimal("0.05")` alone is either five paise or five percent, so `tolerance` without
  `tolerance_basis` fails to construct.
- **Rounding increment is a separate field from tolerance** — an increment transforms in
  steps, a tolerance accepts a difference, and they diverge at every boundary. Rule 6(11)
  uses neither; the schema still expresses both, for the rules that do.
- **Python 3.11, not 3.12** — PaddlePaddle and several CV wheels lag on newer releases.
- **The frontend design system is light-ground and light-first** — a state enforcement tool
  read in daylight, not a dark dashboard. Eight states (five field, three verdict) separable
  in greyscale, colour last of four channels. Full tokens and the two contrast findings are
  in `fnt/DESIGN.md`.

## Technical debt

- [ ] **No usable labelled corpus.** After three rounds, a handful of genuinely-annotated
      Indian retail samples, mostly packaged food; cosmetics has effectively nothing. Every
      accuracy target in the PRD is unbacked. Blocks vision, measurement and tamper from
      being evaluated at all. **This is the largest single risk in the project.**
- [ ] `tamper/` has no code. TAM-001 written, not started.
- [ ] `alembic/` not initialised; `core/db.py` deliberately not built until a real caller
      exists to decide session scope. Officers are config-seeded from `OFFICERS`.
- [ ] `rules/` imports nothing from `contracts`; `models.py:21` still carries a stand-in
      comment. That is why `pipeline/rule_snapshot.py` exists as a translation layer.
- [ ] `test_append_only_enforcement` (evidence) resolves a relative path against the cwd and
      passes vacuously if it scans zero files.
- [ ] `measure_margins` raises on a zero margin because `value` is `gt=0`; a declaration
      flush against ink or the crop edge crashes instead of measuring. Owner unavailable.
- [ ] No `npm audit` gate; `npm ci` reports two moderate vulnerabilities and a deprecated
      `glob@11.1.0`.
- [ ] Pan masala (G.S.R. 881(E)) not encoded.
- [ ] `26167` in the same org has no branch protection. Write access there is direct-push.

---

## Standards

This project follows the full engineering standards: repository structure, layer boundaries,
dependency direction, file/function limits, naming, branching, SemVer, API design, deployment
gates, logging, and backend specifics. They live in the `engineering-standards` skill and load
on demand.

**Overrides for this project:**

- Branch base is `main` plus feature branches, not the four-branch develop chain. Eleven
  people, one merger, no staging environment.
- Layers nest inside modules, not modules inside layers. Ownership isolation.
- Repository is named `26034` with no client-project-layer prefix and no `-bck` / `-fnt`
  suffix, because it is a monorepo.
- `.env.example`, not `.env-example`.
