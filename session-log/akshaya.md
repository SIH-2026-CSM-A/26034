# Session Log - Akshaya
## Date: September 2026
### Ticket VIS-001: Vision Preprocessing Module Optimization
- **Vectorized `remap_curvature`**: Replaced the $O(h \times w)$ raw Python double for-loop with NumPy vectorization (`np.arange`, `np.clip`, `np.sin`, `np.tile`) to ensure high-resolution images ($3000 \times 4000$) process comfortably within performance targets.
- **Added Performance Regression Test**: Implemented `test_remap_curvature_performance_at_realistic_resolution` to guard against latency regressions.
- **Verification**: All linter checks, formatting checks, import boundary contracts (`lint-imports`), and pytest suites pass cleanly.

- Rebased branch onto main cleanly
- Added missing coverage tests for detect_pdp
- Updated Tesseract whitelist comment

## Session - VIS-003: Robust PaddleOCR 3.x Parser & Strict Confidence
- Restored VIS-001 historical records (remap_curvature vectorisation, performance regression tests, rebase notes).
- Implemented strict parsing for PaddleOCR 3.x results without 1.0 confidence fallbacks.
- Configured frame-level provenance (`region_id="frame"`).

<<<<<<< HEAD
### Ticket TAM-001: Tamper Detection (Dual-MRP & Sticker Overlay)
- **Tamper Domain Model**: Implemented `TamperDetectionResult` in `bck/app/modules/tamper/domain.py` with probability bounded by `ge=0.0, le=1.0` and verified `0.0` boundary validation.
- **Conflicting MRP Detection**: Implemented `detect_conflicting_mrps` in `bck/app/modules/tamper/detector.py` to identify conflicting MRP values across spans.
- **Sticker Overlay Detection**: Implemented concise `detect_sticker_overlay` in `bck/app/modules/tamper/detector.py` using OpenCV edge/gradient analysis with isolated module-level constants (`CV_CANNY_LOW=50`, `CV_CANNY_HIGH=150`, `CV_SHADOW_GRADIENT=30.0`, `CV_PADDING=10`).
- **Unit & Integration Tests**: Added 8 comprehensive test cases in `bck/tests/modules/tamper/test_detector.py` covering clean prints, sticker hard edges, printed borders, conflicting MRPs, matching MRPs, single/no MRPs, and zero-bound probability validation.
- **Verification**: 
  - Pytest: 645 passed, 33 skipped cleanly (0 failures, 0 errors).
  - Ruff: `ruff check .` and `ruff format --check .` pass with 0 errors.
  - Import Linter: `lint-imports` passes with 3 kept, 0 broken contracts.

## Date: September 2026 - TAM-001 Rework
- **Sticker Overlay False Positive Fix**: Refactored boundary analysis in `detect_sticker_overlay` to check outer border margin strip rather than whole interior crop, preventing text glyphs (e.g. `cv2.putText` text) from triggering false positives. Added `test_detect_sticker_text_glyphs_clean_print` and verified falsification proof (RED on whole crop analysis, GREEN on boundary analysis).
- **Rule 6(11) Anchor & Unit Sale Price Exclusion**: Enforced explicit MRP anchors (`MRP`, `M.R.P.`, `Maximum Retail Price`, or exact region ID) and excluded unit sale prices (`per kg`, `per 10g`, unit basis, discounts). Fixed number extraction to isolate price digits directly following anchor rather than concatenating non-MRP numbers (e.g. `MRP Rs. 100 Net Wt 250g` extracts `100.00`).
- **Provider Overlap Grouping**: Grouped candidate MRP spans by spatial bounding box overlap (`_spans_spatially_overlap`). Overlapping spans from different OCR engines (e.g. `PADDLEOCR` vs `TESSERACT`) are treated as readings of the same physical site and do not trigger false conflicts.
- **Uncalibrated Priors & Constants**: Extracted module-level probability constants (`PRIOR_CONFLICTING_MRP_PROBABILITY = 1.0`, `PRIOR_STICKER_OVERLAY_PROBABILITY = 0.85`) with explicit docstrings explaining they are uncalibrated priors.
- **Boundary Validation & Precision Assertions**: Replaced `test_tamper_result_zero_bounds` with real boundary validation tests asserting `ValidationError` for `-0.1` and `1.1` probabilities. Updated `test_detect_sticker_hard_edge` to assert `0.85` exact probability.
- **Empty List Semantics & Precondition Validation**: Documented that `[]` signifies "no tampering detected". Added `ValueError` check for empty/None image inputs.
- **File Permissions**: Set `chmod 644` on `detector.py`, `domain.py`, and `test_detector.py`.
- **Verification**: `ruff check .`, `ruff format --check .`, `lint-imports` (3 kept, 0 broken), and 12 tamper tests pass cleanly.

