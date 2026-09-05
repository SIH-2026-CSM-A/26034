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

**Decided**
- All normalisation return types are defined locally in bck/app/modules/extraction/types.py without modifying app.contracts (preserves Abhiram's single-ownership rule).
- Relative date expressions preserve relative_months=N and is_relative=True. If no packing date is provided, the normaliser returns success=False with reason_code=MISSING_PACKING_DATE.
- Pure deterministic address extraction avoids postal validation, geocoding, or LLM/NLP dependencies as per ticket constraints.
- Multi-date strings containing conflicting MM/YYYY or MM/YY dates return success=False with reason_code=AMBIGUOUS_VALUE and confidence=0.0.
- Out-of-bound or impossible calendar dates (31.02.2026, 29.02.2025, 32.01.2026) return success=False with reason_code=INVALID_VALUE and confidence=0.0.