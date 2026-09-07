# Session Log - Sitanshu

### 2026-09-05 — EXT-001 OCR-text normalisation layer — Antigravity

**Done**
- Created bck/app/modules/extraction/types.py — defined DTO schemas (NormalizationResult[T], ReasonCode, MRPValue, NetQuantityValue, DateValue, AddressValue, ConsumerCareValue).
- Created bck/app/modules/extraction/mrp.py — implemented MRP normaliser handling currency symbols (₹, Rs., INR), / suffix, only, thousands separators, and tax inclusivity.
- Created bck/app/modules/extraction/net_quantity.py — implemented Net Quantity normaliser standardising units (g, kg, ml, l, N, pcs), e-mark (℮), number-then-unit, and unit-then-number formats.
- Created bck/app/modules/extraction/date.py — implemented Date normaliser supporting absolute ISO dates (YYYY-MM-DD, YYYY-MM), text months (MAR 2026), MM/YYYY & MM/YY conflicting date ambiguity detection, calendar date validation (31.02.2026, 29.02.2025, 32.01.2026), and explicit relative expressions ("Best before N months from packing"). Unresolved without packing date.
- Created bck/app/modules/extraction/address.py — implemented deterministic Address normaliser extracting legal metrology roles (MANUFACTURER, PACKER, MARKETER, IMPORTER, BRAND_OWNER), entity names, PIN codes (\b[1-9][0-9]{5}\b), and cleaned address blocks.
- Created bck/app/modules/extraction/consumer_care.py — implemented Consumer Care normaliser extracting toll-free/mobile/landline phones, email addresses, and postal complaint blocks, with explicit context keywords including "reach us".
- Created bck/app/modules/extraction/normalise.py — exposed top-level normalisation API functions.
- Created bck/tests/modules/extraction/test_normalise.py — built comprehensive table-driven test suite with 107 test cases covering valid, edge, invalid calendar dates, ambiguous dates, and malformed inputs.
- Verified all quality checks pass cleanly: uv run ruff check ., uv run ruff format --check ., uv run lint-imports, uv run pytest.

### 2026-09-05 — EXT-001 Abhiram Review Feedback & Technical Audit Refactor — Antigravity

**Done**
- Addressed Abhiram Review Item A (Decimal for Net Quantity):
  - Changed NetQuantityValue.value from float to Decimal in types.py.
  - Refactored net_quantity.py to parse quantities directly into Decimal without passing through float conversions.
  - Updated all net quantity test cases and type assertions to check isinstance(val, Decimal).
- Addressed Abhiram Review Item B (Strict ReasonCode Enum):
  - Enforced `reason_code: ReasonCode | None` contract in NormalizationResult[T] (removed `| str`).
  - Added type assertions across test suite to guarantee reason_code is either None or an instance of ReasonCode enum.
- Addressed Abhiram Review Item C (Confidence Constants & UNCALIBRATED PRIORS Docstrings):
  - Replaced all magic floats (0.95, 0.90, 0.85) with descriptive module-level named constants across all five parsers (CONFIDENCE_EXPLICIT_CURRENCY_HEADER, CONFIDENCE_EXPLICIT_QUANTITY_LABEL, CONFIDENCE_FULL_DATE, CONFIDENCE_ADDRESS_WITH_PINCODE, CONFIDENCE_MULTIPLE_CONTACT_CHANNELS, etc.).
  - Added module docstrings in mrp.py, net_quantity.py, date.py, address.py, and consumer_care.py explicitly noting that confidence values represent UNCALIBRATED PRIORS to be recalibrated once DAT-001 evaluation set exists.
- Addressed Abhiram Review Item D (Long Regex Named Comments):
  - Audited all extraction files for regex lines over 80 characters.
  - Added explicit named comments for every long regex detailing 1) what it matches and 2) why it is intentionally long / cannot reasonably be split.
- Addressed Abhiram Review Item E (MRP "45 Rupees Only" Support & False-Positive Guarding):
  - Added explicit support for "45 Rupees Only", "45 rupees only", and "45 Rupees".
  - Enforced strict requirement that arbitrary standalone numbers ("Call us at 45", "500 grams", "Product code 123") must NOT be parsed as MRP unless currency or MRP tokens are present.
- Regex Boundary Fixes:
  - Replaced hardcoded space padding in date.py, consumer_care.py, and net_quantity.py with proper boundary patterns (\b, ^, $, \s).
- Session Log Filename:
  - Renamed session-log/Sitanshu.md to session-log/sitanshu.md.
- Verification:
  - Ran ruff check ., ruff format --check ., lint-imports, and pytest (104 tests passed, 0 failures).

**Decided**
- NetQuantityValue.value must never convert through float to preserve exact decimal precision required for metrology compliance.
- ReasonCode enum contract is strictly closed (no string escape hatches allowed).
- Standalone numeric strings without currency/MRP evidence fail explicitly with ReasonCode.UNPARSEABLE_FORMAT.

## 2026-09-06 — EXT-005 Category Proposal — Antigravity

