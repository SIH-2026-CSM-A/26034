# PCCS Design System Specification
**Packaged Commodity Compliance System — Frontend Design Standards**
*Document Version: 1.0.0 (FNT-001)*  
*Target Domain: Legal Metrology (Packaged Commodities) Rules, 2011 Decision Support*

---

## 1. Visual Identity & Design Philosophy

PCCS is a statutory decision-support instrument used by Legal Metrology enforcement officers (Inspectors, Deputy Controllers, Controllers) across India. 

### Core Tenets
1. **Enforcement Authority, Not Startup SaaS**: 
   - Rejects frivolous trends: zero floating glassmorphic cards, zero multi-color gradient mesh backgrounds, zero decorative illustrations, zero playful confetti or gamified badges.
   - Embraces administrative gravity, precision, and forensic rigor: crisp structural dividers, dense data display, high contrast, and sober geometry.
2. **"It Recommends. It Never Decides."**:
   - The visual hierarchy must make it self-evident that system outputs are evidence-backed determinations subject to mandatory officer confirmation.
   - Findings provide exact Gazette references (e.g., `Rule 7 Table-I`, `Rule 6(1)(a)`) and attached evidentiary crops; the UI frames the human officer as the decision maker.
3. **Cardless Structural Layout**:
   - In accordance with the `frontend-work` and `hallmark` disciplines, the UI avoids "card soup" (grids of thick-bordered cards). Instead, boundaries are created with structural layout dividers, hairline borders (`1px solid #CBD5E1`), background tint changes, and systematic whitespace.
4. **Courtroom Admissibility (BSA §63(4))**:
   - Inspection views and generated packages are intended to support evidentiary proceedings under Bharatiya Sakshya Adhiniyam §63(4). Visual density and export layouts must print clearly to monochrome paper without loss of meaning.

---

## 2. Color Palette & Token Architecture

The color system uses high-contrast, accessible OKLCH-aligned semantic tokens mapped through Tailwind CSS variables.

### A. Primary Institutional Authority (Deep Ashoka Navy)
Used for primary navigation bars, major institutional headings, and key focus outlines:
- `gov-navy-950`: `#061324` (Deep obsidian navy)
- `gov-navy-900`: `#0B2545` (Official seal navy — primary brand anchor)
- `gov-navy-800`: `#133E6E` (Selected states, active chrome)
- `gov-navy-700`: `#1D4E89` (Dividers on dark, secondary action)
- `gov-navy-100`: `#E6EFF8` (Subtle selection tint)
- `gov-navy-50`: `#F0F6FC` (Workspace canvas tint)

### B. Structural Neutrals (Slate / Parchment)
Calm, neutral tones that maximize legibility and visual stamina for officers reviewing hundreds of package scans:
- `gov-slate-900`: `#0F172A` (Primary typography — high legibility)
- `gov-slate-700`: `#334155` (Secondary typography / metadata labels)
- `gov-slate-500`: `#64748B` (Muted hints / statutory citations)
- `gov-slate-300`: `#CBD5E1` (Hairline component boundaries)
- `gov-slate-200`: `#E2E8F0` (Structural layout borders)
- `gov-slate-100`: `#F1F5F9` (Subtle panel background)
- `gov-slate-50`: `#F8FAFC` (Root application surface)
- `white`: `#FFFFFF` (Inspector working surface canvas)

---

## 3. Explicit Verdict-Display Rules (Grayscale-Safe)

### A. The Critical Verdict Rule
> **MANDATORY REQUIREMENT:**
> `POTENTIAL VIOLATION` and `PASS` must **NEVER** be distinguishable by colour alone.
> Every verdict indicator must remain immediately and unmistakably interpretable in 100% grayscale, monochrome displays, and black-and-white photocopied evidence documents.

### B. Permitted Overall Verdicts (Standing Rule)
The system only emits three overall verdict states:
1. `PASS`
2. `REVIEW`
3. `POTENTIAL_VIOLATION`

*Prohibited copy*: Never use "violation confirmed", "non-compliant", "failed", or "illegal" as a finding.

### C. Tri-Fold Distinction Matrix

