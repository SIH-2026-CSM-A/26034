# Session log — Jashwanth

### 2026-09-05 — RUL-001 rule store — Codex

**Branch**

- `feature/26034-RUL-001-rule-store`

**Files changed**

- `bck/app/modules/rules/__init__.py`
- `bck/app/modules/rules/models.py`
- `bck/app/modules/rules/loader.py`
- `bck/app/modules/rules/evaluator.py`
- `bck/app/modules/rules/data/rules.yaml`
- `bck/tests/modules/rules/test_loader.py`
- `bck/tests/modules/rules/test_rule7.py`
- `bck/tests/modules/rules/test_evaluation.py`
- `session-log/jashwanth.md`

**Implementation summary**

- Added a strict YAML-backed legal rule store with safe parsing, atomic validation,
  duplicate-ID rejection, and corpus-file reference validation.
- Encoded the ticket-scoped Rule 6(1), Rule 7, medical-device override, and dated
  G.S.R. 128(E)/312(E) provisions from the committed corpus.
- Added deterministic Table-I lookup, Rule 7(3) ratio handling, Rule 7(4) PDP formulas,
  Rule 7(5) carve-out behavior, effective-date selection, medical-device REVIEW routing,
  and a central UNVERIFIED-to-REVIEW gate.
- Kept rounding increment and tolerance as separate schema and evaluation concepts.
  RUL-001 contains no F18 or Rule 6(11) evaluation.

**Temporary contract**

RuleDefinition is temporarily defined inside app.modules.rules pending CTR-002. Once CTR-002 lands, replace the local definition with the canonical app.contracts import; no rule data or evaluation behavior should change.

**Checks run from `bck/`**

- `uv run pytest tests/modules/rules -q` — 51 passed.
- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — 30 files already formatted.
- `uv run lint-imports` — 3 contracts kept, 0 broken.
- `uv run pytest` — 55 passed.

Ticket status was not changed by Codex. No commit, push, or pull request was created.

### 2026-09-06 — RUL-001 legal provenance audit & verification — Antigravity

**Branch**

- `feature/26034-RUL-001-rule-store`

**Files changed**

- `bck/app/modules/rules/data/rules.yaml`
- `bck/tests/modules/rules/test_loader.py`
- `session-log/jashwanth.md`

**Audit & corrections summary**

- Audited all 17 legal rule definitions against cited committed PDFs in `rules-corpus/`.
- Corrected Rule 6(1)(da) (`R6-1-DA`) quotation marks from double curly quotes to source-visible single curly quotes (`‘best before or use by the date, month and year’`) matching G.S.R. 629(E) p. 10.
- Corrected Rule 7(4) (`R7-4-PDP-AREA`) text to restore the source-visible space before the comma (`package , 40 per cent.`) matching G.S.R. 629(E) p. 12.
- Verified Rule 7(3) (`R7-3-WIDTH-RATIO`) numeral double curly quotes (`“1”`) and letter exceptions (`(i), (I) and (l)`), accounting for the missing PDF font glyph for `l`.
- Verified Rule 7 Table-I (`R7-2-TABLE-I`) verbatim text and 5 area bands with boundary inclusion in lower adjoining bands.
- Verified medical-device override (`R7-MEDICAL-DEVICE-OVERRIDE`) multi-excerpt provenance from G.S.R. 778(E) (Rule 2(h), Rule 7(2), Rule 7(3), Rule 33(2)), effective 2025-10-24, and REVIEW routing.
- Verified G.S.R. 128(E) / G.S.R. 312(E) e-commerce country-of-origin filter rules and non-overlapping effective dates (128(E) effective 2026-07-01 through 2027-06-30; 312(E) effective 2027-07-01 onward).
- Added explicit `EXPECTED_RULE_GAZETTE_MAPPING` and `test_explicit_rule_id_gazette_provenance_mapping` in `test_loader.py` without runtime PDF parsing.

**Checks run from `bck/`**

- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — 30 files already formatted.
- `uv run lint-imports` — 3 contracts kept, 0 broken.
- `uv run pytest` — 56 passed.
- `git diff --check` — passed.

No commit, push, or pull request was created.

### 2026-09-08 — RVW-001 review portal integration correction — Codex

**Agent**

- Codex

**Done**

- Added `app.modules.reviews` to the import-linter independence contract.
- Updated the pinned module-count boundary test from seven to eight modules.
- Confirmed `product_reviews` uses structural anonymity: it has no reviewer identity column,
  account/contact/device/IP/fingerprint field, or reviewer foreign key. `anonymous_token`
  remains a fresh per-row token and is not client supplied, returned, reused, or used for
  deduplication.
- Confirmed `REVIEW_PUBLICATION_THRESHOLD = 3` is a named reviews-module constant documented
  as an uncalibrated prototype prior: one submission provides no corroboration, two remain a
  pair, and three is the smallest repeated-matching cohort selected for the prototype. It is
  neither legally required nor statistically validated.
- Updated PR #113 with the threshold rationale and structural-anonymity statement.

**Verification**

- RVW-001 focused PostgreSQL tests previously passed: 37 passed, zero skips.
- The shared import-boundary failure was the expected missing reviews registration and is now
  addressed in this ticket-authorized change.

**Handoff**

- Abhiram still owns mounting `reviews_router` in application composition.

