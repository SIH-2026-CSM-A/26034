# datasets — compliance evaluation corpus and evaluation harness

**Owner:** Abhiram (`@Abhiram-0910`) — transferred from Aashritha, who is off the project.
**Ticket:** DAT-002.

## Status, 2026-09-08 — four samples, all uncalibrated, none usable for Rule 7

DAT-008 rebuilt the corpus from the four images actually on disk. Before it, `manifest.json`
held twelve records from DAT-005 (#77), every one naming an image that does not exist, while
the four real images were named by no record and no annotation's `image_sha256` matched any
file present. Thirteen integrity guards passed over that. The twelve orphan annotations were
deleted rather than repaired; they described nothing.

What is here now:

| sample | net quantity | category |
| --- | --- | --- |
| `food_parle_g_gluco_biscuits_65g_001` | 55 g + 10 g extra = 65 g | food |
| `food_parle_g_gluco_biscuits_130g_001` | 110 g + 20 g extra = 130 g | food |
| `cosmetics_himalaya_curcuma_face_wash_150ml_001` | 150 ml ℮ | cosmetics |
| `cosmetics_himalaya_neem_turmeric_face_wash_150ml_001` | 150 ml ℮ | cosmetics |

Four SKUs, one image each — not two SKUs with two views. The `cosmetics/` and `food/`
directories were swapped: `raw/cosmetics/cosmetics_himalaya_face_wash_100ml_*` held Parle-G
packets and `raw/food/food_parle_g_biscuits_*` held face wash tubes. That is a legal error,
not a filing one — Rule 6(1)(d)'s first proviso routes a food pack's date declaration to the
food law and its third proviso routes a cosmetic's to the Drugs and Cosmetics Rules, 1945, so
a mis-filed pack is evaluated against the wrong sector override. The directory names also
carried the wrong net quantity (`100ml` on a 150 ml tube), so they were renamed to what the
packs actually read.

**All four are uncalibrated.** No reference object is in any frame, so
`reference_object.present` is false, `pdp.is_measurable` is false, every `numeral_height_mm`
and `letter_height_mm` is null, and every `ground_truth_verdict` is `REVIEW`. No sample here
supports a Rule 7 letter-height finding, and **no accuracy or false-positive figure may be
quoted from this set.** Any tamper false-positive rate over it is n=4 and must be quoted with
its n.

No field is annotated `FAIL`. Each is `PASS` only where the declaration is legible in that
frame and the clause applies; `NOT_APPLICABLE` where a sourced sector override displaces the
clause; and `INSUFFICIENT_EVIDENCE` where a declaration is not in frame or cannot be read.
Rule 26 was checked against all four and reaches none of them: 65 g, 130 g, 150 ml and
150 ml are all above the 10 g / 10 ml threshold.

The two face wash tubes are EU/UK-market packs — Responsible Person addresses in Warsaw,
Riga and London, country of origin UAE, no MRP and no Indian importer. Their MRP and unit
sale price are `NOT_APPLICABLE` under the foreign-retail convention recorded below. **Whether
the LMPC Rules reach a pack in that market at all is unresolved**; nothing in Rule 3 as
encoded excludes it, so no field state rests on the question, but the corpus's cosmetics half
is two packs that were never placed on the Indian market.

None of the four is a field capture. All are e-commerce catalogue images on seamless white,
one with a studio reflection — the provenance DAT-002 recorded below, unchanged. They are not
AI-generated, but OCR and tamper numbers measured over them will read better than the same
code will read a photograph taken in a shop.

`datasets/ingest_images.py` was deleted in DAT-008 rather than fixed. See "Building the
manifest" below.

## History, 2026-09-06 — DAT-002 emptied the corpus

Four annotations and four images previously lived here. All four were deleted in DAT-002
after being checked against their own photographs and against `schema.py` for the first
time. Every one of them was fabricated:

- Both `cosmetics_himalaya_face_wash_100ml_*` annotations described a 100 ml Indian retail
  tube with an MRP of Rs. 180.00 and a Bengaluru manufacturer address. The images are two
  *different* EU export products (Curcuma and Neem face wash), both 150 ml, country of
  origin UAE, a UK responsible-person address, and **no MRP, no unit sale price and no
  Indian consumer-care declaration anywhere on either pack**. They also shared one
  `sku_id` while being different products.
- Both `food_parle_g_biscuits_*` annotations declared 55 g. The packs read
  `55g+10g EXTRA=65g` and `110g+20g EXTRA=130g` — two different pack sizes sharing one
  `sku_id` and one PDP geometry. The consumer-care number was annotated `022-66916911`;
  the pack reads `022-6691 6929`. The unit sale price was computed (5.00 ÷ 55), not read;
  Parle-G wrappers carry none.
- `food_parle_g_biscuits_001` claimed `reference_object.present: true` with the
  `calibrated` tag. **There is no reference object in the frame.** A fabricated
  calibration claim is the one defect that could let a millimetre figure out of an
  uncalibrated photograph.
- All eight declaration bounding boxes were byte-identical across all four files — one
  template copied, not read off any image.
- All four failed `schema.py` validation, which had never been run against them.

None of these were photographs. All four were e-commerce catalogue renders, two on
seamless white with a reflection.

**Nothing in this directory may be treated as ground truth until real captures land.**

## What the corpus must be

Real captures, taken by the team, of packages we physically hold. Each sample:

- shot in ordinary indoor light, not on a white sweep, at 2–3 angles;
- with a **₹10 coin (27.0 mm, RBI-confirmed)** flat in frame and in focus for at least one
  angle per SKU — the only coin dimension this project has a source for. The ₹5 coin at
  25.0 mm appears in older drafts; that figure is sourced in neither `rules-corpus/` nor
  `SIH26034_Research_And_References.md`, so the ₹5 coin must not be added to the schema
  enum or to measurement's `REF_DIMS`;
- annotated only from what is legible in that image. A value that cannot be read is `null`.

`declared` is **per-image, not pack-level** (DAT-008). A declaration that is not in this
frame is `declared: false` with `expected_field_state: INSUFFICIENT_EVIDENCE` — a back-panel
declaration annotated on a front image is exactly that. What distinguishes "not shown here"
from "absent from the pack" is the state, never `declared` on its own: absence from the pack
would have to be `FAIL`, and no single panel can establish it. This supersedes the earlier
rule that `declared: false` meant absent from the pack; the two readings were annotated
inconsistently across DAT-002 and DAT-005.

`ground_truth_verdict` is the verdict the **system should reach given the evidence in that
photograph** — not the compliance status of the physical product. A sample with no
reference object cannot support a Rule 7 letter-height finding, so its height fields are
`INSUFFICIENT_EVIDENCE` and the sample's verdict is `REVIEW`, never `PASS`. Ground truth
that demands the system overclaim will score correct refusals as failures.

Packages outside Chapter II are `NOT_APPLICABLE`, never `FAIL` — the obligation does not
arise. Two limbs, and they are no longer the same one:

- **Rule 3 is [SOURCED] and encoded** as `R3-CHAPTER-II-SCOPE` (RUL-005). A pack over 25 kg
  or 25 litre is out of scope deterministically; a pack bearing `not for retail sale` routes
  to `REVIEW`, not to `NOT_APPLICABLE`, because the marker is evidence and not proof. Annotate
  to that: a 30 kg sack is `NOT_APPLICABLE` throughout, a marked pack is `REVIEW`.
- **The export limb is still [SOFT]** and its old justification was wrong — Rule 25 makes
  Chapter II the standard an export pack must be re-labelled *to*, not a scope exclusion. See
  `rules-corpus/README.md`. Keep annotating a foreign-retail pack's missing INR MRP as
  `NOT_APPLICABLE` by convention, and do not cite Rule 25 for it.

## Layout

- `datasets/raw/<category>/<sku_id>/<sample_id>.<ext>` — image binaries. `raw/` is
  gitignored, and the four DAT-008 captures (512 KB total) are force-added on top of that
  ignore so CI can verify their hashes. A new capture is **not** tracked by dropping it in
  the directory; it has to be `git add -f`ed deliberately, which is the intended friction.
- `datasets/annotations/<category>/<sample_id>.json` — one annotation per image, tracked.
- `datasets/manifest.json` — one record per image, written by hand. See below.
- `schema.py` (Pydantic v2) is authoritative; `schema.json` is exported from it.

## Building the manifest

By hand. There is no script.

`ingest_images.py` was deleted in DAT-008. It wrote a `samples` key while every reader —
`bck/tests/contracts/test_manifest_integrity.py` and the harness — reads `records`, so
running it emptied the manifest as far as every consumer was concerned and left the guards
looping an empty list, green. It also demanded a Google Drive folder ID the offline-demo
design forbids, globbed `*.jpg` only so every `.png` capture was skipped in silence, and
derived `sample_id` as `{category}_{sku_dir}_{stem}`, which double-prefixes the category
that `sku_dir` already starts with. Four records maintained by hand do not need sixty lines
that have never produced a correct manifest and can destroy one.

The `sha256` in each record is the SHA-256 of the image bytes on disk, and
`annotation.image_sha256` must equal it. `test_the_manifest_hash_is_the_hash_of_the_image_on_disk`
checks that against the file rather than against the other document — forging both to agree
still fails.

Identifiers: `sku_id` matches `^(food|cosmetics)_[a-z0-9_]+$`; `sample_id` is
`<sku_id>_<index>`. **One `sku_id` means one physical product at one pack size.** Two pack
sizes are two SKUs.

## Defect cases worth capturing

Buy for these deliberately — a corpus of compliant packs measures nothing:

1. `missing_month_year` — Rule 6(1)(d) date absent or ambiguous.
2. `non_compliant_usp_unit` — Rule 6(11) declared on the wrong unit basis.
3. `missing_unit_sale_price` — Rule 6(11) absent on an applicable pack.
4. `font_below_minimum` — Rule 7 Table-I; only assessable on a calibrated capture.
5. `missing_consumer_care` — Rule 6(1)(n).
6. `incomplete_address` — Rule 6(1)(a); city-only, or Manufactured-by vs Marketed-by unclear.
7. `obscured_free_space` — Rule 8(1) proviso clearance around the quantity declaration.

## Difficulty tags

`small_pdp` · `glare` · `curved` · `multiscript` · `missing_month_year` ·
`flexible_pouch` · `crowded` · `calibrated` · `uncalibrated` · `low_contrast` · `tilted` ·
`partially_occluded`

These are the members of `DifficultyTag` in `schema.py` and the only permitted values.
`export_pack` and `non_domestic` were used in the deleted annotations and are not members.

## Harness

```bash
python -m datasets.eval.harness --annotations datasets/annotations --test-run
python -m datasets.eval.harness --annotations datasets/annotations --predictions predictions.json --output report.json
```
