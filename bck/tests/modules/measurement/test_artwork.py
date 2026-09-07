from app.contracts import MeasurementExact, MeasurementRefusal
from app.modules.measurement import (
    calculate_artwork_pdp_area,
    measure_artwork_ink_extent,
)
from app.modules.measurement.artwork import parse_pdf_geometry
from app.modules.measurement.schemas import PackageShape


def test_pdf_exact_measurement():
    """Assert measure_artwork_ink_extent parses real PDF vectors and returns a precise height."""
    import tempfile

    from reportlab.pdfgen import canvas

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        file_path = tmp.name

    c = canvas.Canvas(file_path)
    # 4.0 mm is exactly 11.338582677165354 points
    c.setFont("Helvetica", 11.338582677165354)
    c.drawString(100, 100, "A")
    c.save()

    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    result = measure_artwork_ink_extent(pdf_bytes, "pdf")

    assert isinstance(result, MeasurementExact)
    assert result.unit == "mm"
    assert round(result.value, 1) == 4.0


def test_pdf_raster_only_refusal():
    """Assert it returns a MeasurementRefusal explicitly naming the raster wrapper."""
    import tempfile

    import cv2
    import numpy as np
    from reportlab.pdfgen import canvas

    # Create a small dummy raster image
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
        img_path = tmp_img.name
    cv2.imwrite(img_path, img)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        pdf_path = tmp_pdf.name

    c = canvas.Canvas(pdf_path)
    c.drawImage(img_path, 10, 10, width=50, height=50)
    c.save()

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    result = measure_artwork_ink_extent(pdf_bytes, "pdf")

    assert isinstance(result, MeasurementRefusal)
    assert "raster scan in a PDF wrapper" in result.reason


def test_pdf_rotated_axes():
    """Assert parse_pdf_geometry swaps X and Y when rotated 90 degrees."""
    import tempfile

    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        file_path = tmp.name

    c = canvas.Canvas(file_path)
    # Set page rotation directly
    c.setPageRotation(90)
    # Use a tiny font so it doesn't bleed outside the rectangle bounds
    c.setFont("Helvetica", 2)
    # Draw a rectangle to mathematically guarantee the 10x4 dimension bounding box
    c.rect(100, 100, 10 * mm, 4 * mm, stroke=0, fill=1)
    # We must draw text so parse_pdf_geometry detects page.chars, safely inside the rect
    c.drawString(105, 105, "X")
    c.save()

    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    geom = parse_pdf_geometry(pdf_bytes)

    assert not isinstance(geom, MeasurementRefusal)
    width_mm, height_mm = geom
    # Rotated 90 degrees, original 10mm width becomes height, 4mm height becomes width
    assert round(width_mm, 1) == 4.0
    assert round(height_mm, 1) == 10.0


def test_artwork_pdp_area_rule_7_integration():
    """Assert calculate_artwork_pdp_area returns correct area and rule limb."""
    import tempfile

    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        file_path = tmp.name

    c = canvas.Canvas(file_path)
    c.setFont("Helvetica", 2)
    # 10mm x 10mm
    c.rect(100, 100, 10 * mm, 10 * mm, stroke=0, fill=1)
    c.drawString(105, 105, "X")
    c.save()

    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    result = calculate_artwork_pdp_area(pdf_bytes, "pdf", PackageShape.RECTANGULAR)

    assert isinstance(result, MeasurementExact)
    assert round(result.value, 1) == 1.0  # 10mm x 10mm = 100mm^2 = 1.0cm^2
    assert result.unit == "cm²"
    assert result.rule_limb == "rectangular"


def test_svg_type_is_unsupported():
    """Assert the SVG path is gone: an svg file_type reaches the unsupported-type refusal.

    SVG ingest is out of MEA-005's scope and tracked as MEA-010. It means parsing
    untrusted XML uploaded by an outside manufacturer, and needs ``defusedxml`` plus its
    own review before it returns. This guards against the dispatch branch coming back.
    """
    result = measure_artwork_ink_extent(b'<svg width="10mm" height="4mm"/>', "svg")

    assert isinstance(result, MeasurementRefusal)
    assert result.reason == "Unsupported artwork file type: svg"