**Done**
- Resolved the two failing tests in `bck/tests/modules/extraction/test_category.py`:
  1. Fixed `Point` fixture construction in `_make_span` to use tuple coordinates `(0.0, 0.0)` matching the `Point = tuple[float, float]` type alias rather than `Point(x=..., y=...)`.
  2. Fixed double-counting regex overlap in `bck/app/modules/extraction/category.py` where a single text declaration `"Medical Devices Rules 2017"` was triggering both statutory and lexical flags. Converted text evaluation to `if / elif` matching per category so a statutory match on a field/span outranks/excludes substring lexical matches on the same text.
- Re-verified full test suite against Abhiram's landed contracts:
  - `uv run pytest tests/modules/extraction/test_category.py` -> **12 passed**.
  - `uv run pytest tests/modules/extraction` -> **272 passed**.
  - `uv run pytest` (full suite) -> **656 passed, 33 skipped**.
- Verified static checks and import boundaries:
  - `uv run ruff format --check .` -> **115 files formatted (PASS)**.
  - `uv run ruff check .` -> **All checks passed (0 errors)**.
  - `uv run lint-imports` -> **Contracts: 3 kept, 0 broken (PASS)**.
  - `git diff --check` -> **PASS**.
- Executed all 5 empirical mutation tests (RED on defect, GREEN when restored).

**Decided**
- A single statutory text phrase (e.g., `"Medical Devices Rules 2017"`) constitutes a statutory evidence signal (`0.95`), not two independent signals. Genuinely independent statutory and lexical evidence from separate fields/spans boost score to `0.98`.

**Verification**
- 12/12 EXT-005 tests passed cleanly.
- 656/656 active repository tests passed cleanly.
- No git commit, push, stage, or PR performed.

### 2026-09-06 — EXT-005 Category Proposal Review Fixes — Antigravity

**Done**
- Resolved Medical Device false positive by removing bare `MD-\d+` pattern from `_COSMETICS_STATUTORY_RE` / `_MEDICAL_DEVICE_STATUTORY_RE` regexes and strictly anchoring to explicit regulatory patterns (`MFG/MD/\d+`, `CDSCO`, `Medical Devices Rules`, `MDR 2017`).
- Resolved Food 14-digit false positive by fixing `_FOOD_STATUTORY_RE` pattern in `bck/app/modules/extraction/category.py` to require explicit FSSAI licensing tokens (e.g., `FSSAI Lic. No. 10012022000123`).
- Documented exact Legal Metrology corpus grounding citations in module docstrings for lexical commodity matching (LMPC 2011 Second Schedule, Third Schedule, Rule 6(8), G.S.R. 881(E), G.S.R. 778(E)).
- Added regression test `test_cream_biscuits_ambiguity_safely_abstains` for overlapping signals (Food biscuits vs Cosmetics cream) returning `None`.
- Replaced raw float magic numbers with module-level named constants for uncalibrated prior evidence scores: `CONFIDENCE_STATUTORY_SIGNAL = 0.95`, `CONFIDENCE_LEXICAL_SIGNAL = 0.80`, `CONFIDENCE_MUTUALLY_REINFORCING = 0.98`.
- Added unit tests `test_bare_md_batch_code_does_not_trigger_medical_device` and `test_arbitrary_14_digit_number_does_not_trigger_food`.
- Verified quality gates: 17/17 category tests passed, 277/277 extraction tests passed, 661/661 backend tests passed, `ruff check` passed, `ruff format --check` passed, `lint-imports` passed.
- Executed mutation falsification check (asserted RED on mutation, GREEN when restored).

**Decided**
- Bare numbers and generic batch prefixes must not trigger category proposals without explicit statutory or lexical token anchoring.
- Ambiguous multi-category commodity overlaps (e.g. cream biscuits) must safely return `None`.

**Verification**
- 17/17 category tests passed.
- 661/661 full test suite passed.
- `ruff check`, `ruff format --check`, `lint-imports`, `git diff --check` clean.
- 0 files committed, 0 files pushed, 0 files staged.

### 2026-09-07 — EXT-006 Bilingual Declarations — Antigravity

**Done**
- Corpus verification of Rule 9(4) from `rules-corpus/LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf` (Page 9):
  - Verified exact statutory text permitting declarations in Hindi in Devanagari script or in English.
- Implemented script classification in `bck/app/modules/extraction/binder.py`:
  - Created `ScriptType` enum (`DEVANAGARI`, `LATIN`, `MIXED`, `NEITHER`) and `detect_script(text: str) -> ScriptType` using Unicode regex range `\u0900-\u097F`.
- Implemented Devanagari numeral and unit token preprocessing:
  - Created `_preprocess_devanagari_text` converting Devanagari digits (`०-९` -> `0-9`) and Devanagari unit / keyword tokens (`ग्राम` -> `g`, `किग्रा` -> `kg`, `मात्रा` -> `Net Qty`, `एमआरपी` -> `MRP`, `रु.` -> `Rs.`).
