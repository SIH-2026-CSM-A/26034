# Session log — Abhiram

### 2026-09-06 — CTR-003 `ProductCategory` into contracts, plus `CategoryProposal` — Claude Code

**Why now**
EXT-005 gives Sitanshu a `propose_category` in `app/modules/extraction/`. `ProductCategory`
lived in `app/modules/rules/base.py`, and a module may not import another module — so the
ticket as written would have been a ticket bug for him rather than a missing type. Moving the
enum down to `contracts` first turns his ticket into an ordinary one.

**What moved**
- `ProductCategory` is now defined in `app/contracts/enums.py` and exported from the package
  surface. `rules/base.py` re-exports it — one definition, not a copy, because
  `sector_overrides` keys on it and a second copy that drifted would confirm a category which
  then routes to nothing.
- Values stay lowercase (`food`, `cosmetics`, `medical_device`) where every other contracts
  vocabulary is upper. Deliberate: they are the `sector:` keys in `rules.yaml` and the strings
  already written to `scans.product_category`. Upper-casing them would leave every type check
  passing while every sector override matched nothing — a medical device silently evaluated
  against the Rule 7 Table-I that G.S.R. 778(E) disapplies. There is a test for exactly this.
- `CategoryProposal` added to `app/contracts/evidence.py` — `category`, `confidence` (0–1),
  `span_refs` (min 1), `reason` (min 1). `ContractModel` already gives frozen + extra-forbid,
  so a proposal citing no evidence cannot be constructed rather than being discouraged.
  No `propose_category` here; that is EXT-005 and it is Sitanshu's.

**Three things worth knowing**
- **The contracts docstring guard caught the paste.** `test_every_enum_member_documents_its_meaning`
  AST-scans `enums.py` and requires a docstring after every member assignment;
  `ProductCategory`'s three members had none. So the move was not a cut-paste — each member
  needed a sourced docstring, taken from the rules the store already holds as VERIFIED:
  Rule 6(1)(a) Explanation III and the Rule 2(kc) proviso for `FOOD`, the third proviso to
  Rule 6(1)(d) for `COSMETICS`, G.S.R. 778(E) for `MEDICAL_DEVICE`. A free falsification of
  that guard, recorded rather than routed around.
- **The re-export needs the redundant alias.** `from app.contracts import ProductCategory` in
  a non-`__init__` module trips F401 under the selected `F` ruleset and ruff offers to delete
  it; `import X as X` does not. Verified both ways. Deleting the line breaks four files in the
  package — `sector.py`, `conditions.py`, `results.py`, `evaluator.py` — so the line carries a
  comment saying why it exists, and both claims in that comment were checked before it was
  written.
- **Stale bytecode nearly bought a false falsification.** `"medical_device"` and
  `"MEDICAL_DEVICE"` are the same byte length, so the `.pyc` mtime-and-size check treated an
  edited `enums.py` as unchanged and one falsification reported green against a defect that
  was really there. Clear `__pycache__` between falsification steps on this repo; same-length
  edits are the exact case the check cannot see.

**A test I wrote and then deleted**
`test_a_category_proposal_is_not_a_confirmed_category` asserted `not isinstance(proposal,
ProductCategory)` and `proposal.category is not proposal`. Neither can fail — a `StrEnum` with
members cannot be subclassed, and the second is trivially true. It restated the type system,
so it went rather than staying as a decorative green tick. The seven guards that remain were
each made to go red against a real defect and then reverted.

**Deliberately not done**
- `Scan.product_category` stays `String(64)`. Changing it is a migration against a table that
  already holds these strings and buys nothing the 422 at the request boundary does not.
  In TODO.md under Next. The `core/models.py` docstring that justified the string type by
  "core may not import app.modules" *was* fixed here — after this ticket that sentence is
  false, and a file claiming a vocabulary lives where it no longer does is a false claim.
- `rules/base.py` still carries its own `Verdict` and `RuleStatus`, and `Verdict` has already
  drifted from contracts: `POTENTIAL VIOLATION` with a space against `POTENTIAL_VIOLATION`.
  Raised as CTR-004 in TODO.md, Abhiram's, sequenced after this. Not folded in — the database
  enum and every persisted verdict row depend on one of those two spellings.

**Gate**
644 passed, 33 skipped (postgres, no local DSN). `ruff check` clean, `ruff format --check`
clean on 137 files, `lint-imports` 3 contracts kept over 108 files and 346 dependencies, exit
code read directly rather than through a pipe.

### 2026-09-06 — PIP-002 HTTP surface and scan orchestration — Claude Code

**Why now**
There was no `app/main.py` and no `FastAPI()` instance anywhere, so `uvicorn app.main:app`
— the dev command in both `CLAUDE.md` and `AGENTS.md` — did not run. `auth_router` had been
exported since CORE-001 and never mounted, `core/db.py`'s `get_session` had no caller, and
`pipeline/verdict.py` and `rule_snapshot.py` were libraries nothing invoked. Six modules
were merged and none of them were composed. CORE-002 landed the tables that morning, which
was the last thing this was waiting on.

**Done**
- `app/main.py` — the application, CORS restricted to the Vite dev origin from
  `settings.cors_origins`, `auth_router` and the new `scan_router` mounted, and a lifespan
  that verifies the three vision model paths and **refuses to start** if one is missing.
  Not per-request and never a fallback: `detect_pdp` and `extract_panel_text` raise
  `FileNotFoundError` without their weights, and without the gate that surfaces as a 500 on
  an officer's first scan rather than as a boot failure on a fresh clone.
- `pipeline/orchestrator.py` — two entry points, `run_image_scan` and `run_catalogue_scan`,
  sharing an evaluation tail. Not one function with a mode flag: a listing arrives as fields
  rather than pixels, and modelling it as its own path is what keeps a marketplace adapter
  an adapter. Both pure — `evaluated_at` is a parameter, so replaying a scan returns the
  same record.
- `pipeline/dispositions.py`, `rule_findings.py`, `measurement_findings.py`, `findings.py` —
  the judgement half, split four ways by the 300-line limit and along real seams:
  what kind of obligation a rule states, how one rule becomes findings, the one place a
  millimetre may be emitted, and the pass over the active rule set.
- `pipeline/router.py`, `schemas.py`, `repository.py`, `responses.py`, `capture.py`,
  `normalisation.py` — `POST /scans`, `POST /scans/image`, `GET /scans`,
  `GET /scans/{id}`, `POST /scans/{id}/review`.
- `core/schema.py` and `core/enums.py` split out of `models.py`, which was at 299 of 300
  and needed `Scan.product_category` and a `reviews` table. Plumbing to `schema`,
  vocabularies to `enums`, tables stay in `models` (292).
- Migration `c16334c8d865`, hand-written. Autogenerate emitted `CREATE TYPE verdict` for
  `reviews.overridden_verdict` and the upgrade failed with `type "verdict" already exists`;
  the column references the existing type with `create_type=False` and the downgrade drops
  only `review_action`. Full cycle verified: upgrade, downgrade -1, upgrade, downgrade base
  leaving zero enum types and zero tables, clean-slate upgrade, `alembic check` clean.
- `rules/` gained `rule_set_version` on `RuleStoreDocument`, one key in `rules.yaml`, and
  `load_store` / `default_rule_set_version`. Nothing in the repo produced a rule-set version
  at all — PIP-001 took it as a parameter and left the source open — so "every response
  carries the rule-set version" could not have been satisfied without it. It is a property
  of the store, not the deployment, which is why it is not in `config.py`.
- `contracts/binding.py` and `DeclarationRole` — the EXT-004 seam. **Held for Sitanshu's
  agreement before merge**; see below.
- `app.main` added as a fifth import-linter layer. Proved it bites by importing
  `app.main` from `modules/evidence/domain.py`.

**Three things that were wrong and are worth knowing**
- **The schema has foreign keys but no `relationship()`, and SQLAlchemy orders dependent
  inserts from relationships, not from FK columns.** Writing a verdict and its findings in
  one flush inserted the findings first and Postgres rejected them. Reproduced in isolation
  before fixing. `add_verdict` now flushes the parent explicitly. Adding relationships would
  be the textbook fix and is the wrong one here: a relationship on an async mapper
  lazy-loads on attribute access and raises `MissingGreenlet` while the response is being
  serialised, which `core/README.md` already warns about.
- **`VerdictRow.id` is a Python-side column default applied at INSERT**, so reading it
  before the flush handed every finding a null foreign key. Assigned explicitly now, the way
  `new_scan` already did for `Scan`.
- **`session.merge()` triggers an autoflush.** Two merges in the persist path flushed the
  unit of work half-built. The scan is already persistent in that session; it is mutated
  directly now.

**A test claim I corrected rather than the code**
I added a guard asserting `alembic/env.py` must import `Base` from `app.core.models` and not
from `app.core.schema`, on the theory that `schema` alone would hand autogenerate an empty
`MetaData`. **It would not.** Importing `app.core.schema` executes `app/core/__init__.py`
first, which imports `models`, so the metadata is populated either way and no test can be
made to fail on the difference. Both the test and the `env.py` docstring now say what is
actually true. The subprocess `alembic check` test stayed, re-scoped to what it does prove —
drift a same-process check can miss — and was falsified against a model column with no
migration.

**Falsification**
Every guard was made to fail and reverted: 16 defects introduced in total. Four of them
initially **failed to fail**, and all four for the same reason — with no confirmed product
category the sector gate settles a rule before its own builder runs, so a test asserting
something about Rule 7's measurement handling passed whether or not that handling existed.
The tests were rewritten to confirm a category that carves nothing out, or to assert against
a rule the gate does not touch. That trap is now documented at the top of
`tests/pipeline/test_orchestrator.py`, because it will catch the next person too.

**The image path does not work yet, and that is the honest state**
EXT-004 is not merged. `app.modules.extraction` exposes nine `normalise_*(text)` functions
and nothing that maps OCR spans to the obligation each answers, so every declaration on the
image path comes back INSUFFICIENT_EVIDENCE carrying `EXT_004_REASON`, which names the
ticket and the stage. An officer or a court reading that can tell "we could not read this
package" from "this system does not do that yet". A test asserts the exact string and goes
red the day EXT-004 lands, which is the signal to delete it. The catalogue path is fully
functional.

**Held for agreement**
`contracts/binding.py` and `DeclarationRole` ship as their own commit and must not merge
until Sitanshu has agreed the shape — he is mid-way through EXT-004 and would otherwise
build the other half against a different guess. Nothing else depends on them; the
orchestrator does not call a binder today. `BoundDeclaration` carries `field_type`,
`span_refs`, `raw_text`, `role`, `region_id`, `binding_confidence`, and the proposed export
is `bind_declarations(spans: Sequence[ExtractedSpan]) -> tuple[BoundDeclaration, ...]`. It
returns bindings and not `NormalisedField`, so EXT-004 does not re-implement nine merged
functions. `DeclarationRole` mirrors extraction's `AddressRole` member for member, with a
test that fails on drift, so his side is an import swap.

**An executable guard for the sector-gate trap, and a sixth mask it found**
The README note had not stopped it recurring, so the guard is now code.
`tests/pipeline/sector_gate.findings_for_rule` is the only sanctioned way to select a
rule's findings and raises when every finding it returned carries
`UNCONFIRMED_CATEGORY_REASON` — meaning the gate answered, not the builder under test. It
takes no product-category argument deliberately: an argument is a thing a test can pass
wrongly, and the condition is readable off the findings themselves. The reason string was
promoted to a named constant in `rule_findings.py` so the helper imports it rather than
matching a substring that could drift. `test_sector_gate_guard.py` keeps it the only route,
refusing a direct `rule_snapshot.rule_id == "…"` comparison elsewhere in the package.

Writing it found a sixth mask I had not counted:
`test_an_uncalibrated_scan_refuses_every_letter_height_field` ran with no category and
asserted `"was not made" in reason or "not been confirmed" in reason` — it accepted the
gate's own answer, so the measurement path never ran in it. Now confirms food and asserts
the measurement reason specifically.

The first version of the AST predicate matched any `x.rule_id == "literal"` and flagged
`test_rule_snapshot.py`, which asserts about a snapshot it built itself — no gate, no
finding, nothing to mask. Narrowed to comparisons reaching through `.rule_snapshot.`, which
is what distinguishes selecting a finding from asserting on an object.

Falsified four ways: the masked shape written fresh outside the helper (caught
structurally), the same shape through the helper (fails at selection with the explanation),
the gate deleted from production code, and the helper's own selection removed so the
structural guard cannot go vacuous.

**EXT-004 wired**
When this was written PR #44 was still open, and the branch was built against the interface
on `origin/feat/ext-004-span-classification` after reading it rather than against a
description. #44 has since merged as `fe7591e`; the branch is rebased onto it and green.

The gated `contracts/binding.py` commit is dropped entirely — `BoundDeclaration`,
`DeclarationRole` and the `AddressRole` mirror test are gone. That was right regardless of
merge state: the real binder returns `NormalisedField` directly, uses no role enum, and
imports only `DeclarationField`, `ExtractedSpan` and `NormalisedField`, all of which were
already on main. My speculative contracts change was never needed.

`bind_spans` replaces the normalisation stage on the image path — extraction normalises
internally, so stages 4 and 5 are one call. The normalisation adapter stays for the
catalogue path only, where the obligation arrives as a dictionary key rather than as prose
in the text; that is exactly what `identity_established` encodes and `bind_spans` has no key
to read. `EXT_004_REASON` and its test are deleted; an unbound declaration is now
INSUFFICIENT_EVIDENCE because no text on the panel mapped to it, which is a statement about
the photograph. It stays INSUFFICIENT_EVIDENCE rather than becoming FAIL for a reason that
survives the binder being good: nothing can tell a declaration never printed from one
printed and not read.

**`declared` had to become multi-valued.** `bind_spans` returns a `NormalisedField` per
address block and its docstring says in as many words not to pick one — a package bearing
"Manufactured by" and "Marketed by" yields two against Rule 6(1)(a), which is one
obligation. My `Mapping[DeclarationField, NormalisedField]` would have silently dropped the
second. It is now a tuple per obligation, and the finding cites the spans behind all of
them.