Each verdict state is differentiated across four concurrent dimensions:
1. **Explicit Text Label** (Bold, spelled out in uppercase)
2. **Distinct Geometric Icon / Symbol** (Circle Check vs. Triangle Alert vs. Octagon Cross)
3. **Distinct Border / Contour Geometry** (Thin solid pill vs. Dashed rectangle vs. Thick solid square)
4. **Contrast & Shading Pattern** (Light tint vs. Stippled midtone vs. High-contrast heavy frame)

| Dimension | `PASS` | `REVIEW` | `POTENTIAL VIOLATION` |
| :--- | :--- | :--- | :--- |
| **Primary Text Label** | **`PASS`** | **`REVIEW`** | **`POTENTIAL VIOLATION`** |
| **Geometric Symbol** | Circle + Checkmark (`✓`) | Triangle + Exclamation (`⚠`) | Stop Octagon + Cross (`✕`) |
| **Container Geometry** | Rounded Pill (`rounded-full`) | Soft Rectangle (`rounded-md`) | Sharp Square (`rounded-sm`) |
| **Border Specification** | `1px solid` hairline border | `2px dashed` warning border | `2px solid` heavy dark border |
| **Monochrome Appearance** | White/Light fill, thin hairline circle with tick | Medium gray/dashed frame, upright triangle | Heavy dark solid border, black badge fill with white cross |
| **Color Value (Normal)** | Text: `#065F46`, Bg: `#ECFDF5`, Border: `#059669` | Text: `#92400E`, Bg: `#FFFBEB`, Border: `#D97706` | Text: `#991B1B`, Bg: `#FEF2F2`, Border: `#DC2626` |
| **Screen Reader Announcement** | `"Verdict: PASS. Compliant with LMPC rules."` | `"Verdict: REVIEW. Requires human officer confirmation."` | `"Verdict: POTENTIAL VIOLATION. Discrepancy flagged."` |

### D. Per-Field Finding States
For individual package declarations under Rule 6(1):
- `PASS`: Requirement satisfied with verified proof.
- `REVIEW`: Ambiguity, low OCR confidence, or uncalibrated image requiring inspector confirmation.
- `POTENTIAL_VIOLATION`: Discrepancy detected against an explicit statutory clause.
- `INSUFFICIENT_EVIDENCE`: Image illegible, distorted, or missing reference object. **Crucial Rule: `INSUFFICIENT_EVIDENCE` is NOT `FAIL` / `POTENTIAL_VIOLATION`.**
- `EXEMPT`: Commodity carved out by statutory amendment (e.g. Medical Devices under MDR 2017).

---

## 4. Typography & Type Scale

The typography uses system-native clarity and monospace tabular precision.

### Type Families
- **Interface Body & Headings (`font-sans`)**: Inter, system-ui, -apple-system, Segoe UI, sans-serif. Clean, unpretentious humanist sans-serif with distinct numeral forms.
- **Data, Citations & Measurements (`font-mono`)**: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace. Used for:
  - Gazette numbers: `G.S.R. 629(E)`
  - Rule clauses: `Rule 6(1)(a)`, `Rule 7 Table-I`
  - Dimensions & Areas: `142.5 cm²`, `2.5 mm`
  - Prices & Currencies: `₹ 120.00`, `Rs. 0.25 / g`
  - Dates: `2026-09-05`
  - Cryptographic Hashes: `SHA-256` hash chains for evidence tamper verification.

### Type Scale
- **Display Heading (`text-2xl` / 24px, 700 bold, -0.02em tracking)**: Main application surface headers.
- **Section Heading (`text-lg` / 18px, 600 semibold, -0.01em tracking)**: Major panel & inspection column headers.
- **Subsection Title (`text-sm` / 14px, 600 semibold)**: Declaration group titles and metadata sections.
- **Body Text (`text-sm` / 14px, 400 normal, 1.5 line-height)**: Operational instructions, findings, descriptions.
- **Data / Tabular (`text-xs` / 12px, font-mono, tabular-nums)**: Metric values, timestamps, and audit records.
- **Caption / Meta (`text-[11px]` / 11px, 500 medium, text-gov-slate-500)**: Field footnotes, legal disclaimers.

