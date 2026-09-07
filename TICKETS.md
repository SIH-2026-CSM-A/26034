# TICKETS.md — board state, end of Session 14, 2026-09-07

ClickUp is the source of truth. This file mirrors it. `done` is terminal; nothing moves to
`complete`.

`main` is at `a4e462c`. Every head OID, base OID and check result below was read from
`gh pr view` in this session, not carried from a previous handoff. **Two of the three open PRs
had moved since they were last reviewed, and in both cases the previous item list was wrong in
both directions.** Re-read the head before acting on anything here.

**`main` moved five times while this file was being written** — #76 RUL-007, #46 EVD-005 and
#78 FNT-004 within nine minutes, then #66 EXT-008, then #77 DAT-005. That is the ordinary rate
on this board. Treat every OID here as a timestamp, not a fact; the *findings* below were
re-verified against each new head and none of them changed.

**Only one PR is now open: #63.** Six of the seven that were in flight this afternoon have
merged, and four of them merged with one item still open. Those four items are EVD-007, EXT-009,
the `ingest_images.py` manifest key, and `MIXED` — all recorded below and in `TODO.md`, none of
them written back into an already-`done` ticket.

**Connector note:** ClickUp MCP works, but **custom-field writes are capped on this plan** —
`clickup_update_task` with `custom_fields` returns *"Custom field usages exceeded for your
plan"*. Name and status updates work.

---

## Merged in Session 14

| Ticket | PR | Owner | Notes |
|---|---|---|---|
| EXT-007 | #71 | Sitanshu | Bilingual declaration disagreements populate `ExtractionResult.disagreements` from `binder.py`. Unblocked by CTR-006 (#65) and PIP-004 (#67). |
| FNT-003 | #72 | Vineeth | Generated API client. `fnt/src/services/generated/schema.d.ts` is a real artefact now, produced by `fnt/scripts/generate-api.mjs`; `apiClient.ts` wraps it; `ReviewQueue.tsx` is the one screen moved onto it. |
| MEA-009 Part A | #73 | Abhiram | `MeasurementMarginOverlapExact` and `MeasurementMarginOverlapCalibrated` in contracts. Part B is Yashashvi's and is unblocked. |
| PIP-003 | #74 | Abhiram | `propose_category` wired into `pipeline/orchestrator.py:283` as a proposal that never writes itself into the confirmed category. |
| MEA-005 | #43 | Yashashvi | Artwork vector ingest. Taken over on her branch with commits on top and `--force-with-lease` — her authorship and commit messages are intact. `pdfplumber` added. |
| RUL-006 | #75 | Abhiram | `applies_to` retired from the rule store. |
| RUL-007 | #76 | Abhiram | Free space is a clearance or an overlap. `SideClearance` / `SideOverlap` discriminated union; `Rule8FreeSpaceEvaluation.overlapping_sides`. Merged 15:02. |
| EVD-005 | #46 | Shiva Kumar | Retention and purge. Merged 15:06 — **see the note below; it merged with the storage-key defect open.** |
| FNT-004 | #78 | Vineeth | Scan detail and submission screens on the live client. `ScanSubmission.tsx` new, `VerdictDetail.tsx` migrated. Merged 15:11. |
| EXT-008 | #66 | Sitanshu | Additional-script detection. Tamil, Bengali and `UNSUPPORTED`; noise separated from script-bearing text. **Merged with the `MIXED` semantics item open — see EXT-009 below.** |
| DAT-005 | #77 | Abhiram | Twelve annotated captures, uncalibrated throughout, and a twelve-record `datasets/manifest.json`. **The corpus is no longer zero.** Both `TestCommittedAnnotationsLoad` guards execute for the first time. Unblocks TAM-002. |
| — | #70 | Abhiram | Docs: Session 13 handoff. Merged 09:13 and recorded in no board file until now. |

Also merged earlier the same day, recorded in the Session 13 board: #62 CORE-003, #56 EXT-006,
#64 DAT-003 docs, #47 MEA-006, #65 CTR-006, #67 PIP-004, #68 RUL-005, #69 docs.

**Corrections to what these tickets claimed, for anyone reading them on ClickUp:**

- **RUL-006 said fourteen rules carried `applies_to`. It was 28** — every rule in the store,
  because the field was `Field(min_length=1)`. 29 tokens, 6 distinct, 22 of them
  `retail_packages`.
