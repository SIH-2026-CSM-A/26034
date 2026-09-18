"""Fixtures every test package shares.

One thing lives here: a stand-in for the third model call ``run_image_scan`` makes. Panel
detection and OCR are replaced test by test, because neither model is present in CI; the
constrained Tesseract re-read of price and quantity is the same kind of call and the
``tesseract`` binary is no more present than the weights are. Any test anywhere that drives
the image path — ``tests/pipeline``, the vendor self-scan, a category confirmation — would
otherwise reach it, and a scan that raises there is a scan with no verdict.

The stand-in agrees with the first reading, so it moves no finding. A test about the
re-read patches ``pytesseract`` underneath the real :func:`arbitrate_field_declaration`
instead — see ``tests/pipeline/test_evidence_doubts.py``.
"""

import pytest


@pytest.fixture(autouse=True)
def second_reading_agrees(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.vision.ocr import arbitrate_mrp

    def agree(image, primary_span, tessdata_dir=None):
        return arbitrate_mrp(
            primary_span.text,
            primary_span.text,
            span_id=primary_span.span_id,
            primary_reading=primary_span,
        )

    monkeypatch.setattr("app.pipeline.orchestrator.arbitrate_field_declaration", agree)
