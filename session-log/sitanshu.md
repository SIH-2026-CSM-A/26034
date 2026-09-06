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