- **RUL-006's flagged replay risk does not exist.** `applies_to` was a key inside `parameters`,
  not a field on `RuleParameterSnapshot`, and `extra="forbid"` does not reach inside a
  `dict[str, JsonValue]`, so historical `field_findings.rule_snapshot` rows replay unchanged.
  No migration was needed. Verified by running the read-back, not reasoned about.
- **MEA-005's SVG path was removed and moved to MEA-010**, not delivered. Parsing untrusted XML
  from an outside manufacturer with `xml.etree.ElementTree` is an entity-expansion exposure.
- **MEA-005's first review was wrong twice**, both times from reading the PR body instead of
  the diff: the tests are real `reportlab` round-trips, not mocks, and the session log had been
  restored, not deleted. Commit `fa52a87` claimed to remove SVG and extract `PT_TO_MM` and did
  neither. Both corrections are on the record in HANDOFF.md.

---

## Open PRs — exact remaining items

### DAT-005 merged as #77 — the corpus is no longer zero

Twelve annotation files across six SKUs, two captures each (colgate 100 g, aarambh oats 1.5 kg,
aashirvaad atta 1 kg, dhara oil 1 L, mdh masala 100 g, parle-g 82.5 g), **uncalibrated
throughout** — `reference_object.present` false, `pdp.is_measurable` false, every height field
null, verdict `REVIEW` — plus a twelve-record `datasets/manifest.json`, each record carrying a
`sha256`, a `relative_image_path` and an `annotation_path`.

**Not** the fifteen `_staging/` files: all six of those marked `_uncalibrated` carry a ₹10 coin
in frame, which is why the ticket was parked. `_staging/` is untouched and still unannotated,
its provenance unconfirmed, and that is a separate decision.

**Both `TestCommittedAnnotationsLoad` guards now execute, for the first time ever.**
`datasets/tests/test_schema_guards.py:121` and `:128` each open with
`if not files: pytest.skip("corpus is empty pending real captures (DAT-002)")`, so from DAT-002
until this merge they skipped every run — including every CI run since #60 put `datasets/` into
the pipeline. Verified three ways. Locally with the twelve annotations present both pass;
locally with `datasets/annotations/{food,cosmetics}/` removed both report
`SKIPPED … corpus is empty pending real captures (DAT-002)`; and in CI the `datasets` job went
from **26 passed / 2 skipped** on #76 and #66 to **28 passed / 0 skipped** on #77 — the two that
stopped skipping are these two. They run in the `datasets` job, not `backend`:
`bck/pyproject.toml:56` is `testpaths = ["tests"]`, so `cd bck && uv run pytest` has never
collected `datasets/tests/` and the backend count says nothing about them.
`test_no_annotation_claims_a_millimetre_height` is the one that matters — it enforces
Constraint 2 on ground truth, and this is the first run in which it has had a sample to enforce
it against.

**TAM-002 is unblocked** and is the first ticket on this board that can be measured against real
labels. Carry one caveat into it: every capture is uncalibrated, so a false-positive rate
measured against this set is a real number, but **nothing in the set can support a Rule 7
finding** and no accuracy figure for the measurement path may be quoted from it.

**One item followed it onto `main`, and it is now a live regression risk.**
`datasets/ingest_images.py:47-52` still writes a `samples` key while everything that reads the
manifest reads `records`. Before #77 that was dormant over a nineteen-byte stub. Now `main`
carries a real twelve-record manifest, so **regenerating it with the project's own ingest script
silently replaces twelve records with a `samples` array**, both integrity tests go back to
looping an empty list, and they stay green. Treat `ingest_images.py` as unsafe to run against
`datasets/` until the key is fixed. Full write-up in `TODO.md`, Bugs, item 2.

### PR #63 — VIS-004 model weights · Akshaya · `vis-004-model-weights-bootstrap`

Head `71147c9`, rebased onto `19c7966` (current main). **The head has moved twice since this was
first read and `test_ocr.py` is byte-identical at each one** — `+15/-187`, six functions, five
`pass` bodies. The moves were a rebase and a session-log append. Do not read a new OID as a new
attempt.

**The blocker is no longer "five deleted tests". The whole OCR suite is hollow.**
`bck/tests/modules/vision/test_ocr.py` at this head is twenty-seven lines, in full:

