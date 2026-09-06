# Session log — Abhiram

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
- Branch was cut from `origin/main` (4ad693b), which does not yet carry EVD-002's `boto3`.

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