**Point 4 exposed a hole that was mine, not EXT-004's.** Nothing persisted spans at all,
classified or otherwise, and `EvidenceEntryRow` had no writer anywhere in the application —
the table shipped in CORE-002 and nothing had ever written to it. `repository.add_evidence_entry`
now hash-chains the verdict together with every span, naming the unplaced ones by id inside
the payload so the distinction is inside the hash rather than alongside it. The payload is
hashed and stored as the same canonical string, which is what `payload_json` being text is
for; falsified by storing a re-serialised copy and watching verification break.

**Verified live, and precisely how.** No YOLO or PaddleOCR weights exist on this machine, so
a genuine model run is still not possible — that half of the gap I flagged is not closed by
EXT-004. What did run: a real JPEG uploaded over HTTP, with only `detect_pdp` and
`extract_panel_text` substituted and everything downstream real. Result — the address bound
from the anchor plus its downward cluster across three spans, net quantity `100 g`, MRP
`₹ 45.00`, seven unbound declarations carrying the new reason, verdict REVIEW, and an
evidence entry holding six spans with `Batch XY-7741` correctly named as unclassified. The
chain verifies. Separately, the empty-weights attempt gave a real end-to-end confirmation of
the failure contract: 500 with the scan id, scan at FAILED, zero verdicts, zero findings,
zero evidence entries.

**Adjusted for VIS-003, ahead of its merge**
VIS-003 makes `extract_panel_text` return `contracts.ExtractedSpan` directly — vision mints
`span_id` (uuid4), sets `source_provider`, and writes `region_id="panel"` — and the local
`vision.ocr.ExtractedSpan` dataclass goes. The pipeline's `_adapt_spans` is deleted; spans
now pass through untouched. Minting an id here as well would give one run of text two
identifiers, and `evidence_span_ids` would cite the one nothing else in the record holds.
`tests/pipeline/test_span_provenance.py` asserts structurally that `app.pipeline` never
constructs an `ExtractedSpan` and never writes `span_id`, `source_provider` or `region_id`
by keyword, by dict key, or by attribute. The first version checked keyword arguments only
and `model_copy(update={"region_id": ...})` — the way anyone would actually do it on a
frozen model — walked straight past; caught by falsifying it, and all three routes are
checked now.

The call stays positional. VIS-003 renamed the parameters to `text_detection_model_dir` and
`text_recognition_model_dir` without changing their order or meaning, so a positional call
is correct against both signatures and this branch does not have to land in lockstep with
theirs. Verified by overlaying their `ocr.py` and running `run_image_scan` end to end
against real contract spans: identity preserved, `region_id` untouched, 65 findings, REVIEW.

`tesseract_tessdata_dir` is a fourth checked model path — VIS-003 makes
`extract_mrp_quantity` raise `FileNotFoundError` without it. The chain does not call that
function yet, because the constrained re-read needs a bound MRP crop and binding is EXT-004;
it is checked at startup regardless, since the point of the gate is that this lands at boot
rather than the first time an officer scans a price.

**`region_id` is left as vision writes it — and the reason is not deference**
The hardcoded `"panel"` looked like something the pipeline should replace with a reference
to the PDP detection. It should not, because `extract_panel_text` is handed the *whole
frame* and not a crop of that detection. The spans were not read off the principal display
panel; they were read off the photograph. Overwriting would put a provenance into the
evidence chain that nothing established — worse than a vague value, in the one field an
export uses to show an officer which crop a reading came from. Two further reasons hold
independently: the field belongs to the layer that knows which image it read, and the moment
vision emits spans from more than one region a pipeline that stamped every span with one
value would erase exactly the distinction the field exists for. Where the panel *was*
detected is recorded once, on `ImageScanResult.panel`. Raised as VIS-004.

**Incomplete / for the next session**
- A full image scan through YOLO and PaddleOCR has no test — weights are gitignored and CI
  has none. The quality-gate rejection path is covered without them, and the catalogue path
  end to end. A `models`-marked set mirroring the `postgres` one is the shape when there are
  cached weights to point at.
- 65 findings per scan, most INSUFFICIENT_EVIDENCE. Truthful — Rule 7 and Rule 9 govern
  every declaration the store requires, and each is its own finding — but heavy to read.
  If it should be narrower, that is a `governs_declarations` field on the rule store, not a
  filter in the pipeline.
- `measure_margins` still raises on a zero margin, so Rule 8(1)'s proviso is not called from
  the chain at all. Owner unavailable; flagged for its own ticket.
- VIS-003's PaddleOCR 3.x constructor against a 2.x call site is still there. The
  orchestrator is its first real caller and is where it will surface.
- `ScanStatus.PROCESSING` is never written. Nothing can observe it in a synchronous
  request; it stays in the enum for the queue.

### 2026-09-06 — RUL-003 multi-piece package, definition 2(kc) — Claude Code

**Why now**
RUL-002 encoded 2(ka) and 2(kb) from G.S.R. 722(E) and deliberately left 2(kc) out, which
was tracked as a deferral line in ARCHITECTURE.md rather than left as a silent absence.
This is that line being closed. The definition matters beyond completeness: a multi-piece
package's pieces are individually labelled and individually saleable, which is what
decides whether an inner piece has to stand as a retail package in its own right.

**Done**
- `data/rules.yaml` — `R2-KC-MULTI-PIECE-PACKAGE` (Rule 2(kc)) and
  `R2-KC-MULTI-PIECE-FOOD` (its proviso), both citing
  `GSR-722E__2023-10-06__amendment-rules-2023.pdf`, effective 2024-01-01, severity REVIEW.
- `PackageDefinitionCondition` gained `constituents_individually_packaged_or_labelled` and
  `retail_sale_of_individual_pieces_permitted`. Both are `false` on 2(ka) and 2(kb),
  because neither clause states either limb — the fields record what a clause says, not
  what could be inferred about it.
- `ConstituentSimilarity.IDENTICAL` completes the axis, so the three definitions are
  mutually exclusive on one field and no package can satisfy two of them.
- `SectorOverrideCondition.package_type` (optional, `None` = any package type) and the
  matching keyword on `sector_overrides`, `controlling_framework`,
  `rule_33_relaxation_applies` and `pdp_declaration_mandatory`.
- `sector.py` grew a single `_applicable()` that defines "does this override apply" once.
  `rule_33_relaxation_applies` had been re-implementing the same four checks; a second
  copy is how a scoped override fires in one reader and not the other.

**Decisions**
- The proviso to 2(kc) is its own rule, not a field on the definition. It has its own
  gazette text and its own scope, and the next scoped proviso is now a YAML rule rather
  than a branch in an evaluator.
- That proviso is scoped by `package_type`. Both it and `R6-1-A-EXPL-III-FOOD` route food
  to the FSSA 2006, but Explanation III applies to every food package while 2(kc)'s
  proviso applies only to multi-piece ones. An unscoped override would have fired on every
  food package and claimed a routing G.S.R. 722(E) does not support. The rule id is what
  distinguishes the two in a finding, since the framework string is identical.

**Not encoded, and why**
- **No multi-piece outer-wrapper rule.** G.S.R. 722(E) does not amend rule 9, and
  "multi-piece package" appears nowhere in the Maharashtra compilation or in any other
  gazette in `rules-corpus/` — three occurrences in the whole corpus, all in G.S.R.
  722(E). Rule 9(3) already applies generally to any package with an outside container.
  The two new definition fields are the hook a future ticket would join on; that join is
  not in the gazette and was not invented. `test_the_gazette_states_no_multi_piece_outer_wrapper_rule`
  pins this.
- **Rule 6(11).** Paragraph 4 of G.S.R. 722(E) exempts combination, group and multi-piece
  packages from the unit sale price declaration. It is the only other multi-piece-specific
  obligation in the instrument and it is deliberately out of the store — Rule 6(11) is a
  format rule stating no tolerance and no rounding increment.

**Verification**
520 passed / 2 skipped, ruff clean, `lint-imports` 3 kept 0 broken. Mutation-checked the
scoping by deleting the `package_type` guard in `_applicable()`: three tests fail,
including RUL-002's `test_a_sector_override_moves_only_the_obligations_it_names`.

**Outstanding**
- RUL-002 has no entry in this log — it merged as PR #32 before the docs PR was written.
  Worth backfilling alongside `TODO.md`, which is still not updated for either ticket.

### 2026-09-06 — FNT-002 officer design system, verdict detail, review queue — Claude Code

**Why now**
FNT-001 left a Vite scaffold and nothing an officer could look at. The verdict surface is
the part of this system a judge actually sees, and a generic component-library look would
undercut the claim that the tool was designed for Legal Metrology work rather than
assembled from defaults.

**Done**
- `fnt/DESIGN.md` — the palette, the state colours and every contrast measurement, written
  down rather than implied by the CSS.
- Officer surface: verdict detail and review queue, on the three-verdict vocabulary.

**Decisions**
- **Fixture citations follow `rules.yaml` on `main`, not the ticket text.** The encoded
  rule set is authoritative; a ticket description is a brief. Concretely, Rule 8's
  free-space limb cites **Rule 8(1) proviso**, not Rule 8(1) — RUL-002 split placement and
  free space into two rules with two evidence requirements, and a fixture citing 8(1) for
  a clearance measurement would be wrong on screen and wrong in a screenshot.

**Rejected**
- **Lightening the focus tint** to fix Query Ochre at 3.97:1. A focus signal measured at
  1.04:1 against Field Paper is not a signal. Fixed instead by grounding unfilled chips on
  an explicit Field Paper background so they stop inheriting the row tint.
- Leaving the hatch under chip labels. Text over a hatch line measures **3.4:1**; a hatched
  ground is a legitimate channel but not underneath a letterform. Fixed with an inset
  plate rather than by removing the hatch, which carries meaning of its own.

Both findings and both numbers are recorded in `DESIGN.md` so the next person changing a
colour has the measurements rather than the conclusion.

---

### 2026-09-06 — RUL-002 Rule 8, Rule 9, sector overrides, medical devices — Claude Code

**Why now**
`ARCHITECTURE.md` carried two technical-debt bullets that were both real bugs: Rule 7
Table-I encoded as a universal lookup, and Combination and Group packages absent from the
schema entirely. The first one produces a wrong finding, not just a missing feature.

**Done**
- Rule 8 and Rule 9 as four separate rules with four condition kinds —
  `R8-1-PDP-PLACEMENT`, `R8-1-FREE-SPACE`, `R9-1-MANNER`, `R9-3-OUTER-CONTAINER`. Rule 8
  is *where* a declaration appears, Rule 9 is *how*; different evidence, different
  consequences, never one check.
- `evaluate_rule8_free_space()` reads the 1x and 2x multiples from the store, not from
  Python, and names which sides fell short. `FreeSpaceMeasurement` fields are
  `PositiveDecimal`, so an absent clearance arriving as zero fails to construct rather
  than passing.
- `sector.py` — sector overrides as a table built by reading the rule store. Medical
  devices from G.S.R. 778(E); food to the FSSA 2006 via Rule 6(1)(a) Explanation III;
  cosmetics to the Drugs and Cosmetics Rules 1945 via the third proviso to Rule 6(1)(d).
- Combination (2(ka)) and Group (2(kb)) packages from G.S.R. 722(E).
- Schema split three ways — `base.py`, `conditions.py`, `models.py` — because `models.py`
  was heading past the 300-line limit and `conditions` importing `models` while `models`
  needs `RuleCondition` is a cycle.
- The one authorised cross-directory edit: `pipeline/rule_snapshot.py`'s deep import of
  `app.modules.rules.models` folded into the package import, now that `Severity` and
  `DeclarationRequiredCondition` are on the public surface.

**Decisions**
- **`Rule7Route` generalised** from `LMPC_TABLE_I` / `MEDICAL_DEVICES_RULES_2017` to
  `LMPC_TABLE_I` / `SECTOR_FRAMEWORK`. A route enum carrying one sector's answer is an
  if/else chain in disguise — the next sector would mean editing the enum and every
  comparison against it. Which framework took over now travels by value on
  `SectorOverride`, with the rule id that says so.
- **The medical-device guard lives in `minimum_character_height()`**, not at the two
  evaluator callsites. That function is exported and was sector-blind, which is the
  *actual* bug: a caller reaching it directly gets a Rule 7 band applied to a package the
  rule does not reach. One guard there covers every caller.
- Medical devices are a **carve-out, not a stricter path**. A device measured below a
  Table-I band is `REVIEW`, not `POTENTIAL VIOLATION` — no MDR 2017 thresholds are encoded
  and none were invented.

**Rejected**
- **Leaving the guard at the two evaluator callsites.** That fixes two symptoms and leaves
  every other caller of the public lookup broken.
- **Adding any new `declaration_required` rule.** `tests/pipeline/test_rule_snapshot.py`
  asserts `set(DECLARATION_FIELDS) == encoded` exactly, so a new declaration string would
  have forced an edit to pipeline's map — outside this ticket. Every new rule got its own
  condition kind instead, which is the better modelling anyway: Rule 8(1)'s evidence is a
  measurement, not a text span.
- **Rule 6(11).** Format rule, no tolerance, no rounding increment. Untouched.

---

### 2026-09-06 — CTR-003 deep-copy rule parameters into the snapshot — Claude Code

**Why now**
PIP-001 shipped `snapshot_from_rule` with a `deepcopy` whose justification was weaker than
its docstring implied. Either it was load-bearing and needed a test, or it was not and the
docstring needed correcting. It was the second.

**Done**
- `parameters` deep-copied into `RuleParameterSnapshot`, and the isolation claim in the
  docstring corrected to state what actually holds.

**Decisions**
- **The deepcopy is not what provides isolation today.** `parameters` is typed
  `dict[str, JsonValue]`, and re-validation on construction rebuilds every container, so
  the property would hold without it. It ships as **annotation-independence**: if the
  annotation is ever widened to `dict[str, Any]`, re-validation stops rebuilding and the
  deepcopy becomes the only thing standing between a snapshot and the rule it came from.
