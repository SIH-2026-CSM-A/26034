# rules-corpus

Immutable source documents. **Add files, never edit them.** Every rule encoded in
`bck/app/modules/rules/` must cite a file in this directory by name, and a rule whose
`gazette_ref` does not resolve to a corpus PDF fails to load. That gate is tested.

There is no automated sync and there must not be one. `consumeraffairs.gov.in`,
`doca.gov.in` and `egazette.gov.in` all refuse programmatic access. These were downloaded by
hand and are updated by hand when an amendment lands. **Do not build a fetcher.**

## Files

| File | Notification | Date | What it does |
|---|---|---|---|
| `LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf` | — | to 31.10.2021 | Full consolidated rules text. Maharashtra Legal Metrology compilation by S Y Mundhe, Assistant Controller. Semi-official. |
| `GSR-629E__2017-06-23__amendment-rules-2017.pdf` | G.S.R. 629(E) | 23.06.2017, w.e.f. 01.01.2018 | The Rule 7 rewrite. Unified Table-I banded by PDP area; former Table-II removed. |
| `GSR-722E__2023-10-06__amendment-rules-2023.pdf` | G.S.R. 722(E) | 06.10.2023, in force 01.01.2024 | Combination Package 2(ka), Group Package 2(kb), Multi-piece Package 2(kc). Paragraph 4 carries a Rule 6(11) unit-sale-price exemption, deliberately not encoded. |
| `GSR-778E__2025-10-23__medical-devices-mdr-2017.pdf` | G.S.R. 778(E) | 23.10.2025, gazetted and in force 24.10.2025 | Medical devices harmonised with the Medical Devices Rules, 2017. §2 → rule 2(h) proviso (PDP → MDR 2017); §3(i) → rule 7(2) height; §3(ii) → rule 7(3) width; §4 → rule 33 renumbered (1), new (2) disapplies the relaxation. |
| `GSR-881E__2025-12-02__pan-masala.pdf` | G.S.R. 881(E) | 02.12.2025 | Second Amendment Rules 2025 — pan masala. Not yet encoded. |
| `GSR-128E__2026-02-13__country-of-origin-ecommerce-filter.pdf` | G.S.R. 128(E) | 13.02.2026 | Inserts Rule 6(10A) — country-of-origin filter on e-commerce websites. Does **not** touch Rule 6(1). |
| `GSR-312E__2026-04-27__country-of-origin-second-amendment.pdf` | G.S.R. 312(E) | 27.04.2026, **effective 01.07.2027** | Substitutes 6(10A). Not yet in force — encode with `effective_from: 2027-07-01`, don't omit. |
| `DoCA-FAQ__2017__gsr-629E-implementation.pdf` | — | 2017 | FAQs on implementing G.S.R. 629(E). **Not** the source for the two [SOURCED] claims below. |

## Known gaps

**There is no enforced member-consumer guard anywhere in the repo.** ARCHITECTURE.md and
HANDOFF.md both stated that `ARUCO_MARKER`, `RULER_SCALE` and `CHECKERBOARD` were deleted
from `ReferenceObjectType` for lacking `REF_DIMS` entries. They are still present at
`datasets/schema.py:55-57` and still lack them. The rule — a member ships only alongside
something that consumes it — is right and has been applied fresh on every ticket since,
but nothing enforces it. Unresolved.


**Consolidated e-book (amended to 24.12.2024) — not captured.** `doca.gov.in/lm-ebook/`
returns "Access denied" for both the page and the direct PDF. Consequence: no consolidated
text covering November 2021 to date. The individual gazettes cover 2017 and 2023–2026,
leaving an unverified window between 31.10.2021 and 06.10.2023. Retry from a different
network, or look for a recent consolidation hosted by another state Legal Metrology
department.

**DoCA Legal Metrology FAQ, 11.11.2025 — not captured.** Two clarifications we rely on come
from it via three independent secondary reports (TaxGuru, Legality Simplified, AZB Partners)
rather than from the PDF itself:

- Q3 — retail sale price may be declared using either `₹` or `Rs.`
- Q12 — a complete name and address of the brand owner with "Marketed by" or "Brand Owner"
  satisfies Rule 6(1)(a)

Status **[SOURCED]**, not [VERIFIED]. Both are encoded in EXT-001. Replace this note when the
primary PDF is captured.

## Rule 7 — height of letters and numerals

Current since 01.01.2018 per G.S.R. 629(E). Rule 7(2) is a **single Table-I banded by
principal display panel area**, applying to letters and numerals alike. The former Table-II
no longer exists.

