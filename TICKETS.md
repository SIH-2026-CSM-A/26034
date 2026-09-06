# TICKETS.md — board state, 2026-09-06 (end of session 3)

ClickUp list `26034 Build` (`1300450000005736`), space `SIH Team` (`1300450000003833`).
Fields: `Module 26034` (dropdown) · `Files` (text) · `Branch` (text).
Statuses: `to do` · `doubt` · `in progress` · `review` · `done` · `complete`.

**`done` is the terminal status. Nothing moves to `complete`.**

The ClickUp connector works — create and update tickets directly. If it rate-limits again,
stop and give Abhiram each ticket as one pasteable markdown block: title, assignee, status,
priority, the three custom field values, description.

`main` is at `bc41ea5` plus the docs PR and CI-003. **529 tests passing**, 3 import contracts
kept, 0 broken.

---

## Status

| Ticket | Owner | Status | PR |
|---|---|---|---|
| CI-001 scaffold | Abhiram | done | #3 |
| COR-001 rule corpus | Abhiram | done | #6 |
| INF-001 CODEOWNERS + import guard | Abhiram | done | #7 |
| INF-002 handoff | Abhiram | done | #10 |
| INF-003 gh auth login steps | Abhiram | done | #11 |
| CTR-002 contracts v1 | Abhiram | done | #17 |
| CORE-001 auth, RBAC, jurisdiction scoping | Abhiram | done | #25 |
| **PIP-001 verdict assembly + rule snapshot adapter** | Abhiram | **done** | **#28** |
| **PIP-002 HTTP surface, orchestration, scan endpoints** | Abhiram | **review** | — |
| **CI-002 frontend build gate** *(no ClickUp ticket)* | Abhiram | **done** | **#30** |
| **CTR-003 snapshot deep copy** *(no ClickUp ticket)* | Abhiram | **done** | **#33** |
| **RUL-002 Rule 8/9, sector overrides, Combination/Group** | Abhiram *(from Jashwanth)* | **done** | **#32** |
| **FNT-002 officer design system, verdict detail, review queue** | Abhiram *(Vineeth's module)* | **done** | **#35** |
| **RUL-003 multi-piece package 2(kc) + food proviso** *(no ClickUp ticket)* | Abhiram | **done** | **#36** |
| **EVD-003 hash chain verification + append-only** | Shiva Kumar | **done** | **#31** |
| docs: session log, TODO, tickets *(no ClickUp ticket)* | Abhiram | done | #37 |
| CI-003 frontend always reports *(no ClickUp ticket)* | Abhiram | in flight | — |
| EXT-001 | Sitanshu | done | #4 |
| EXT-002 country of origin | Sitanshu | done | #18 |
| EXT-003 name, dimensions, unit price | Sitanshu | done | #24 |
| **EXT-004 span classification + spatial role binding** | Sitanshu | **to do** | — |
| RUL-001 | Jashwanth | done | #21 |
| VIS-001 | Akshaya | done | #5 |
| VIS-002 PDP detection + OCR | Akshaya | done | #20 |
| **VIS-003 constrained re-OCR, arbitration, offline** | Akshaya | **in progress — rework** | #29 open |
| **TAM-001 conflicting MRP + sticker overlay** | Akshaya *(from Shivasai)* | **to do** | — |
| MEA-001 | Yashashvi | done | #9 |
| MEA-002 artwork mode + Rule 9 contrast | Yashashvi | done | #13 |
| MEA-003 ratio + margins | Yashashvi | done | #22 |
| EVD-001 | Shiva Kumar | done | #12 |
| EVD-002 MinIO + BSA report | Shiva Kumar | done | #23 |
| FNT-001 | Yashwanth *(one-time exception)* | done | #14 |
| **DAT-001 corpus, labelling schema, eval harness** | Aashritha | **in progress — rework** | #34 open |

### PIP-002 — open questions for review

1. **`contracts/binding.py` and `DeclarationRole` must not merge until Sitanshu agrees the
   shape.** They are a separate commit at the end of the branch and nothing else depends on
   them. `BoundDeclaration` carries `field_type`, `span_refs`, `raw_text`, `role`,
   `region_id`, `binding_confidence`; the proposed export is
   `bind_declarations(spans: Sequence[ExtractedSpan]) -> tuple[BoundDeclaration, ...]`.
2. **65 findings per scan.** Rule 7 and Rule 9 govern every declaration the store requires,
   so each pairing is its own finding and most are INSUFFICIENT_EVIDENCE. Truthful, heavy to
   read. Narrowing it is a `governs_declarations` field on the rule store, not a pipeline
   filter — needs a decision.
3. **`request-recapture` records an event and nothing else.** No re-capture workflow behind
   it; the vocabulary is complete so the UI has something to write.

**Unavailable:** Jashwanth, Yashashvi, Vineeth. **Never started:** `fnt-admin` (Rohan).
**Reserve:** Likhitha.

---

## Open reworks — exact remaining items

### #29 VIS-003 — Akshaya

Four pushes, all byte-identical to the first (blob range `ef2dd9d..5587ce4` unchanged).
**Verify the head OID and the blob hashes before reviewing again.** Five items:

1. `test_ocr_network_isolation` cannot fail — PaddleOCR is patched, so nothing runs. Prove it
   by putting a real HTTP call in the path and confirming red.
2. No synthetic-crop test for 8/B, 0/O, 5/S, 1/l. `arbitrate_mrp("150", "1S0")` is a string
   comparison, not an OCR test. This is the ticket's central accuracy claim.
3. `ArbitrationResult` carries no `EvidenceProvider` on either reading.
4. `arbitrate_mrp` has no caller; `extract_mrp_quantity` returns a bare `str`, so the
   constrained pass is disconnected from the Paddle spans.
5. Whitelist `"0123456789.Rskgmlg/-"` excludes `₹` — on the one field the pass exists to
   protect — has `g` twice, and no `M` or `P`.

Separate, not a review failure but a latent crash: the PaddleOCR constructor uses 3.x kwargs
while the call site is `ocr.ocr(image, cls=False)`, the 2.x signature. Both tests mock the
library so CI cannot catch it.

### #34 DAT-001 — Aashritha

Four rounds in, real progress each time. **Fixed:** all `letter_height_mm` and
`numeral_height_mm` nulled on uncalibrated packs; stale `pdp` block removed from the Himalaya
files; `pdp_geometry` correct at 56.0 cm² in the 50–100 band at 1.5mm; manifest cut from 89
lines to 53 with **every empty-file hash gone**; placeholder `drive_folder_id` removed;
`schema.py` cites Rule 6(1)(aa) alone. The Tata Salt annotation correctly derives `Rs. per kg`
from a ≥1 kg net quantity under Rule 6(11) and says so in its notes.

**Remaining:**

1. `cosmetics_himalaya_face_wash_100ml_001` appears **twice** in the manifest — once `.jpg`,
   once `.png`, same `sample_id` and `annotation_path`, different `sha256`. The harness would
   load it twice and the two hashes disagree about which file the sample actually is. Keep the
   `.jpg` (it is what the annotation's `image_filename` points at) and drop the `.png` record.
2. `food_parle_g_biscuits_001` has `reference_object.present: false` and every height nulled,
   but its notes still read "Small PDP (48 cm²) sample with calibrated coin reference target."
   Either set `reference_object` with `object_type` and `known_dimension_mm: 27.0` and restore
   the heights, or delete that sentence.
3. **Still unanswered after four rounds:** does the Himalaya tube carry an INR MRP? Both files
   are tagged `export_pack` and `non_domestic` while declaring `MRP Rs. 180.00`. If no INR MRP,
   `declared: false` and `expected_field_state: NOT_APPLICABLE` with the reason recorded. If
   there is one, drop the `export_pack` tag.
4. Manifest `image_path` uses
   `datasets/raw/cosmetics/cosmetics_himalaya_face_wash_100ml_001/…` while the annotations'
   `image_filename` says `datasets/raw/cosmetics/himalaya_face_wash_100ml/001.jpg`. Two path
   schemes for the same file — nothing downstream can resolve an image from an annotation.

Written review has now failed on the same underlying issue four times. Next move is a
fifteen-minute call with one annotation open beside the actual photograph, not a fifth round.

---

## Owed on every future ticket

- A personalised **"Before you raise the PR"** block built from that ticket's own acceptance
  criteria and its specific failure modes — including *"prove the test can fail: introduce
  the defect it guards against, confirm red, revert."*
- The `Files` field must include the matching test path **and** `session-log/<name>.md`.
  Omitting the session log produced false out-of-scope flags on every review last session.
- A rebase instruction placed **immediately before opening the PR**, not before starting
  work. Stale base is the recurring cause of "no checks reported" on this repo.