- **The test pins the property, and cannot fail under the current annotation.** That is
  stated in the test's own docstring rather than left for a reader to discover by deleting
  the deepcopy and watching nothing break. A test that cannot currently fail is worth
  keeping only if it says so.

**Rejected**
- Deleting the deepcopy as dead weight. The cost is one copy per snapshot; the failure it
  guards against is a verdict record silently re-adjudicating itself after an amendment,
  which is the exact thing snapshotting exists to prevent.

---

### 2026-09-06 — CI-002 frontend build gate — Claude Code

**Why now**
`fnt/` had no CI at all. Backend changes were gated and frontend changes were not, so a
frontend PR could merge without ever having been built.

**Done**
- Build gate on `fnt/**` pull requests, pathed so backend-only PRs do not run it and do
  not wait on it.

**Rejected**
- Running the frontend job on every PR regardless of path. It would add a required check
  to backend PRs that tells nobody anything, and eleven people opening PRs continuously
  makes wasted CI minutes real rather than theoretical.

---

### 2026-09-06 — PIP-001 verdict assembly and rule parameter snapshot — Claude Code

**Why now**
`contracts` v1 shipped `VerdictRecord` and `RuleParameterSnapshot` with nothing building
either. The rules module models a rule richly and contracts models it flatly, and the
translation between the two had to live in exactly one place before anything downstream
depended on it.

**Done**
- `pipeline/rule_snapshot.py` — the rules `RuleDefinition` to `contracts`
  `RuleParameterSnapshot` adapter, and the only place that translation happens.
- `pipeline/verdict.py` — `derive_verdict` and `assemble_verdict`.

**Decisions**
- **`derive_verdict` and `assemble_verdict` are two functions, not one**, because
  `VerdictRecord.findings` is `min_length=1`. The spec said "zero findings returns
  `REVIEW`", and a record with zero findings cannot be constructed — so that sentence
  cannot describe a `VerdictRecord`-returning function. `derive_verdict` takes a sequence
  and returns a `Verdict`, so the empty case has somewhere to live; `assemble_verdict`
  builds the record and requires at least one finding. **The contract won and the spec
  bent**, which is the right way round: a record with no findings behind it has no
  evidence chain.
- An unmapped declaration string raises `UnmappedDeclarationError` rather than being
  skipped. A dropped declaration is a finding that silently never gets made, which reads
  downstream as a package with nothing wrong with it.
- A tolerance with no basis raises `UnbasedToleranceError`. `Decimal("0.05")` alone is
  five paise or five percent.

**Rejected**
- Collapsing the two verdict functions and returning `None` for the empty case. It pushes
  a null check onto every caller to preserve a sentence in a ticket.
- Copying a bare tolerance figure into the snapshot. It would rebuild the ambiguity one
  layer down, where nothing checks it.

---

### 2026-09-06 — CORE-001 auth, RBAC, jurisdiction scoping — Claude Code

**Why now**
Nothing downstream was blocked on auth, which is why it waited until contracts landed. It
was built now because a scan pipeline with no access control is not demoable to a
government evaluator, and because a generic three-role RBAC scheme reads as a system
designed without talking to the department.

**Done**
- `bck/app/core/rbac.py` — `RoleTier` (`STATE`/`REGIONAL`/`DISTRICT`), one ordered
  `StrEnum` where declaration order *is* the hierarchy and each member's value *is* the
  jurisdiction column it pins. `rank`, `scope_fields` and `covers()` all derive from
  position, so the "each tier is one level narrower" property cannot drift. No
  `is_controller()`/`is_deputy()`/`is_inspector()` triplet to keep in sync.
- `Jurisdiction` and `Principal`, both on `ContractModel` (frozen, `extra="forbid"`).
  `Principal` validates that the jurisdiction fills exactly its tier's depth, in both
  directions. Load-bearing: a `DISTRICT` principal with `district=None` would produce a
  filter one predicate short and quietly see its whole region, so it cannot be constructed.
- `scope_to_jurisdiction(statement, principal, entity)` — ANDs one equality predicate per
  pinned level onto a real SQLAlchemy `select()`. `getattr` on a missing column raises
  rather than silently returning an unfiltered query.
- `bck/app/core/config.py` — the first `Settings` (pydantic-settings), covering the keys
  `.env.example` already declared plus JWT, `role_designations`, `cost_ceilings` and
  `officers`. `get_settings()` is `lru_cache`d. `jwt_secret` has no default and a
  32-byte minimum: a missing key fails at startup rather than shipping a guessable one.
- `settings.cost_ceiling(provider)` — the single surface AGENTS.md's "never call a paid
  API without the cost ceiling in `core/config.py`" deny rule refers to. It existed only
  as a rule until now. `CLOUD_OCR` ships at `Decimal("0")`, keyed by the existing
  `EvidenceProvider` vocabulary rather than a fresh one. Unknown provider raises rather
  than defaulting to something permissive.
- `bck/app/core/auth.py` — OAuth2 password flow + JWT per ARCHITECTURE.md's stack row.
  bcrypt hashing, `create_access_token`, `principal_from_token`, the
  `get_current_principal` dependency, a `require_tier(minimum)` factory, and
  `POST /auth/token` on `auth_router`. Decoding pins an explicit algorithm allowlist and
  requires `exp`, then rebuilds the `Principal` through its own validation — so a
  tampered jurisdiction is refused even when the signature is intact.
- `bck/tests/core/` — 41 tests, each run twice (82) via an autouse parameterised fixture.

**Decided**
- **Designations are config, tiers are code.** `SIH26034_TI.md` flags that nomenclature
  varies by state and the pilot state is not chosen. The three structural levels are
  fixed; every title comes from `Settings.designation(tier)` via `ROLE_DESIGNATIONS`.
  Nothing outside the default dict in `config.py` spells "Controller" or "Inspector".
- **The config-swap test is a parameterised autouse fixture, not an assertion.** Asserting
  a config value changed proves nothing. Every test in `tests/core/` is collected once per
  naming profile, so the whole permission and scoping suite runs against both. The second
  profile is invented for the test and shares no word with the default — it is explicitly
  not a claim about any state's actual titles.
- **The scoping test runs a real query.** In-memory SQLite (stdlib driver, no new
  dependency), a mapped `ScanRecord` table, records across two states / two regions /
  three districts, and absence assertions on the rows that come back — not a call to the
  permission function. Verified by mutation: making `scope_to_jurisdiction` a no-op fails
  12 tests; hardcoding a designation fails the profile-swapped run only.
- **Config-seeded officers, no users table.** Credentials are configuration until there
  is a schema to hold them. `OFFICERS` is empty by default — a deployment that configures
  none has no accounts, rather than a default account somebody forgets to remove. The
  token and dependency surface does not change when a DB-backed store replaces it.
- **No refresh token.** FastAPI's own password-flow pattern has none, and a second
  credential lifetime is a second thing to get wrong.
- Three new dependencies: `pyjwt`, `bcrypt`, and `python-multipart` — the last is required
  by `OAuth2PasswordRequestForm`, so it comes with the approved password flow rather than
  as a separate choice. No `httpx`: dependencies and route handlers are tested as the
  callables they are.
- No new import-linter contract. The existing layers contract already places `app.core`
  below `app.modules`; probed it by adding a `from app.modules.rules import loader` to
  `core/rbac.py` and confirming `lint-imports` reports BROKEN, then removed it.

**Incomplete**
- No `core/db.py`. There is still no engine or session factory, and no `app/main.py` to
  mount `auth_router` on — the router is exercised by calling its handler directly.
  Whoever first needs a request-scoped session adds it.
- `scope_to_jurisdiction` constrains the statement it is handed. A caller that never calls
  it is unscoped and nothing catches that. The fix is a repository layer that owns the
  session and applies it on the way past — noted in the function's own docstring, and it
  needs a persistence layer to exist first.
- Officers live in `OFFICERS` rather than a table. A users migration is a separate ticket.
- Branch was rebased onto `origin/main` (c5a9d6e) before merge — carries EVD-002's `boto3`, VIS-002's vision dependencies, and EXT-003.

### 2026-09-05 — CTR-002 contracts v1 — Claude Code

**Done**
- `bck/app/contracts/` v1, six modules behind one import surface: `base.py`
  (`ContractModel`, `extra="forbid"` + `frozen=True`), `enums.py`, `evidence.py`,
  `measurement.py`, `rules.py`, `records.py`, re-exported from `__init__.py` with
  `__all__` so consumers write `from app.contracts import X` and file moves inside the
  package are not a nine-way breaking change.
- `bck/tests/contracts/test_contracts.py` — 36 tests, written as the properties the
  other tickets depend on rather than as field-spelling checks.
- Naming sweep: product name settled as **PCCS — Packaged Commodity Compliance System**
  across README, ARCHITECTURE, AGENTS, CLAUDE and TODO. The case-insensitive sweep for
  the old placeholder name is clean from the repo root.

**Decided**
- `DeclarationField` is one member per Rule 6 clause, not per role. 6(1)(a) is a single
  obligation covering manufacturer, packer and importer, and by Explanation II the
  marketer or brand owner too. Which role a declaration was made under is a property of
  the extracted value — `AddressRole` in extraction already models it. Rejected fifteen
  role-shaped members: it turns one obligation into five findings an officer has to
  reconcile. Clause letters read out of the Maharashtra compilation during the ticket,
  not from memory.
- Measurement variant names stay Yashashvi's — `MeasurementExact` /
  `MeasurementCalibrated` / `MeasurementRefusal`, discriminated on `mode`. The ticket
  offered `ExactFromArtwork` / `CalibratedEstimate` / `Refused`. Rejected, because her
  MEA-001 shape is merged and tested and matching it exactly makes MEA-002 a
  delete-and-import instead of a rewrite. Verified field-for-field and by replaying every
  construction site in her `services.py` against the contracts models.
- `tolerance` requires `tolerance_basis`. The First Schedule states maximum permissible
  error as a percentage of declared quantity; a money tolerance is an absolute amount.
  `Decimal("0.05")` alone is either five paise or five percent, so a bare figure now
  fails to construct. Rejected storing one pre-resolved number — it cannot be re-derived
  from the gazette text afterwards.
- `rounding_increment` and `tolerance` are separate fields. An increment transforms a
  value in steps, a tolerance accepts a difference; they diverge at every boundary. Rule
  6(11) uses neither — `rules-corpus/README.md` establishes it is a format rule — but
  the schema has to express both for the rules that do.
- `EvidenceProvider` is a closed enum rather than a free string. Cost: Akshaya files a
  contracts ticket to add a provider. Benefit: the evidence chain cannot carry "paddle",
  "PaddleOCR" and "paddleocr" as three providers.
- `VerdictRecord` carries no `rule_definition_id` or `rule_set_id` and a test asserts the
  field names stay absent. Snapshots go on via `RuleParameterSnapshot.from_rule()`.
- Two deliberate departures from the ticket's field list, both flagged in the PR:
  `NormalisedField.span_refs` is plural, because an address is read as several spans and
  a singular ref leaves the evidence chain unable to cite what was used; and
  `numeric_value: Decimal | None` sits alongside `normalised_value: str`, because PR #4
  review already forced `NetQuantityValue.value` to `Decimal` for First Schedule
  comparisons and re-parsing a number out of a string at each comparison site undoes that.

**Hit**
- Another session committed on this branch mid-ticket: `docs: sync HANDOFF and TICKETS`
  landed on `feature/26034-CTR-002-contracts-v1`, was moved to `docs/sync-handoff-tickets`,
  and the branch was `reset --hard HEAD~1`. The reset reverted every edit I had made to
  *tracked* files — the contracts `__init__.py` and README, and the four doc headings —
  while the new untracked modules survived and were committed as a WIP checkpoint. Redone
  and verified. This is the hazard AGENTS.md warns about; a worktree would have prevented
  it, and I should use one whenever another agent is live on this repo.
- That sync commit also added a HANDOFF.md note quoting the old placeholder product name
  literally, which trips the CTR-002 sweep. It is not on this branch, so it is not mine to
  fix here — `docs/sync-handoff-tickets` needs the note rephrased before it merges, or
  the naming sweep goes dirty again on main.

**Verified rather than assumed**
- Mutation-tested the four guard tests: added a documented sixth `FieldState` member, a
  documented fourth `Verdict` member, an undocumented enum member, and a `rule_set_id`
  field on `VerdictRecord`. Each made exactly the intended test fail; each was reverted.
  A test that passes the moment it is written is a test that has not been shown to fail.
- Proved the import boundary instead of eyeballing it: added `from app.core import ...`
  and then `from app.modules.measurement import ...` to a contracts module. `lint-imports`
  exited 1 naming the violation both times, exits 0 clean.

**Review round 1 — three defects fixed, one citation corrected**
- Rebased onto `main`; MEA-002 merged as #13 while this PR was open, which is what
  surfaced the first two.
- `MeasurementExact` was missing `rule_limb`. MEA-002 added it and
  `calculate_pdp_area`'s artwork branch constructs with it, so `extra="forbid"` would
  have raised the moment she swapped. Added, matching `MeasurementCalibrated`.
- `confidence_interval` was `gt=0`, but `measure_contrast_ratio` returns exactly 0.0 for
  a zero-variance crop and her merged test asserts that value. Relaxed to `ge=0`;
  negative still rejected. Being strict here would have pushed a real measurement into
  INSUFFICIENT_EVIDENCE, which is the exact confusion this project must not make.
- `COUNTRY_OF_ORIGIN` citation checked against the corpus rather than reconciled by
  preference. Rule 6(1)(aa) is the package declaration — "shall be mentioned on the
  package". G.S.R. 128(E) does not touch 6(1): it inserts **Rule 6(10A)** (in force
  01.07.2026, substituted by G.S.R. 312(E) from 01.07.2027), obliging an *e-commerce
  entity* to provide a searchable and sortable country-of-origin filter in listings.
  Two different provisions with two different targets, so the docstring documents both
  and says which one this field is. Neither routes through 6(1)(g).
  **`datasets/schema.py` (DAT-001, merged) cites "Rule 6(1)(g) / GSR 128(E)" for this
  field and is wrong on both limbs — Aashritha's file, raised not edited.**
