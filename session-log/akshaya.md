# TAM-002: Tamper Module Wiring & Evaluation

- **Public Entry Point**: Exposed `detect_tampering(image: np.ndarray, spans: list[ExtractedSpan]) -> list[TamperDetectionResult]` in `app.modules.tamper` (`__init__.py`). Designed for orchestrator composition without modifying `pipeline/orchestrator.py`.
- **False-Positive Evaluation**: Evaluated against all 12 uncalibrated dataset captures under `datasets/annotations/{food,cosmetics}/` (6 SKUs, front and back, untampered). Total false-positive count: **0**.
- **Priors Status**: `PRIOR_CONFLICTING_MRP_PROBABILITY` (0.95) and `PRIOR_STICKER_OVERLAY_PROBABILITY` (0.85) remain unchanged as uncalibrated expert priors. The untampered corpus provides no empirical grounds for probability adjustment.
- **Claim Boundary Notice**: All captures are uncalibrated (`reference_object.present` is false, height fields null). No Rule 7 letter-height accuracy figures are supported or quoted from this corpus. Tamper detection metrics are strictly segregated from measurement accuracy paths.
