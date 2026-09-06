# Session Log - Sitanshu

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

## 2026-09-06 — EXT-006 Bilingual Declarations — Antigravity

**Done**
- Implemented deterministic script detection (`detect_script`) with `ScriptType` enum (`DEVANAGARI`, `LATIN`, `MIXED`, `NEITHER`) using Unicode regex `\u0900-\u097F`.
- Updated `_preprocess_devanagari_text` in `bck/app/modules/extraction/binder.py` to translate Devanagari numerals (`०-९` -> `0-9`) and standard unit tokens (`gram` -> `g`, `matra` -> `Net Qty`) without broad dictionary translation.
- Implemented 2D spatial adjacency predicate (`_are_spans_spatially_adjacent`) using polygon bounding-box geometry and named constants (`MAX_VERTICAL_GAP_MULTIPLIER = 3.0` and `MAX_HORIZONTAL_OFFSET_MULTIPLIER = 3.0`).
- Implemented spatial bilingual pairing (`_pair_bilingual_fields`) combining matching Devanagari and Latin spans of the same field type into single `NormalisedField` records with plural `span_refs`.
- Added `bck/app/modules/extraction/evidence.py` defining `ExtractionResult`.
- Created comprehensive test suite `bck/tests/modules/extraction/test_bilingual_declarations.py` covering all 14 required test scenarios.
- Executed all 5 empirical mutation checks (all 5 RED on mutation, GREEN when restored).
- All 274 pytest unit tests passed, `ruff format --check .` clean, `ruff check .` clean, `lint-imports` clean.

**Decided**
- Primary bilingual pairing signal relies on 2D bounding-box spatial adjacency and script dissimilarity rather than broad semantic translation or string equality.
- Rule citation verified directly against corpus PDF: `rules-corpus/LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf`, Page 9, Rule 9(4).

**Verification**
- 274/274 extraction unit tests passed in 0.45s.
- `ruff format --check .`, `ruff check .`, and `lint-imports` all passed with 0 errors.
- `git diff --check` cleanly passed.
- No git commit or push performed per user rules.
