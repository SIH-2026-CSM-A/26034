# datasets — Compliance Evaluation Dataset & Evaluation Harness

**Owner:** Aashritha (@aashrithareddybodanampally-byte)  
**Ticket:** `feature/26034-DAT-001-corpus-eval`  
**Purpose:** Labelled packaging image corpus ground-truth annotations, labelling schema, and offline evaluation harness under the Legal Metrology (Packaged Commodities) Rules, 2011 (LMPC 2011).

---

## 1. Raw Imagery Storage & Acquisition

Raw image binaries (`*.jpg`, `*.jpeg`, `*.png`, `*.webp`, etc.) are deliberately **excluded from Git tracking** per `.gitignore` to maintain repository performance and avoid binary bloat.

- **Authoritative Raw Image Repository:**  
  [Shared Google Drive: 26034 FMCG Packaging Image Corpus](https://drive.google.com/drive/folders/1_REPLACE_WITH_SHARED_DRIVE_FOLDER_ID_SIH26034)
- **Local Download Path:**  
  `datasets/raw/<category>/<sku_id>/<sample_id>.<ext>`
- **Tracking Policy:**  
  Only machine-readable ground-truth annotations (`datasets/annotations/**/*.json`), schema definitions (`schema.py`, `schema.json`), evaluation code (`datasets/eval/`), and documentation are version-controlled in Git. Each annotation record links to the corresponding raw image filename and its canonical SHA-256 cryptographic checksum to preserve the BSA 63(4) evidence integrity chain.

---

## 2. SKU Breakdown

The evaluation dataset focuses on the two primary consumer sectors with the highest volume of packaged commodities and enforcement frequency under LMPC 2011: **Packaged Food** (primary evaluation track) and **Cosmetics** (secondary evaluation track).

### Packaged Food SKUs (10 SKUs)

| SKU Identifier | Common Name | Packaging Substrate | Packaging Form | PDP Band (cm²) | Primary Verification Focus |
|---|---|---|---|---|---|
| `food_parle_g_biscuits` | Parle-G Glucose Biscuits | BOPP Flexible Film | Flow-wrap pouch | $A \le 50$ (Small PDP) | Rule 7 minimum numeral/letter height ($1.0\text{ mm}$), crowded text |
| `food_amul_butter_100g` | Amul Butter Pasteurized | Paperboard Carton | Folding box | $50 < A \le 100$ | Clean rectangular layout, net weight declaration, MRP format |
| `food_tata_salt_1kg` | Tata Salt Vacuum Evaporated | Multi-layer Poly Pouch | Pillow pouch | $100 < A \le 500$ | Rule 6(11) Unit Sale Price (`Rs. __ per kg` threshold), matte finish |
| `food_maggi_noodles_70g` | Maggi 2-Minute Masala Noodles | Flexible Laminate Film | Pillow flow-wrap | $50 < A \le 100$ | Wrinkled substrate, Unit Sale Price (`Rs. __ per g`), FSSAI dual declaration |
| `food_haldirams_bhujia_150g` | Haldiram's Nagpur Aloo Bhujia | Metallized BOPP/PET | Stand-up pouch | $100 < A \le 500$ | Multi-script text (Devanagari Hindi & Latin English), specular glare |
| `food_coca_cola_can_300ml` | Coca-Cola Original Taste | Aluminum Can | Cylindrical two-piece | $50 < A \le 100$ | Rule 7(4) cylindrical PDP area calculation ($0.40 \times H \times C$), curved surface |
| `food_dabur_honey_250g` | Dabur 100% Pure Honey | Glass Jar | Hexagonal/round jar | $50 < A \le 100$ | Neck & shoulder exclusion from PDP area, cylindrical distortion |
| `food_kissan_jam_500g` | Kissan Mixed Fruit Jam | Glass Jar with Paper Label | Cylindrical jar | $100 < A \le 500$ | Curved label, Rule 6(1)(n) consumer care contact extraction |
| `food_lays_chips_50g` | Lay's India's Magic Masala | Metallized Pillow Pouch | Nitrogen-flushed pouch | $100 < A \le 500$ | High specular glare, non-planar reflective surface, crinkle distortion |
| `food_mtr_gulab_jamun_tin_1kg` | MTR Ready-to-Eat Gulab Jamun | Metal Tin / Canister | Cylindrical rigid tin | $100 < A \le 500$ | Embossed / printed lid vs body label, date of manufacture parsing |

### Cosmetics & Personal Care SKUs (4 SKUs)

| SKU Identifier | Common Name | Packaging Substrate | Packaging Form | PDP Band (cm²) | Primary Verification Focus |
|---|---|---|---|---|---|
| `cosmetics_nivea_creme_tin_50ml` | Nivea Creme Classic Blue Tin | Aluminum Tin | Circular shallow tin | $A \le 50$ (Small PDP) | Circular surface area PDP calculation, Drugs & Cosmetics Rules date proviso |
| `cosmetics_himalaya_face_wash_100ml` | Himalaya Purifying Neem Face Wash | Polyethylene (PE) | Squeeze tube | $50 < A \le 100$ | Tapered cylindrical/elliptical surface, crimp area exclusion, small font size |
| `cosmetics_dettol_soap_75g` | Dettol Original Bathing Bar | Coated Paper Wrapper | Flow-wrapped bar | $50 < A \le 100$ | Rectangular faces, net weight when packed, manufacturer vs marketer address |
| `cosmetics_parachute_coconut_oil_200ml` | Parachute 100% Pure Coconut Oil | Rigid HDPE Bottle | Cylindrical bottle | $50 < A \le 100$ | Cylindrical curvature, vertical text alignment, numeral height compliance |

---

## 3. Principal Display Panel (PDP) Categories & Legal Metrology Issues

### 3.1 PDP Size Categories & Legal Thresholds (Rule 7, Table-I)

Under G.S.R. 629(E) (effective 01.01.2018), minimum numeral and letter heights are banded strictly by PDP surface area:

| Band Identifier | PDP Area ($A$) | Min Height Normal (mm) | Min Height Blown/Moulded (mm) | SKU Representation in Corpus |
|---|---|---|---|---|
| `A_le_50` | $A \le 50\text{ cm}^2$ | $1.0\text{ mm}$ | $1.5\text{ mm}$ | `food_parle_g_biscuits`, `cosmetics_nivea_creme_tin_50ml` |
| `50_lt_A_le_100` | $50 < A \le 100\text{ cm}^2$ | $1.5\text{ mm}$ | $3.0\text{ mm}$ | `food_amul_butter_100g`, `food_maggi_noodles_70g`, `food_coca_cola_can_300ml`, `cosmetics_dettol_soap_75g` |
| `100_lt_A_le_500` | $100 < A \le 500\text{ cm}^2$ | $2.5\text{ mm}$ | $4.0\text{ mm}$ | `food_tata_salt_1kg`, `food_haldirams_bhujia_150g`, `food_kissan_jam_500g`, `food_mtr_gulab_jamun_tin_1kg` |
| `500_lt_A_le_2500`| $500 < A \le 2500\text{ cm}^2$ | $4.0\text{ mm}$ | $6.0\text{ mm}$ | Multi-pack / bulk cartons (future expansion) |
| `2500_lt_A` | $A > 2500\text{ cm}^2$ | $6.0\text{ mm}$ | $6.0\text{ mm}$ | Commercial sacks / corrugated shippers |

- **Small PDP ($A \le 50\text{ cm}^2$):** Critical test for optical character recognition resolution and spatial localization. Letter height measurements require a reference calibration object (e.g. INR 5 coin) or pre-print artwork. Uncalibrated photos must return `INSUFFICIENT_EVIDENCE` (Rule Standing Constraint #2).
- **Large & Cylindrical PDPs:** Evaluates cylindrical projection compensation ($0.40 \times \text{height} \times \text{circumference}$) and exclusion of neck/flange/chime areas per Rule 7(4).

### 3.2 Known Legal Metrology Defect & Issue Test Cases in Corpus

The evaluation dataset incorporates real-world compliance defects to benchmark decision-support accuracy:

1. **`missing_month_year` (Rule 6(1)(d)):** Commodity pre-packed without month and year of manufacture or packing, or where dates are printed with ambiguous single-number formatting without clear indicators.
2. **`non_compliant_usp_unit` (Rule 6(11)):** Unit Sale Price declared on an incorrect unit basis (e.g. declaring `Rs. __ per 100g` or `Rs. __ per packet` instead of the statutory `Rs. __ per g` when net weight $< 1\text{ kg}$).
3. **`missing_unit_sale_price` (Rule 6(11)):** Complete absence of the mandatory Unit Sale Price declaration on applicable retail packages.
4. **`font_below_minimum` (Rule 7 Table-I):** Printed numerals or letters measuring below statutory minimum thresholds for the package's PDP area.
5. **`missing_consumer_care` (Rule 6(1)(n)):** Absence of mandatory consumer grievance details (missing email address, telephone number, or contact designation).
6. **`incomplete_address` (Rule 6(1)(a)):** Generic city-only mention without complete postal address, or failure to distinguish "Manufactured by" from "Marketed by" / "Brand Owner".
7. **`obscured_free_space` (Rule 8(1)):** Surrounding typography or graphics intruding into the statutory clearance zone surrounding the net quantity declaration (height of numeral above/below, twice height left/right).

---

## 4. Naming Conventions & Condition Tags

### 4.1 Identifiers & File Structure

- **SKU Identifiers:** `^(food|cosmetics)_[a-z0-9_]+$`  
  *Examples:* `food_parle_g_biscuits`, `cosmetics_himalaya_face_wash_100ml`
- **Sample Image Filename:** `<sku_id>_<sample_index>.<ext>`  
  *Examples:* `food_parle_g_biscuits_001.jpg`, `cosmetics_nivea_creme_tin_50ml_001.jpg`
- **Annotation JSON Filename:** `<sample_id>.json`  
  *Path:* `datasets/annotations/<category>/<sample_id>.json`

### 4.2 Condition & Difficulty Tags

Every sample record is tagged with one or more condition descriptors to evaluate OCR and extraction resilience under difficult real-world capture conditions:

| Tag | Description | Evaluation Challenge |
|---|---|---|
| `small_pdp` | PDP surface area $A \le 50\text{ cm}^2$ | Low character pixel count, high crowding |
| `glare` | Specular reflection from metallic, gloss, or transparent film | Saturated whiteout regions occluding declaration spans |
| `curved` | Cylindrical, conical, or spherical package substrate | Tangential foreshortening, non-linear character distortion |
| `multiscript` | Dual or multiple scripts (e.g., Devanagari Hindi + English) | Multilingual OCR script routing and token grouping |
| `missing_month_year` | Date of manufacture/packing omitted or defective | Rule 6(1)(d) negative verification test case |
| `flexible_pouch` | Crinkled, warped, or non-rigid substrate | Line break fragmentation and irregular baseline geometry |
| `crowded` | High-density typography adjacent to mandatory fields | False spatial binding and segmentation errors |
| `calibrated` | Frame contains verified fiducial/coin reference target | Calibrated physical measurement pipeline verification |
| `uncalibrated` | Natural in-situ capture without reference target | Standing rule enforcement: must yield `INSUFFICIENT_EVIDENCE` |
| `low_contrast` | Text color low contrast against background substrate | Binarization and edge detection degradation |

---

## 5. Ground-Truth Schema & Evaluation Harness Quickstart

- **Schema Definition:** See [`schema.py`](file:////wsl.localhost/Ubuntu/home/aashritha_reddy/Ps_034/datasets/schema.py) (Pydantic v2) and [`schema.json`](file:////wsl.localhost/Ubuntu/home/aashritha_reddy/Ps_034/datasets/schema.json) (JSON Schema Draft 2020-12).
- **Run Offline Evaluation Harness:**
  ```bash
  python -m datasets.eval.harness --annotations datasets/annotations --test-run
  ```
- **Compute Precision & Recall with Predictions:**
  ```bash
  python -m datasets.eval.harness --annotations datasets/annotations --predictions predictions.json --output report.json
  ```
