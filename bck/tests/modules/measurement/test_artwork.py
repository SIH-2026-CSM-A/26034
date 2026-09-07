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


def _load_svg_fixture(filename: str) -> bytes:
    from pathlib import Path

    file_path = Path(__file__).parent / "fixtures" / "svg" / filename
    with open(file_path, "rb") as f:
        return f.read()


def test_svg_exact_mm_dimensions():
    """Assert the extracted area matches the expected cm2 using MeasurementExact."""
    svg_bytes = _load_svg_fixture("standard.svg")
    result = calculate_artwork_pdp_area(svg_bytes, "svg", PackageShape.RECTANGULAR)

    assert isinstance(result, MeasurementExact)
    assert result.unit == "cm²"
    # 210mm x 297mm = 623.7 cm^2
    assert round(result.value, 1) == 623.7


def test_svg_swapped_dimensions():
    """Assert swapped width/height (4mm x 10mm) returns correct dimensions."""
    svg_bytes = _load_svg_fixture("swapped.svg")
    # Using calculate_artwork_pdp_area: 4 * 10 = 40 mm^2 = 0.4 cm^2
    result = calculate_artwork_pdp_area(svg_bytes, "svg", PackageShape.RECTANGULAR)

    assert isinstance(result, MeasurementExact)
    assert result.unit == "cm²"
    assert round(result.value, 2) == 0.40


def test_svg_unit_conversion():
    """Assert 'in' and 'pt' are correctly converted to millimeters and evaluated."""
    svg_bytes = _load_svg_fixture("converted_units.svg")
    result = calculate_artwork_pdp_area(svg_bytes, "svg", PackageShape.RECTANGULAR)

    assert isinstance(result, MeasurementExact)
    assert result.unit == "cm²"
    # width = 2in = 50.8mm
    # height = 144pt = 2in = 50.8mm
    # area = 50.8 * 50.8 = 2580.64 mm^2 = 25.8 cm^2
    assert round(result.value, 1) == 25.8


def test_svg_viewbox_refusal():
    """Assert MeasurementRefusal is returned for viewbox_only.svg."""
    svg_bytes = _load_svg_fixture("viewbox_only.svg")
    result = measure_artwork_ink_extent(svg_bytes, "svg")

    assert isinstance(result, MeasurementRefusal)
    assert "missing" in result.reason.lower() or "physical unit" in result.reason.lower()


def test_svg_billion_laughs_protection():
    """Assert the parser safely refuses the file without hanging."""
    svg_bytes = _load_svg_fixture("billion_laughs.svg")
    result = measure_artwork_ink_extent(svg_bytes, "svg")

    assert isinstance(result, MeasurementRefusal)
    reason_lower = result.reason.lower()
    assert "entitiesforbidden" in reason_lower
