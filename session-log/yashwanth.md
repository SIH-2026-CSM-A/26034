# Session Log — Yashwanth

### 2026-09-06 — EXT-004 OCR span classification and spatial role binder — Antigravity

**Branch**
- `feat/ext-004-span-classification` (PR #44)

**Files changed**
- `bck/app/modules/extraction/binder.py`
- `bck/app/modules/extraction/__init__.py`
- `bck/tests/modules/extraction/test_binder.py`
- `session-log/yashwanth.md`

**What was done**
- Implemented `bind_spans` in `bck/app/modules/extraction/binder.py` to classify extracted OCR spans and bind them to canonical `NormalisedField` records according to spatial proximity, keyword anchor headers, and specialized field normalisers.
- Added anchor regex matching for address blocks (`Manufactured by`, `Packed by`, `Marketed by`, `Imported by`, `Brand Owner`).
- Bound address blocks via downward vertical clustering across multi-line spans, extracting valid 6-digit Indian PIN codes.
- Bound net quantity, MRP, manufacture/expiry/best before dates, commodity names, dimensions, consumer care details, and country of origin.
- Ensured strict span conservation: every input span is either assigned to a resolved field or retained in `unclassified_spans`.
- Added comprehensive unit tests in `bck/tests/modules/extraction/test_binder.py` covering single and multiple address bindings, pin code extraction, multi-field label parsing, and unclassified span preservation.
- All checks passed cleanly (`ruff check`, `ruff format`, `lint-imports`, `pytest`).

---

### 2026-09-06 — RUL-004 `governs_declarations` scoping on the rule store — Antigravity

**Branch**
- `rul-003-governs-declarations` (ticket RUL-004)

**Files changed**
- `bck/app/modules/rules/models.py`
- `bck/app/modules/rules/evaluator.py`
- `bck/app/modules/rules/data/rules.yaml`
- `bck/tests/modules/rules/test_loader.py`
- `bck/tests/modules/rules/test_evaluation.py`
- `session-log/yashwanth.md`

**What was done**
- Addressed PR review feedback on RUL-004 (`governs_declarations` scoping):
  - Audited statutory text in `rules-corpus/` for `R9-1-MANNER`, `R9-3-OUTER-CONTAINER`, `R8-1-PDP-PLACEMENT`, `R7-2-TABLE-I`, and `R7-3-WIDTH-RATIO`.
  - Replaced temporary "pending corpus review" placeholder comments in `bck/app/modules/rules/data/rules.yaml` with production-grade statutory explanations demonstrating why these clauses genuinely govern all declarations under the Legal Metrology (Packaged Commodities) Rules, 2011.
  - Verified that Rule 6(11) (unit sale price) is intentionally excluded from `rules.yaml` per architectural decisions and test `test_rule_store_excludes_f18_and_rule_6_11`.
  - Wired `rule_governs_declaration` into the execution path of `evaluate_rule` in `bck/app/modules/rules/evaluator.py`, verifying target declaration fields and raising `ValueError` when an un-governed declaration field is evaluated against a rule.
  - Replaced brittle `assert len(populated) == 13` in `bck/tests/modules/rules/test_loader.py` with property-based assertions over loaded rules.
  - Replaced literal test in `bck/tests/modules/rules/test_evaluation.py` with an evaluation-path falsification test verifying that evaluating an out-of-scope declaration against a narrowed rule fails via `evaluate_rule`, while a widened rule succeeds.
  - Restored append-only discipline in `session-log/yashwanth.md`, preserving the complete EXT-004 session entry alongside RUL-004.

---

### 2026-09-07 — VND-001 Part A: Vendor domain models and routing service — Antigravity

**Branch**
- `vnd-001-vendor-self-scan`

**Files changed**
- `bck/app/modules/vendor/domain.py`
- `bck/app/modules/vendor/service.py`
- `bck/tests/modules/vendor/__init__.py`
- `bck/tests/modules/vendor/test_domain.py`
- `bck/tests/modules/vendor/test_service.py`
- `session-log/yashwanth.md`

**What was done**
- Implemented Part A of VND-001 in `bck/app/modules/vendor/`:
  - `domain.py`:
    - Defined `VendorType` StrEnum (`GODOWN`, `SUPERMARKET`, `KIRANA`) for vendor trade classification.
    - Implemented `VendorSubmission` ContractModel carrying vendor identity (`id`, `name`, `vendor_type`), territorial jurisdiction (`state` required, `region` and `district` optional, mirroring the Scan jurisdiction shape), and label image reference (`image_reference`).
    - Maintained architectural boundary: `VendorSubmission` does NOT wrap a scan type; any scan generated traverses the identical pipeline as an officer-initiated scan.
    - Kept vendor types local to `app.modules.vendor` without modifying `app.contracts`, following the `ExtractionResult` precedent in `ARCHITECTURE.md`.
  - `service.py`:
    - Implemented canonical pure function `route_verdict` (aliased as `route_vendor_submission` and `route_vendor_result` as a single implementation) taking `jurisdiction: Jurisdiction` and `verdict: Verdict` (no caller-supplied `officer_tier`; `target_tier` is derived purely from jurisdiction and verdict).
    - Function returns `RoutingDecision` indicating destination officer tier, whether an on-site physical inspection visit is required, and whether action is required.
    - `Verdict.PASS` routes as informational (`requires_visit=False`, `action_required=False`) to the territorial officer's queue.
    - `Verdict.REVIEW` flags for action (`requires_visit=False`, `action_required=True`).
    - `Verdict.POTENTIAL_VIOLATION` flags for action and mandates an on-site physical inspection visit (`requires_visit=True`), routing to the field inspecting tier (`DISTRICT` if pinned; `REGIONAL` or `STATE` if unpinned).
    - Removed unreachable `INSUFFICIENT_EVIDENCE` branch: `Verdict` only has `PASS`, `REVIEW`, and `POTENTIAL_VIOLATION`; `INSUFFICIENT_EVIDENCE` is a `FieldState` that resolves to `Verdict.REVIEW` at verdict assembly time.
    - Exported `scope_vendor_query` delegating directly to `scope_to_jurisdiction` from `app.core.rbac`.
  - Unit tests:
    - Implemented `bck/tests/modules/vendor/test_domain.py` testing enum values, submission creation, field alias access, jurisdiction mirroring, empty string validation, extra-field forbidding, and model immutability.
    - Implemented `bck/tests/modules/vendor/test_service.py` covering all three branches of `route_verdict`, null-district routing behavior across tiers, state-to-district inspection rerouting, single-implementation alias equality, and jurisdiction query scoping. Constructed objects only, zero DB/persistence dependencies.

---

### 2026-09-07 — VND-001 Part B: Vendor persistence repository and jurisdiction lookup — Antigravity

**Branch**
- `vnd-001-vendor-self-scan`

**Files changed**
- `bck/app/modules/vendor/repository.py`
- `bck/app/modules/vendor/__init__.py`
- `bck/tests/modules/vendor/test_repository.py`
- `session-log/yashwanth.md`

**What was done**
- Built Part B of VND-001 (`bck/app/modules/vendor/repository.py`) after synchronizing and rebasing onto `origin/main` following the merge of CORE-004 (#90):
  - Synchronized and verified the four tables landed in CORE-004 (`vendors`, `vendor_scans`, `complaints`, `product_reviews`) and their models in `app.core.market` and `app.core.complaints`.
  - Implemented `persist_vendor_scan` (aliased as `record_vendor_scan`, `persist_vendor_submission`, and `record_vendor_submission`):
    - Stages a `VendorSubmission` as a `vendor_scans` row against an existing scan.
    - If the vendor is not yet present in `vendors`, stages the parent `VendorRow` first and performs a load-bearing flush so the foreign key constraint is satisfied without requiring unpromised ORM relationship ordering.
    - If the vendor already exists, reuses the existing `VendorRow` without duplicate key errors.
    - Strict session boundary: repository stages and flushes; transaction commit is owned by the caller.
  - Implemented `get_vendor_jurisdiction` (aliased as `lookup_vendor_jurisdiction`):
    - Looks up a vendor by `vendor_id` and reconstructs the territorial `Jurisdiction` (state required, region and district optional) for direct consumption by Part A's `route_verdict`.
    - Returns `None` when the vendor is not present in storage.
  - Implemented `to_uuid` coercion:
    - Transparently handles Python `UUID` instances, standard UUID strings, and non-UUID domain identifiers (like `VND-BLR-001`) via deterministic UUIDv5 hashing with `NAMESPACE_DNS`, ensuring repeatable lookups.
  - Implemented `to_core_vendor_type` enum mapping:
    - Bridges domain uppercase `VendorType` (`GODOWN`, `SUPERMARKET`, `KIRANA`) with core lowercase `VendorType` (`godown`, `supermarket`, `kirana`) as declared in `app.core.enums` and the database migration.
  - Added query helpers `get_vendor` and `get_vendor_scan`.
  - Maintained strict import rules: `vendor/` imports only from `app.contracts`, `app.core`, and itself. No imports from `pipeline`, other modules, complaints, or product reviews.
  - Exported public models, services, and repository functions in `bck/app/modules/vendor/__init__.py`.
  - Created comprehensive unit tests in `bck/tests/modules/vendor/test_repository.py` against a real database session:
    - Verified vendor and attribution row persistence with verified attributes.
    - Verified multiple scan attributions reusing a single vendor row.
    - Verified primary key constraint refusing duplicate attributions for the same scan (`IntegrityError`).
    - Verified jurisdiction reconstruction across full, regional, and state-level vendor territories.
    - Verified missing vendor lookups return `None`.
    - Verified end-to-end integration piping `get_vendor_jurisdiction` directly into `route_verdict` across all branches and tiers.
    - Verified caller-owned transaction commit / rollback discipline.
    - Verified UUID coercion, vendor type mapping, and alias identities.

---

### 2026-09-07 — VND-001 Part B Refactor: Typed UUIDs and Core VendorType Unification — Antigravity

**Branch**
- `vnd-001-vendor-self-scan`

**Files changed**
- `bck/app/modules/vendor/domain.py`
- `bck/app/modules/vendor/repository.py`
- `bck/app/modules/vendor/__init__.py`
- `bck/tests/modules/vendor/test_domain.py`
- `bck/tests/modules/vendor/test_repository.py`
- `session-log/yashwanth.md`

**What was done**
- Unified vendor identification on `uuid.UUID`:
  - Updated `VendorSubmission.id` (and alias property `vendor_id`) to `uuid.UUID`, validating incoming strings or UUID instances natively via Pydantic.
  - Updated repository signatures (`scan_id: UUID`, `vendor_id: UUID`) and eliminated downstream `to_uuid()` coercion function entirely.
  - Updated `test_domain.py` and `test_repository.py` fixtures to use real UUIDs (`uuid4()`).
- Unified `VendorType` enum:
  - Deleted duplicate local `VendorType` enum in `domain.py`.
  - Imported and re-exported `app.core.enums.VendorType` (the lowercase enum: `godown`, `supermarket`, `kirana`) from `app.core`.
  - Deleted `to_core_vendor_type()` from `repository.py` and removed from `__all__`.
  - Updated `test_domain.py` to assert the lowercase values (`"godown"`, `"supermarket"`, `"kirana"`).
  - Updated `test_repository.py` to use `VendorType` directly.

---

### 2026-09-07 — VND-001 Lint, Independence Contract, and CODEOWNERS Alignment — Antigravity

**Branch**
- `vnd-001-vendor-self-scan`

**Files changed**
- `bck/tests/modules/vendor/test_service.py`
- `session-log/yashwanth.md`

**What was done**
- Fixed E501 line length violation in `bck/tests/modules/vendor/test_service.py`: shortened `test_service_aliases` docstring to 94 characters (<= 100 characters max).
- Prepared plain text diffs for `bck/pyproject.toml` (adding `app.modules.vendor` to import-linter independence contract) and `.github/CODEOWNERS` (assigning `/bck/app/modules/vendor/`, `/bck/tests/modules/vendor/`, and `/session-log/yashwanth.md` to `@ybaddam8-png`) for ticket review by Abhiram.
- Left `bck/pyproject.toml` and `.github/CODEOWNERS` unstaged and uncommitted per `AGENTS.md` module ownership boundaries (Abhiram owns `.github/` and core repo config).
- Investigated `test_coin_oblique_synthetic_geometry` in `tests/modules/measurement/test_measurement.py`: confirmed it is a pre-existing failure on `origin/main` (under Yashashvi's `measurement/` module) and was completely untouched by this branch. Left untouched as instructed.

---

### 2026-09-07 — VND-001 PR opened, CI verified

**PR:** #101, `vnd-001-vendor-self-scan` -> `main`

**CI result:** 1 failing (`test_independence_contract_covers_every_module_on_disk`,
expected — blocked on Abhiram's pyproject.toml/CODEOWNERS diffs, already posted on the
ticket). 981 passed, 2 skipped. Lint, format, import-boundaries all green.

**Note:** `test_coin_oblique_synthetic_geometry` (measurement/, Yashashvi's) failed
locally on this machine every run but passed clean in CI — likely environment/precision
flake, not a real regression. Flagged, not touched.

**Status:** waiting on Abhiram to apply the two config diffs and approve. Nothing else
outstanding on VND-001.
