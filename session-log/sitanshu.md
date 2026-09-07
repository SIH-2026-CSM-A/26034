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

### 2026-09-07 — EXT-008 Additional Script Detection & Reviewer Hardening (Sitanshu)

**Done**
- Stable Corpus Citation (LMPC 2011 Rule 9(4)):
  - Removed "Page 9" pdftotext artifact from citation. Grounded in gazette reference `Legal Metrology (Packaged Commodities) Rules, 2011, Rule 9(4)`: Rule 9(4) permits the use of other languages in addition to Hindi or English. EXT-008 distinguishes recognized additional scripts from unidentified non-text noise.
- Scalable Script-Bearing vs Noise Separation (`ScriptType.UNSUPPORTED`):
  - Extended `ScriptType` enum with `UNSUPPORTED = "UNSUPPORTED"`.
  - Implemented zero-dependency script-bearing letter detection via stdlib `unicodedata.category(c).startswith("L")`.
  - Non-handled script letters (e.g. Telugu, Kannada, Malayalam, Gujarati) classify as `ScriptType.UNSUPPORTED`, separating them cleanly from script-free noise/digits/punctuation (`ScriptType.NEITHER`).
  - Handled scripts (`DEVANAGARI`, `LATIN`, `TAMIL`, `BENGALI`) remain explicitly recognized. Multi-script spans return `ScriptType.MIXED`.
- Preserved Lexicon & Normalisation Boundaries:
  - Kept Devanagari lexicon intact. Did NOT add Tamil/Bengali/regional lexicons, numeral normalisers, or unit normalisers (preserving Rule 9(4) statutory boundary).
- Span Conservation:
  - Ensured `UNSUPPORTED` script spans remain conserved in `ExtractionResult.unclassified_spans` alongside Tamil and Bengali spans.
- Unit & Regression Testing in `bck/tests/modules/extraction/test_bilingual_declarations.py`:
  - Added assertions for `detect_script("నికర పరిమాణం") == ScriptType.UNSUPPORTED` (Telugu) and `detect_script("ಅನುಪಾತ") == ScriptType.UNSUPPORTED` (Kannada).
  - Verified `detect_script("నికర పరిమాణం") != detect_script("12345 !!!")` (UNSUPPORTED vs NEITHER).
  - Verified `detect_script("నికర పరిమాణం 500g") == ScriptType.MIXED` (Telugu + Latin).
  - Added Telugu span conservation check in `test_additional_script_unclassified_span_conservation`.

**Verification**
- 20/20 tests in `test_bilingual_declarations.py` passed (`0.27s`).
- Full backend suite: 730 passed, 32 skipped (`23.11s`).
- Quality gates: `ruff check .` (PASS), `ruff format --check .` (PASS), `lint-imports` (3 kept, 0 broken PASS).
- Executed mutation falsification check (disabled `UNSUPPORTED` classification -> RED failure `AssertionError: assert NEITHER == UNSUPPORTED`, restored -> GREEN).
