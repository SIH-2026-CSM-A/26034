# TICKETS.md — board state, end of Session 6, 2026-09-07

ClickUp is the source of truth. This file mirrors it. The connector was rate-limited for all
of Session 6, so several moves below were made by hand and some tickets were never created —
both are marked.

`done` is the terminal status. Nothing moves to `complete`.

---

## Merged in Session 6

| Ticket | PR | Owner | Notes |
|---|---|---|---|
| CI-004 | #60 | Abhiram | `datasets` CI job + repo-hygiene step. Not yet a required check. |
| TAM-001 | #55 | Akshaya | Tamper detection. Uncalibrated thresholds, no caller. TAM-002 follows. |
| CTR-005 | #58 | Abhiram | Margin measurement types as siblings. **Ticket never created on the board** — create it retroactively as `done`. |
| DAT-004 | #59 | Abhiram | Schema adopts measurement's reference-object vocabulary. |

---

## Open PRs — exact remaining items

### PR #46 — EVD-005 retention and purge · Shiva Kumar · `evd-005-retention-purge`

Blocked on CORE-003. Head `e510224` at last review. **CI red at `Format check`** — that is
`ruff format --check .`, and Lint passed while Import boundaries and Tests were skipped, so
nothing about the code has been verified by CI yet.

Owed, none confirmed:
1. **The false attestation.** `storage_key = f"evidence/{entry.payload_hash}"` keys on the
   payload hash while the CAS client keys on image bytes. When they differ, `purge_image`
   takes its not-found branch, `purge_evidence` returns `True`, and `append_purge_entry`
   writes an immutable chain entry attesting a destruction that never happened. Derive the key
   from what `store_image` returned; write no audit record on a no-op.
2. `is_purged` reads `payload.get("type")` but persisted payloads are JSON strings, so it
   returns `False` for everything on the database path — purge detection is memory-only.
3. **The legal hold is inverted.** HOLD on any `POTENTIAL_VIOLATION` with no review row; HOLD
   on `CONFIRM` or `OVERRIDE`; RELEASE only on `REJECT`. The docstring describes the opposite
   of what the code does — fix both.
4. `S3ContentAddressedStorageClient.purge_image` catches bare `Exception` and returns, so a
   permissions failure reads as "already purged".
5. `purge_evidence(e0, e0, ...)` passes an entry as its own predecessor in several tests.
6. `test_chain_verification_tampered_purge` proves nothing about purging — remove the purge
   entirely and it still passes, because the tampering alone causes `payload_hash_mismatch`.

Also: the PR carries `bck/app/core/config.py`, `bck/app/pipeline/repository.py` and
`bck/tests/core/test_persistence.py`, all Abhiram's. He must say what each edit is for; they
get split or folded into CORE-003.

When CORE-003 lands, his hash-chain test expectations move because `asset_type` joins
`compute_entry_hash`. Expected, not a regression.

### PR #47 — MEA-006 permit zero margin results · Yashashvi · `mea-006-zero-margin`

**Unblocked by #58.** Head `1518ebe`, CI red on backend. The design call in it was right and
is what shipped in CTR-005.

1. Rebase and drop the contracts half:
   `git checkout origin/main -- bck/app/contracts/__init__.py bck/app/contracts/measurement.py`
   The PR then touches only `services.py`, its tests and her session log, and the merge-gate
   escalation disappears.
2. `MeasurementMarginCalibrated.confidence_interval` is `gt=0`. `measure_margins` computes
   `confidence = max(0, dist_px) * conf_interval`, exactly `0.0` for a zero margin, so the
   field path now raises while the artwork path succeeds. Floor the interval at the mm
   equivalent of one pixel at the measured scale. Module-level constant, documented as an
   uncalibrated prior. Not a hardcoded epsilon.
3. Add the calibrated twin of `test_zero_margin_is_valid`: `is_artwork=False`, a reference
   scale, zero margin, asserting a non-zero interval comes back.
4. `max(0, dist_px)` swallows overlap. A negative distance means ink intruding into the free
   space Rule 8(1)'s proviso requires — the violation the measurement exists to detect. Handle
   it as a distinct outcome, not a clamped zero.
5. Say in the PR body that this does not restore Rule 8 — `pipeline/` still never calls
   `measure_margins`.

### PR #56 — EXT-006 bilingual declarations · Sitanshu · `ext-006-bilingual-declarations`

Head `9cf855f`, three checks green. Six of nine review items properly closed, including the
`किलोग्राम` ordering fix with a ten-case boundary test, `MIXED` barred from pairing,
`pair_conf` changed from `max` to `min`, and `StrEnum`.

1. **BLOCKER — the lexicon change is in the log, not the branch.** The final entry says
   `मूल्य` → MRP and `अधिकतम राशी` → MRP were removed and
   `test_bare_mulya_does_not_cause_false_mrp` added. Both mappings are still in
   `_DEVANAGARI_TOKEN_MAP`; the test exists only inside that log sentence. The audit reasoning
   is correct and should be kept — `मूल्य` is generic price, used in the corpus inside
   `अजधकतम खुिरा मूल्य`. Commit the change.
2. The module docstring carries the *Statutory Corpus Citation* / *Engineering Priors* block
   **verbatim twice** plus a third partial restatement of Rule 9(4). Keep one. Preserve the
   sentence stating the 3.0 multipliers are engineering heuristics and not statutory
   thresholds.
