import numpy as np

from app.modules.vision.pdp import detect_pdp


def test_zero_spans_refusal_proof():
    blank_image = np.zeros((100, 100, 3), dtype=np.uint8)
    try:
        result = detect_pdp(blank_image)
        assert len(result) == 0, "Expected 0 spans"
    except ValueError as e:
        assert "No PDP detected" in str(e) or "not found" in str(e).lower()
