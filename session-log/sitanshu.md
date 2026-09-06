# Session log — Sitanshu

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