| PDP area (cm²) | Minimum height, normal (mm) | Blown, formed or moulded (mm) |
|---|---|---|
| A ≤ 50 | 1.0 | 1.5 |
| 50 < A ≤ 100 | 1.5 | 3.0 |
| 100 < A ≤ 500 | 2.5 | 4.0 |
| 500 < A ≤ 2500 | 4.0 | 6.0 |
| 2500 < A | 6.0 | 6.0 |

**There is no 2.0mm or 3.0mm normal-print band.** A value outside this table is invented.

**Rule 7(3)** — width not less than one third of height, except the numeral "1" and the
letters i, I and l.

**Rule 7(4) — PDP area computation.** Rectangular: height × width of the display side.
Cylindrical or nearly cylindrical: **40%** of (height × circumference). Any other shape: 40%
of total surface area, **or an area considered to be the principal display panel** — that
second limb is the answer for irregular shapes; measure the identified panel through the
homography rather than refusing. Excludes tops, bottoms, flanges at the top and bottom of
cans, and the shoulder and neck of bottles and jars.

**Rule 7(5) exception** — except for net weight, retail sale price, date of expiry / best
before / use by, and consumer care details, sub-rules (1) to (4) do not apply where the same
information is also required under any other law in force.

**Medical devices carve-out** — G.S.R. 778(E) routes numeral and letter height for medical
devices to the Medical Devices Rules, 2017, disapplies the Rule 33 relaxation, and makes PDP
declaration non-mandatory. **Table-I is therefore not universal.** The guard lives in
`minimum_character_height()`, not at the evaluator callsites, so every caller is covered.

A flat 1mm/2mm figure and a 1.7mm figure both appear in older project documents, including
`SIH26034_PSR.md` §3. Neither is current law. **That file is not a source for rule facts.**

## Rule 6(11) — unit sale price

**This is a format rule, not a tolerance.** It prescribes the unit basis on which the unit
sale price must be declared:

| Net quantity | Required declaration |
|---|---|
| Less than 1 kg | `Rs. __ per g` |
| 1 kg or more | `Rs. __ per kg` |
| Less than 1 m | `Rs. __ per cm` |
| 1 m or more | `Rs. __ per metre` |
| Less than 1 litre | `Rs. __ per ml` |
| 1 litre or more | `Rs. __ per litre` |
| Sold by count | `Rs. __ per number` |

The rule states **no tolerance, no rounding increment and no permitted difference**. The
±₹0.01 and ±₹0.05 figures appearing in earlier project documents are assumptions, not law,
and must not be encoded. A test asserts the rule store excludes them.

F18 is therefore two checks: is a unit sale price declared, and is it declared on the correct
unit basis for the net quantity.

## Rules 8 and 9 — placement versus manner

**Rule 8 governs placement. Rule 9 governs manner. They are distinct and must never be
merged into one check.**

- **Rule 8(1)** — declarations appear on the principal display panel. Its proviso: the space
  around the quantity declaration must be free of printed information, above and below by at
  least the **numeral's** height, left and right by at least twice that height. Geometrically
  measurable, so its evidence requirement is a calibrated measurement, not a text span.
  **Derive the threshold from `numeral_height_mm`, not `letter_height_mm`.**
- **Rule 8(2)** — returnable soft-drink bottles: retail sale price on crown cap and/or bottle.
- **Rule 9(1)–(4)** — legible and prominent; contrasting colour for retail-sale-price and
  net-quantity numerals; blown/formed/moulded and hand-script provisos; not read through
  liquid; Hindi/English.
- **Rule 9(3)** — an outer container or wrapper must carry all declarations unless it is
  transparent and the inner declarations are readable through it.

## Other provisions worth encoding

- **Rule 6(1)(a) Explanation III** — for food articles the Food Safety and Standards Act,
  2006 governs the manufacturer declaration instead.
- **Rule 6(1)(d) third proviso** — for cosmetics the Drugs and Cosmetics Rules, 1945 govern
  the date declaration. Cosmetics is the secondary demo category.
- **Rule 6(1)(aa)** — country of origin or manufacture or assembly, on the package. Distinct
  from Rule 6(10A), which is an e-commerce listing obligation evaluated against a
  `CatalogueRecord`.
- **Rule 13(2)–(3)** — unit selection: below 1 kg declare in grams, below 1 m in centimetres,
  below 1 litre in millilitres; at or above those thresholds use the larger unit.
- **Rule 26** — packages of 10 g or 10 ml or less are exempt, except tobacco products.
  Medical devices declared as drugs get no exemption.
- **Rule 31(2)** — in an advertisement stating retail sale price, the net quantity font size
  must equal that of the retail sale price.

