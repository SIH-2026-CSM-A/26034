# Session log — Abhiram

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
