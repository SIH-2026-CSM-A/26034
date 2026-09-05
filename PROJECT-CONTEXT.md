# PROJECT-CONTEXT.md

**Attach this to your brain chat alongside your setup doc and the coding standards.**

This exists because your AI has never seen an Indian product label, does not know what a Principal
Display Panel is, and will otherwise infer the domain from the words in your ticket. Inferring is
where invented rule numbers come from.

---

## 1. What the system does, in one paragraph

An officer photographs a packaged product, or the system ingests an e-commerce listing. The system
extracts the declarations that Indian law requires on that package, checks each one against the
Legal Metrology (Packaged Commodities) Rules, 2011, screens the image for signs of tampering, and
returns a per-field finding with the exact rule clause cited and the evidence attached. A human
officer then confirms, overrides or annotates. Nothing reaches an enforcement action without that
human step.

**It recommends. It never decides.** That distinction is the product.

---

## 2. Domain glossary

Your AI will guess at these otherwise, and its guesses will be plausible and wrong.

| Term | What it means here |
|---|---|
| **Legal Metrology** | The Indian legal framework governing weights, measures and packaged-goods declarations. Enforced by state Legal Metrology departments. |
| **LMPC Rules / PC Rules 2011** | The Legal Metrology (Packaged Commodities) Rules, 2011. The rulebook this system checks against. |
| **Declaration** | A statement the law requires printed on a package — name and address of the manufacturer, net quantity, MRP, date of manufacture, consumer care details, and others. Rule 6(1) lists them. |
| **PDP** | Principal Display Panel. The face of the package the consumer sees on a shelf. Its **area in cm²** determines the minimum font height required, so measuring it is not cosmetic — it decides compliance. |
| **MRP** | Maximum Retail Price. Must be printed inclusive of all taxes. Both `₹` and `Rs.` are acceptable forms. |
| **Net quantity** | The quantity of product, excluding packaging. Distinct from gross weight. |
| **Rule 6** | The declarations that must appear. |
| **Rule 7** | How large the letters and numerals must be. Banded by PDP area. See §5 — this is the single most misquoted rule in the project. |
| **Rule 8** | Where declarations must be placed. |
| **Rule 9** | The manner of declaration — legibility, contrast, language. |
| **Gazette / G.S.R.** | The official notification that enacts or amends a rule. `G.S.R. 629(E)` is a specific amendment. Every rule we encode must cite one. |
| **Controller / Deputy / Inspector** | The actual Legal Metrology enforcement hierarchy. Our roles model these, not generic admin/user tiers. |
| **BSA §63(4)** | Bharatiya Sakshya Adhiniyam — the Indian evidence law provision governing admissibility of electronic records. Our evidence package is shaped to satisfy it. |
| **ONDC** | Open Network for Digital Commerce. The pathway by which e-commerce listing data reaches us in production. |
| **Bhashini** | An Indian government language platform. We use it for **output localisation only** — translating our findings into regional languages. It is **not** an OCR system. Confusing the two is a technical error a judge can challenge. |

---

## 3. Repository and module map

One repository, `github.com/SIH-2026-CSM-A/26034`. Backend in `bck/`, frontend in `fnt/`.

```
bck/app/contracts/          Cross-module types. Imports nothing. ABHIRAM ONLY.
bck/app/core/               Auth, RBAC, config, cost ceilings. ABHIRAM ONLY.
bck/app/pipeline/           Ingestion and orchestration. ABHIRAM ONLY.
bck/alembic/                Migrations. ABHIRAM ONLY.
bck/app/modules/vision/         Preprocessing, PDP detection, OCR
bck/app/modules/extraction/     Spans to fields, normalisation
bck/app/modules/measurement/    Calibration, homography, ink extent
bck/app/modules/rules/          Rule store, evaluator, verdict assembly
bck/app/modules/tamper/         Field-localised forgery detection
bck/app/modules/evidence/       Hash chain, object store, exports
fnt/                        React frontend — officer surface and admin surface
datasets/                   Labelled corpus and eval harness
rules-corpus/               Immutable source gazettes. Add, never edit.
session-log/                One file per person.
```

**The import rule.** A module may import from `contracts` and `core` and itself. Nothing else.
Modules never import each other. `pipeline` composes modules. `contracts` imports nothing.
Enforced by import-linter in CI.

**Why it is this shape.** Layers nest *inside* modules — `router.py`, `service.py`,
`repository.py`, `schemas.py` live within each module directory rather than as top-level
`routes/`, `services/`, `repositories/` folders. With ten people owning directories, the
conventional horizontal layout would make every ticket a three-way ownership collision. If your AI
proposes reorganising into horizontal layers because "that's the standard structure", it has not
read this.

---

## 4. How data moves, end to end

Know this even if your ticket touches one step. It is how you tell whether your output is the right
shape for whoever consumes it.

1. **Capture** — an image, or a structured catalogue record from a listing. Both are first-class
   inputs; the listing path is not a screenshot with a parser bolted on.
2. **Quality gate** — blur, glare, completeness. A failure here returns a capture instruction to
   the officer, never a verdict.
3. **Preprocess** — deskew, curvature remap for bottles and cans, glare mask and inpaint, CLAHE on
   the lightness channel only so brand colours don't shift.