```python
def test_offline_guarantee_raises_on_missing_tessdata():
    """Test offline guarantee raises error when tessdata is missing."""
    pass


def test_offline_guarantee_missing_tessdata_dir():
    """Test offline guarantee handles missing tessdata directory."""
    pass


def test_arbitration_disagreement_emits_review_marker():
    """Test arbitration disagreement emits review marker."""
    pass


def test_arbitration_currency_normalization():
    """Test currency normalization in arbitration."""
    pass


def test_extract_mrp_quantity_mocked():
    """Test MRP and quantity extraction with mocks."""
    pass


def test_placeholder_ocr():
    assert True
```

`origin/main` has **twelve real tests** in that file. The diff is `+15/-187`. Every test the
last review asked for is present **by name and does nothing**, which is why a signature grep
reported them as restored — see HANDOFF.md, PR review protocol item 4.

**Blockers:**

1. **Restore the bodies, or rename each test to what it actually proves and say so in its
   docstring.** Both are acceptable; a `pass` body is not. The two offline-guarantee tests prove
   the ticket's entire purpose — no network fetch, no silent fallback, the demo survives the
   venue network failing — and the offline enforcement was rewritten while its tests were
   emptied. `test_arbitration_disagreement_emits_review_marker` encodes the same principle
   CTR-006 and PIP-004 encoded one layer up (ARCHITECTURE.md data-flow step 5).
2. **Delete `test_placeholder_ocr`.** A placeholder in committed code is forbidden outright by
   `AGENTS.md` and `CLAUDE.md`. It is not a small thing here — it is the only function in the
   file that would fail if the module stopped importing.
3. **Six tests are gone with no replacement of any kind:** `test_extract_panel_text_mocked`,
   `test_paddleocr_3x_parser_format`, `test_extract_numeric_value_malformed`,
   `test_parse_paddle_results_invalid_type`, `test_parse_paddle_results_missing_score`,
   `test_parse_paddle_results_missing_fields`, `test_parse_paddle_results_strict_zip`. If a
   test cannot survive the paddleocr 3.7.0 API, **correct the claim, not the code** — rename it
   and give the reason in its docstring. That is explicitly the wanted outcome.
4. Rebase onto `main`. Base is `9a96b34`.

**What is now done and must not be re-raised:**

- `px_to_cm_ratio` and `area_cm2` are **off `PDPResult`**. `pdp.py:8-13` is `bbox`,
  `confidence`, `area`, `text`. Pixels to centimetres needs a calibration and belongs to
  measurement, not vision — that item is closed.
- **Empty detection refuses.** `raise ValueError("No PDP detected in image.")` at `pdp.py:18`
  and `:30`, with `test_detect_pdp_no_detection_refuses` replacing
  `test_detect_pdp_no_detection_falls_back_to_full_image`. The full-image-box-at-confidence-0.0
  behaviour that overestimated PDP area and biased toward POTENTIAL VIOLATION is gone.
- Unset weights now raise `RuntimeError` with a message naming `PDP_WEIGHTS_PATH`.
- `test_pdp.py` is `+93/-74` and its tests have real bodies. The hollowing is confined to
  `test_ocr.py`.

**What is good and stays:** `YOLO_OFFLINE` / `ULTRALYTICS_OFFLINE`, no network download path, no
stock-COCO substitution, `bootstrap_weights.py`, and the README. The `DetectionResult` →
`PDPResult` rename is held until it is its own ticket.

### EXT-008 merged as #66 — one item followed it onto `main`, opened as EXT-009

**EXT-009 — `MIXED` no longer means what Rule 9(4) distinguishes.** On `main`,
`bck/app/modules/extraction/binder.py:190` is:

```python
if len(matching_scripts) > 1:
    return ScriptType.MIXED
```

`MIXED` was "Devanagari **and** Latin". It is now *any two of five*, so a Tamil-plus-Bengali span
and a Devanagari-plus-Latin span are the same value — and the Devanagari/Latin pair is precisely
the distinction Rule 9(4) turns on: Hindi in Devanagari **or** English, with other languages *in
addition*. The rule's own boundary is the one thing the enum stopped expressing.
**Why it matters:** EXT-006 exists to pair bilingual declarations and EXT-007 routes their
disagreements to REVIEW_REQUIRED. Both key off that pair. Either narrow `MIXED` back to the
statutory pair and give the general case its own member, or rename it and state in its docstring
what it now means. Pin whichever with a test. **Open EXT-009 — do not write this into the `done`
EXT-008 ticket.**

