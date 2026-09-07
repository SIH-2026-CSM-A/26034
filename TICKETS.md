# TICKETS.md — board state, end of Session 13, 2026-09-07

ClickUp is the source of truth. This file mirrors it. `done` is terminal; nothing moves to
`complete`.

**Connector note:** ClickUp MCP works again, but **custom-field writes are capped on this plan**
— `clickup_update_task` with `custom_fields` returns *"Custom field usages exceeded for your
plan"*. Name and status updates work. Consequence below on FNT-003.

---

## Merged in Session 13

| Ticket | PR | Owner | Notes |
|---|---|---|---|
| CORE-003 | #62 | Abhiram | `asset_type` on the evidence entry, its column, its migration. Created retroactively — it shipped with no board ticket. |
| EXT-006 | #56 | Sitanshu | Bilingual Devanagari/Latin pairing. Both blockers closed properly. |
| DAT-003 | #64 | Abhiram | Docs only after rescope: unsafe purge form, AGENTS heading, ownership reassignment. |
| MEA-006 | #47 | Yashashvi | Zero margin permitted; half-plane slicing fix beyond ticket scope. |
| CTR-006 | #65 | Abhiram | `CompetingReadings` + `DisagreementReason` in contracts. |
| PIP-004 | #67 | Abhiram | Contested declaration routes to REVIEW_REQUIRED. |
| RUL-005 | #68 | Abhiram | Rule 3 Chapter II scope limb. |
| — | #69 | Abhiram | Docs: Session 13 log, Rule 25 export-limb correction. |

---

## Open PRs — exact remaining items

### PR #63 — VIS-004 model weights · Akshaya · `vis-004-model-weights-bootstrap`

Head `7b8ca16`, three checks green. **Green is not evidence here** — the suite has had guards
removed. Twelve OCR tests deleted across two pushes; five restored on the second.

**Blockers — restore or justify each individually in the PR body:**

1. `test_offline_guarantee_raises_on_missing_tessdata` and
   `test_offline_guarantee_missing_tessdata_dir` — these prove the ticket's entire purpose: no
   network fetch, no silent fallback, the demo survives the venue network failing. The offline
   enforcement was rewritten and its tests deleted.
2. `test_arbitration_disagreement_emits_review_marker` — providers that disagree on a numeric
   field surface both readings rather than arbitrating (ARCHITECTURE.md data-flow step 5). The
   same principle CTR-006 and PIP-004 encoded one layer up this session.
3. `test_arbitration_currency_normalization`, `test_extract_mrp_quantity_mocked`,
   `test_extract_panel_text_mocked` — the constrained re-OCR on MRP and net quantity.

If a test cannot survive the 3.7.0 API, rename it to state what it actually proves and give the
reason in its docstring. **Correct the claim, not the code.**

**Also still owed from the first review:** `px_to_cm_ratio` and `area_cm2` come off `PDPResult`
entirely — pixels to centimetres needs a calibration and belongs to measurement, not vision. The
empty-detection branch must refuse rather than return a full-image box with `confidence 0.0` and
an area attached, which overestimates PDP area and biases toward POTENTIAL VIOLATION. The
`DetectionResult` → `PDPResult` rename is held until it is its own ticket.

**What is good and stays:** `YOLO_OFFLINE` / `ULTRALYTICS_OFFLINE`, no network download path, no
stock-COCO substitution, `bootstrap_weights.py`, and the README.

### PR #66 — EXT-008 additional-script detection · Sitanshu · `ext-008-additional-script-detection`

Head `a415ccf`, three checks green, three files, one module. Shape is clean.

1. Remove `"Page 9"` from the Statutory Corpus Citation. Page numbers are a `pdftotext`
   artefact, not a stable reference — cite the gazette file as every rule in the store does.
   Keep the substance: Rule 9(4) permits other languages in addition.
2. **The ticket's actual ask is not done.** `NEITHER` still means both "a script we recognise
   but do not normalise" and "not text in any script". Adding Tamil and Bengali regexes moved
   the defect one script over — a Telugu span and `"12345 !!!"` still share a bucket. Separate
   the two conditions and add the test that pins it.

### PR #46 — EVD-005 retention and purge · Shiva Kumar · `evd-005-retention-purge`

Head `7215b2b`. **Red on `Format check`.** That step runs before Lint, Import boundaries and
Tests, so **nothing in this PR has been verified by CI.** Single quotes where the house style is
double, and a multi-line `with` that ruff wants parenthesised, in `test_retention_purge.py`.

