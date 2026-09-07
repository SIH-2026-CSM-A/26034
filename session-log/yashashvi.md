# Yashashvi — Session Log

## 2026-09-05 — MEA-001

- Implemented the physical measurement module for calibration, ink extent, and PDP area.
- Used Antigravity as the coding agent.
- Implemented the three measurement modes: Exact, Calibrated, and Refusal.
- Reverted the `param2` threshold to `30` to prevent false-positive calibrations.
- Implemented the domain ruling for `OTHER` package shapes: true 3D surface area cannot be determined defensibly from a single 2D photograph, so the implementation uses the refusal path rather than making an unsupported depth assumption.
- Added/updated tests for the measurement behaviour.
- All required checks passed, including pytest (`9 passed`).
- Raised the MEA-001 Pull Request and moved the ClickUp ticket to `review`.
- Noted that `MeasurementResult`, `MeasurementExact`, `MeasurementCalibrated`, and `MeasurementRefusal` are local stand-ins until `CTR-002` lands, matching the agreed approach.
- Implemented MeasurementExact for artwork paths and WCAG contrast ratio for Rule 9

## 2026-09-06 — MEA-004

- Implemented perspective distortion correction using Homography for physical measurements.
- Antigravity completed this phase, updating `detect_reference_object` to return `(scale, conf, H)`.
- Applied cv2.getPerspectiveTransform and cv2.warpPerspective before scale calculations for id_card and ean_13. coin_10 deliberately returns no homography — a circle under perspective gives no corner correspondences — so it returns scale only and callers skip rectification.
- Added method-specific confidence intervals tied to reference stability (1% for ID, 5% for Coin, 10% for EAN-13).
- Added a regression test proving the perspective warp round-trips. It does not prove absolute measurement accuracy: baseline and result run the same code path, so a systematic scale error cancels.
- Completed MEA-004 using the Gemini AI agent.

## 2026-09-07 — MEA-005
- Replaced the global `pdfplumber` mock with a true `reportlab` round-trip test for vector PDF ingestion.
- Moved the `pdfplumber` import to the module top-level so missing dependencies crash loudly instead of surfacing as false measurement refusals.

## 2026-09-07 — MEA-006
- Relaxed margin measurement constraints to ge=0 for MeasurementMarginExact and MeasurementMarginCalibrated to permit zero margins on flush declarations.
- Retained gt=0 constraints on other measurement types.
- Successfully falsified and passed test_zero_margin_is_valid.

## 2026-09-07 — MEA-006 (Rework)
- Dropped contract types in favor of main's sibling implementation.
- Removed margin clamping to preserve negative overlap distances.
- Added calibrated zero-margin test and overlap falsification tests.

## 2026-09-07 — MEA-006 (Final)
- Dropped local contract modifications; inheriting main's MeasurementMarginExact and MeasurementMarginCalibrated.
- Removed max(0) clamping in measure_margins to correctly preserve and return negative overlap distances.
- Floored calibrated confidence_interval at the pixel quantisation limit (1 pixel's mm equivalent) to prevent false-certainty 0.0 intervals.
- Added test_zero_margin_calibrated_path and test_margin_overlap_is_negative.
- NOTE: This PR strictly addresses measurement logic and does not restore Rule 8. Wiring the orchestrator is a separate ticket.

## 2026-09-07 — MEA-006 (Overlap Refusal)
- Updated margin slicing to extend to the bounding box center, allowing detection of active ink overlaps.
- Intercepted negative margin distances in the loop, emitting MeasurementRefusal for overlaps.
- Added confidence interval floor at mm_per_pixel.

## 2026-09-07 — MEA-007 (Coin Perspective Fix)
- Resolved E501 formatting lint errors by structuring MeasurementRefusal strings.
- Fixed synthetic test focal length to correctly match application's image-diagonal assumption.
- Corrected homography math in services.py to properly compute the optical center shift (dx, dy) and apply an inverse translation matrix, achieving true perspective scale recovery.

## 2026-09-08 — MEA-011
- Replaced MeasurementRefusal with MeasurementMarginOverlapExact and MeasurementMarginOverlapCalibrated for negative clearances in measure_margins.
- Used Antigravity to safely inject and revert defects to falsify test boundaries (flush limits, type dispatch, and magnitude constraints).
- Refactored test_margin_overlap_is_negative to verify both artwork and calibrated paths using literal expected values.
- Verified all tests pass cleanly.

## 2026-09-08 — MEA-012
- Exposed measure_artwork_ink_extent and calculate_artwork_pdp_area through measurement/__init__.py to provide a public service-level entry point.
- Refactored test_artwork.py to target the public API, ensuring the functions are visible to the rest of the application.
- Retained parse_pdf_geometry as an internal helper.
- Passed all import boundary checks and test verifications.

## 2026-09-08 — MEA-013
- Addressed MEA-007 technical debt.
- Renamed PRIOR_CONFIDENCE_ELLIPSE_FIT to MIN_ELLIPSE_FIT_SCORE and moved it out of the prior block.
- Updated coin_10 confidence interval to scale inversely with fit_confidence.
- Extracted tilt sign-ambiguity logic into resolve_coin_tilt_ambiguity and added test_resolve_coin_tilt_ambiguity.
- Successfully injected and caught a defect in the tilt logic to falsify test_coin_oblique_synthetic_geometry.
- Documented the geometric expectation assumption in the synthetic test docstring.
- FINDING: Empirical evaluation of contour selection against the staging dataset could not be performed because the 26034-dat worktree is not present on this local machine.