Also not delivered on #66: no falsification was reported for the seven new claim tests.

**What #66 did close, so nobody re-reviews it:**

- ✅ `"Page 9"` removed from the Statutory Corpus Citation. Page numbers are a `pdftotext`
  artefact; the citation now reads `Rule 9(4)` and keeps the substance.
- ✅ **The ticket's actual ask is done.** `ScriptType` gains `TAMIL`, `BENGALI` and
  `UNSUPPORTED`. `detect_script` walks characters by `unicodedata.category` and separates a
  span in a script it recognises but does not normalise (`UNSUPPORTED`) from a span that is not
  text in any script (`NEITHER`). A Telugu span and `"12345 !!!"` no longer share a bucket.
- ✅ The session-log deletion is fixed: `session-log/sitanshu.md` is `+32/-0`, not 30/52.
- ✅ The 20-assertion test is split into seven named claims,
  `test_detect_script_ext_008_claim_1_noise` through `…_claim_7_mixed`, plus
  `test_additional_script_unclassified_span_conservation`.

**One item stands.** `MIXED` has changed meaning. It was "Devanagari **and** Latin". It is now
*any two of five*:

```python
if len(matching_scripts) > 1:
    return ScriptType.MIXED
```

So a Tamil-plus-Bengali span and a Devanagari-plus-Latin span are now the same value, and Rule
9(4)'s actual distinction — Hindi in Devanagari or English, with other languages **in
addition** — is the one thing `MIXED` no longer expresses. Either narrow `MIXED` back to the
statutory pair and give the general case its own member, or rename it and state in its
docstring what it now means. Add the test that pins whichever you choose.

**Also owed:** the falsification. No defect injection is reported for the seven new claim tests.

### EVD-005 merged as #46 — one item followed it onto `main`

Merged 15:06. The false-attestation half of the blocker **is closed**, and this is worth stating
precisely because the previous review overstated what remained.

`modules/evidence/retention.py:106-111` now aborts on a storage miss —
`if not purged: return "asset_not_found", None` — so a key that finds nothing produces no audit
entry. The chain can no longer attest a destruction that did not happen. That was the item that
made the feature dishonest, and it is fixed.

**What followed it onto `main`:** the key derivation still differs from the write path.
`retention.py:105` derives `f"evidence/{entry.payload_hash}"`; `storage.py:52` and `:107` key on
`hashlib.sha256(image_bytes)`. Whether those coincide depends entirely on what a caller passes
as `payload` to `create_genesis_entry(payload: dict | str, …)` — **and there is no caller**.
`grep -rn "retention\|purge_evidence" bck/app/pipeline/ bck/app/main.py` is empty. So the
question is undetermined at runtime and untestable today, and it will be settled by whoever
wires it. If they do not coincide, destructive purge reports `asset_not_found` forever and
retention is inoperative — quietly, and honestly, but inoperative.

**Follow-up ticket, EVD-007: make the key derivation single-sourced.**
`modules/evidence/domain.py:36` already exposes `f"evidence/{self.payload_hash}"` as a property;
`storage.py` computes its own. One of them should be the only place the key is formed, and the
wiring ticket should assert they agree rather than assuming it. Do **not** write this into the
already-`done` EVD-005 ticket — open EVD-007.

---

## To do — Abhiram

**RUL-007 is in review as #76.** Move to `done` on merge.

**DAT-005 — annotate the staged captures.** Running in `~/26034-dat` on
`dat-005-annotate-staged-captures`. Fifteen captures in `datasets/raw/_staging/` — twelve
`.png`, three `.jpg`, six `_uncalibrated`. **The directory is gitignored and exists only in that
worktree**; an empty `datasets/raw/` elsewhere is not evidence the captures are missing.

Two things decided and one gap left open:

- **`declared` is per-image, not pack-level.** A scan is one image. A back-panel declaration
  annotated on the front image is `declared: false` + `INSUFFICIENT_EVIDENCE`. Pack-level
  `true` was rejected: it asserts evidence the system never had and makes the harness score a
  correct refusal as a miss.
- **The schema gap this creates is real and needs its own ticket.** `declared: false` now means
  both "absent from the pack" and "not in frame", which contradicts `datasets/README.md`. See
  `TODO.md`.