`cd bck && uv run ruff format . && uv run ruff check . --fix`

Then rebase onto CORE-003: `asset_type` is required with no default and inside
`compute_entry_hash`. `create_genesis_entry` and `append_entry` must take it as a **required
parameter** — a constructor default reintroduces at the call site exactly what the no-default
column prevents. Member set is three, not five. `EvidenceAssetType` now lives in
`app.contracts`; delete the local definition and import it.

**Good news:** `config.py`, `repository.py` and `test_persistence.py` are no longer in the diff.
The ownership escalation is cleared — seven files, all his module.

**Six review items stand.** The `storage_key` false attestation is the blocker: it keys on
`payload_hash` while the CAS client keys on image bytes, so `purge_evidence` returns `True` and
writes an immutable chain entry attesting a destruction that never happened. CORE-003 did not
touch it.

### PR #43 — MEA-005 artwork vector ingest · Yashashvi · `mea-005-artwork-vector-ingest`

**Unblocked — `pdfplumber` approved.** Pure Python over `pdfminer.six`, no system libraries.
Scoped to PDF; SVG is a separate ticket. Flag the dependency in the PR body per the deny rules.
Needs a rebase — main moved eight times this session.

---

## To do — Abhiram

**MEA-009 — an overlapping margin is a finding, not a refusal.** Part A (contracts) is his and
blocks Part B (Yashashvi). A negative margin means ink intruding into the Rule 8(1) free space —
the violation the measurement exists to detect — and returning `MeasurementRefusal` makes a
detected violation look like a failed measurement.

**PIP-003 — wire `propose_category` into the orchestrator** as a proposal that never writes
itself into the confirmed category.

**DAT-005 — annotate the staged captures. Parked, not cancelled.** All six `*_uncalibrated`
files have ₹10 coins in frame, so the uncalibrated half of the set does not exist and the
refusal path has no sample. Cropping destroyed the declaration block; inpainting left visible
starbursts. **Needs six real photographs — one per SKU, no reference object in frame.** Check
Rule 26 against the corpus before annotating the 2 g Maggi sachet or the 6 ml Dove sachet: if
the exemption applies, most Rule 6(1) obligations are NOT_APPLICABLE, not FAIL — and an exempt
obligation the label happens to satisfy is still NOT_APPLICABLE, not PASS.

---

## To do — team

**EXT-007 — Sitanshu. Unblocked.** Both CTR-006 and PIP-004 are on main. Finish or park #66
first; never two branches in one module. **At `binder.py:604` the value check runs before
`_are_spans_spatially_adjacent` at 607** — move adjacency above value, or the ticket records
disagreements between unrelated declarations. CTR-006's validator refuses a `field_type` in both
`fields` and `disagreements`, so both readings must leave `fields` entirely.

**FNT-003 — Vineeth.** Generate the API client from the OpenAPI schema and move exactly one
screen onto it. **The ticket's branch field is wrong** — it reads `fnt-001-generated-api-client`
because the custom-field write was rejected by the plan cap. **The branch is
`fnt-003-generated-api-client`.** Renamed from FNT-001 because that id and FNT-002 were both
already taken by shipped work.

**MEA-007, MEA-008 — Yashashvi.** Homography from an ellipse fit rather than a bounding box;
`REF_DIMS` has no entry for the printable 50 mm calibration card. MEA-008 may legitimately close
as a finding that the artefact does not exist.

**TAM-002 — Akshaya. Blocked on DAT-005.** Wiring plus false-positive rate on real labels.
Tamper detection must not be described as working until it has run against annotated labels.

---

## Board hygiene

Move to `done` when their PRs merge: RUL-005 (#68 merged — do this), RUL-006 (in review).

**RUL-006 is out of "To do — Abhiram" and in review.** `applies_to` is removed from the rule
store. Two corrections to what the ticket said, for anyone reading it on ClickUp: it claimed
**fourteen** rules carried the field — it was **28**, every rule in the store, because
`applies_to` was `Field(min_length=1)` (29 tokens, 6 distinct, 22 of them `retail_packages`).
And the replay risk the ticket flagged does not exist: `applies_to` was a key inside
`parameters`, not a field on `RuleParameterSnapshot`, and `extra="forbid"` does not reach
inside a `dict[str, JsonValue]`, so historical `field_findings.rule_snapshot` rows replay
unchanged. No migration was needed.

Not yet on the board: nothing outstanding. CORE-003 was created retroactively; CTR-005 already
existed; the duplicate RUL-005 was deleted.

`Module 26034` option UUIDs cannot be backfilled on this plan.