- Implemented spatial bilingual pairing:
  - Added `_are_spans_spatially_adjacent` evaluating bounding-box gap vs heights and widths (`MAX_VERTICAL_GAP_MULTIPLIER = 3.0`, `MAX_HORIZONTAL_OFFSET_MULTIPLIER = 3.0`).
  - Added `_pair_bilingual_fields` pairing Devanagari and Latin spans in the same region with matching field type, numeric value, and unit into single `NormalisedField` records with `span_refs = (latin_span_id, devanagari_span_id)`.
- Enforced span conservation in `bind_spans`:
  - Guaranteed every input OCR span is accounted for either in `NormalisedField.span_refs` or returned in `unclassified_spans`.
- Created comprehensive test suite `bck/tests/modules/extraction/test_bilingual_declarations.py`:
  - Added 10 test cases covering monolingual regression, bilingual Net Qty pairing, Devanagari-only binding, unclassified span conservation, mixed script spans, script detection unit tests, spatial adjacency, distant span non-pairing, wrong declaration non-merging, and span conservation set equality assertion.
- Verified quality gates and mutation falsification:
  - 11/11 bilingual tests passed cleanly.
  - 694 passed, 32 skipped across full backend suite.
  - `ruff check .` -> **0 errors (PASS)**.
  - `ruff format --check .` -> **139 files formatted (PASS)**.
  - `lint-imports` -> **3 kept, 0 broken (PASS)**.
  - `git diff --check` -> **PASS**.
  - Executed 3 mutation tests (script detection, spatial multiplier, bilingual pairing) asserting RED on defect and GREEN on restore.

**Decided**
- Bilingual declarations in Devanagari and Latin script representing the same declaration field are spatially paired into single `NormalisedField` records with plural `span_refs`.
- Prohibited creating `bck/app/modules/extraction/evidence.py` or modifying contracts, normalisers, or pipeline files.

**Verification**
- 11/11 `test_bilingual_declarations.py` tests passed.
- 694 passed, 32 skipped across full backend suite.
- `ruff check`, `ruff format --check`, `lint-imports`, `git diff --check` clean.
- Committed (`1fb89c42bbd6aeb37496aefd136f564b90289182`), pushed to `origin/ext-006-bilingual-declarations`, 0 PRs created.


### 2026-09-07 — EXT-006 Final Lexicon Audit (Sitanshu)

**Done**
- Inspected statutory rules corpus (`rules-corpus/GSR-722E__2023-10-06__amendment-rules-2023.pdf`, `LMPC-2011`) for Devanagari price terms:
  - Verified that "मूल्य" is a generic term for price/value (used in "यूजिट जबक्री मूल्य" and "अजधकतम खुिरा मूल्य"), not an explicit statutory synonym for MRP.
  - Verified that "अधिकतम राशी" is unsupported by statutory text or project evidence.
- Lexicon Hardening in `bck/app/modules/extraction/binder.py`:
  - Removed generic "मूल्य" -> MRP and "अधिकतम राशी" -> MRP mappings from `_DEVANAGARI_TOKEN_MAP`.
  - Retained explicit Devanagari tokens ("शुद्ध मात्रा", "Net Qty"), ("निवल मात्रा", "Net Qty"), ("एमआरपी", "MRP"), ("रुपये", "Rs."), and ("रु.", "Rs.") along with standard unit conversions.
- Regression Testing & Quality Gates:
  - Added regression test `test_bare_mulya_does_not_cause_false_mrp` in `bck/tests/modules/extraction/test_bilingual_declarations.py` proving bare "मूल्य" is not classified as `RETAIL_SALE_PRICE`.
  - Verified `pytest tests/modules/extraction/test_bilingual_declarations.py`, `ruff check`, `ruff format --check`, `lint-imports`, and `git diff --check`.


### 2026-09-07 — EXT-006 Reviewer Blocker Hardening (Sitanshu)

**Done**
- Codebase & Lexicon Hardening in `bck/app/modules/extraction/binder.py`:
  - Empirically verified and removed unsupported lexicon mappings `("मूल्य", "MRP")` and `("अधिकतम राशी", "MRP")` from `_DEVANAGARI_TOKEN_MAP`.
  - Retained corpus-supported Devanagari mappings: `("शुद्ध मात्रा", "Net Qty")`, `("निवल मात्रा", "Net Qty")`, `("एमआरपी", "MRP")`, `("रुपये", "Rs.")`, `("रु.", "Rs.")`, and unit abbreviations.
  - Deduplicated header comments in `binder.py` to preserve exactly one Statutory Corpus Citation block and one Engineering Priors & Calibration Note block.
  - Documented `detect_script` limitation regarding `NEITHER` classification (non-Devanagari/Latin scripts, pure digits, punctuation-only spans).
- Test Hardening in `bck/tests/modules/extraction/test_bilingual_declarations.py`:
  - Added regression test `test_bare_mulya_does_not_cause_false_mrp` executing `bind_spans` on `"मूल्य ५० N"` and asserting no `RETAIL_SALE_PRICE` field is created.
  - Retained `test_bare_matra_does_not_cause_false_net_quantity` proving bare `"मात्रा"` is not mapped to `NET_QUANTITY`.
  - Verified 18 targeted test functions passing in `test_bilingual_declarations.py`.