3. PR body and log say 11 tests; the file has 17. Both say 694 passed; main has moved.
4. He now wraps every `_dispatch_single_span` confidence in `min(span.confidence, X)`, which
   changes monolingual behaviour too. Probably correct, outside ticket scope — state it in the
   PR body rather than reverting.
5. Not blocking, docstring note only: `detect_script` puts a Tamil or Bengali span and
   `"12345 !!!"` in the same `NEITHER` bucket, and Rule 9(4)'s proviso is what permits that
   additional language.

### PR #43 — MEA-005 artwork vector ingest · Yashashvi · `mea-005-artwork-vector-ingest`

Untouched in Session 6. Still blocked on a new `pdfplumber` dependency, which needs Abhiram's
decision before the PR can proceed.

---

## To do — Abhiram

### CORE-003 — `asset_type` on EvidenceEntry, its column, and its migration
**In flight, Lane A, plan stage.** Unblocks #46. Two decisions are made and are not open:
`asset_type` is required with no default; `asset_type` is folded into `compute_entry_hash`.
Also fixes `bck/tests/core/test_persistence.py`. Out of scope: `retention.py`, `storage.py`,
and `chain.py`'s purge logic — all Shiva's.

### DAT-005 — annotate the fifteen staged captures
**Highest value on the board.** `~/26034-dat/datasets/raw/_staging/`, six SKUs. Check Rule 26
against the corpus before writing ground truth for the 2 g Maggi sachet — if the exemption
applies, most Rule 6(1) obligations are `NOT_APPLICABLE`, not FAIL. `reference_object` must
now satisfy the DAT-004 vocabulary: `present: true` requires `object_type: coin_10` and
`known_dimension_mm: 27.0`. Heights stay null on every uncalibrated capture. The
`manifest.json` rebuild moved here from DAT-003.

### CI/datasets required status check
It has reported once, so it can now be added. Browser only:
`github.com/SIH-2026-CSM-A/26034/settings/rules` → `main-protection` → Require status checks →
`+ Add checks` → `datasets` → Save. Change nothing else. Never add a `paths:` filter after.

### DAT-003 — ownership reassignment only
**Rescoped. Do not run its original setup step** — it unzips `dat001-raw-corpus.zip` into
`datasets/raw/`, re-importing the fabricated corpus DAT-002 deleted. What remains:
`.github/CODEOWNERS` reassigning `datasets/` away from Aashritha; the AGENTS.md ownership
table to match; `bck/app/modules/measurement/README.md`, which names `@Abhiram-0910` where
measurement belongs to Yashashvi.

### PIP-003 — wire the category proposal into the orchestrator
`propose_category` merged in #52 with no caller. A proposal is evidence, never a confirmation:
`Scan.product_category` is set only by an officer's explicit act. The load-bearing test is
that a proposal never mutates it. The sector gate stays exactly as it is.

### Docs PR — the `rtk` gotcha
CLAUDE.md and AGENTS.md both document the purge as bare `find … -exec`, which is the unsafe
shape. Must become `/usr/bin/find`, with the exit-1 behaviour and the `gh run view`
interception recorded.

---

## To create — not yet on the board

### TAM-002 — wire tamper detection and calibrate its priors
Akshaya. **Blocked on DAT-005.** Export and call both detectors from the orchestrator; a
tamper finding routes to REVIEW and never produces `POTENTIAL_VIOLATION` on its own. Carried
over from the TAM-001 review: a conflict flags every span in every cluster including agreeing
ones, so it does not localise; `off\b` in the exclusion list drops a whole span, a false
negative on the MRP; spans skipped by the `continue` branches are indistinguishable from
clean. Once the corpus exists, report the false-positive rate — if the sticker detector fires
on clean labels, cut it to conflicting-MRP only for the demo.

### MEA-008 — REF_DIMS has no entry for the printable 50 mm calibration card
Yashashvi. F2's manufacturer self-check names it. Deliver the `REF_DIMS` entry, the detector
branch and a confidence prior together, or close the ticket with the finding that the artefact
does not exist yet. Do not write `50.0` as though it were sourced the way the ₹10 coin's
27.0 mm is.

### EXT-007 — a bilingual declaration whose two renderings disagree
Sitanshu. **Blocked on #56.** Non-pairing is correct; silently emitting two contradictory
`NormalisedField` records of the same type is not. Read ARCHITECTURE.md's data-flow step 5 —
providers that disagree surface both readings rather than arbitrating. Likely REVIEW, not
`INSUFFICIENT_EVIDENCE` (both were read perfectly well) and not FAIL (which is wrong is an
officer's call).

---

## Board moves owed by hand

Connector was rate-limited. These were not made programmatically — verify each:

`done` — DAT-002, CTR-004, CI-004, TAM-001, DAT-004, and CTR-005 once created.
`in progress` — EVD-005, MEA-006, EXT-006, CORE-003.
`to do` — DAT-003, DAT-005, PIP-003, and TAM-002 / MEA-008 / EXT-007 once created.

Several existing tickets are missing the `Module 26034` option UUID — it rejects a plain
string and needs a UUID from `clickup_get_custom_fields`.