4. **PDP detection** — locates the principal display panel and yields its pixel area.
5. **OCR** — PaddleOCR over the panel; a character-whitelisted Tesseract second pass on MRP and net
   quantity, where a misread has legal consequences. Emits spans with polygons and confidences.
6. **Extraction** — spans classified to declaration types, spatially bound (distinguishing
   "Manufactured by" from "Marketed by"), values normalised to canonical units and ISO dates.
7. **Measurement** — only where calibration exists. Otherwise the field is marked
   `INSUFFICIENT_EVIDENCE` and routed to review.
8. **Rule evaluation** — deterministic. Takes normalised fields plus a rule-set version, returns a
   per-field state. Rule parameters are **snapshotted into the record**, never joined from a live
   table, so replaying an old scan gives the old answer.
9. **Tamper screening** — field-localised, scored per region, attached as evidence rather than fed
   into the verdict.
10. **Verdict assembly** — PASS / REVIEW / POTENTIAL VIOLATION.
11. **Evidence record** — immutable, hash-chained to the previous entry.
12. **Human confirmation** — an officer confirms, overrides or annotates.

Offline: steps 1–7 plus a cached rule subset run on device; results queue and re-validate on
reconnect. Offline is a P0 requirement, not a future enhancement.

---

## 5. Rule 7 — the fact most likely to be got wrong

If your ticket touches font height, read this and then ask for the gazette anyway.

**Current law since 1 January 2018**, per G.S.R. 629(E) dated 23 June 2017. Rule 7(2) is a **single
Table-I banded by PDP area**, applying to letters and numerals alike. The old Table-II no longer
exists.

| PDP area | Normal (mm) | Blown / formed / moulded (mm) |
|---|---|---|
| ≤ 50 cm² | 1.0 | 1.5 |
| 50–100 cm² | 1.5 | 3.0 |
| 100–500 cm² | 2.5 | 4.0 |
| 500–2500 cm² | 4.0 | 6.0 |
| > 2500 cm² | 6.0 | 6.0 |

Rule 7(3) requires a width-to-height ratio of at least 1/3, excepting the numeral `1` and the
letters `i`, `I`, `l`.

**Not current law:** a flat 1mm/2mm figure, or 1.7mm. Both appear in older project documents,
including `SIH26034_PSR.md` §3. If your AI quotes either, it read a stale file.

**Medical devices are carved out.** The LMPC Amendment Rules 2025 route numeral and letter height
for medical devices to the Medical Devices Rules, 2017 instead, disapply the Rule 33 relaxation,
and make PDP declaration non-mandatory. Table-I is therefore **not universal**.

---

## 6. The five constraints that never bend

1. **Verdicts are PASS / REVIEW / POTENTIAL VIOLATION.** Never "violation confirmed", never
   "non-compliant" as a finding. A human confirmation step always sits between output and
   enforcement. This applies to code, log lines, UI strings and documentation.
2. **Never a millimetre figure from an uncalibrated photograph.** Three modes: exact from pre-print
   artwork; a calibrated estimate with a stated confidence interval when a reference object is in
   frame; an explicit refusal otherwise. There is no fourth mode, and the API should make one
   unrepresentable.
3. **Every legal, factual or statistical claim traces to `SIH26034_Research_And_References.md`.**
   Not in the file, not asserted.
4. **Rule numbers and thresholds come from `rules-corpus/`, never from memory.** A rule without a
   gazette reference does not ship.
5. **No stubs, no placeholders, no fake data, no TODO comments in committed code.**

Two more that follow from these:

**`INSUFFICIENT_EVIDENCE` is not `FAIL`.** "We could not read it" and "it is not there" are
different findings with different consequences for a citizen. The five per-field states exist
precisely to keep them apart.

**No LLM and no agent loop in the verdict path.** It is deterministic and must be reproducible.
LangGraph and model calls belong in the copilot, which is a separate concern.

---

## 7. Reference constants worth having correct

Your AI will confidently produce wrong values for these.

| Constant | Value | Note |
|---|---|---|
| ID-1 card | 85.60 × 53.98 mm | ISO/IEC 7810 |
| ₹10 coin diameter | 27.0 mm | |
| EAN-13 symbol width | 37.29 mm | Nominal at 100% magnification. **Not 31.35 mm** — that is a module-width figure and a common error. |

---

## 8. Things already decided — don't re-propose them

Check `TODO.md` in the repo for the full cut list. The ones that come up most:

- **Not Supabase.** Free projects auto-pause after 7 days, and the deployment must be sovereign.
- **Not a custom rules DSL.** A small YAML format is correct for now. A DSL is this project's most
  likely over-engineering failure.
- **Not a separate vector database.** pgvector in the same Postgres handles a corpus this size.
- **Not cloud-primary OCR.** Self-hosted PaddleOCR is primary; cloud is an opt-in per-request
  escalation, disabled by default. Cloud-primary would make the offline path a second, weaker
  implementation and put product images outside the sovereign boundary.
- **Not Next.js.** SSR buys nothing for an authenticated internal tool.
- **Not two repositories.** One monorepo with CODEOWNERS and import-linter.
- **Python 3.11, not 3.12.** PaddlePaddle and several CV wheels lag.