- Struck the F18 unit-sale-price tolerance blocker from ARCHITECTURE.md and TODO.md.
  COR-001 resolved it: Rule 6(11) is a format rule with no tolerance and no rounding
  increment, and the ±₹0.01 / ±₹0.05 figures were assumptions, not law.
- Verified the swap end-to-end rather than by inspection: ran Yashashvi's merged
  measurement suite with the contracts models substituted for her local ones. All 8
  pass. MEA-002 is a delete-and-import.

**Incomplete**
- `tamper/` and `evidence/` have no contract types of their own yet — nothing crosses a
  boundary from them until EVD-002 and the tamper ticket exist. Deliberate, not forgotten.
- `PackageShape` stays local to measurement. It does not cross a boundary today; the rules
  module consumes a PDP *area*, not a shape.

### 2026-09-05 — VP-CI-001 repo scaffold — Claude Code

**Done**
- `bck/` package skeleton: `contracts`, `core`, `pipeline`, and six module packages under
  `modules/`. Every directory has a README naming its owner.
- `bck/pyproject.toml` — Python 3.11, uv, FastAPI stack, dev group, ruff (line 100,
  py311, E/F/I/N/UP/B/SIM), and the two import-linter contracts.
- `.github/workflows/ci.yml` — ruff check, ruff format --check, lint-imports, pytest on
  every PR, with uv cached against `bck/uv.lock`.
- `.github/CODEOWNERS`, `.gitignore`, `bck/.env.example`, `AGENTS.md`, root `README.md`.
- Fixed `.github/workflows/claude.yml` re-triggering on its own replies
  (`github.actor != 'claude'` guard around the existing condition).
- Verified the boundary rather than assuming it: added
  `from app.modules import rules` to `vision/__init__.py`, `lint-imports` exited 1 naming
  the violation, removed it, re-ran the full set green. Also confirmed
  `test_import_boundaries.py` fails when a module package exists without a contract entry.

**Decided**
- Layers nest inside each module (`router.py`/`service.py`/`repository.py`/`schemas.py`),
  not as top-level `api/`/`services/`/`repositories/`. Deviation from T3 §4, recorded in
  AGENTS.md. Reason: ten owners; horizontal layers make every ticket a three-way
  ownership collision. Rejected the T3 layout for that reason — do not re-propose it.
- Base branch is `main`. T4's develop→staging→release→production chain is superseded here;
  one environment does not justify a four-branch promotion chain.
- No empty `router.py`/`service.py` files. The ticket bars stubs, so the layer convention
  is documented in each module README instead of pre-created as empty files.
- `bck` is installed as a real package (hatchling) rather than relying on cwd being on
  `sys.path` — `lint-imports` is a console script and would not have found `app` otherwise.
- Rejected a `docs/` directory (T3 §3 checklist) for now — nothing to put in it yet, and
  an empty one is exactly the placeholder the ticket rules out.

**Incomplete**
- Alembic not initialised — `bck/alembic/` is `.gitkeep` + README. Separate ticket.
- No application entrypoint; `uv run uvicorn app.main:app` in the README is the target,
  not something that runs today.
- GitHub usernames unconfirmed for `measurement` and `rules`; both fall back to
  @Abhiram-0910 in CODEOWNERS and AGENTS.md. Update both files together when known.
- Branch protection on `main` (PR-only, CI green) is a GitHub settings change, not a file
  — still needs doing in the repo settings.

---

## 2026-09-06 — CORE-002 persistence (Claude Code, Opus 5)

Branch `core-002-persistence`. Closes the two-part debt item left by CORE-001: `alembic/`
was `.gitkeep` + README, and `core/db.py` was deliberately unbuilt because no caller
existed to decide session scope. PIP-002 is that caller.

**Built**
- `app/core/db.py` — async engine, session factory, one request-scoped `get_session`.
  Both factories `lru_cache`d like `get_settings`, so importing `app.core` opens no pool
  and a missing `DATABASE_URL` fails at first use naming the setting. No module-level
  engine or session.
- `app/core/models.py` — `Scan`, `VerdictRow`, `FieldFindingRow`, `EvidenceEntryRow`,
  plus `ScanSourceType` / `ScanStatus` / `CalibrationMethod`. 298 lines, under the limit.
- `alembic.ini`, `alembic/env.py`, one revision `64a9392a6859`.
- `docker-compose.yml` (repo root) — `db` only, `pgvector/pgvector:pg16`.
- `.github/workflows/ci.yml` — a `postgres` service on the same image, plus
  `DATABASE_URL`/`JWT_SECRET` on the test step.
- `tests/core/test_persistence.py` (SQLite, portable) and `tests/persistence/`
  (postgres-marked, skips when unreachable).

**Decided**
- **One session per request; the caller commits, the dependency does not.** A
  teardown-commit fires after the response body is built, where a failure can no longer
  change the status code, and it commits work a handler may have abandoned.
  `expire_on_commit=False` because a post-commit attribute read otherwise raises
  `MissingGreenlet` mid-serialisation. `pool_pre_ping=True` because the demo laptop sleeps.
- **One DSN string for both modes.** `postgresql+psycopg://` is valid for `create_engine`
  and `create_async_engine` alike; the app runs async, `env.py` runs the same string
  synchronously. No URL rewriting, no async Alembic template, no new dependency —
  psycopg 3 and greenlet were already in the lock.
- **JSONB where the shape varies and nothing joins on it** (`image_refs`,
  `capture_metadata`, `field_providers`, `rule_snapshot`, `evidence_span_ids`,
  `evidence_regions`); typed everywhere something filters or constrains.
- **`calibration_method` is a typed column, not a key in `capture_metadata`** — it gates
  whether a millimetre figure may be emitted at all, so it is constrained and queryable.
- **`evidence_entries.timestamp` is text and the payload is text, not `timestamptz` and
  not `jsonb`.** `compute_entry_hash` hashes the timestamp *string* and
  `compute_payload_hash` hashes canonical JSON bytes; both column types re-render what
  they store, and re-rendered bytes hash differently. Storing them as text is the only
  shape where a reloaded chain verifies.
- **Snapshot goes on `FieldFindingRow`, not `VerdictRow`** — the ticket said VerdictRow,
  but in `contracts` a snapshot hangs off each `FieldFinding`, and findings under one
  verdict can cite different rules. One snapshot per verdict would lose rules.
- **`EvidenceEntryRow`, not `EvidenceEntry`** — the latter already exists as a frozen
  pydantic type in `modules/evidence/domain.py`.
- Ticket's `EvidenceEntry` column list (`hash`, `prev_hash`, `storage_ref`) was
  incomplete: `verify_chain` also needs `sequence`, `timestamp`, `payload_hash`,
  `entry_hash` and the payload. Persisted the full entry.
- `models.py` in `core/` contradicts `core/README.md`'s "no business rules". Kept it there
  — no module owns persistence, modules cannot import each other, Alembic needs one
  `MetaData` — and said so in the README rather than leaving the contradiction silent.

**Proved able to fail** (introduced the defect, confirmed red, reverted — nine in all)
- Renaming `Scan.district` away → the scoping tests cannot even collect.
- `server_default="FAIL"` on `field_findings.state` → the schema-property test red.
- Enum column replaced by a bare `String` → the round-trip and INSUFFICIENT_EVIDENCE
  tests red. `StrEnum` compares equal to its own value, so that test carries an explicit
  `isinstance` assertion; without it the substitution would have passed.
- Reloading the snapshot from the live rule instead of from storage → snapshot test red.
- Non-canonical JSON on the way to storage → chain verification red.
- A `rule_id` column, and a foreign key to a non-`scans` table, on `verdicts` → red.
- Removing the enum drops from the migration downgrade → `type "scan_source_type" already
  exists` on the next upgrade, exactly as predicted; the migration test goes red.
- Removing `UniqueConstraint(scan_id, sequence)` → the duplicate-entry test red.
- `alembic check` has its own guard-the-guard: a column dropped behind Alembic's back,
  asserting `check` reports it. Without that, a `check` comparing nothing would look
  identical to a clean one.

**Gate** — 557 passed / 2 skipped with a database, 551 / 8 without (the 6 postgres tests
skip cleanly). ruff clean, format clean, `lint-imports` 3 kept / 0 broken, all exit codes
read directly rather than through a pipe.

**Compose verified on the real image** (same session, after WSL integration was enabled)

`docker compose down -v` → `up -d db` → `alembic upgrade head` on a clean volume, against
`pgvector/pgvector:pg16`, server reporting `PostgreSQL 16.13`. Then `alembic check` clean,
`downgrade base` leaving zero enum types, `upgrade head` again, `pytest -m postgres` 6/6,
and the full suite 557 passed / 2 skipped. ruff, format and `lint-imports` all exit 0.
**Nothing behaved differently on 16 from the 18.6 run** — same DDL, same `alembic check`
result, same six tests, same failure classes from the falsifications.

**`localhost:5432` does not reach the container on this machine.** The system PostgreSQL
18 cluster holds `127.0.0.1:5432` and shadows Docker's `0.0.0.0:5432` publish, so the
default DSN in `.env.example` silently hits the local cluster instead — it happens to fail
authentication rather than connecting, which is luck, not a safeguard. Everything above ran
with `POSTGRES_PORT=5433` and `DATABASE_URL=...@localhost:5433/pccs`; the compose file
already parameterises the host port for exactly this. Either stop the local cluster or
export `POSTGRES_PORT`. Worth knowing before someone trusts a green run on 5432.

**Correction to the falsification record above.** Two of the nine were not valid as first
run, and were redone properly on pg16:

