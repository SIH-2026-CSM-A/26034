# datasets — compliance evaluation corpus and evaluation harness

**Owner:** Abhiram (`@Abhiram-0910`) — transferred from Aashritha, who is off the project.
**Ticket:** DAT-002.

## Status, 2026-09-06 — the corpus is empty

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
  angle per SKU — the only coin dimension this project has a source for. `coin_inr_5` at
  25.0 mm appears in older drafts and is **not** sourced; do not use it;
- annotated only from what is legible in that image. A value that cannot be read is
  `null`, and `declared: false` means the declaration is absent from the pack, not that
  the photograph failed to show it.

`ground_truth_verdict` is the verdict the **system should reach given the evidence in that
photograph** — not the compliance status of the physical product. A sample with no
reference object cannot support a Rule 7 letter-height finding, so its height fields are
`INSUFFICIENT_EVIDENCE` and the sample's verdict is `REVIEW`, never `PASS`. Ground truth
that demands the system overclaim will score correct refusals as failures.

Packages sold outside India for retail there are outside LMPC scope; a missing INR MRP on
such a pack is `NOT_APPLICABLE`, not `FAIL`. That scope limb is **[SOFT]** — verify it
against the corpus text before encoding it as a rule rather than an annotation convention.

## Layout

- `datasets/raw/<category>/<sku_id>/<sample_id>.<ext>` — image binaries, gitignored.
- `datasets/annotations/<category>/<sample_id>.json` — one annotation per image, tracked.
- `datasets/manifest.json` — built from `datasets/raw/` by walking the directory. It is
  not synced from Google Drive; the demo has to survive the venue network failing.
- `schema.py` (Pydantic v2) is authoritative; `schema.json` is exported from it.

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
