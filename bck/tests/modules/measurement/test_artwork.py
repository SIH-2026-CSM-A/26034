from app.contracts import MeasurementExact, MeasurementRefusal
from app.modules.measurement.artwork import (
    calculate_artwork_pdp_area,
    measure_artwork_ink_extent,
    parse_pdf_geometry,
)
from app.modules.measurement.schemas import PackageShape


def test_pdf_exact_measurement():
    """Assert measure_artwork_ink_extent parses real PDF vectors and returns a precise height."""
    import tempfile

    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        file_path = tmp.name

    c = canvas.Canvas(file_path)
    # 4.0 mm is exactly 11.338582677165354 points
    c.setFont("Helvetica", 4.0 * mm)
    c.drawString(100, 100, "A")
    c.save()

    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    result = measure_artwork_ink_extent(pdf_bytes, "pdf")

    assert isinstance(result, MeasurementExact)
    assert result.unit == "mm"
    assert not hasattr(result, "confidence_interval")
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


def test_svg_exact_measurement():
    """Assert measure_artwork_ink_extent returns exactly 4.0 for SVG."""
    svg_str = b'<svg width="4mm" height="4mm"></svg>'
    result = measure_artwork_ink_extent(svg_str, "svg")

    assert isinstance(result, MeasurementExact)
    assert result.value == 4.0
    assert result.unit == "mm"
    assert not hasattr(result, "confidence_interval")


def test_artwork_pdp_area_rule_7_integration():
    """Assert calculate_artwork_pdp_area returns correct area and rule limb."""
    svg_str = b'<svg width="10mm" height="10mm"></svg>'
    result = calculate_artwork_pdp_area(svg_str, "svg", PackageShape.RECTANGULAR)

    assert isinstance(result, MeasurementExact)
    assert result.value == 1.0  # 10mm x 10mm = 100mm^2 = 1.0cm^2
    assert result.unit == "cm²"
    assert result.rule_limb == "rectangular"
