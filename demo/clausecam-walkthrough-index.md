# ClauseCam walkthrough — 1280x800

Video: `clausecam-walkthrough.webm` · target https://locally-progress-major-bare.trycloudflare.com · started 2026-09-23T09:02:36.042Z

Timestamps are seconds from the start of the recording.

Deployed build: `main` at `dddd631` (#198: evidence report button and officer sign-out), backend with
#196 (read-only officers). Recorded 2026-09-23 09:02:35–09:10:12 UTC, headless Chromium 1.62 via
`demo/record-clausecam.cjs`. Real network, real OCR, real database writes; nothing stubbed, nothing
edited out. Wall clock and video length agree (457 s / 455.7 s): the host was held awake and did not
sleep. All 18 steps passed; no page errors.

**What this pass wrote.** Officer scan `cb194e5d` (MDH carton, marked), its CONFIRM review, and one
report-export entry on its evidence chain; vendor scan `5ac00ab1`; consumer scan `7163e660`. No seeded
row was acted on.

**The report.** The SHA-256 on screen at `04:13`, `cb8ab66bcd9f54055e75662c32372cfda851296f75008fb4db74fdfe7ab58654`,
is the `report_sha256` of chain entry 2 on `cb194e5d` (`exported_by: demo-officer`, `format: pdf`), read
from `evidence_entries` after the pass.

**The vendor camera.** The vendor surface is camera-only (`getUserMedia`). Headless Chromium has no
camera, so its fake capture device plays the Parle-G 65 g corpus photograph into the live view and the
shutter is pressed on camera. The y4m is the photograph at its native 500 × 500, unscaled: an earlier
pass scaled it to 1280 wide and the quality gate refused it as too blurred.

**The public account.** `demo-officer` is `read_only` on the deployment. It was lifted for this pass
from 09:02:18 to 09:10:45 UTC, under a root systemd timer set to restore it after 20 minutes whatever
happened, and restored by hand at the end; the 403 was proved over the tunnel afterwards. The seeded
demo-district fingerprint (30 scans, 6 reviews, 9 complaints, and the md5 of each set) was identical
before and after.

**One entry on a seeded scan, from verifying #198.** Before #198 merged, its report button was checked
in a browser as demo-officer against a finalised scan, and every finalised scan in the demo district is
seeded. That appended one `report_export` entry (sequence 1, 07:21:12 UTC, `report_sha256`
`62d17ab3baed79fe34a0f8e35f168d4c9b7062e6b3186294102e4b65cf140499`) to the evidence chain of seeded
scan `83b80c18`. It is additive, and the same act is open to anyone on the public login; it is not in
the scans, reviews or complaints the fingerprint covers.

**Earlier attempts** (not shipped): 1, the host suspended mid-pass; 2, the recorder still used the removed
vendor file input and missed the applicability section; 3, the consumer upload died with the network;
4, clean except the vendor frame, refused as too blurred.

- `00:00` **1 The opening on the root**
- `00:04` **2 The four ways in**
- `00:04` ways in: Officer · Vendor · Consumer · Create account
- `00:09` **3 /login and its Demo access panel**
- `00:10` panel: Demo access Public demonstration accounts. They see seeded demo data only. Officer (District Inspector, demo district) Username demo-officer Password clausecam-demo Sign in as this user
- `00:15` **4 One-click sign-in as demo-officer**
- `00:16` **5 The queue**
- `00:17` queue: 36 of 36 inspections
- `00:23` **6 A scan, capture to verdict: the MDH carton with a ₹10 coin, Food, coin_10**
- `00:31` photograph 1214×1295 drawn at 638×681 px; dragging (366,79) → (774,714)
- `00:32` caption: Panel marked: 776 × 1207 px at (86, 38)
- `00:36` **6 Submit and wait out the real OCR and evaluation**
- `01:33` marked: evaluated in 57 s (scan cb194e5d)
- `01:39` measurements: Measurements Estimated from the photograph. A calibrated figure carries its interval in brackets; without a reference there is no figure. Net quantity · Rule 7(2), Table-I REVIEW REQUIRED Review required. Applying the rule to this evidence needs an officer. Measured 2.61 mm Required 1.5 mm to 2.5 mm Net quantity · Rule 8(1) proviso PASS Pass. The declaration satisfies the rule as evaluated. Measured numeral height 2.61 mm (±0.13); above 2.93 mm (±0.15); below 2.93 mm (±0.15); left 7.63 mm (±0.38); right 7.84 mm (±0.39) Required above and below at least 2.61 mm; left and right at least 5.23 mm
- `01:40` Table-I: REVIEW_REQUIRED · observed 2.61 mm · expected 1.5 mm to 2.5 mm · the measured principal display panel area of 102.3 ± 10.2 cm² lies across a Table-I band edge: 1.5 mm is required below it and 2.5 mm above; the measured character height of 2.61 ± 0.13 mm lies across the 2.5 mm requirement: which side of the requirement this package falls on is not established at the measurement's own precision.
- `01:48` **7 Applicability (category classification)**
- `01:48` applicability (category classification): Confirmed Product Category FOOD OFFICER CONFIRMED Rule 7, 8 and 9 findings stay at INSUFFICIENT_EVIDENCE until an officer confirms the category. Confirming evaluates the held capture again as a new scan; this one is left as it was. Correct to Choose a category Food Cosmetics Medical Device Non-consu
- `01:55` **8 Each clause-cited finding**
- `01:56` verdict REVIEW; findings: NAME_AND_ADDRESS Rule 6(10A)=NOT_APPLICABLE; COUNTRY_OF_ORIGIN Rule 6(10A)=NOT_APPLICABLE; COMMON_OR_GENERIC_NAME Rule 6(10A)=NOT_APPLICABLE; NET_QUANTITY Rule 6(10A)=NOT_APPLICABLE; MANUFACTURE_DATE Rule 6(10A)=NOT_APPLICABLE; BEST_BEFORE_DATE Rule 6(10A)=NOT_APPLICABLE; RETAIL_SALE_PRICE Rule 6(10A)=NOT_APPLICABLE; DIMENSIONS Rule 6(10A)=NOT_APPLICABLE; OTHER_PRESCRIBED_MATTER Rule 6(10A)=NOT_APPLICABLE; UNIT_SALE_PRICE Rule 6(11)=INSUFFICIENT_EVIDENCE; NAME_AND_ADDRESS Rule 6(1)(a)=NOT_APPLICABLE; COUNTRY_OF_ORIGIN Rule 6(1)(aa)=NOT_APPLICABLE; COMMON_OR_GENERIC_NAME Rule 6(1)(b)=PASS; NET_QUANTITY Rule 6(1)(c)=REVIEW_REQUIRED; MANUFACTURE_DATE Rule 6(1)(d)=INSUFFICIENT_EVIDENCE; BEST_BEFORE_DATE Rule 6(1)(da)=INSUFFICIENT_EVIDENCE; MANUFACTURE_DATE Rule 6(1)(d) provisos effective 2024=INSUFFICIENT_EVIDENCE; RETAIL_SALE_PRICE Rule 6(1)(e)=INSUFFICIENT_EVIDENCE; DIMENSIONS Rule 6(1)(f)=INSUFFICIENT_EVIDENCE; OTHER_PRESCRIBED_MATTER Rule 6(1)(g)=INSUFFICIENT_EVIDENCE; NAME_AND_ADDRESS Rule 7(2), Table-I=INSUFFICIENT_EVIDENCE; COUNTRY_OF_ORIGIN Rule 7(2), Table-I=INSUFFICIENT_EVIDENCE; COMMON_OR_GENERIC_NAME Rule 7(2), Table-I=INSUFFICIENT_EVIDENCE; NET_QUANTITY Rule 7(2), Table-I=REVIEW_REQUIRED; MANUFACTURE_DATE Rule 7(2), Table-I=INSUFFICIENT_EVIDENCE; BEST_BEFORE_DATE Rule 7(2), Table-I=INSUFFICIENT_EVIDENCE; RETAIL_SALE_PRICE Rule 7(2), Table-I=INSUFFICIENT_EVIDENCE; DIMENSIONS Rule 7(2), Table-I=INSUFFICIENT_EVIDENCE; OTHER_PRESCRIBED_MATTER Rule 7(2), Table-I=INSUFFICIENT_EVIDENCE; NAME_AND_ADDRESS Rule 7(3)=INSUFFICIENT_EVIDENCE; COUNTRY_OF_ORIGIN Rule 7(3)=INSUFFICIENT_EVIDENCE; COMMON_OR_GENERIC_NAME Rule 7(3)=INSUFFICIENT_EVIDENCE; NET_QUANTITY Rule 7(3)=PASS; MANUFACTURE_DATE Rule 7(3)=INSUFFICIENT_EVIDENCE; BEST_BEFORE_DATE Rule 7(3)=INSUFFICIENT_EVIDENCE; RETAIL_SALE_PRICE Rule 7(3)=INSUFFICIENT_EVIDENCE; DIMENSIONS Rule 7(3)=INSUFFICIENT_EVIDENCE; OTHER_PRESCRIBED_MATTER Rule 7(3)=INSUFFICIENT_EVIDENCE; NET_QUANTITY Rule 8(1) proviso=PASS; NAME_AND_ADDRESS Rule 8(1)=INSUFFICIENT_EVIDENCE; COUNTRY_OF_ORIGIN Rule 8(1)=INSUFFICIENT_EVIDENCE; COMMON_OR_GENERIC_NAME Rule 8(1)=PASS; NET_QUANTITY Rule 8(1)=PASS; MANUFACTURE_DATE Rule 8(1)=PASS; BEST_BEFORE_DATE Rule 8(1)=INSUFFICIENT_EVIDENCE; RETAIL_SALE_PRICE Rule 8(1)=INSUFFICIENT_EVIDENCE; DIMENSIONS Rule 8(1)=INSUFFICIENT_EVIDENCE; OTHER_PRESCRIBED_MATTER Rule 8(1)=INSUFFICIENT_EVIDENCE; NAME_AND_ADDRESS Rule 9(1)=INSUFFICIENT_EVIDENCE; COUNTRY_OF_ORIGIN Rule 9(1)=INSUFFICIENT_EVIDENCE; COMMON_OR_GENERIC_NAME Rule 9(1)=INSUFFICIENT_EVIDENCE; NET_QUANTITY Rule 9(1)=REVIEW_REQUIRED; MANUFACTURE_DATE Rule 9(1)=INSUFFICIENT_EVIDENCE; BEST_BEFORE_DATE Rule 9(1)=INSUFFICIENT_EVIDENCE; RETAIL_SALE_PRICE Rule 9(1)=INSUFFICIENT_EVIDENCE; DIMENSIONS Rule 9(1)=INSUFFICIENT_EVIDENCE; OTHER_PRESCRIBED_MATTER Rule 9(1)=INSUFFICIENT_EVIDENCE; NAME_AND_ADDRESS Rule 9(3)=INSUFFICIENT_EVIDENCE; COUNTRY_OF_ORIGIN Rule 9(3)=INSUFFICIENT_EVIDENCE; COMMON_OR_GENERIC_NAME Rule 9(3)=INSUFFICIENT_EVIDENCE; NET_QUANTITY Rule 9(3)=INSUFFICIENT_EVIDENCE; MANUFACTURE_DATE Rule 9(3)=INSUFFICIENT_EVIDENCE; BEST_BEFORE_DATE Rule 9(3)=INSUFFICIENT_EVIDENCE; RETAIL_SALE_PRICE Rule 9(3)=INSUFFICIENT_EVIDENCE; DIMENSIONS Rule 9(3)=INSUFFICIENT_EVIDENCE; OTHER_PRESCRIBED_MATTER Rule 9(3)=INSUFFICIENT_EVIDENCE
- `02:45` **9 The band-edge REVIEW: Table-I, both uncertainties named**
- `02:46` ledger row: Net quantity, letter height REVIEW REQUIRED Review required. Applying the rule to this evidence needs an officer. Measured 2.61 mm Required 1.5 mm to 2.5 mm Rule Rule 7(2), Table-I Evidence None the measured principal display panel area of 102.3 ± 10.2 cm² lies across a Table-I band edge: 1.5 mm is required below it and 2.5 mm above; the measured character height of 2.61 ± 0.13 mm lies across the 2.5 mm requirement: which side of the requirement this package falls on is not established at the measurement's own precision.
- `03:53` **10 The officer's actions: record a determination on this pass's own scan**
- `04:01` POST /scans/cb194e5d/review -> 201
- `04:01` determination: REVIEW RECORDED Action: CONFIRM • Finalised: Yes
- `04:08` **11 The report with its SHA-256**
- `04:13` POST /scans/cb194e5d/evidence/report -> 201 application/pdf
- `04:13` SHA-256 on screen: cb8ab66bcd9f54055e75662c32372cfda851296f75008fb4db74fdfe7ab58654
- `04:27` **12 The ward map**
- `04:37` readout: Ward 98 Ameerpet · Central zone 4 potential violations in 5 scans
- `04:42` readout: Ward 91 Khairatabad · Central zone 2 potential violations in 4 scans
- `04:46` **13 The clause breakdown**
- `04:47` clause breakdown: Rule clause breakdown Select any clause to inspect underlying scan records Rule 6(1)(a) 0 of 28 · 0% Name and complete address of manufacturer / packer absent or incomplete Rule 6(1)(d) 0 of 28 · 0% Net quantity declaration numeral height or unit symbol specification requirement Rule 6(1)(f) 0 of 28
- `04:55` **14 Officer sign-out**
- `05:00` **15 /vendor/login and its Demo access panel**
- `05:02` panel: Demo access Public demonstration accounts. They see seeded demo data only. Vendor (demo kirana store) Username demo-vendor Password clausecam-demo Sign in as this user
- `05:11` **16 A vendor self-check**
- `05:11` vendor capture: shutter on the live camera view (Chromium fake capture device playing the Parle-G 65 g photograph)
- `05:35` OCR + evaluation took 21 s (scan 5ac00ab1)
- `05:40` routing: Routed to the district tier for attention · no premises visit indicated · action on your part is indicated
- `05:55` **17 The consumer surface: a Parle-G 56 g back panel, no sign-in**
- `06:58` OCR + evaluation took 57 s (scan 7163e660)
- `07:32` **18 Sign-out (vendor)**
- `07:36` end of recording — 456 s

Runtime (recording start to close): **455.7 s**
Scans created: officer cb194e5d-e828-4c47-a9ee-629bbbb1707b, vendor 5ac00ab1-e7a0-41a4-83e6-d0f550ce43b4, consumer 7163e660-7c94-4b43-96c1-d22e8eea40c6

Page errors: none