**Verification**
- `grep -n 'मूल्य'` in `binder.py` -> 0 token map matches.
- `grep -n 'अधिकतम राशी'` in `binder.py` -> 0 token map matches.
- `grep -n 'test_bare_mulya'` in `test_bilingual_declarations.py` -> line 38.
- Cleared `__pycache__` via `/usr/bin/find`.
- Executed controlled mutation test (proves RED on defect with 5 failures, GREEN on restore with 18 passed).
- All 18 tests in `test_bilingual_declarations.py` PASSED (`0.17s`).
- Full suite executed via `/snap/bin/uv run pytest`: 704 passed, 32 skipped in 33.89s.
- `ruff check`, `ruff format --check`, `lint-imports`, `git diff --check` all clean (PASS).


### 2026-09-07 — EXT-007 Bilingual Declaration Disagreement (Sitanshu)

**Done**
- Base Branch: `ext-007-bilingual-disagreement` branched directly from `origin/main` (`d1114af`).
- Prerequisites Verified: CTR-006 (#65) and PIP-004 (#67) present on `origin/main`.
- Adjacency-Order Correction in `bck/app/modules/extraction/binder.py`:
  - Re-ordered candidate pairing loop inside `_pair_bilingual_fields` so spatial adjacency check (`_are_spans_spatially_adjacent`) executes **BEFORE** the value/unit mismatch check.
  - Enforced the three required disagreement conditions: (1) same field type, (2) spatially adjacent spans, (3) differing numeric value, unit, or normalised value.
- Disagreement Handling & Representation:
  - Diverted contested bilingual pairs into `ExtractionResult.disagreements` as `CompetingReadings` using `DisagreementReason.BILINGUAL_VALUE_MISMATCH`.
  - Both original reading candidates are preserved inside `CompetingReadings.readings` (Latin candidate first, Devanagari second).
  - Ensured strict contract disjointness: contested `field_type` is suppressed from `ExtractionResult.fields`.
- Test Matrix:
  - Expanded `bck/tests/modules/extraction/test_bilingual_declarations.py` to 26 unit tests covering agreeing bilingual pairs, numeric contradictions, unit contradictions, spatial separation, script restrictions (MIXED/NEITHER), monolingual regression, reading preservation, disjointness, and downstream PIP-004 routing (`REVIEW_REQUIRED` state and `REVIEW` verdict; no false `FAIL` / `INSUFFICIENT_EVIDENCE`).
- Falsification:
  - Temporarily commented out spatial adjacency check in `_pair_bilingual_fields`.
  - Executed pytest -> 3 tests failed RED (`test_disagreement_requires_spatial_adjacency` failed because distant spans were wrongfully treated as disagreements).
  - Restored spatial adjacency check -> pytest returned GREEN (26 passed).

**Verification**
- Focused Tests: `uv run pytest tests/modules/extraction/test_bilingual_declarations.py` (26 passed).
- All 4 Quality Gates:
  - `ruff check .` -> clean (PASS).
  - `ruff format --check .` -> clean (PASS).
  - `lint-imports` -> 3 contracts kept over 111 files / 368 dependencies (PASS).
  - `pytest` -> 749 passed, 32 skipped in 15.32s (PASS).
- `__pycache__` count: 0 (after `/usr/bin/find . -name __pycache__ -type d -exec rm -rf {} +`).
- No contracts files modified (`bck/app/contracts/**` untouched).
- No AI-attribution trailer.

### 2026-09-07 — EXT-007 Reviewer Blocker Fix: Same-Field-Type Agreeing & Disagreeing Pairs (Sitanshu)

**Done**
- Resolved Reviewer Blocker Defect: Fixed ordering and filtering in ind_spans() in ck/app/modules/extraction/binder.py where ields.extend(bilingual_fields) was executing before computing contested_field_types.
- Fix Implementation:
  - Computed contested_field_types = {d.field_type for d in bilingual_disagreements} from ilingual_disagreements.
  - Filtered ilingual_fields to construct uncontested_bilingual_fields excluding any field whose ield_type is in contested_field_types.
  - Extended only uncontested_bilingual_fields into ields.
  - Guaranteed invariant: If a ield_type appears in disagreements, that ield_type MUST NOT appear in ields, preventing Pydantic ExtractionResult disjointness validation failures when multiple bilingual pairs of the same obligation exist on a package.
- Regression Tests Added (ck/tests/modules/extraction/test_bilingual_declarations.py):
  - 	est_same_field_type_agreeing_and_disagreeing_pairs: Verifies 4 spans forming 2 bilingual NET_QUANTITY pairs (Pair A disagreeing 500g vs 250g, Pair B agreeing 500g vs 500g). Asserts ind_spans() constructs without ValueError, NET_QUANTITY appears in disagreements, NET_QUANTITY does NOT appear in ields, len(disagreements) == 1, and both competing readings are preserved.
  - 	est_contested_type_unpaired_third_span_lands_in_unclassified: Verifies an unpaired single span of a contested ield_type lands in unclassified_spans.
- Falsification:
  - Temporarily bypassed uncontested_bilingual_fields filtering (restored unconditional ields.extend(bilingual_fields)).
  - Executed pytest -> Failed RED with expected Pydantic ValidationError: field_types ['NET_QUANTITY'] appear in both fields and disagreements.
  - Restored uncontested_bilingual_fields filter -> Passed GREEN.
- Quality Gates:
  - pytest tests/modules/extraction/test_bilingual_declarations.py -> 28 passed in 0.86s.
  - Full pytest -> 782 passed, 32 skipped in 16.18s.
  -
uff format --check . -> clean (148 files formatted).
  -
uff check . -> clean (All checks passed!).
  - lint-imports -> clean (3 contracts kept, 0 broken).
  - __pycache__ count: 0 (excluding .venv).

### 2026-09-07 — EXT-008 Additional Script Detection Reviewer Hardening & Append-Only Reconstruction (Sitanshu)

**Done**
- Session Log Append-Only Reconstruction:
  - Reconstructed `session-log/sitanshu.md` from `origin/main` to restore historical entries and enforce strict append-only log history per AGENTS.md rule 9.
- Statutory Corpus Citation Cleanup (LMPC 2011 Rule 9(4)):
  - Removed "Page 9" pdftotext artifact from citation in `binder.py` and session log.
  - Grounded in stable gazette citation `Legal Metrology (Packaged Commodities) Rules, 2011, Rule 9(4)`: Rule 9(4) permits the use of other languages in addition to Hindi or English. EXT-008 distinguishes recognized additional scripts from unidentified non-text noise.
- Scalable Script-Bearing vs Noise Separation (`ScriptType.UNSUPPORTED`):
  - Extended `ScriptType` enum with `UNSUPPORTED = "UNSUPPORTED"`.
  - Implemented zero-dependency script-bearing letter detection via stdlib `unicodedata.category(c).startswith("L")`.
  - Non-handled script letters (e.g. Telugu, Kannada, Malayalam, Gujarati, Chinese, Arabic) classify as `ScriptType.UNSUPPORTED`, separating them cleanly from script-free noise/digits/punctuation (`ScriptType.NEITHER`).
- Non-ASCII Latin Script Diacritic Identification:
  - Implemented zero-dependency Latin identification via stdlib `unicodedata.name(char, "").startswith("LATIN ")`.
  - Accented Latin letters (`"é"`, `"Café"`, `"Nestlé"`, `"München"`) and decomposed combining marks (`"é"`) classify as `ScriptType.LATIN`.
- MIXED Script Classification & Bilingual Pairing Semantics:
  - `ScriptType.MIXED` represents any span containing two or more recognized/handled script categories.
  - Multi-script spans (e.g. Tamil + Latin, Bengali + Latin, Telugu + English) evaluate to `ScriptType.MIXED`.
  - In `_pair_bilingual_fields()`, `ScriptType.MIXED` spans fail `is_valid_bilingual_pair` (which strictly requires Latin <-> Devanagari). Mixed-script spans are excluded from bilingual pairing and land safely in `ExtractionResult.unclassified_spans`.
- Test Suite Refactoring & Independent Claim Parametrization:
  - Refactored `test_detect_script_ext_008_additional_scripts` into 7 independent claim tests / parametrized cases covering: (1) Noise (`NEITHER`), (2) Accented Latin (`LATIN`), (3) Devanagari (`DEVANAGARI`), (4) Tamil (`TAMIL`), (5) Bengali (`BENGALI`), (6) Unsupported script text (`UNSUPPORTED` vs `NEITHER`), and (7) Multi-script combinations (`MIXED`).
- Triple Mutation Falsification:
  - Falsification 1 (`UNSUPPORTED` Guard): Disabled `has_unsupported` letter check -> RED failure (`AssertionError: assert NEITHER == UNSUPPORTED`). Restored -> GREEN.
  - Falsification 2 (Latin Diacritic Guard): Bypassed `name.startswith("LATIN ")` -> RED failure (`AssertionError: assert UNSUPPORTED == LATIN`). Restored -> GREEN.
  - Falsification 3 (`MIXED` Guard): Bypassed `matching_scripts > 1` -> RED failure (`AssertionError: assert TAMIL == MIXED`). Restored -> GREEN.

**Verification**
- 30/30 tests in `test_bilingual_declarations.py` passed (`1.52s`).
- 797 passed, 32 skipped across full backend suite (`16.00s`).
- Quality gates: `ruff check` (PASS), `ruff format --check` (PASS), `lint-imports` (PASS), `git diff --check` (PASS).
- `session-log/sitanshu.md` numstat against `origin/main`: 0 deletions, additions > 0.


### 2026-09-07 — ExT-004 Declaration Bounding Box Prerequisite for Rule 8 Free-Space Clearance (Sitanshu)

**Done**
- Source-of-Truth Inspection & Data Flow Audit:
  - Audited bck/app/modules/extraction/binder.py and extraction data models.
  - Verified NormalisedField.span_refs identifies backing ExtractedSpan objects whose polygons field (tuple[Point, ...]) contains source bounding geometry.
  - Confirmed measure_margins() in bck/app/modules/measurement/services.py expects bounding box representation.
- Implementation of get_declaration_bbox() in bck/app/modules/extraction/binder.py:
  - Pure canonical query helper: get_declaration_bbox(field: NormalisedField, spans: Sequence[ExtractedSpan]) -> tuple[float, float, float, float] | None.
  - Calculates exact (min_x, min_y, max_x, max_y) enclosing bounding envelope over the union of all polygons of referenced spans.
  - Preserves exact floating-point canvas pixel coordinates; quantization (floor/ceil integer conversion) is deferred to downstream measurement callers.
- Refusal Behavior:
  - Returns None (refusal) when geometry is undeterminable: empty span_refs, missing referenced span_id, empty or < 3 vertex polygons, non-finite (NaN/Inf) coordinates, or degenerate zero/negative area envelopes (min_x >= max_x or min_y >= max_y).
- Unit Testing & Falsification (bck/tests/modules/extraction/test_bilingual_declarations.py):
  - Added 11 focused unit tests covering single span, bilingual pairs, multi-line address envelopes, empty refs refusal, missing span ID refusal, empty polygons, < 3 vertex polygons, maloformed point refusal, non-finite coord refusal, degenerate geometry refusal, and fractional floating-point preservation.
  - Executed 6 independent falsification mutations (multi-span union truncation, min/max corruption, dummy refusal bbox, float quantization, non-finite coords, degenerate envelope) — all 6 went RED under mutation and returned 100% GREEN upon restoration.
- Quality Gates & Integrity:
  - All 4 quality gates passed: ruff check . (0 errors), ruff format --check . (0 format violations), lint-imports (3 contracts kept, 0 broken across 115 files), pytest (812 passed, 32 skipped).
  - Targeted extraction tests: 39 passed in 1.23s.
  - python -m py_compile passed cleanly on modified modules.
  - Rebased cleanly onto current origin/main (c4922ce2463cd4485969c3de09b1d5d9db2e7033).
  - No contracts, pipeline, or measurement files modified. Zero AI-attribution trailers.


### 2026-09-08 — EXT-011 Product Categorisation Taxonomy (Sitanshu)

**Done**
- Verified Taxonomy Contracts & Boundaries:
  - Confirmed `ProductCategory` enum in `bck/app/contracts/enums.py` retains exactly 3 gazette-anchored members (`food`, `cosmetics`, `medical_device`), matching `sector:` keys in `bck/app/modules/rules/data/rules.yaml`.
  - Confirmed `CategoryProposal` remains a contract model defined in `bck/app/contracts/evidence.py` and exported strictly via `bck/app/contracts/__init__.py`. It is NOT exported from `bck/app/modules/extraction/__init__.py`.
  - Confirmed `propose_category` in `bck/app/modules/extraction/category.py` remains a pure, deterministic inference function returning `CategoryProposal | None`.
- Refactored Category Unit Tests (`bck/tests/modules/extraction/test_category.py`):
  - Replaced imported confidence constants (`CONFIDENCE_STATUTORY_SIGNAL`, `CONFIDENCE_LEXICAL_SIGNAL`, `CONFIDENCE_MUTUALLY_REINFORCING`) with hardcoded literal float assertions (`0.95`, `0.80`, `0.98`) to adhere to strict literal test assertion contracts.
  - Added `test_equal_confidence_tie_returns_none` verifying that when two active categories evaluate to equal non-zero confidence scores, `propose_category` deterministically abstains and returns `None`.
- Falsification Verification:
  - Purged bytecode (`__pycache__`) and verified surviving count was 0.
  - Mutated conflict/tie abstention guard in `category.py` (`if second_score >= top_score:` replaced with `if False:`).
  - Executed pytest without `-x` -> 3 tests failed RED (`test_conflicting_category_evidence_returns_none`, `test_competing_food_and_cosmetics_lexical_signals_safely_abstain`, `test_equal_confidence_tie_returns_none`).
  - Restored `category.py` from scratchpad backup -> All 19 tests passed GREEN (100%).
- Scope & Verification:
  - All 327 extraction module unit tests passed (`327 passed`).
  - Verified no contracts, pipeline, core model, or analytics files were touched.
  - Checked `git diff --numstat origin/main -- session-log/sitanshu.md` confirming 0 deletions.

- Deterministic Display Category Taxonomy Implementation:
  - Implemented `DisplayCategory(StrEnum)` (`packaged_food`, `cosmetics`, `non_food_packaged_goods`, `electronics`, `household`) and `DisplayCategoryTaxonomy(dataclass)` in `bck/app/modules/extraction/category.py`.
  - Implemented `classify_display_category(result: ExtractionResult) -> DisplayCategoryTaxonomy | None` covering demo product space branches (`packaged_goods` -> `packaged_food`, `cosmetics`, `non_food_packaged_goods` -> `electronics`, `household`).
  - Restored imported confidence constants (`CONFIDENCE_STATUTORY_SIGNAL`, `CONFIDENCE_LEXICAL_SIGNAL`, `CONFIDENCE_MUTUALLY_REINFORCING`) across test expected value assertions in `bck/tests/modules/extraction/test_category.py`.
- Legal Sector & Data Flow Isolation:
  - `DisplayCategory` remains completely separate from `ProductCategory` (`food`, `cosmetics`, `medical_device`).
  - `CategoryProposal.category` remains strictly `ProductCategory` and is not auto-confirmed.
  - Electronics and household products return `propose_category(result) is None` for legal sector proposal, preventing illegal sector rule dispatch while providing valid display taxonomy classification.
- ANL-001 & Scope Alignment:
  - ANL-001 is not present in the repository, so analytics vocabulary alignment is not claimed.
- Comprehensive Verification Results:
  - Focused category unit tests (`bck/tests/modules/extraction/test_category.py`): 29 passed.
  - Extraction module unit tests (`bck/tests/modules/extraction`): 337 passed.
  - Full backend pytest suite: 851 passed, 32 skipped, 1 pre-existing MEA-007 synthetic geometry failure.
  - Quality gates: `ruff check` (0 errors), `ruff format --check` (clean), `lint-imports` (3 contracts kept), `compileall -q app` (0 errors), `git diff --check` (clean).
- Falsification Verification:
  - All 7 display & legal taxonomy falsification mutations (disable electronics, disable household, remove parent hierarchy, disable display tie resolution, disable legal tie resolution, invalid display in CategoryProposal, widen ProductCategory) evaluated to RED and restored to 100% GREEN.


- CMP-001 Manufacturer Complaint Loop (Part A - Domain & Service):
  - Created `bck/app/modules/complaints/` domain & service modules (`domain.py`, `service.py`, `__init__.py`).
  - Implemented `ComplaintStatus` StrEnum (`RAISED`, `ACKNOWLEDGED`, `RESOLVED`, `REJECTED`).
  - Implemented immutable `ComplaintRecord` representing pure domain append-only complaint thread history rows (`id`, `scan_id`, `verdict_id`, `manufacturer_name`, `issue_summary`, `status`, `raised_by_officer_id`, `raised_at`, `supersedes_id`).
  - Implemented explicit transition validation (`validate_status_transition`) enforcing valid paths (`RAISED` -> `ACKNOWLEDGED`, `RESOLVED`, `REJECTED`; `ACKNOWLEDGED` -> `RESOLVED`, `REJECTED`). Disallowed all reverse/terminal transitions (e.g. `RESOLVED` -> `RAISED`), raising `InvalidStatusTransitionError`. Reopening after resolution requires constructing a new thread referencing `prior_complaint` via `supersedes_id`.
  - Implemented structural officer confirmation gate (`ConfirmedVerdict`) requiring a non-null officer `ReviewRow` with finalising action (`CONFIRM`, `REJECT`, `OVERRIDE`) yielding effective verdict `POTENTIAL_VIOLATION`. Rejecting machine-only verdicts, missing reviews, `ANNOTATE`, `REQUEST_RECAPTURE`, effective `PASS`, `REVIEW`, or invalid `OVERRIDE` by raising `UnconfirmedVerdictError`.
  - Implemented factual complaint text builder `build_issue_summary()` citing `rule_id`, `field`, `measured_value`, `required_value`, and "potential violation", while rejecting forbidden legal terms ("violation confirmed", "illegal", "non-compliant").
  - Implemented `ComplaintService` methods `raise_complaint()` and `transition_complaint()`.
  - Created unit tests in `bck/tests/modules/complaints/test_complaints_domain.py` covering all transition rules, confirmation gate checks, wording restrictions, and append-only thread behaviors.
- Falsification Verification:
  - Mutated transition matrix in `domain.py` so `RESOLVED -> RAISED` became legal.
  - Executed `pytest` without `-x` -> Falsification suite failed RED (`FAILED tests/modules/complaints/test_complaints_domain.py::TestInvalidTransitions::test_invalid_transitions` - `Failed: DID NOT RAISE InvalidStatusTransitionError`).
  - Restored original `domain.py` -> Test suite returned 100% GREEN (13 passed).
- Quality Gates & Scope Compliance:
  - `pytest tests/modules/complaints/test_complaints_domain.py`: 13 passed.
  - `ruff check app/modules/complaints tests/modules/complaints`: 0 errors.
  - `ruff format --check app/modules/complaints tests/modules/complaints`: 4 files formatted.
  - `lint-imports`: 3 contracts kept (Layers, Module independence, No bck.* import path).
  - `compileall -q app`: 0 errors.
  - Full backend pytest suite: 918 passed, 51 skipped, 1 pre-existing MEA-007 synthetic geometry failure (`test_coin_oblique_synthetic_geometry`).
  - Bytecode purge: 0 surviving `__pycache__` directories.
  - Ownership integrity: No changes to `repository.py` (Part B deferred), `contracts/**`, `core/**`, `pipeline/**`, `persistence/**`, `migrations/**`, `analytics/**`, `frontend/**`, `rules/**`, `measurement/**`, `evidence/**`.

- CMP-001 Manufacturer Complaint Loop (Part B - Persistence Repository):
  - Created `bck/app/modules/complaints/repository.py` and exported repository API in `bck/app/modules/complaints/__init__.py`.
  - Implemented pure domain <-> SQLAlchemy ORM mappings (`_record_to_row`, `_row_to_record`) between `ComplaintRecord` and `ComplaintRow` (`app.core.complaints.ComplaintRow`).
  - Implemented async persistence repository functions: `add_complaint()`, `get_complaint()`, `get_complaints_for_scan()`, and `get_latest_complaint_for_scan()`.
  - Enforced append-only thread integrity: status escalation rows reference previous complaint IDs via `supersedes_id` without executing any SQL `UPDATE` queries.
  - Implemented unit test suite in `bck/tests/modules/complaints/test_complaints_repository.py`.
- Falsification Verification:
  - Mutated `_record_to_row` in `repository.py` to drop `supersedes_id` mapping (setting `supersedes_id=None`).
  - Executed pytest without `-x` -> Test suite failed RED (`FAILED tests/modules/complaints/test_complaints_repository.py::test_get_complaints_for_scan` - `AssertionError: Differing attributes: ['supersedes_id']`).
  - Restored clean `repository.py` -> Test suite returned 100% GREEN (21 passed across `test_complaints_domain.py` and `test_complaints_repository.py`).
- Quality Gates & Scope Compliance:
  - `pytest tests/modules/complaints/`: 21 passed.
  - `ruff check .`: 0 errors.
  - `ruff format --check .`: 179 files formatted.
  - `lint-imports`: 3 contracts kept (Layers, Module independence, No bck.* import path).
  - `compileall -q app`: 0 errors.
  - Full backend pytest suite: verified.
  - Bytecode purge: 0 surviving `__pycache__` directories.
  - Ownership integrity: Modified ONLY allowed files (`repository.py`, `__init__.py`, `test_complaints_repository.py`, `session-log/sitanshu.md`). No modifications to `contracts`, `pipeline`, `frontend`, `analytics`, `measurement`, `evidence`, `rules`, `core`, `persistence`, `migrations`. No git commits or pushes made.

- EXT-010 Follow-Up (Typed Declaration-BBox Refusal & Dead Branch Removal):
  - Refactored get_declaration_bbox() in bck/app/modules/extraction/binder.py to replace ambiguous None returns with typed BboxRefusal(reason=BboxRefusalReason, span_id=...).
  - Added BboxRefusalReason(StrEnum) with 7 explicit reasons categorised into Category A (evidence gap: NO_SPAN_REFS, UNKNOWN_SPAN_ID) and Category B (geometry defect: EMPTY_POLYGON, INSUFFICIENT_VERTICES, MALFORMED_VERTEX, NON_FINITE_COORDINATE, DEGENERATE_ENVELOPE).
  - Added @dataclass(frozen=True) class BboxRefusal(reason: BboxRefusalReason, span_id: str | None = None).
  - Implemented bbox_refusal_officer_reason(refusal: BboxRefusal) -> str ensuring distinct officer-facing messages across all seven refusal reasons.
  - Removed dead hasattr(pt, "x") geometry branch in polygon processing since ExtractedSpan.polygon is typed as tuple[tuple[float, float], ...]. Uses tuple indexing (x, y) = pt[0], pt[1].
  - Updated extraction tests in bck/tests/modules/extraction/test_bilingual_declarations.py covering all seven refusal causes, span traceability, category distinctions, and officer refusal messages.
- Falsification Verification:
  - Falsification A: Mutated MALFORMED_VERTEX return path -> pytest failed RED (AssertionError in test_insufficient_vertices_and_malformed_vertex_have_distinct_reasons).
  - Falsification B: Mutated bbox_refusal_officer_reason to return "generic failure" -> pytest failed RED (AssertionError in test_all_seven_reasons_produce_distinct_officer_messages).
  - Falsification C: Mutated MALFORMED_VERTEX return to EMPTY_POLYGON -> pytest failed RED (AssertionError in test_get_declaration_bbox_refusal_malformed_point).
  - Falsification D: Mutated EMPTY_POLYGON return to None -> pytest failed RED (AssertionError in test_get_declaration_bbox_refusal_empty_polygon).
- Quality Gates & Scope Compliance:
  - pytest tests/modules/extraction/test_bilingual_declarations.py: 57 passed.
  - ruff check .: All checks passed!
  - ruff format --check .: 187 files formatted.
  - lint-imports: 3 contracts kept.
  - Full backend pytest suite: 966 passed, 51 skipped, 1 pre-existing MEA-007 synthetic geometry failure (test_coin_oblique_synthetic_geometry).
  - Bytecode purge: 0 surviving __pycache__ directories.
  - Ownership & Scope Integrity: Modified ONLY allowed files (binder.py, test_bilingual_declarations.py, session-log/sitanshu.md). No changes made to bck/app/contracts/, measure_margins(), pipeline wiring, or EXT-011. No git commits or pushes made.
