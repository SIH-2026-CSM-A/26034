# rules-corpus

Immutable source documents. **Add files, never edit them.** Every rule encoded in
`bck/app/modules/rules/` must cite a file in this directory by name, and a rule with no
`gazette_ref` must fail to load.

There is no automated sync and there must not be one. `consumeraffairs.gov.in`,
`doca.gov.in` and `egazette.gov.in` all refuse programmatic access. These were downloaded
by hand and are updated by hand when an amendment lands. **Do not build a fetcher.**

## Files

| File | Notification | Date | What it does |
|---|---|---|---|
| `LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf` | — | to 31.10.2021 | Full consolidated rules text. Maharashtra Legal Metrology compilation by S Y Mundhe, Assistant Controller. Semi-official. |
| `GSR-629E__2017-06-23__amendment-rules-2017.pdf` | G.S.R. 629(E) | 23.06.2017, w.e.f. 01.01.2018 | The Rule 7 rewrite. Unified Table-I banded by PDP area; former Table-II removed. |
| `GSR-722E__2023-10-06__amendment-rules-2023.pdf` | G.S.R. 722(E) | 06.10.2023 | Combination Package and Group Package definitions. |
| `GSR-778E__2025-10-23__medical-devices-mdr-2017.pdf` | G.S.R. 778(E) | 23.10.2025, gazetted 24.10.2025 | Medical devices harmonised with the Medical Devices Rules, 2017. |
| `GSR-881E__2025-12-02__pan-masala.pdf` | G.S.R. 881(E) | 02.12.2025 | Second Amendment Rules 2025 — pan masala. |
| `GSR-128E__2026-02-13__country-of-origin-ecommerce-filter.pdf` | G.S.R. 128(E) | 13.02.2026 | Country-of-origin filter on e-commerce websites. |
| `GSR-312E__2026-04-27__country-of-origin-second-amendment.pdf` | G.S.R. 312(E) | 27.04.2026, **effective 01.07.2027** | Country of origin, second amendment. Not yet in force. |
| `DoCA-FAQ__2017__gsr-629E-implementation.pdf` | — | 2017 | FAQs on implementing G.S.R. 629(E). |

## Known gaps

**Consolidated e-book (amended to 24.12.2024) — not captured.** `doca.gov.in/lm-ebook/`
returns "Access denied" for both the page and the direct PDF. Consequence: no consolidated
text covering November 2021 to date. The individual gazettes above cover 2017 and
2023–2026, leaving an unverified window between 31.10.2021 and 06.10.2023. Retry from a
different network, or look for a recent consolidation hosted by another state Legal
Metrology department.

**DoCA Legal Metrology FAQ, 11.11.2025 — not captured.** Two clarifications we rely on are
sourced from it via three independent secondary reports (TaxGuru, Legality Simplified, AZB
Partners) rather than from the PDF itself:

- Q3 — retail sale price may be declared using either `₹` or `Rs.`
- Q12 — a complete name and address of the brand owner with "Marketed by" or
  "Brand Owner" satisfies Rule 6(1)(a)

Status **[SOURCED]**, not [VERIFIED]. Both are encoded in EXT-001. Replace this note when
the primary PDF is captured. The 2017 FAQ above is a different, older document and is not
the source for these two claims.

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

**Rule 7(3)** — width shall be not less than one third of height, except the numeral "1"
and the letters i, I and l.

**Rule 7(4) — PDP area computation.** Rectangular package: height × width of the display
side. Cylindrical or nearly cylindrical: 40% of (height × circumference). Any other shape:
40% of total surface area. Excluding top, bottom, flanges at top and bottom of cans, and
the shoulder and neck of bottles and jars.

**Rule 7(5) exception** — except for net weight, retail sale price, date of expiry or best
before or use by date, and consumer care details, sub-rules (1) to (4) do not apply where
the same information is also required under any other law in force.

**Medical devices carve-out** — G.S.R. 778(E) routes numeral and letter height for medical
devices to the Medical Devices Rules, 2017, disapplies the Rule 33 relaxation, and makes
PDP declaration non-mandatory. **Table-I is therefore not universal.**

A flat 1mm/2mm figure and a 1.7mm figure both appear in older project documents, including
`SIH26034_PSR.md` §3. Neither is current law. That file is not a source for rule facts.

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
and must not be encoded.

F18 is therefore two checks: is a unit sale price declared, and is it declared on the
correct unit basis for the net quantity.

Confirmed in the Maharashtra compilation and against the DoCA e-book text. The e-book PDF
itself is not in this directory — see Known gaps.

## Other provisions worth encoding

- **Rule 8(1)** — the space around the quantity declaration must be free of printed
  information: above and below by at least the height of the numeral, left and right by at
  least twice that height. Geometrically measurable from an image.
- **Rule 6(1)(a) Explanation III** — for food articles, the Food Safety and Standards Act,
  2006 governs the manufacturer declaration instead.
- **Rule 6(1)(d) proviso** — for cosmetics, the Drugs and Cosmetics Rules, 1945 govern the
  date declaration. Relevant: cosmetics is the secondary demo category.
- **Rule 9(3)** — an outer container or wrapper must carry all declarations unless it is
  transparent and the inner declarations are readable through it. No inner declarations are
  required if the outer package carries all of them.
- **Rule 13(2)–(3)** — unit selection: below 1 kg declare in grams, below 1 m in
  centimetres, below 1 litre in millilitres; at or above those thresholds use the larger
  unit.
- **Rule 26** — packages of 10 g or 10 ml or less are exempt, except tobacco products.
  Medical devices declared as drugs get no exemption.
- **Rule 31(2)** — in an advertisement stating retail sale price, the net quantity font
  size must equal that of the retail sale price.

## Scope note on the 2026 amendments

G.S.R. 128(E) and G.S.R. 312(E) concern **country of origin and e-commerce display**, not
general labelling. G.S.R. 312(E) takes effect **01.07.2027** and is therefore not currently
in force — encode it with `effective_from: 2027-07-01` so it evaluates correctly against a
scan date, rather than omitting it.