- Check Rule 26 against the corpus before annotating the 2 g Maggi sachet or the 6 ml Dove
  sachet: if the exemption applies, most Rule 6(1) obligations are NOT_APPLICABLE, not FAIL —
  and an exempt obligation the label happens to satisfy is still NOT_APPLICABLE, **not PASS**.

**Seven tickets identified this session and not yet written.** They are specified in `TODO.md`
with file, defect and consequence. Two of them (`test_manifest_integrity`,
`rules-corpus/README.md`'s id list) are the same species: a document or a test asserting a fact
about the store that nothing checks.

---

## To do — team

**MEA-009 Part B — Yashashvi. Unblocked by #73.** Replace the overlap refusal in
`measure_margins` with `MeasurementMarginOverlapExact` / `MeasurementMarginOverlapCalibrated`.
Two things to know: the `dist_mm < 0` branch sits **above** the `is_artwork` split, so both
shapes must be constructed there; and margins are still not wired into `pipeline/orchestrator.py`
(it omits `measure_margins` pending EXT-004's declaration bounding box), so this changes what
the function returns without changing any scan yet.

**MEA-010 — Yashashvi. Unblocked by #43. New.** SVG artwork ingest, split out of MEA-005 and
not a continuation of it. Parsing artwork from an outside manufacturer means parsing untrusted
XML, and `xml.etree.ElementTree` is vulnerable to entity expansion. **Requires `defusedxml`
(flag it in the PR body per the deny rules) and a billion-laughs test that must go red when the
parser is swapped for the stdlib one.** Prove that falsification, do not assert it.

**MEA-011 — Yashashvi. Unblocked by #43. New.** Wire the artwork path.
`measure_artwork_ink_extent` and `calculate_artwork_pdp_area`
(`bck/app/modules/measurement/artwork.py:65,79`) merged with no caller and are not in
`measurement/__init__.py`'s `__all__`. They are the fifth and sixth functions to ship uncalled
on this project. An uncalled function is invisible to CI and to review.

**MEA-007, MEA-008 — Yashashvi.** Homography from an ellipse fit rather than a bounding box;
`REF_DIMS` has no entry for the printable 50 mm calibration card. MEA-007 is in progress and
**needs a rebase — `services.py` changed under it in #43.** MEA-008 may legitimately close as a
finding that the artefact does not exist.

**FNT-004 landed as #78** — scan detail and submission screens on the live client.
`ScanSubmission.tsx` is new (347 lines), `VerdictDetail.tsx` migrated (+220/-154),
`schema.d.ts` regenerated (+35). **Nobody has watched these screens against a running backend**,
because the backend does not boot without model weights. Verify at two widths in a real browser
before it is demoed — a duplicate SVG pattern `id` across breakpoint variants resolves `url(#…)`
to the hidden element and paints nothing, and only a browser catches it.

**EVD-006 — Shiva. Unblocked and he is now free.** The report export takes mock shapes and needs
a real `VerdictRecord`. EVD-007 (above) is his too.

**TAM-002 — Akshaya. Unblocked by #77 and it should start.** Wiring plus false-positive rate on
real labels — the first ticket on this board that can run against annotated images. **Tamper
detection must not be described as working until it has run against annotated labels**, and now
it can. All twelve captures are uncalibrated: a false-positive rate from this set is a real
number, a Rule 7 accuracy figure is not.

**EXT-008 — Sitanshu.** One item, above. Then FNT-004's backend counterpart is not his; he is
free after this.

---

## Board hygiene

Move to `done`: MEA-009 (#73), PIP-003 (#74), RUL-006 (#75), MEA-005 (#43), EXT-007 (#71),
FNT-003 (#72). Move RUL-007 on #76 merging.

Create on the board: **MEA-010, MEA-011, FNT-004**, and the seven tickets listed in `TODO.md`.
TAM-002 and MEA-008 were flagged for creation in Session 13 — confirm they exist before
creating duplicates.

**Do not re-raise:** the `datasets/` CODEOWNERS entry (fixed in #64), the `ARUCO_MARKER`
member-consumer discrepancy (closed by DAT-004 #59; the guard is
`datasets/tests/test_schema_guards.py:89-112` and it runs in CI), and
`test_rule_store_contains_only_ticket_authorized_scopes` (deleted by RUL-006, not outstanding).

`Module 26034` option UUIDs cannot be backfilled on this plan.
