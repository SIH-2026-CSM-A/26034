"""Pre-print artwork is evaluated exactly: the one path on which a millimetre is a fact.

The PDF is made here with reportlab at a stated physical size, rendered by the real
``rasterise_artwork``, and read through the real binding, segmentation, measurement and
evaluation. Only OCR is replaced, and it is replaced by the PDF's own characters — the text
the file contains, at the pixel boxes the render puts them at — so nothing in the test
guesses where the print is.
"""

import io
from datetime import UTC, datetime
from unittest.mock import patch

import pdfplumber
import pytest
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.contracts import DeclarationField, EvidenceProvider, ExtractedSpan, FieldState
from app.modules.measurement import PackageShape
from app.modules.rules import ProductCategory
from app.pipeline.orchestrator import (
    ARTWORK_RASTER_DPI,
    ArtworkRefusal,
    ImageScanResult,
    PackageConfirmations,
    run_artwork_scan,
)

NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)


def artwork(lines: dict[str, tuple[float, float]], size_mm=(100, 70), font_pt=14) -> bytes:
    """A label ``size_mm`` wide by high, with ``lines`` of text at (x, y) in millimetres."""
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(size_mm[0] * mm, size_mm[1] * mm))
    # The panel's own extent, as a die-line artwork carries it: a white, unstroked rectangle
    # the size of the panel. MEA-005 measures the artwork's content, not the page, so the
    # panel has to be drawn to be measured.
    page.setFillColorRGB(1, 1, 1)
    page.rect(0, 0, size_mm[0] * mm, size_mm[1] * mm, stroke=0, fill=1)
    page.setFillColorRGB(0, 0, 0)
    page.setFont("Helvetica", font_pt)
    for text, (x, y) in lines.items():
        page.drawString(x * mm, y * mm, text)
    page.save()
    return buffer.getvalue()


def spans_from(file_bytes: bytes) -> list[ExtractedSpan]:
    """What a perfect OCR of the render would report: each line, at its rendered box."""
    scale = ARTWORK_RASTER_DPI / 72.0
    spans = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page = pdf.pages[0]
        for index, line in enumerate(page.extract_text_lines()):
            x0, x1 = line["x0"] * scale, line["x1"] * scale
            top, bottom = line["top"] * scale, line["bottom"] * scale
            spans.append(
                ExtractedSpan(
                    span_id=f"art-{index}",
                    region_id="panel",
                    polygon=((x0, top), (x1, top), (x1, bottom), (x0, bottom)),
                    text=line["text"],
                    confidence=1.0,
                    source_provider=EvidenceProvider.PADDLEOCR,
                )
            )
    return spans


def scan(file_bytes: bytes, file_type: str = "pdf", **overrides):
    kwargs = dict(product_category=ProductCategory.FOOD, evaluated_at=NOW, subject_ref="art")
    kwargs.update(overrides)
    with patch("app.pipeline.orchestrator.extract_panel_text", return_value=spans_from(file_bytes)):
        return run_artwork_scan(file_bytes, file_type, **kwargs)


def finding_for(result, rule_id, field=DeclarationField.NET_QUANTITY):
    return next(
        f
        for f in result.verdict.findings
        if f.rule_snapshot.rule_id == rule_id and f.field is field
    )


LABEL = {"Net Quantity: 100 g": (20, 40), "MRP Rs. 45.00": (20, 20)}


def test_the_numeral_height_is_exact_and_banded_against_the_artworks_own_area() -> None:
    """100 x 70 mm is 70 cm2, Table-I's second band: 1.5 mm. The digits measure 3.47 mm.

    The figure is what 14 pt Helvetica digits measure on the 600 dpi render — 82 px, so
    3.47 mm — and the render is the ground truth here, not a font table.
    """
    result = scan(artwork(LABEL))
    assert isinstance(result, ImageScanResult)
    assert result.panel.bbox[2:] == pytest.approx((2362, 1654), abs=1)
    table = finding_for(result, "R7-2-TABLE-I")
    assert table.state is FieldState.PASS
    assert table.expected_value == "1.5 mm"
    assert float(table.observed_value.split()[0]) == pytest.approx(3.47, abs=0.05)
    assert "±" not in table.observed_value, "artwork is exact; there is no interval"


def test_free_space_around_the_quantity_is_measured_on_the_render() -> None:
    result = scan(artwork(LABEL))
    free_space = finding_for(result, "R8-1-FREE-SPACE")
    assert free_space.state is FieldState.PASS
    assert "numeral height 3.47 mm" in free_space.observed_value

    # A line whose cap height sits 1.5 mm under the quantity's baseline: less than the
    # numeral's own 3.47 mm.
    crowded = artwork({**LABEL, "Best before 12 months": (20, 35)})
    assert finding_for(scan(crowded), "R8-1-FREE-SPACE").state is FieldState.FAIL


def test_placement_passes_because_the_artwork_is_the_panel() -> None:
    result = scan(artwork(LABEL))
    placement = finding_for(result, "R8-1-PDP-PLACEMENT")
    assert placement.state is FieldState.PASS
    assert "(artwork)" in placement.observed_value


def test_a_cylinders_label_is_its_circumference_wide() -> None:
    """Rule 7(4)(b): 40 % of 7 cm x 10 cm = 28 cm2, so Table-I's first band, 1.0 mm.

    Not 40 % of height x pi x width: a wrap-around label is not a diameter.
    """
    cylinder = PackageConfirmations(shape=PackageShape.CYLINDRICAL)
    table = finding_for(scan(artwork(LABEL), confirmations=cylinder), "R7-2-TABLE-I")
    assert table.expected_value == "1.0 mm"


def test_an_svg_is_sized_but_not_read() -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="70mm"></svg>'
    result = run_artwork_scan(svg, "svg", product_category=None, evaluated_at=NOW, subject_ref="a")
    assert isinstance(result, ArtworkRefusal)
    assert "cannot be rendered" in result.reason


def test_a_raster_in_a_pdf_wrapper_is_refused_for_carrying_no_units() -> None:
    import numpy as np
    from PIL import Image
    from reportlab.lib.utils import ImageReader

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(100 * mm, 70 * mm))
    page.drawImage(ImageReader(Image.fromarray(np.full((70, 100, 3), 200, dtype=np.uint8))), 0, 0)
    page.save()
    result = run_artwork_scan(
        buffer.getvalue(), "pdf", product_category=None, evaluated_at=NOW, subject_ref="a"
    )
    assert isinstance(result, ArtworkRefusal)
    assert "raster scan" in result.reason