## Encoded rule ids

`R6-1-A` · `R6-1-AA` · `R6-1-D` · `R6-11` · `R7-2-TABLE-I` · `R7-3-WIDTH-RATIO` ·
`R7-4-PDP-AREA` · `R7-MEDICAL-DEVICE-OVERRIDE` · `R8-1-PDP-PLACEMENT` · `R8-1-FREE-SPACE` ·
`R9-1-MANNER` · `R9-3-OUTER-CONTAINER` · `R2-KA-COMBINATION-PACKAGE` ·
`R2-KB-GROUP-PACKAGE` · `R2-KC-MULTI-PIECE-PACKAGE` · `R2-KC-MULTI-PIECE-FOOD` ·
`R6-1-A-EXPL-III-FOOD` · `R6-1-D-COSMETICS` · `R6-10A-ECOMMERCE-FILTER`

Package definitions carry `severity: REVIEW` — a definition classifies, it does not propose a
violation.

## Scope note on the 2026 amendments

G.S.R. 128(E) and G.S.R. 312(E) concern **country of origin and e-commerce display**, not
general labelling. G.S.R. 312(E) takes effect **01.07.2027** and is therefore not currently in
force — encode it with `effective_from: 2027-07-01` so it evaluates correctly against a scan
date, rather than omitting it.

## Rule 26 — small-package exemption

Packages of **10 g or 10 ml or less are exempt**, except tobacco products. Medical devices
declared as drugs get no exemption.

This is load-bearing for the evaluation corpus, not a footnote: the first real capture is a
**2 g** sachet. If the exemption applies, most Rule 6(1) obligations on it are
`NOT_APPLICABLE`, not `FAIL` — and ground truth that marks them FAIL would train the eval set
to score a correct refusal as a miss. Read the corpus text before annotating any sample at or
under the threshold.

## Scope of the Rules themselves

Two separate claims used to sit under this heading as one. They are different provisions,
they are sourced differently, and RUL-005 encoded only the first.

### Chapter II scope — [SOURCED], encoded by RUL-005

Chapter II is headed **"PROVISIONS APPLICABLE TO PACKAGES INTENDED FOR RETAIL SALE"** and
**Rule 3** names the packages it does not reach:

> **3. Applicability of the Chapter-** The provisions of this chapter shall not apply to-
> (a) packages of commodities containing quantity of more than 25 kilogram or 25 litre;
> (b) cement, fertilizer and agricultural farm produce sold in bags above 50 kilogram; and
> (c) packaged commodities meant for industrial consumers or institutional consumers

Definitions in **Rule 2(bb)** and **Rule 2(bc)**, both *as substituted*, and both requiring
the package to bear a declaration `not for retail sale`. Encoded as `R3-CHAPTER-II-SCOPE`.

Three things worth carrying forward:

- **The compilation does not name the notification** that substituted 2(bb) and 2(bc). It
  prints only *"(i) for clauses (bb) and (bc), the following clauses shall be substituted,
  namely"*. Semi-official source; the clause text is verbatim, the instrument is not in the
  corpus.
- **The Rules name no institutions.** Hotels, hospitals, airlines and railways are canonical
  in secondary commentary and appear **nowhere** in this corpus. Do not list them.
- **Rule 3(b) is subsumed by 3(a)** on this text — everything in bags above 50 kg is already
  above 25 kg — so it decides nothing that 3(a) has not already decided.

### The export limb — still [SOFT], and its old justification was wrong

The claim was that an export pack carrying no INR retail sale price is outside scope, making
a missing MRP `NOT_APPLICABLE`. **Rule 25 does not support that and points the other way:**

> **25. Restrictions on sale of export packages in India.-** An export package shall not be
> sold in India unless the manufacturer or packer has re-packed or relabeled the commodity in
> accordance with the provisions contained in Chapter II, and where any export package is
> sold in India without such re-packing or re-labeling, such package shall be liable to be
> seized in accordance with the provisions of the Act.

Rule 25 is Chapter IV and is not a scope exclusion. It makes Chapter II the standard an
export pack must be **brought up to** before it may be sold in India, and failing that a
seizure trigger. **`export package` is undefined anywhere in this compilation** — three
occurrences of the word, all in Rule 25 and its chapter heading.

What the limb actually rests on is a **territoriality** argument about the Legal Metrology
Act 2009, not Rule 3 and not Rule 25. That may well be right; it is not sourced here. The
limb stays **[SOFT]** and must not be encoded by citing Rule 25, which would put a rule
number behind a proposition it does not carry.
