import io

import defusedxml.ElementTree as ET  # noqa: N817
import pdfplumber

from app.contracts import MeasurementExact, MeasurementRefusal, MeasurementResult
from app.modules.measurement.schemas import PackageShape
from app.modules.measurement.services import _compute_rule_7_area

PT_TO_MM = 25.4 / 72.0
"""PostScript points to millimetres. A PDF user-space unit is 1/72 inch by definition."""


def parse_pdf_geometry(file_bytes: bytes) -> tuple[float, float] | MeasurementRefusal:
    """Extract bounding box dimensions in mm from a vector PDF using pdfplumber."""

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            if not pdf.pages:
                return MeasurementRefusal(reason="PDF contains no pages.")
            page = pdf.pages[0]

            if not page.chars:
                if page.images:
                    return MeasurementRefusal(
                        reason="The file is a raster scan in a PDF wrapper and "
                        "contains no physical units."
                    )
                return MeasurementRefusal(reason="PDF contains no vector characters or images.")

            x0s = (
                [c["x0"] for c in page.chars]
                + [r["x0"] for r in page.rects]
                + [r["x0"] for r in page.curves]
            )
            x1s = (
                [c["x1"] for c in page.chars]
                + [r["x1"] for r in page.rects]
                + [r["x1"] for r in page.curves]
            )
            tops = (
                [c["top"] for c in page.chars]
                + [r["top"] for r in page.rects]
                + [r["top"] for r in page.curves]
            )
            bottoms = (
                [c["bottom"] for c in page.chars]
                + [r["bottom"] for r in page.rects]
                + [r["bottom"] for r in page.curves]
            )

            min_x, max_x = min(x0s), max(x1s)
            min_y, max_y = min(tops), max(bottoms)

            width_pt = max_x - min_x
            height_pt = max_y - min_y

            width_mm = float(width_pt * PT_TO_MM)
            height_mm = float(height_pt * PT_TO_MM)

            return width_mm, height_mm
    except Exception as e:
        return MeasurementRefusal(reason=f"Failed to parse PDF: {str(e)}")


def parse_svg_geometry(file_bytes: bytes) -> tuple[float, float] | MeasurementRefusal:
    try:
        root = ET.fromstring(file_bytes)
    except Exception as e:
        return MeasurementRefusal(reason=f"Failed to parse SVG: {str(e)}")

    width_attr = root.get("width")
    height_attr = root.get("height")

    if not width_attr or not height_attr:
        return MeasurementRefusal(reason="SVG missing physical unit (width/height).")

    def _parse_dim(dim_str: str) -> float | None:
        dim_str = dim_str.strip().lower()
        if dim_str.endswith("mm"):
            return float(dim_str[:-2])
        elif dim_str.endswith("cm"):
            return float(dim_str[:-2]) * 10.0
        elif dim_str.endswith("in"):
            return float(dim_str[:-2]) * 25.4
        elif dim_str.endswith("pt"):
            return float(dim_str[:-2]) * PT_TO_MM
        else:
            return None

    try:
        width_mm = _parse_dim(width_attr)
        height_mm = _parse_dim(height_attr)
    except ValueError:
        return MeasurementRefusal(reason="Invalid numeric dimension in SVG.")

    if width_mm is None or height_mm is None:
        return MeasurementRefusal(reason="SVG lacks a valid physical unit (mm, cm, in, pt).")

    return width_mm, height_mm


def measure_artwork_ink_extent(file_bytes: bytes, file_type: str) -> MeasurementResult:
    """Measure the exact physical ink extent (height) of an artwork file."""
    if file_type.lower() == "pdf":
        geom = parse_pdf_geometry(file_bytes)
    elif file_type.lower() == "svg":
        geom = parse_svg_geometry(file_bytes)
    else:
        return MeasurementRefusal(reason=f"Unsupported artwork file type: {file_type}")

    if isinstance(geom, MeasurementRefusal):
        return geom

    _, height_mm = geom
    return MeasurementExact(value=height_mm, unit="mm")


def calculate_artwork_pdp_area(
    file_bytes: bytes, file_type: str, shape: PackageShape
) -> MeasurementResult:
    """Calculate the exact PDP area of an artwork file according to Rule 7(4)."""
    if file_type.lower() == "pdf":
        geom = parse_pdf_geometry(file_bytes)
    elif file_type.lower() == "svg":
        geom = parse_svg_geometry(file_bytes)
    else:
        return MeasurementRefusal(reason=f"Unsupported artwork file type: {file_type}")

    if isinstance(geom, MeasurementRefusal):
        return geom

    width_mm, height_mm = geom
    area_cm2, rule_limb = _compute_rule_7_area(height_mm, width_mm, shape)

    return MeasurementExact(value=area_cm2, unit="cm²", rule_limb=rule_limb)
