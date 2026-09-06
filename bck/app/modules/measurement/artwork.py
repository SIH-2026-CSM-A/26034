import io
import re
import xml.etree.ElementTree as ET

import pdfplumber

from app.contracts import MeasurementExact, MeasurementRefusal, MeasurementResult
from app.modules.measurement.schemas import PackageShape
from app.modules.measurement.services import _compute_rule_7_area


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

            width_mm = float(width_pt * 25.4 / 72.0)
            height_mm = float(height_pt * 25.4 / 72.0)

            return width_mm, height_mm
    except Exception as e:
        return MeasurementRefusal(reason=f"Failed to parse PDF: {str(e)}")


def parse_svg_geometry(file_bytes: bytes) -> tuple[float, float] | MeasurementRefusal:
    """Extract physical dimensions in mm from an SVG using xml.etree.ElementTree."""
    try:
        # Strip namespaces for easier tag matching
        it = ET.iterparse(io.BytesIO(file_bytes))
        for _, el in it:
            _, _, el.tag = el.tag.rpartition("}")
        root = it.root
    except ET.ParseError:
        return MeasurementRefusal(reason="Failed to parse SVG file.")

    if root.tag != "svg":
        return MeasurementRefusal(reason="Not a valid SVG root element.")

    width_attr = root.get("width")
    height_attr = root.get("height")
    viewbox_attr = root.get("viewBox")

    def parse_length(length_str: str) -> float | None:
        if not length_str:
            return None
        match = re.match(r"^([\d.]+)([a-zA-Z%]*)$", length_str.strip())
        if not match:
            return None
        val, unit = float(match.group(1)), match.group(2)
        if unit == "mm":
            return val
        elif unit == "cm":
            return val * 10.0
        elif unit == "in":
            return val * 25.4
        elif unit == "pt":
            return val * 25.4 / 72.0
        elif unit == "pc":
            return val * 25.4 / 6.0
        elif unit == "px" or not unit:
            return val * 25.4 / 96.0
        return None

    w_mm = parse_length(width_attr) if width_attr else None
    h_mm = parse_length(height_attr) if height_attr else None

    if w_mm is not None and h_mm is not None:
        return w_mm, h_mm

    if viewbox_attr:
        parts = viewbox_attr.replace(",", " ").split()
        if len(parts) == 4:
            vb_w, vb_h = float(parts[2]), float(parts[3])
            if w_mm is not None and vb_w > 0:
                scale = w_mm / vb_w
                h_mm = vb_h * scale
            elif h_mm is not None and vb_h > 0:
                scale = h_mm / vb_h
                w_mm = vb_w * scale
            else:
                w_mm = vb_w * 25.4 / 96.0
                h_mm = vb_h * 25.4 / 96.0
            return w_mm, h_mm

    return MeasurementRefusal(reason="Could not determine physical dimensions from SVG attributes.")


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