---

## 5. Spacing Scale & Layout Grid

A strict 4px / 8px incremental grid is enforced throughout all components:

| Token | Pixels | Application |
| :--- | :--- | :--- |
| `--space-1` | `4px` | Badge internal padding, hairline gaps |
| `--space-2` | `8px` | Icon-to-text spacing, button horizontal padding |
| `--space-3` | `12px` | Table cell compact padding, input padding |
| `--space-4` | `16px` | Standard panel padding, form row spacing |
| `--space-6` | `24px` | Section gutters, cardless panel separation |
| `--space-8` | `32px` | Primary column gaps in inspection workbench |
| `--space-12` | `48px` | Major layout regions |

---

## 6. Layout Principles & Surface Boundaries

PCCS establishes two structurally independent operational surfaces:

### A. Officer Surface (`/officer/*`) — Owned by Vineeth
- **Target User**: Legal Metrology Inspector in the field or at testing laboratory.
- **Layout Architecture**:
  - Split Workbench Layout: Left viewport anchors the captured package image/artwork with pan-and-zoom inspection controls; Right viewport displays the declaration findings list and measurement calibration tools.
  - Quick-action triage bar at bottom with keyboard shortcuts (`Confirm`, `Override`, `Annotate`).
  - Strict absence of administrative controls.

### B. Admin Surface (`/admin/*`) — Owned by Rohan
- **Target User**: State Controller, Deputy Controller, System Auditor.
- **Layout Architecture**:
  - Full-width tabular and policy configuration layouts.
  - Hierarchy management (Inspector assignment, jurisdiction boundaries).
  - Gazette Rule Corpus maintenance and audit trail inspector.
  - Independent navigation and security boundaries from the officer route tree.

---

## 7. Component Conventions

1. **Cardless Surfaces**: 
   - Never nest cards within cards. Use subtle background contrast (`bg-white` over `bg-gov-slate-50`) bordered by `1px solid border-gov-slate-200`.
2. **Buttons & Controls**:
   - Rectangular, solid, 2px border or clean fill. Border-radius strictly capped at `4px` (`rounded-sm` or `rounded`).
   - Sizable tap/click targets (minimum 36px height).
3. **Data Density**:
   - High information density without visual noise. Compact tabular rows, clear vertical grid alignment.
4. **No Re-Drawn Chrome**:
   - No mock browser title bars, no simulated mobile phone skins, no fake window frames.

---

## 8. Interaction & The 8-State Discipline

In accordance with Hallmark and frontend engineering standards, all interactive components must explicitly accommodate all 8 states:

1. **Default**: Calibrated base appearance.
2. **Hover (`:hover`)**: Subtle background tint shift (`gov-slate-100`), never layout shift or bounce.
3. **Focus-Visible (`:focus-visible`)**: Instant 2px outline with 2px offset (`outline-gov-navy-900`), minimum 3:1 contrast against surrounding surface. **Never animate the focus ring appearance.**
4. **Active (`:active`)**: 1px downward translation or distinct depression shade.
5. **Disabled (`:disabled`)**: Opacity 50%, cursor `not-allowed`, zero pointer events, maintain readable contrast.
6. **Loading (`[data-state="loading"]`)**: Clear textual state ("Validating...", "Ingesting..."), subtle non-distracting spinner or pulse.
7. **Error (`[data-state="error"]`)**: Solid high-contrast error boundary, explicit human-readable recovery instruction.
8. **Success (`[data-state="success"]`)**: Quiet confirmation with icon and timestamp.

---

## 9. Accessibility & Statutory Compliance

- **WCAG 2.1 AA / AAA Compliance**: Contrast ratio for all text exceeds 4.5:1 (normal text) and 7:1 (large text / key statuses).
- **Non-Color Dependence (WCAG 1.4.1)**: Color is never the sole carrier of meaning.
- **Full Keyboard Operability (WCAG 2.1.1)**: Complete tab-sequence accessibility across all forms, tables, and split panes.
- **Print Optimization**: High-resolution print styling ensuring generated evidence exhibits, rule citations, and verdict stamps render cleanly in legal brief formats.
