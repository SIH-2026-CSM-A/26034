# Demo recordings — 2026-09-20 (Session 42, second recording)

Two passes of the same script against the live tunnel
(`https://locally-progress-major-bare.trycloudflare.com`, backend at `b1bf4bd`, #174, frontend
at `d7e5620`),
recorded with Playwright's own video recorder in headless Chromium 1.62. Real network, real
OCR, real database writes. No response was stubbed and no click was synthesised on anything
not on screen. The videos are gitignored; the indexes and the script are not.

| Pass | File | Runtime | Failed steps | Page errors |
|---|---|---|---|---|
| Phone 390×844 | `pccs-demo-390x844.webm` (25.8 MB, 633.9 s of video) | **634.0 s** | none | none |
| Desktop 1280×800 | `pccs-demo-1280x800.webm` (39.3 MB, 623.6 s of video) | **623.6 s** | none | none |

Per-step timestamps: `pccs-demo-390x844-index.md`, `pccs-demo-1280x800-index.md`. Each index
lists every scan and complaint the pass created, by id, and carries the Table-I finding and
the ledger row in full, unsliced.

Script: `record.cjs`. Rerun with
`PCCS_OFFICER_PASSWORD=… PCCS_VENDOR_PASSWORD=… NODE_PATH=$(npm root -g) node demo/record.cjs phone|desktop`.

## The Table-I finding, as it appeared on screen

Both passes, marked submission (776 × 1207 px at (86, 38)), from the review ledger row:

> Net quantity, letter height · **REVIEW REQUIRED** · Review required. Applying the rule to this
> evidence needs an officer. · Measured **2.61 mm** · Required **1.5 mm to 2.5 mm** · Rule 7(2),
> Table-I · Evidence None · the measured principal display panel area of 102.3 ± 10.2 cm² lies
> across a Table-I band edge: 1.5 mm is required below it and 2.5 mm above; the measured
> character height of 2.61 ± 0.13 mm lies across the 2.5 mm requirement: which side of the
> requirement this package falls on is not established at the measurement's own precision.

Phone: scan `fd1890c1`, held from 10:09 to 10:34. Desktop: scan `f855dc0c`, held from 09:59 to
10:24. The 25 s ledger hold is the longest in the recording. The measurements card that
precedes it shows the same state, measured and required values; the reason is on the ledger.

The unmarked submission before it (phone `bf659589`, desktop `94ea5efc`) is Table-I
INSUFFICIENT EVIDENCE, observed 2.61 mm, no required value: "the character height was measured
but the principal display panel area was not, and Table-I bands the height against that area".

## What each pass shows, in order

1. **Consumer, no sign-in, two products.** `/consumer`, a fresh close capture of a Parle-G 56 g
   back panel: the browser decodes `8901719100015 · EAN-13 · check digit does not verify`; the
   real OCR wait (57 s in both passes); REVIEW; one row per declaration naming its rule (net
   quantity `56 g` and MRP `₹ 10.00` REVIEW under Rule 6(1)(c) and 6(1)(e), manufacture date
   `2024-06-10` PASS under 6(1)(d)); the ingredients line as read, running to "(1101(i)) AND
   DOUGH CONDITIONER (223)."; the additive section with **INS 503(ii), 500(ii), 472e, 1101(i)
   and 223**, each against its FSS citation and 1101(i) "Not assessed — this code is not in the
   sourced reference"; the barcode section; then the SAFE consensus for `8901719100015`, which the reviews panel had
   already loaded from the decoded barcode (**SAFE, 9 shoppers**, marked as seeded). "Check
   another label", the MDH Kitchen King carton (no barcode read, 54–55 s, REVIEW), then
   `8901725113320` typed in → **UNSAFE, 4 shoppers**, marked as seeded.
2. **Vendor.** Sign in as `balaji-kirana`, submit the 65 g corpus Parle-G, REVIEW in 20–21 s, the
   routing line *"Routed to the district tier for attention · no premises visit indicated ·
   action on your part is indicated"*, sign out.
3. **Officer.** Sign in as `inspector1`; the vendor's scan is the top row of the queue. Open it,
   the Rule 6(1) rows worded *"Could not be read from this photograph. That is not a finding
   that it is absent."* Confirm the category as Food → re-evaluated as a new scan. Open a
   catalogue listing the machine has marked POTENTIAL VIOLATION (retail sale price not declared,
   `R6-1-E`) and record the **Confirm** determination through the determination sheet with a
   note → `POST /review 201`, finalised. Dashboard: the GHMC choropleth, hover Ward 121
   Kukatpally and Ward 91 Khairatabad, select one. Complaints: raise one against that
   confirmation → 201, append the acknowledgement → 201; the thread moves from Raised to
   Acknowledged. Phone: listing `f95ecffc`, complaint `1b36fdff`; desktop: listing `5fe91053`,
   complaint `a5918238`.
4. **The measurement.** `/officer/new`, the MDH carton with a ₹10 coin, Food, `coin_10`.
   Unmarked, then marked: the finding above.

## Deviations from the brief, stated

- **The officer confirms a listing the demonstration seeded.** The complaints page lists
  finalised scans from the newest 50 only, and each pass adds four scans before that step, so
  the confirmations `seed_demo.py` made have left that window. Two catalogue listings were
  submitted before recording, in the shape of the seed's `listing()` and titled "[Seeded demo]"
  like the rest of that corpus, each omitting the retail sale price so the pipeline reaches
  POTENTIAL VIOLATION under Rule 6(1)(e): `seeded-demo-s42-001` (`5fe91053`) and
  `seeded-demo-s42-002` (`f95ecffc`). Each pass confirms one on camera, which is the order the
  story asks for: an officer confirms before any enforcement act. They were submitted as
  `inspector1`, not as `demo-seeder`, whose password is not on this machine.
- **The SAFE consensus was not typed.** The reviews panel loaded it from the barcode decoded in
  the browser; the script logs that and does not type over it. The UNSAFE consensus was typed.
- **"Hold both results on screen"**: the app has no side-by-side view, so the unmarked and marked
  results are held 12 s each in turn, then the marked scan's ledger row for 25 s.
- **After confirming the category** the page lands on the new scan while it is still evaluating;
  the script waits for completion via the API and reloads. The reload is visible.

## What failed or was thrown away

- Session 42's first pair (phone 600.7 s, desktop 616.3 s, both clean) was superseded: it was
  recorded before the ingredient extractor was fixed, so its additive section reads "No INS or
  E additive codes found", and only its desktop pass carried the officer's determination. Logs
  `.phone-s42a.log`, `.desktop-s42a.log`.
- Before that: phone attempt 1 was superseded by the two-product consumer act
  (`.phone-attempt1.log`); desktop attempts 1 and 2 failed the complaint step because the page
  had no finalised POTENTIAL VIOLATION in its newest-50 window (`.desktop-attempt1.log`,
  `.desktop-attempt2.log`). All wrote real scans.
- Nothing failed in the two recorded passes.

## Raised, not fixed

- The Parle-G barcode: every structurally valid scanline the decoder finds (31 across two
  scales) reads `8901719100015`, the OCR reads the same digits from the human-readable line, and
  the modulo-10 check digit for `890171910001` is 7. The print does not conform; the display
  "check digit does not verify" is the honest one.
- The consumer chip reads `REVIEW` where the officer chip reads `REVIEW REQUIRED` for the same
  field state.
- The dashboard's ward readout is computed from the newest 30 scans, so it drifts as passes add
  scans: Ward 91 read "1 potential violation in 3 scans" on the phone pass and "0 potential
  violations in 2 scans" on the desktop pass. Real, and not a number to narrate.