## Date: September 2026 - TAM-001 Probability Calibration & Heuristics Documentation
- **Probability Prior Calibration**: Removed `1.0` certainty probability from `PRIOR_CONFLICTING_MRP_PROBABILITY`, setting it to `0.95` as absolute certainty is mathematically invalid for OCR evidence evaluation. Added explicit docstrings identifying all probability outputs as uncalibrated expert priors.
- **Heuristic Parameter Documentation**: Documented computer vision border mask gradient thresholds (`CV_CANNY_LOW`, `CV_CANNY_HIGH`, `CV_BORDER_SHADOW_GRADIENT`, `CV_BORDER_MARGIN`) as uncalibrated empirical defaults awaiting dataset tuning against SIH research references.
- **Test Suite Updates**: Updated `test_detect_conflicting_mrps_conflicting_mrps` to assert `0.95` (`PRIOR_CONFLICTING_MRP_PROBABILITY`).

## Date: September 2026 - TAM-001 Directional Boundary Analysis & Mandatory MRP Anchor Fix
- **Directional Step-Discontinuity Analysis**: Refactored `detect_sticker_overlay` to compare mean pixel intensity just inside vs just outside the perimeter borders across the four crop sides. Added `test_detect_sticker_neighboring_text_clean` verifying clean return `[]` when neighboring text ("Net Wt 250g") is rendered ~12px below MRP line. Demonstrated falsification proof (RED failure on old detector, GREEN on directional analysis).
- **Mandatory Anchor MRP Extraction**: Removed quantifier star (`*`) from regex prefix anchor group in `_extract_mrp_value` so that the MRP/currency anchor is mandatory before price digits. Added `test_extract_mrp_value_reversed_order` verifying `"Net Wt 250g MRP Rs. 100"` extracts `100.00` instead of `250.00`. Demonstrated falsification proof (RED failure on old regex `AssertionError: '250.00' == '100.00'`, GREEN on mandatory anchor).
- **Verification**: `ruff check .`, `ruff format --check .`, `lint-imports` (3 kept, 0 broken), and 14 tamper tests pass cleanly.
=======
## Session - VIS-004: PaddleOCR 3.7.0 & Offline Setup Protocol
- **PaddleOCR 3.7.0 API Migration**: Standardized PaddleOCR initialization in `bck/app/modules/vision/ocr.py` to use `text_detection_model_dir`, `text_recognition_model_dir`, `use_textline_orientation=False`, `device="cpu"`, and `ocr.predict(image)`, completely eliminating legacy PaddleOCR 2.x parameters (`cls=False`).
- **PDP Empty-Detection Graceful Fallback**: Verified in `bck/app/modules/vision/pdp.py` that missing, unset, or non-existent `PDP_WEIGHTS_PATH` values return full-image bounds `(0, 0, w, h)` with `confidence=0.0` without falling back to COCO weights or network downloads. Added comprehensive unit tests in `bck/tests/modules/vision/test_pdp.py`.
- **Environment Configuration**: Updated `bck/.env.example` with all four required offline environment variables (`PDP_WEIGHTS_PATH`, `OCR_DET_MODEL_DIR`, `OCR_REC_MODEL_DIR`, `TESSERACT_TESSDATA_DIR`) using real path examples and explicit documentation that blank values are treated as unset.
- **Offline Model Setup Documentation**: Expanded `bck/app/modules/vision/README.md` with complete CLI setup protocols, model storage footprint summary (~25.8 MB total), Tesseract apt installation, tessdata path export, and PaddleOCR v4 tarball extraction steps.
- **Verification**: Executed full verification suite (`ruff check .`, `ruff format --check .`, `lint-imports`, and `pytest` with 686 passed, 32 skipped).
>>>>>>> 24d3e2a (feat(vision): bootstrap local weights and 3.7.0 PaddleOCR API (VIS-004))