- *Enum column replaced by a `String`* and *`UniqueConstraint` removed* were originally
  applied to `app/core/models.py` only. The schema comes from the **migration**, not the
  model, so in both cases the constraint was still present in the database and the test was
  never actually deprived of what it tests. The first attempt showed an ERROR (the
  model/migration disagreement, which is `alembic check`'s job) and the second showed a
  PASS. Neither proved the guard.
- Redone by editing the migration as well: removing `UniqueConstraint` gives
  `Failed: DID NOT RAISE IntegrityError`, and making `field_state` a `VARCHAR` so the type
  is never created gives `assert isinstance(..., InvalidTextRepresentation)` → `assert
  False`, because the cast then fails with `UndefinedObject` instead. Both red. That second
  one is precisely what the `isinstance` assertion was added for — a bare
  `pytest.raises(DBAPIError)` would have passed against a schema with no enum type in it.

The lesson worth carrying: **a guard on a database constraint is only falsified by editing
the migration.** Editing the model tests Alembic's drift check, which is a different guard.

**Two changes during review of PR #40** (same session)

- **`field_findings.rule_id`** as `String(120)`, NOT NULL, indexed, plus
  `UniqueConstraint(verdict_id, field, rule_id)`. `(verdict_id, field)` is correctly not
  unique — one declaration against several rules is several findings — but the triple is,
  and that cannot be stated while `rule_id` lives only inside the snapshot JSONB. F32
  (violation rate by rule clause, P0) filters on it, which puts it on the typed side of
  the line this schema already draws. Written from `rule_snapshot["rule_id"]` and nowhere
  else; the round-trip test asserts the column and the document agree, since that
  agreement is the whole basis for querying by it. Revision `64a9392a6859` amended in
  place rather than stacked — nothing was merged, so there was no history to preserve.
  Falsified by removing the constraint **from the migration**: `DID NOT RAISE
  IntegrityError`. `models.py` went to 318 lines doing this and was trimmed back to 299
  by moving duplicated rationale into `core/README.md`, which the module docstring
  already names as its home.
- **Enum value drift guard.** `alembic check` compares tables and columns and is blind to
  the labels inside an enum type that already exists. Confirmed directly: adding
  `BARCODE` to `contracts.DeclarationField` leaves `check` reporting "No new upgrade
  operations detected", and the failure would surface later as `invalid input value for
  enum declaration_field` at the first insert. PIP-002 touches every declaration field, so
  this was live rather than hypothetical. New postgres-marked test reads labels out of
  `pg_enum` and asserts they equal the Python members for all six types. Falsified twice —
  once via `contracts.DeclarationField` (the real scenario) and once via a `models.py`-local
  enum to isolate it from the other tests that a contracts change also turns red.
  Adding an enum member from here on needs a hand-written `ALTER TYPE ... ADD VALUE`
  revision, which cannot run inside a transaction; noted in `alembic/README.md` and
  `HANDOFF.md`.

**Incomplete / for the next session**
- No `app/main.py` still. Added to TODO under PIP-002 — see the note there.
- MinIO and Redis are not in compose, so `test_minio_storage.py` still skips everywhere.
- `.env.example` ships the DSN on port 5432. Fine for CI and a clean machine; see the port
  note above for a laptop already running PostgreSQL.

---

## 2026-09-06 — session 4 handoff docs (Claude Code)

Docs-only ticket on `docs-handoff-session4`. No application code touched.

**What was done**
- Merged `HANDOFF-addendum-2026-09-06-session4.md` into `HANDOFF.md` section by section,
  under the existing headings, with the superseded lines removed rather than left alongside.
  Verified `Legal findings` (84 lines) and `The frontend design system` (38 lines) are
  byte-identical to `HEAD`. Added one new section the protocol requires and the file had no
  home for: **Claims that turned out wrong, and who caught them.**
- Restored `session-log/sitanshu.md` (45 lines) from `266b00b`, the commit before PR #44's
  merge deleted it. Deleted the stray `bck/session-log/shiva-kumar.md` and appended its one
  real line to the root `session-log/shiva-kumar.md` under a dated heading.
- Rewrote `TICKETS.md` and `TODO.md`, verified `ARCHITECTURE.md` against the tree rather than
  rewriting it, and updated `AGENTS.md` and `CLAUDE.md`.

**Corrected against GitHub rather than carried forward**
The addendum was wrong on two board facts and both were checked with `gh`:
- **MEA-004 (#42) had not merged.** It is open and red — on `ruff format --check`, not on
  tests. Session 4 merged four PRs, not five.
- **DAT-001 (#34) had not been closed.** It is still open, red and thirteen commits behind.
- `RUL-003` was being used for the `governs_declarations` ticket, which is **RUL-004**;
  RUL-003 is session 3's merged multi-piece ticket (#36).
- **#45's two owed items are already fixed** — `_extract_numeric_value` returns `""` on
  `"150.00.5"` and `session-log/akshaya.md` is present — but that log rewrite deleted her
  VIS-001 history, the same defect as #44 deleting Sitanshu's.
- **#46 and #47 are open PRs now**, not in-flight work, and both edit `app/contracts/`.

**Verified, not assumed**
- All six open PRs are on a stale base, 2 to 13 commits behind `main` (`git merge-base`).
  A stale base does **not** reliably show as red: #45 and #47 are green two commits behind.
- Grepping a CI log for `ERROR` returns exactly three lines on this repo and all three are
  passing tests — Postgres server logs under the "Stop containers" step, from the
  `field_state` enum-drift guard and the two uniqueness tests. Checked against green run
  `34039775921`.
- `637 passed, 33 skipped` locally; ruff clean, `ruff format` clean, 3 import contracts kept.

**Incomplete / for the next session**
- Closing #34 is an action nobody has taken. It needs doing before the board is honest.
- Three PRs (#43, #46, #47) fail the merge gate on one clause each — a new dependency and
  two shared-contract changes. They need an explicit decision, not a quiet merge.
- The image path has still never run with real YOLO or PaddleOCR weights. It is in TODO under
  Bugs, not Later, because it sits on the demo path.

---

## Session 5 — 2026-09-06, docs (Claude Code)

Branch `docs-handoff-session4`. Documentation only, no code touched.

- **HANDOFF.md, two entries.** Constraints: a falsification can run against stale bytecode and
  report a green pass over a real defect, because `.pyc` staleness is mtime-and-size and a
  falsification edit is usually a same-length string swap. `find . -name __pycache__ -type d
  -exec rm -rf {} +` first, always. Any falsification claimed on 2026-09-06 without that step
  is soft — caught in CTR-003, which nearly believed the false pass. Hard nos: a test that
  cannot fail gets deleted, not shipped green;
  `not isinstance(proposal, ProductCategory)` is unfalsifiable because a `StrEnum` with
  members cannot be subclassed, so it restated the type system.
- **CLAUDE.md** carries both, because the falsification procedure with the hole in it lives
  there. The delete rule is written against the existing rename rule, not over it: rename when
  a true claim is left, delete when there is none. The PIP-001 deepcopy test still stands.
- **#34 corrected.** It is now closed on GitHub (confirmed with `gh pr view 34`), superseded by
  DAT-002 + DAT-003. Recorded in HANDOFF.md, TICKETS.md and TODO.md that its branch
  `feature/26034-DAT-001-corpus-images` survives at `47fa16d` and **DAT-002 branches from it,
  not from `main`** — deleting it loses the corrected sha256 hashes and the five fabricated-
  annotation deletions. TICKETS.md's stale-base table drops to five PRs, 2 to 4 behind.

---

## Session 6 — 2026-09-06, CTR-004 (Claude Code)

Branch `ctr-004-verdict-rulestatus-unification`. Reconciles the duplicated `Verdict` and
`RuleStatus` between `app.contracts` and `app.modules.rules`. Not committed at session end —
handed back for review first.

**What changed, and why.**
- `rules.RuleStatus` is deleted. `app/modules/rules/base.py` now re-exports
  `app.contracts.RuleStatus` under the same alias pattern `ProductCategory` already used, so
  `models.py`, `evaluator.py` and `__init__.py` keep importing it from `.base` and nothing
  below `base.py` changed. A verdict record carries the status, so the value crosses the
  module boundary and must not be spelled twice.
- `rule_snapshot.py` no longer does `RuleStatus(rule.status.value)`. With one class that
  conversion is an identity function, so it is `status=rule.status` and the `RuleStatus`
  import is gone. The comment that justified the conversion went with it.
- `rules.Verdict.POTENTIAL_VIOLATION` and `rules.Severity.POTENTIAL_VIOLATION` change from
  `"POTENTIAL VIOLATION"` to `"POTENTIAL_VIOLATION"`, together with **17** `severity:` lines
  in `rules.yaml`. Three edits, one commit: `rule_findings.py:194` builds a `Verdict` from a
  `Severity` value and the loader builds a `Severity` from the yaml string, so any two of the
  three agreeing without the third raises at runtime rather than at import.
- `SEVERITY_ROUTING`'s docstring argued the two severity enums cannot be value-converted
  *because of the space*. That reason is now gone; the real reason — the two vocabularies
  share no word at all — is written in its place. The routing table itself is untouched:
  `rules.Severity` and `contracts.RuleSeverity` still mean different things.
- `app/pipeline/dispositions.py` needed no edit. It names `Verdict` members, never values.

**Falsifications.** `__pycache__` cleared before each. Baseline 662 passed, 32 skipped.
- Revert only `rules.yaml` to the spaced spelling → **102 failed**. Red.
- Revert only `Verdict.POTENTIAL_VIOLATION` → **6 failed**, all through
  `rule_findings.py:194` with `ValueError: 'POTENTIAL_VIOLATION' is not a valid Verdict`.
  Red. The coupling is covered; it was not a missing test.
- Revert only `Severity.POTENTIAL_VIOLATION` → **117 failed**. Red.
- Reintroduce a duplicate `RuleStatus` inside `rules/base.py` → **the whole suite stayed
  green.** `RuleParameterSnapshot.status` is typed to the contracts enum and a `StrEnum`
  member from the duplicate arrives at validation as `"VERIFIED"`, which pydantic coerces
  straight back into the contracts member. Nothing in the repo could see the duplication
  come back. Added `test_the_rules_module_names_the_contracts_rule_status_and_not_a_copy`
  in `tests/pipeline/test_rule_snapshot.py`, re-ran the same falsification, and exactly one
  test went red.

**No migration, verified rather than assumed.** `64a9392a6859` creates the `verdict` enum as
`PASS`/`REVIEW`/`POTENTIAL_VIOLATION` — the contracts spelling, underscore already — and
`c16334c8d865` reuses that same type for `reviews.overridden_verdict`. `field_findings.
rule_snapshot` is `JSON` with a `JSONB` variant, and `_parameters` puts conditions,
`applies_to`, `evidence_requirement` and `declaration_fields` into it, never a severity. No
migration file contains the spaced string. The rules spelling never reached the database.

**One correction to the ticket.** It says 18 `severity: POTENTIAL VIOLATION` lines in
`rules.yaml`. There are **17** (the other 10 severity lines are `REVIEW`). All 17 changed.

`663 passed, 32 skipped`; ruff clean, `ruff format --check` clean, `lint-imports` 3 contracts
kept over 108 files analysed.

## Session 7 — 2026-09-07, CI-004 (Claude Code)

**`datasets/` had never been executed by CI, and its one test file could not be imported.**
Two independent causes, both confirmed before anything was written.

The backend job runs with `working-directory: bck`, and `bck/pyproject.toml` sets
`testpaths = ["tests"]`. `uv run pytest` therefore never leaves `bck/tests`. Nothing in the
repo has ever pointed pytest at `datasets/`. And pointing it there by hand did not work
either:

```
$ cd bck && uv run pytest ../datasets/eval/test_harness.py -q --collect-only
../datasets/eval/test_harness.py:8: in <module>
    from datasets.eval.harness import (
E   ModuleNotFoundError: No module named 'datasets'
no tests collected, 1 error in 0.09s
```

27 tests, never run once. `datasets/schema.py` would have rejected all four of the
fabricated annotations that reached `main` and survived four review rounds. The validator
existed. Nothing ran it.

**The fix to `test_harness.py` is not a copy of `test_schema_guards.py`.** That file does
`sys.path.insert(0, DATASETS_DIR)` and then `from schema import …`. Copying it verbatim
fails, because `datasets/eval/harness.py:22` itself does `from datasets.schema import …` and
`datasets/eval/__init__.py` does `from datasets.eval import harness` — both by package name.
So the anchor has to be the repo root: same mechanism (`Path(__file__).resolve().parents[N]`
plus `sys.path.insert`, imports carrying `# noqa: E402`), one level further up. Five lines.

**The `app` requirement was verified, not assumed.** DAT-004 will add a cross-module guard
under `datasets/` that imports `app.modules.measurement`, and `app` is importable only once
`bck` is installed. `cd bck && uv run python -c "import app.modules.measurement"` succeeds
from the synced environment with no environment variables set, and resolves to
`bck/app/modules/measurement/__init__.py` — the editable install. That is why the job syncs
`bck` and runs pytest with `working-directory: bck` rather than standing up an environment of
its own. DAT-004 will not discover this in CI.

**No `paths:` filter, and the comment saying so now sits at workflow level.** A first draft
put it on the job, which is wrong twice over: `paths:` is a trigger filter under
`on:`, a job cannot carry one, and adding one to `ci.yml` would silence `backend` and
`datasets` together. Confirmed by reading the block — `on: pull_request:` bare, no `paths:`,
no `branches:`, no `types:`. The only occurrence of the string `paths` anywhere in
`.github/workflows/` is the prose warning at the top of `frontend.yml`, which already records
this deadlock costing `--admin` merges from #30 onward. Ours is the same one that blocked
#32, #33, #36 and #37.

**The hygiene step does not use `git ls-files -z | tr '\0' '\n'`.** That pairing reintroduces
the hole it closes: a filename containing a newline — the same class of shell-quoting
accident that produced #42's junk file — is split by `tr` into two lines, either of which can
look innocent. Plain `git ls-files` quotes such a name under `core.quotePath`, so it arrives
on one line as `"news\nline.txt"` and the double quote in it trips the first pattern.
`^"?rules-corpus/` in the exclusion accounts for that same quoting, so an oddly-named gazette
stays exempt rather than being unquoted into scope.

Root allowlist built from `git ls-files | grep -v /` against the tree, not from memory:
twelve files, `.gitignore` through `docker-compose.yml`.

**Falsifications — three, all after `find . -name __pycache__ -type d -exec rm -rf {} +`.**

- `test_the_rs10_coin_remains_available`, `"coin_inr_10"` → `"coin_inr_5"` →
  **1 failed, 24 passed, 2 skipped.** Red. Reverted with `git checkout --`;
  `git status --porcelain` on the file is empty, so it is byte-identical to HEAD.
- Staged `bad")file.txt` and `-oops.txt` at the root → **both hygiene checks matched both
  files** (`grep exit=0` twice, so both `if` blocks reach `exit 1`). `git ls-files` rendered
  the first as `"bad\")file.txt"`, which is the quoting the step relies on. Unstaged and
  deleted; both checks return to `grep exit=1`.
- Free third: commented out the `sys.path.insert` → **collection error, 1 error in 0.12s**,
  the exact `ModuleNotFoundError` this ticket exists for. Restored → 25 passed, 2 skipped.

**Not done, deliberately.** No `ruff` step on `datasets/`: the seven pre-existing UP042
findings in `datasets/schema.py` (`str, Enum` → `StrEnum`) would make the job red on arrival,
and converting a schema that serialises to JSON is its own change. Worth a ticket. Not added
as a required status check either — a required check cannot be added before it has reported
once, so that is a separate step after this goes green.

**One hazard noted, not fixed.** With the repo root on `sys.path` and `datasets/` also on it
(pytest adds the latter as `eval/`'s package basedir), `schema` and `datasets.schema` are two
distinct module objects in one session, holding two distinct copies of the pydantic classes.
Harmless today — no test crosses them — but an `isinstance` spanning the two files would fail
confusingly. Unifying it means editing `test_schema_guards.py`, which DAT-004 is holding in
another worktree.

`25 passed, 2 skipped` for `datasets/`, `686 passed, 32 skipped` for `bck/`; ruff clean,
`ruff format --check` clean over 139 files, `lint-imports` 3 contracts kept over 109 files
and 357 dependencies. Both counts are as-of this branch's base SHA — DAT-004 is renaming
`"coin_inr_10"` to `"coin_10"` in `datasets/tests/test_schema_guards.py` and adding a
cross-module guard concurrently, so whichever of the two merges second has to re-run and
re-report.

**Correction, made after the first green run.** The `Dataset tests` comment claimed rootdir
resolves to `bck/` and that `bck/pyproject.toml` supplies the pytest config. The CI log says
otherwise — `rootdir: /home/runner/work/26034/26034`, no `configfile:` line,
`asyncio: mode=Mode.STRICT` — and the same holds locally. With `../datasets` as the argument
the common ancestor is the repo root, which has no ini file, so pytest loads no config at
all. No result moves (nothing under `datasets/` is async, 25 passed either way) and
`working-directory: bck` is still needed to reach the synced environment that has `app`
installed, but the comment was wrong in both environments and now says what actually happens.

## Session 8 — 2026-09-07, CTR-005 (Claude Code, Opus 5)

**Margin measurement types as siblings, not subclasses.** PR #47 (MEA-006, still open)
proposed `MeasurementMarginExact(MeasurementExact)` and
`MeasurementMarginCalibrated(MeasurementCalibrated)`, children relaxing the parent's
`value` from `gt=0` to `ge=0`. `contracts/` is single-owner so the type half lands here
and #47 rebases down to `services.py` plus its tests.

Extracted `_MeasurementExactBase` and `_MeasurementCalibratedBase` — shared fields, no
`value` declared — and made all four public types siblings of them, each with its own
constraint and its own `mode` literal. The two bases are deliberately *not* chained even
though both carry `unit`: `rule_limb` documents Rule 7(4) on the artwork side and Rule
7(2) on the calibrated side, and sharing the field would force one docstring over both.

**The ticket's premise about `confidence_interval` was wrong, and it mattered.** It
assumed `gt=0`, so that `measure_margins`' `confidence = max(0, dist_px) * conf_interval`
would raise on a zero margin. It is `ge=0`, deliberately, with a field docstring and two
tests pinning both directions — a zero-variance contrast-ratio crop genuinely has no
spread. So nothing was blocking a "0.0 mm ± 0.0" reading from a photograph. Decision
after raising it: tighten on `MeasurementMarginCalibrated` alone to `gt=0`, leaving the
base and `MeasurementCalibrated` at `ge=0`. Zero *value* is a physical fact (flush
against the edge); zero *interval* is a false precision claim about a distance carrying
pixel quantisation and reference-object localisation error. Tightening in a child is the
safe direction — it guarantees strictly more than its base — and is the exact inverse of
the relaxation this ticket removes.

**Consequence left for MEA-006:** `measure_margins` will now raise on a zero margin
through the calibrated path. That is Yashashvi's floor to add in `services.py`, not a
regression, and not a contracts relaxation.

**Field reordering checked against the evidence chain rather than assumed.** Moving
`unit`/`rule_limb` into a base reorders serialisation for `MeasurementExact` and
`MeasurementCalibrated` too. It cannot move a hash, for three independent reasons: no
measurement model reaches the hashed payload at all (`contracts/records.py` has zero
`Measurement` references; `FieldFinding` carries `observed_value`/`expected_value` as
strings, and measurements are rendered to those in `pipeline/rule_findings.py` before a
finding exists); `compute_payload_hash` and `pipeline/repository.py:268` both serialise
with `json.dumps(..., sort_keys=True)`, which is recursive; and no pinned-hash fixture
exists — grep for 32+ hex-char literals across `bck/tests/` returns nothing. The one
serialisation-equality assertion, `test_orchestrator.py:184`, compares two runs of the
same code.

**Six falsifications, all red, all reverted.** `MeasurementExact.value` → `ge=0` (test 3);
`MeasurementMarginExact(MeasurementExact)` (test 4); both margin `value` → `gt=0`
(tests 1–2); `MeasurementMarginExact` dropped from the union (test 5);
`MeasurementMarginCalibrated.confidence_interval` → `ge=0` (test 6); both margin `value`
constraints removed (negative case).

**One process failure worth recording.** The first falsification pass reverted with
`git checkout -- <file>` before the work was committed, so HEAD was still `origin/main`
and the revert silently discarded the whole refactor — the next falsification then
"failed" for the wrong reason. Redone against a committed baseline. This is precisely the
hazard the `ge=0` diff audit exists for: after every revert, grep the branch diff for
`ge=0` and confirm each occurrence is intended. Final audit shows exactly six constraint
sites — `ge=0` on the two margin `value` fields and on the untouched base
`confidence_interval`, `gt=0` on both strict `value` fields and on the margin
`confidence_interval`. Nothing relaxed by accident.

`693 passed, 32 skipped`; ruff clean, `ruff format --check` clean, `lint-imports` 3
contracts kept over 109 files analysed. Exit codes read directly, not through a pipe.

## Session 9 — 2026-09-06, DAT-004 (Claude Code)

Branch `dat-004-reference-object-vocabulary`, from `origin/main`.

- **The drift.** `datasets/schema.py` offered `coin_inr_10` / `credit_card_id1`;
  `detect_reference_object` dispatches on `coin_10` / `id_card` / `ean_13` and everything
  else falls to the terminal `MeasurementRefusal` at `services.py:191`. No annotation could
  reach measurement. The dimensions already agreed exactly — 27.0 mm, 85.60 x 53.98 mm,
  37.29 mm — only the spelling differed. Hidden because the corpus is empty and no eval
  harness has ever run against measurement. Blocked DAT-005 and demo scenario 4.
- **Measurement's names won; the schema adopted them.** Not a coin toss:
  `app/pipeline/orchestrator.py:124` already documents `Calibration.reference_type` as
  "the reference object in frame — as `app.modules.measurement` names it". The pipeline
  had ruled measurement authoritative; the schema was the outlier. Renaming in measurement
  would have touched merged reviewed code and PR #47, open against that module.
- **`ARUCO_MARKER` / `RULER_SCALE` / `CHECKERBOARD` deleted.** No `REF_DIMS` entry, no
  detector branch, no sourced dimension, no reference anywhere in the repo outside their
  own declaration line. An annotation naming one hit the same refusal `coin_inr_10` hit —
  unreachable capability. Keeping them would have meant an exemption list in the new guard,
  and the exemption list is the thing that rots.
- **The rule this establishes, and it is in the guard's docstring:** a
  `ReferenceObjectType` member exists only alongside its `REF_DIMS` entry and its detector
  branch. When ArUco or a checkerboard is genuinely built, the member arrives in the same
  PR as its dimension and its branch. `TestMeasurementCanConsumeEveryOfferedObject` is what
  enforces that, so it carries no exemptions.
- **`datasets/README.md:42` — dropped the identifier, kept the warning.** It named
  `coin_inr_5`. Re-spelling it `coin_5` was rejected: that invents a third identifier
  appearing nowhere in the repo, which is the same defect the three deletions above remove.
  The warning is about a physical object whose 25.0 mm figure was written from memory, so
  it now names the ₹5 coin in plain English and says the figure is sourced in neither
  `rules-corpus/` nor `SIH26034_Research_And_References.md`. Same reasoning applied to the
  enum's own Rs 1 / Rs 2 / Rs 5 comment. `HANDOFF.md:377` carries the same prose and was
  left alone — docs PR, not this one.
- **Falsified twice**, `__pycache__` purged with `/usr/bin/find` before each. Note `rtk`
  refuses `find -exec` and prints a message rather than running it, so the CLAUDE.md purge
  command silently does nothing through the wrapper — the first attempt here purged nothing
  and the baseline that followed was worthless. Use `/usr/bin/find` explicitly.
  (1) `COIN_10 = "coin_ten"` → guard red naming `coin_ten`, plus four literal-asserting
  tests. (2) `ARUCO_MARKER = "aruco_marker"` re-added → guard red naming `aruco_marker`,
  and **nothing else failed**, which is the stronger proof: the claim is about a new member
  without a `REF_DIMS` entry, not about a rename. Both reverted, 9 passed / 2 skipped.
- **The guard is inert in CI until CI-004 lands.** `bck/pyproject.toml` sets
  `testpaths = ["tests"]` and `ci.yml` has one job with `working-directory: bck`, so
  nothing collects `datasets/tests/`. No `sys.path` hack was needed or added — `bck`
  installs editable into `bck/.venv`, so `cd bck && uv run pytest
  ../datasets/tests/test_schema_guards.py` imports `app` cleanly.
- **For CI-004, found while verifying:** `datasets/` is not ruff-clean under `bck`'s
  config. Seven pre-existing UP042 (every enum class in `schema.py` is `(str, Enum)`, not
  `StrEnum`) and one pre-existing `ruff format` diff in
  `test_no_annotation_claims_a_millimetre_height`. None of it is in this diff and none of
  it was touched. A datasets job that runs ruff will go red on arrival.
- **Raised, not added:** `REF_DIMS` has no entry for the printable 50 mm calibration card
  F2 (manufacturer self-check) names. Own ticket on Yashashvi. No placeholder enum member
  left for it — that would be the defect this PR deletes three of.
- **Gate:** `686 passed, 32 skipped`; ruff clean, `ruff format --check` clean,
  `lint-imports` 3 contracts kept over 109 files. `datasets/eval/test_harness.py` 17 passed.

**Rebased onto CI-004 (#60) on 2026-09-07**, which is when this guard first executed anywhere
but a laptop, then onto CTR-005 (#58). Numbered 9 rather than 6 on landing: 6 was already
CTR-004, and CI-004 (7) and CTR-005 (8) reached `main` first. Both times this entry was
appended below theirs rather than inserted above it, and both times the resolution was checked
as a pure append — `git diff origin/main -- session-log/abhiram.md` shows one hunk, 0
deletions, and everything above this heading hashes identical to `main`.

**The `rtk` / `find` interception, pinned down.** My earlier note was right that it happens and
wrong about why, and the correction matters because it decides how much past work is suspect.
It is **not** intermittent and it does **not** exit zero:

- `find . -name __pycache__ -type d -exec rm -rf {} +` as the **first token** of a command →
  `rtk: rtk find does not support compound predicates or actions (e.g. -not, -exec). Use
  `find` directly.`, **exit 1**, and **51 `__pycache__` directories still there afterwards**.
  A measured no-op, not a partial one.
- `/usr/bin/find` with the identical arguments → exit 0, 51 → 0.
- The trigger is position, not shape. `echo x && find … -exec …`, `find` inside `$( )`, and
  `find` inside a `for` loop all reach the real binary and work. Three consecutive loop runs
  purged 51 → 0 with empty output, which is why this first read as flaky.

Because it exits **1**, a falsification written `find … && pytest` is blocked rather than
silently misled — the failure is loud. The hazard is the **semicolon**: `find … ; pytest` is
what CLAUDE.md's phrasing invites and what I ran, and it discards the 1 and runs the suite on
stale bytecode. So the exposure is real but bounded to `;`-separated purges with `find` first,
not to every falsification on the project.

**CI-004's datasets job has no ruff step**, deliberately. It runs `uv run pytest ../datasets`
with `working-directory: bck`, and nothing else. That matches what I found before it landed —
`datasets/` carries seven pre-existing UP042 (every enum class in `schema.py` is `(str, Enum)`)
and one `ruff format` diff in `test_no_annotation_claims_a_millimetre_height`. None is mine.
Anyone adding a ruff step to that job turns it red on arrival; the pre-existing findings have
to be cleared in their own PR first.

**Correction to the `rtk` note above, made after measuring it properly.** The claim that "the
trigger is position, not shape" is **wrong**, and so was the earlier note on PR #59 saying it
merely "runs nothing". `echo x && find … -exec …` is refused exactly as a bare `find …` is —
position within the line is irrelevant. What actually reproduces:

- a **single-line** command containing `find … -exec rm -rf {} +` → refusal, **exit 1**,
  51 `__pycache__` dirs before and 51 after;
- the same `find` line inside a **multi-line** command → exit 0, 51 → 0;
- `/usr/bin/find`, either shape → exit 0, 51 → 0.

`type -t find` reports `function` in both shapes, so it is not a question of whether the
wrapper is installed. I am deliberately not asserting the internal cause — I have now been
wrong about the mechanism twice, and the observable rule is what anyone here needs.

The load-bearing part is unchanged and is the answer to whether older work is suspect: it
exits **1**, not 0. `find … && pytest` is blocked loudly. Only `find … ; pytest` — single
line, semicolon, which is the shape CLAUDE.md's wording invites — discards the 1 and runs on
stale bytecode. Anything that used `&&` or `/usr/bin/find` is sound. The safe form is
`/usr/bin/find`, and that belongs in CLAUDE.md and HANDOFF.md in the next docs PR.

**CI result after rebasing onto CI-004 (#60).** All three checks green — `CI/datasets`,
`CI/backend`, `Frontend/frontend`. The datasets job log reports
`rootdir: /home/runner/work/26034/26034`, `collected 28 items`, `26 passed, 2 skipped in
0.71s`. CI-004 documented 27 (25 passed, 2 skipped), so the delta is exactly the one new
guard, executing outside a laptop for the first time.

## Session 10 — 2026-09-07, CORE-003 (Claude Code, Opus 5)

**`asset_type` on the evidence entry, its column and its migration.** Split out of #46
(EVD-005) because `alembic/` is single-owner and a migration cannot be edited after it
merges. Shiva carries no `alembic/` file; the note to send him is in the PR body.

**The enum had to move to `contracts/`, and that was not a style choice.** `core/models.py`
needs the type for its column and `modules/evidence/domain.py` needs it for the entry model.
The layer contract is `main > pipeline > modules > core > contracts`, so `core` may not
import from `modules` — #46's definition inside `domain.py` could never have supported a
column. It sits in `contracts/enums.py` next to `EvidenceProvider`, which is the same shape
one question over: that records what *produced* evidence, this records what it *is*.

**Three members, each with a consumer.** `FIELD_VERDICT` had zero usages anywhere in #46 and
is gone. `GEOLOCATION` and `PERSONAL_IDENTIFIER` were one member wearing two names —
`get_retention_days` routes both to `evidence_pii_retention_days` through a single `in (...)`
and no branch tells them apart — merged as `PERSONAL_DATA`. `PRODUCT_IMAGE` and `AUDIT_LOG`
keep Shiva's spelling so his branch needs no rename.

**`DERIVED_ARTEFACT` is deliberately out, and this defers a migration.** Nothing in the repo
consumes an original-capture-versus-derived-artefact distinction: no thumbnail, crop or
re-render path, and no retention branch for one. Under the deletion rule it does not ship.
The cost being accepted: when **EVD-006** lands the derived-artefact retention branch that
consumes the member, adding it needs a hand-written
`ALTER TYPE evidence_asset_type ADD VALUE 'DERIVED_ARTEFACT'`, which **cannot run inside a
transaction** and which `alembic check` does not report as drift — it passes clean and then
fails at the first insert with `invalid input value for enum`. **That migration is Abhiram's
to write**, not EVD-006's author's, for the same single-owner reason this ticket exists.
The three member docstrings state only the window or behaviour that consumes them and must
not be softened to imply the set is complete.

**Authorised ownership exception — this ticket only.** Four files under
`bck/app/modules/evidence/` and `bck/tests/modules/evidence/` were edited by Abhiram and not
by their owner: `domain.py`, `chain.py`, `test_hash_chain.py`, `test_chain_verification.py`.
**Reason: Decision 2 puts `asset_type` inside `compute_entry_hash`, which lives in
`chain.py`, and the field must be on the entry model to reach it.** Authorised by Abhiram
for CORE-003 and **not precedent for editing another owner's module.** `retention.py`,
`storage.py`, the purge functions and the legal-hold rule are untouched.

**Two files broke that the ticket did not name**, both mine and both found by running rather
than reading: `bck/tests/persistence/test_postgres.py:348` constructs an `EvidenceEntryRow`,
and `bck/tests/pipeline/test_api.py` reconstructs an `EvidenceEntry` from a row in two
places. The second pair only fails with a live database, so they were invisible in the
skipped run and surfaced when the postgres-marked suite was enabled.

**The CORE-002 drift guard does not extend itself.** `ENUM_TYPES` in `test_postgres.py` is a
hand-written dict and the schema comparison at line 128 is `types >= ENUM_TYPE_NAMES`, a
superset test — a new enum type absent from the dict is not caught in either direction.
Added `"evidence_asset_type": EvidenceAssetType` by hand. That one line is what puts the new
type into the label comparison, into the post-upgrade check, and into the post-downgrade
`not types & ENUM_TYPE_NAMES` check, which is what proves the `DROP TYPE` actually runs.

**Verified against the real database, not asserted.** Full cycle on `26034-db-1`:
`downgrade base` → `upgrade head` → column present as `USER-DEFINED`/`evidence_asset_type`,
`is_nullable=NO`, `column_default` empty, type carrying exactly three labels → `downgrade -1`
→ column gone **and `select count(*) from pg_type where typname='evidence_asset_type'`
returns 0** → `upgrade head` → `alembic check` clean.

**Falsification.** Removed `asset_type` from the `compute_entry_hash` input string, leaving
the original four fields. `test_relabelling_an_asset_type_breaks_the_entry_hash` went red in
both parametrisations; reverted, green again, `git diff` clean. Every purge used
`/usr/bin/find` with the surviving directory count asserted at zero rather than trusting an
exit code.

`740 passed, 2 skipped` with Postgres live (`710 passed, 32 skipped` without). Ruff clean,
`ruff format --check` clean, `lint-imports` 3 contracts kept over 111 files analysed.

**Open discrepancy, carried forward — not investigated in this lane.** `ARUCO_MARKER`,
`RULER_SCALE` and `CHECKERBOARD` are still present in `datasets/schema.py` (lines 55-57) and
have no corresponding entries in `REF_DIMS`, which holds only `id_card`, `coin_10` and
`ean_13`. `ARCHITECTURE.md` and `HANDOFF.md` both state they were deleted. They were not.
The members that were actually removed are the Rs1/Rs2/Rs5 coins, and the comment above them
gives a different reason — their dimensions were written from memory and `coin_inr_5` is on
the Hard Nos list — not absence of a consumer. Consequence: there is no enforced
member-consumer guard anywhere in the repo, and the deletion rule applied in this ticket was
applied fresh rather than inherited from that precedent.

---

## Session 11 — 2026-09-07, CTR-006 (Claude Code, Opus 5)

**Ticket.** A contracts representation for competing readings of one declaration. Unblocks
Sitanshu on EXT-007.

**The bug this makes unrepresentable.** EXT-006 (#56) refuses to pair a Devanagari and a
Latin declaration whose values disagree — `binder.py:604`, `if (f1.numeric_value !=
f2.numeric_value) or (f1.unit != f2.unit): continue`. Both spans then fall through to
`bind_spans`'s tail loop and each becomes its own `NormalisedField` of the same
`field_type` in `fields`. `orchestrator.by_obligation` groups them into
`declared[NET_QUANTITY] = (f1, f2)`, and `rule_findings._one_declaration` decides presence
on nothing but that tuple's truthiness — so a package declaring "500 g" on one line and
"२५० ग्राम" on the next got **PASS**, with `observed_value="500 g | 250 g"` printed as if
it were one reading. `tests/modules/extraction/test_bilingual_declarations.py:185` pins
today's two-record behaviour; EXT-007 changes it.

**Shipped.** `DisagreementReason` in `contracts/enums.py`, `CompetingReadings` in
`contracts/evidence.py` (`field_type`, `readings: tuple[NormalisedField, ...]` with
`min_length=2`, `reason`), both exported, two README rows and a sixth load-bearing note.

**One enum member, deliberately.** `BILINGUAL_VALUE_MISMATCH`, and its docstring covers
both limbs of that `or` — the numeric value and the unit. A second member for the unit limb
has no consumer: PIP-004 routes both to REVIEW_REQUIRED identically and the officer sees
both readings either way. Same rule that kept `DERIVED_ARTEFACT` out of CORE-003 — a member
ships alongside something that consumes it. The docstring is deliberately not narrowed to
`numeric_value`, because a narrow docstring is what makes the next person add a second
member for a case the first already covers.

**Authorised crossing into `modules/extraction/`, and it is not precedent.**
`ExtractionResult` is **not** in `contracts/` — it is `binder.py:48`, a bare
`pydantic.BaseModel`. CTR-006's out-of-scope line puts `modules/extraction/` off limits, but
the capability has nowhere else to land. Abhiram authorised the crossing for this ticket
only, same shape as CORE-003's evidence crossing: the `disagreements` field, its import, and
the disjointness validator. Nothing else in `binder.py` was touched — **the non-pairing
branch at 604 is EXT-007's**. Moving `ExtractionResult` into `contracts/` was considered and
settled against: ARCHITECTURE.md records that as tidy-up rather than correction, and
PIP-002's `contracts/binding.py` was dropped from history so it would not be recreated.

**Why the disjointness invariant is a validator and not an assertion.** The ticket asked for
a test that `fields` and `disagreements` are disjoint by `field_type`. Nothing populates
`disagreements` until EXT-007, so a test asserting disjointness over real `bind_spans`
output would be **vacuously true** — the decorative green tick five PRs on this project have
already shipped. Refusing the overlap at construction is what makes the guard real today,
and it is also the stronger form: two collections mean a consumer can double-count, and
someone forgets exactly once.

**Falsification — four defects, four reds, all reverted.** Each with
`/usr/bin/find . -name __pycache__ -type d -exec rm -rf {} +` first and the surviving
directory count asserted at **0** rather than trusting an exit code.

| Defect introduced | Test that went red |
|---|---|
| `Field(min_length=2)` → `min_length=1` | `test_a_single_reading_is_not_a_disagreement` |
| `wrong` set forced empty in the cross-check validator | `test_a_reading_of_another_obligation_is_refused` |
| `both` set forced empty in the disjointness validator | `test_a_field_in_disagreements_is_never_also_in_fields` |
| `ContractModel` `frozen=True` → `frozen=False` | `test_a_disagreement_is_frozen` |

The frozen test is called out because "a mutation test against a frozen object" is on this
repo's list of five unfalsifiable tests. This one was falsified against the config that
makes it hold, and it goes red.

**Gate.** `739 passed, 32 skipped` locally. Baseline on `origin/main` measured in the same
session by stashing: `731 passed, 32 skipped` — exactly **+8**, nothing else moved. Ruff
clean, `ruff format --check` clean, `lint-imports` **3 contracts kept over 111 files**
(checked it analysed something rather than passing fast on a missing install).

**Note for whoever next edits CLAUDE.md.** Its stated local baseline of `707 passed / 32
skipped` is stale — it predates EXT-006. The number on `origin/main` today is 731/32. Not
corrected here; doc updates go in their own PR.

**Handed to EXT-007 (Sitanshu).** At `binder.py:604` the value check runs **before**
`_are_spans_spatially_adjacent` at 607. As ordered, the branch cannot tell "two scripts
disagreeing about one declaration" from "two unrelated declarations elsewhere on the panel".
The adjacency check has to move above the value check, or EXT-007 will record disagreements
that are not disagreements.

**Handed to PIP-004, and it is not optional polish.** `rule_findings.py` needs zero lines to
stop the wrongful PASS — once EXT-007 diverts the pair into `disagreements` they never enter
`extraction.fields`, so `by_obligation` never sees them, `declared` has no key, and
`_one_declaration` falls to the `unreadable_reason` branch. But that branch yields
**INSUFFICIENT_EVIDENCE**, which the constraints forbid: both readings were read perfectly
well. `verdict.py:56-59` tests REVIEW_REQUIRED and INSUFFICIENT_EVIDENCE one at a time and
both return `Verdict.REVIEW`, so the package-level verdict is the same either way — what
PIP-004 buys is the correct **reason string on the officer surface**. Without it the system
tells an officer "the evidence needed could not be obtained" about a label it read perfectly,
twice. Four edit points:

1. `EvidenceContext`, `app/pipeline/rule_findings.py:60-93` — a field carrying the
   contested obligations.
2. `_one_declaration`, `app/pipeline/rule_findings.py:167-197` — a REVIEW_REQUIRED branch
   **above** the `if values:` test. Its own branch: never sharing an expression with
   INSUFFICIENT_EVIDENCE or FAIL, and no set membership test.
3. `orchestrator.py:240`, the image path — fed from `extraction.disagreements`. Includes
   `field_providers` at `:256`, which is `dict.fromkeys(declared, ...)` and would otherwise
   omit a contested obligation that now carries a finding.
4. `orchestrator.py:295`, the catalogue path — a listing supplies one value per obligation
   key, so this passes empty.

PIP-004 merges **before** EXT-007, so the forbidden state never reaches `main`.

## Session 12 — 2026-09-07, PIP-004 (Claude Code, Opus 5)

**Ticket.** Route a contested declaration to REVIEW_REQUIRED rather than
INSUFFICIENT_EVIDENCE. Merges before EXT-007 so the forbidden state never reaches `main`.

**The state this closes.** CTR-006 (#65) landed `CompetingReadings` and
`ExtractionResult.disagreements` and nothing read them. Once EXT-007 diverts two
contradictory readings out of `extraction.fields`, `by_obligation` never sees them,
`context.declared` has no key, and `_one_declaration` falls past `if values:` to the
`unreadable_reason` branch — **INSUFFICIENT_EVIDENCE** on a label that was read perfectly,
twice. Package verdict is REVIEW either way (`verdict.py:56-59` tests both states in
separate branches); what this buys is the reason string on the officer surface. An officer
told the declaration could not be read re-photographs a package that needs no second photo.

**Shipped.** `EvidenceContext.contested:
Mapping[DeclarationField, tuple[CompetingReadings, ...]]`; a REVIEW_REQUIRED branch at the
top of `_one_declaration`; `by_obligation` widened to serve both collections; the image path
fed from `extraction.disagreements` with `field_providers` extended to cover
disagreement-only obligations; the catalogue path passing `{}`.

**REVIEW_REQUIRED is a literal, not `FIELD_STATE_FROM_VERDICT[evaluate_rule(...)]`.** The
research question the ticket asked was whether REVIEW_REQUIRED is reachable through that
mapping. **It is** — `dispositions.py:21`, keyed by `Verdict.REVIEW`. CTR-006's note that
the mapping is not total over `FieldState` is right about the two members it names,
`NOT_APPLICABLE` and `INSUFFICIENT_EVIDENCE`, and REVIEW_REQUIRED is not in that company.
It is still produced outside the mapping, for three reasons. Nothing was evaluated — the
rule was never applied because no declaration was resolved to apply it to. The round trip
computes a constant: `evaluate_rule` (`evaluator.py:66-76`) has one gate,
`UNVERIFIED → REVIEW`, so proposing `Verdict.REVIEW` returns REVIEW unconditionally. And it
would hand this branch the FAIL branch's exact expression,
`FIELD_STATE_FROM_VERDICT[evaluate_rule(rule, X)]` — one token
(`Verdict.REVIEW` → `Verdict(rule.severity.value)`) from routing a contested declaration to
FAIL, which is the accident the five-state vocabulary exists to prevent. Literals are
already the house pattern for every branch that did not evaluate: `sector_findings`,
`observation_findings`, `listing_findings`, and the `unreadable_reason` branch. Skipping
the evaluator loses nothing, because the gate's answer for an UNVERIFIED rule is REVIEW —
the same state.

**A tuple per obligation, matching `declared`.** Rule 6(1)(a) is one obligation covering
manufacturer, packer and importer, so two spatially distinct bilingual pairs can each
disagree against it. A `Mapping[DeclarationField, CompetingReadings]` would drop one
silently — the same class of defect as the wrongful PASS this line of work exists to fix.
`by_obligation` was widened with a `TypeVar` constrained to `NormalisedField` and
`CompetingReadings` rather than a second grouping loop written: the same obligation can
carry two of either, for the same reason, so two loops would be one bug waiting to differ.

**No contracts change.** `CompetingReadings`, `DisagreementReason`,
`FieldState.REVIEW_REQUIRED`, `FieldFinding.observed_value` / `.evidence_span_ids` and
`EvidenceProvider.PADDLEOCR` were all already on `main` and exported. Nothing raised with
the owner.

**The sector gate still runs first, and that is correct — do not "fix" it.** A gated rule
(R6-1-A, R6-1-D, …) with an unconfirmed category still yields the gate's
INSUFFICIENT_EVIDENCE even for a contested field, because `sector_findings` returns before
`declaration_findings` runs. A confirmed category is a **precondition of evaluation**, not
a filter applied after it: whether the packaged rules govern an obligation at all is settled
before we ask what we observed. Recorded here because it looks like a miss and is not.

**Two tests, because one was not enough.** Both on **R6-1-C** — governs NET_QUANTITY,
VERIFIED, absent from `SECTOR_GOVERNED_RULES`, and named by `sector_gate.py` as an ungated
declaration rule.

`test_a_contested_declaration_is_review_required_not_insufficient_evidence` proves the
branch exists. It does **not** prove the branch sits above `if values:` — an obligation
present only in `contested` has an empty `declared` tuple and reaches REVIEW_REQUIRED under
either ordering. Abhiram caught that in review before any code was written.
`test_a_contested_declaration_outranks_a_resolved_one` puts the same `DeclarationField` in
**both** collections and asserts REVIEW_REQUIRED beats PASS. Its `EvidenceContext` is built
directly, because CTR-006's `_a_disagreement_is_never_also_a_field` refuses that shape at
`ExtractionResult` construction — that invariant belongs to extraction; what is pinned here
is the pipeline's branch ordering, which no validator in another layer holds in place. Its
docstring says so, so it does not get read as decorative and deleted.

**Falsification — three defects, all reverted.** Each with
`/usr/bin/find . -name __pycache__ -type d -exec rm -rf {} +` first and the surviving
directory count asserted at **0**.

| Defect introduced | Result |
|---|---|
| Contested branch deleted | `..._not_insufficient_evidence` red on **INSUFFICIENT_EVIDENCE** — the exact bug |
| Literal → `FieldState.INSUFFICIENT_EVIDENCE` | Both contested tests red |
| Branch moved **below** `if values:` | `..._outranks_a_resolved_one` red on **PASS**; the other test **passed** |

The third row is the one worth keeping. It is the direct demonstration that the first test
alone would have left the ordering untested, and that the second test is the thing holding
it — a reorder produces a wrongful PASS on a self-contradicting package and only that test
notices.

**Gate.** `741 passed, 32 skipped` locally. Baseline measured on `origin/main` @ `a95e8fb`
in this session, clean tree, bytecode purged: `739 passed, 32 skipped` — exactly **+2**,
nothing else moved. Ruff clean, `ruff format --check` clean, `lint-imports` **3 contracts
kept over 111 files / 368 dependencies**, exit code read directly rather than through a pipe.

**CLAUDE.md's baseline is still stale.** It says `707 passed / 32 skipped`; `origin/main`
is 739/32. Session 11 flagged it at 731/32 and it has moved again since. Not corrected here
— doc updates go in their own PR.

**Unblocks EXT-007 (Sitanshu).** The pipeline now consumes `disagreements`. Session 11's
handover still stands: at `binder.py:604` the value check runs before
`_are_spans_spatially_adjacent` at 607, and the adjacency check has to move above it or
EXT-007 will record disagreements that are not disagreements.

## Session 13 — 2026-09-07, RUL-005 (Claude Code, Opus 5)

**Ticket:** RUL-005 — encode the retail-sale scope limb. PR #68, cut from a95e8fb and
rebased onto d1114af when PIP-004 (#67) landed underneath it.

Read-only research pass first, then the encoding. Three of the ticket's premises were wrong
and the research pass corrected them before any code was written.

### What the corpus actually says

The limb is **Rule 3, "Applicability of the Chapter"**, and it has **three limbs, not one**.
The ticket named only 3(c); 3(a) — more than 25 kg or 25 litre — is the limb that actually
fires on real packages and is computable from `NET_QUANTITY` today.

Rule 3 disapplies **Chapter II only** (rules 3–23). Every rule in the store that produces a
finding is inside it; the Rule 2 definitions are Chapter I and are `NOT_AN_OBLIGATION`
anyway. A guard pins that set so a future Chapter III rule cannot be silently suppressed.

**Corpus gaps found, recorded rather than filled from memory:**

- The compilation prints the substitution of clauses 2(bb) and 2(bc) as *"(i) for clauses
  (bb) and (bc), the following clauses shall be substituted, namely"* and **does not name the
  notification**. Recorded in the rule's own comment. Semi-official source, stated as such.
- **Hotels, hospitals, airlines and railways are nowhere in this corpus.** They are canonical
  in secondary commentary. Anything listing them is listing them from memory.

### Two corrections to the plan, both accepted before implementation

**Rule 3(b) is subsumed by 3(a).** Bags above 50 kg are already above 25 kg, so confirming
3(b) can never change an answer 3(a) has not given. Its parameters are stored; no officer
input was built, because that would be a branch that can never fire. `rule_3b_is_subsumed_by_rule_3a()`
reads both figures from the store and is guarded, so an amendment reopens the question
instead of leaving a stale comment.

**An excluded package would otherwise have returned PASS.** `derive_verdict` documented
NOT_APPLICABLE as falling through to PASS — correct while sector overrides were the only
source of that state, since they carve out *some* obligations and leave the rest. Rule 3
carves out all of them. Without the new all-NOT_APPLICABLE pass this ticket would have
replaced POTENTIAL_VIOLATION with PASS on the very package it exists to fix.

### Shape

`app/modules/rules/scope.py`, sibling to `sector.py`. `SectorOverrideCondition` was **not**
bent to fit and no `ProductCategory` member was invented: a scope limb is not a sector, not
an override target, and does not vary per rule. Decided once per scan in `build_findings`,
applied in `_findings_for_rule` **before** the sector check — a sector override moves one
obligation, Rule 3 decides whether the chapter holding it reaches the package at all.

Every threshold is read from the store via `rule_by_id`; none is written in Python.

**No contracts change.** Both new inputs are plain `bool` on `EvidenceContext`, reaching it
the way `source_is_listing` does. `product_category` is a contracts type because it is
persisted on the `scans` row — these are not. Persisting the officer's assertion as a column
and filtering on it needs a contracts enum plus a migration: **raised, not taken.** The
assertion already appears in the `reason` of every finding it produces.

### Falsification — sixteen defects, all confirmed red

Bytecode purged with the absolute-path `find` first, every time. Three findings worth the
next person's attention:

1. **Two tests could not fail on their first draft.** The marker test and the threshold test
   read their expected value *out of the store* and fed it back — comparing the store against
   itself. A same-length edit to `not_for_retail_sale_marker` in `rules.yaml` left both green.
   Both now pin corpus literals (`25`, `50`, `"not for retail sale"`). This is the fifth
   instance of the unfalsifiable-test pattern on this project and the first where the test
   fetched its own expectation; worth watching for specifically.
2. **A docstring asserted a binder behaviour that is false.** It claimed the binder leaves
   `not for retail sale` unclassified. Measured: on its own line it binds to
   `COMMON_OR_GENERIC_NAME`. Per CLAUDE.md the *claim* was corrected, not the code — and a
   marker printed beside a batch code, which is how packs actually carry it, genuinely is
   unbound and now carries a test that does prove the all-spans read matters.
3. **The 739 existing tests passing unchanged is itself the evidence** for "nothing is
   inferred from an absence". Worth stating as a result rather than as an intention.

### Baseline

**741 passed / 32 skipped on `origin/main` (d1114af), measured in-session** — and 739/32 on
a95e8fb before PIP-004 landed, measured the same way. CLAUDE.md still says 707/32; that is now
two merges stale and someone should correct it. This branch: **772 / 32**. Zero regressions,
zero new skips. `ruff` clean, `lint-imports` exit 0 over 112
files, 3 contracts kept / 0 broken, checked directly rather than through a pipe.

`ruff format` reformatted two files that were already on `main` clean; folded in.

### Not done, deliberately

- **The HTTP surface was not exercised.** `app.main` refuses to boot without four model
  weight paths absent from this machine, and mocking them would not be an end-to-end check.
  Verified through the suite, including the orchestrator image path over patched vision,
  which does cover OCR text → normalisation → scope → verdict.
- **The export limb is dropped and stays [SOFT].** It is Rule 25, Chapter IV, and it points
  the *other* way: it makes Chapter II the standard an export pack must be re-labelled to
  before sale in India, not a scope exclusion. `export package` is undefined in the whole
  compilation. The limb rests on a territoriality argument about the Act, which is not
  sourced here. The docs PR corrects `rules-corpus/README.md`, which had claimed Rule 25
  supports it.

## Session 14 — 2026-09-07, MEA-009 Part A (Claude Code, Opus 5)

**Ticket:** MEA-009 Part A — a measurement outcome for a negative margin. Branch
`mea-009-margin-overlap-outcome`, cut from `2817c6b`. `contracts/` only; Part B is
Yashashvi's and is blocked on this landing.

### The problem

`measure_margins` (`modules/measurement/services.py`, MEA-006 / #47) computes a clearance per
direction and returns `MeasurementRefusal(reason="Margin overlaps active ink region.")` when
the figure comes back negative. A negative clearance means the surrounding ink has crossed
into the free space Rule 8(1)'s proviso requires — the violation the measurement exists to
detect. A refusal maps to INSUFFICIENT_EVIDENCE in `pipeline/measurement_findings.py:37`, so
the current shape says "we could not obtain the evidence" about a package we measured exactly
and whose measurement *is* the finding. Standing constraint #5 is the reason that matters.

### Two types, not one

`MeasurementMarginOverlapExact` and `MeasurementMarginOverlapCalibrated`, siblings off
`_MeasurementExactBase` and `_MeasurementCalibratedBase` — the same private bases CTR-005's
four hang off, never subclasses of any of them.

The deciding evidence was in the producing code, not in the ticket. **The `dist_mm < 0` branch
sits above the `is_artwork` split**, so an overlap arises on both provenances, and the
calibrated arm already computes `confidence = max(abs(dist_px) * conf_interval,
confidence_floor)` — `abs()`, so a negative distance already has a well-defined interval that
a single type would throw away. A single type would also need `confidence_interval: float |
None` and `reference_object: str | None`, which is exactly the shape this module exists to
make unrepresentable: a millimetre figure with no stated provenance. That is standing
constraint #2, and `test_millimetre_payload_with_no_calibration_source_is_rejected_by_the_union`
is the existing guard on it.

**The field is `overlap`, not `value`, and this is the one place these types depart from their
four siblings.** `pipeline/measurement_findings.py:59` formats any millimetre-bearing result as
`f"{result.value} {result.unit}"`. An overlap carrying `value=0.4` would reach an officer as
the identical string a 0.4 mm *clearance* produces — same number, opposite meaning, and no way
downstream to tell them apart. Under this name that line raises instead of misreporting, and
the mode has to be handled deliberately. Same reasoning as `MeasurementRefusal`, which carries
no `value` on purpose. `extra="forbid"` closes the other direction.

`gt=0`, as a positive magnitude. Zero is not an overlap — a flush declaration has a clearance
of exactly 0.0 and is already `MeasurementMarginExact`; admitting 0.0 here would give one
physical fact two representations. The direction lives in the type name, not in the sign.
`confidence_interval` tightened to `gt=0` on the calibrated variant, mirroring
`MeasurementMarginCalibrated`: reversing the sign of a distance recovered from a photograph
changes none of the pixel quantisation that made that tightening necessary.

**Observation, not verdict.** No `numeral_height_mm`, no multiple, no side name, no severity.
Rule 8(1)'s multiples are read from the rule store by `modules/rules/placement.py:52-55` and
compared against the numeral's own height. A test pins the field-name set against a literal so
a threshold added later turns red.

**No migration and no enum change.** `mode` is a `Literal`, not a `contracts.enums` member; no
ORM model or migration references a measurement type; the two evidence renderers branch on
report strings rather than on the union. Verified before assuming it.

### Naming corrected in review before any code was written

The plan proposed `MeasurementOverlapExact` with mode `margin_overlap_exact`. Abhiram caught
that the class name and its own discriminator disagreed: CTR-005's convention is the class name
minus `Measurement`, snake-cased, *is* the mode — `MeasurementMarginExact` → `margin_exact`.
These are margin outcomes, so `Margin` belongs in the name. Renamed before implementation.

### Falsification — nine defects, every one confirmed red, all reverted

Bytecode purged with the absolute-path `find` before each, surviving directory count asserted
at **0** rather than trusting the exit code. `measurement.py` restored byte-for-byte after each
and asserted equal to the original.

| Defect introduced | Test that went red |
|---|---|
| `gt=0` → `ge=0` on both overlap types (same byte length) | `..._of_exactly_zero_is_not_an_overlap`, alone |
| Lower bound removed — negative handed straight through | `..._is_carried_as_a_positive_magnitude` (+ the zero test) |
| Field renamed `overlap` → `value` | `..._cannot_be_read_as_a_margin_value` (+ 4 that name the field) |
| `reference_object` defaulted to `None` on the calibrated base | `..._without_a_reference_object_raises` (+ the CTR-005 guard on the same base) |
| `confidence_interval` given a default on the overlap type | `..._without_a_confidence_interval_raises`, alone |
| `gt=0` interval tightening dropped | `..._may_not_claim_a_zero_width_confidence_interval`, alone |
| Overlap made a subclass of the margin it inverts | `..._is_not_substitutable_for_a_margin` (+ 2) |
| A `numeral_height_mm` field added | `..._carries_a_rule_threshold`, alone |
| Calibrated overlap dropped from the union | `..._round_trips_through_the_union_as_itself`, alone |

**The first pass of this ran with `-x` and was a false confirmation.** Four of the nine reported
red on a test that was merely first in file order, not on the test the defect claims to be
caught by — for D3 it reported the round-trip guard, not the `value`-shadowing guard. Re-run
without `-x`, every defect turns its own claimed test red. This is the exact pattern AGENTS.md
warns about under "check that the defect you inject is the defect the test claims to catch",
and `-x` is a good way to walk into it.

**One test was not written, deliberately.** The union round-trip was already covered by
`test_each_measurement_shape_round_trips_through_the_union_as_itself`; the two overlap shapes
were added to its tuple and its docstring corrected from five shapes to seven, rather than a
second round-trip test being written beside it.

### Gate

Baseline **772 passed / 32 skipped** on `origin/main` @ `2817c6b`, measured in this session
with a clean tree and bytecode purged. This branch: **780 / 32** — **+8**, exactly the eight new
test functions, nothing else moved. `ruff check`, `ruff format --check` and `lint-imports` all
exit 0, read directly rather than through a pipe; 3 contracts kept / 0 broken over 112 files
and 377 dependencies.

CLAUDE.md still claims 707 / 32. That is now five merges stale and Session 13 already flagged
it. Not corrected here — doc updates go in their own PR.

### Raised, not taken

`FreeSpaceMeasurement` (`modules/rules/results.py:82`) types all four clearances as
`PositiveDecimal`, so `evaluate_rule8_free_space` cannot today accept an overlap — nor a flush
margin of `0.0`, which is a pre-existing gap the margin types already had. It is in
`modules/rules/` and it is not MEA-009. Abhiram is opening a ticket; flagged in the PR body and
not touched here.

### Unblocks MEA-009 Part B (Yashashvi)

The types are exported and inert until `modules/measurement` returns them. Two things Part B
should know before starting. **The overlap branch is above the `is_artwork` split**, so both
shapes have to be constructed there, not one. And **margins are still not wired into the
pipeline at all** — `pipeline/orchestrator.py:156-164` deliberately omits `measure_margins`,
because it needs a declaration bounding box that EXT-004 supplies, so Part B changes what the
function returns without changing what any scan currently does.
