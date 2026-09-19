"""The geometric rules run on a scan, from the pixels under the declarations they govern.

Everything here goes through :func:`~app.pipeline.orchestrator.run_image_scan`. Only the two
model calls are replaced — panel detection and OCR — and OCR is replaced by spans whose
polygons are the true boxes of text this module has actually drawn on the frame. The
quality gate, deskew, binding, glyph segmentation, every measurement and every evaluator
are the real ones.

The frame is declared as artwork at 254 dpi, so one pixel is exactly 0.1 mm and each
expected figure below can be checked by hand against the drawing.

**Category is confirmed as food throughout**, for the reason ``test_orchestrator`` gives:
Rule 7 and Rule 8(1) placement are sector-gated, and with no category the gate settles them
before any of this runs. Food carves nothing out of either.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from app.contracts import (
    DeclarationField,
    EvidenceProvider,
    ExtractedSpan,
    FieldState,
    MeasurementRefusal,
)
from app.core import CalibrationMethod
from app.modules.measurement import PackageShape
from app.modules.rules import ProductCategory
from app.modules.vision.pdp import OfficerMarkedPanel
from app.pipeline.orchestrator import (
    Calibration,
    ImageScanResult,
    PackageConfirmations,
    _panel_area,
    run_image_scan,
)

NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
ARTWORK = Calibration(method=CalibrationMethod.ARTWORK, artwork_dpi=254.0)
PANEL = (100, 100, 1000, 700)
"""The detected panel: 100 mm x 70 mm = 70 cm2, Table-I's second band (1.5 mm). The frame is
120 mm x 90 mm = 108 cm2, its third (2.5 mm). Which band a finding quotes says which area
was measured. It covers 65 % of the frame, so the deskew takes its outline for the label."""

QUANTITY = "Net Quantity: 100 g"
FONT = cv2.FONT_HERSHEY_SIMPLEX


class Label:
    """A dark panel with light print, and the spans an OCR pass over it would report."""

    def __init__(self, panel: tuple[int, int, int, int] = PANEL) -> None:
        self.frame = np.full((900, 1200, 3), 200, dtype=np.uint8)
        self.panel = panel
        x, y, w, h = panel
        cv2.rectangle(self.frame, (x, y), (x + w, y + h), (40, 40, 40), -1)
        self.spans: list[ExtractedSpan] = []

    def write(self, text: str, origin: tuple[int, int], *, span_id: str, squeeze: float = 1.0):
        """Draw ``text`` and record its span. ``squeeze`` narrows the print horizontally."""
        (width, height), baseline = cv2.getTextSize(text, FONT, 1.6, 3)
        patch_ = np.full((height + baseline + 8, width + 8, 3), 40, dtype=np.uint8)
        cv2.putText(patch_, text, (4, height + 4), FONT, 1.6, (230, 230, 230), 3)
        if squeeze != 1.0:
            patch_ = cv2.resize(
                patch_, (int(patch_.shape[1] * squeeze), patch_.shape[0]), cv2.INTER_NEAREST
            )
        x, y = origin
        h, w = patch_.shape[:2]
        self.frame[y : y + h, x : x + w] = patch_
        self.spans.append(
            ExtractedSpan(
                span_id=span_id,
                region_id="panel",
                polygon=((x, y), (x + w, y), (x + w, y + h), (x, y + h)),
                text=text,
                confidence=0.95,
                source_provider=EvidenceProvider.PADDLEOCR,
            )
        )
        return self


class Detection:
    bbox = PANEL
    area = PANEL[2] * PANEL[3]
    confidence = 0.9
    method = "model"


def as_ocr_reports_them(label: Label) -> list[ExtractedSpan]:
    """The label's spans in the coordinates of the frame OCR is actually handed.

    The deskew crops to the panel's outline, so OCR sees the panel with its corner at the
    origin and reports polygons there. Handing back photograph coordinates instead would
    have every measurement below land 10 mm away from the print it is about.
    """
    if label.panel is not PANEL:
        return list(label.spans)  # too small to be taken for the label, so no deskew ran
    dx, dy = PANEL[0], PANEL[1]
    return [
        span.model_copy(update={"polygon": tuple((x - dx, y - dy) for x, y in span.polygon)})
        for span in label.spans
    ]


def scan(label: Label, *, detection=Detection, **overrides) -> ImageScanResult:
    kwargs = dict(
        calibration=ARTWORK,
        product_category=ProductCategory.FOOD,
        evaluated_at=NOW,
        subject_ref="scan-geometry",
    )
    kwargs.update(overrides)
    with (
        patch("app.pipeline.orchestrator.detect_pdp", return_value=detection()),
        patch(
            "app.pipeline.orchestrator.extract_panel_text",
            return_value=as_ocr_reports_them(label),
        ),
    ):
        result = run_image_scan(label.frame, **kwargs)
    assert isinstance(result, ImageScanResult), result
    return result


def finding_for(result: ImageScanResult, rule_id: str, field=DeclarationField.NET_QUANTITY):
    return next(
        f
        for f in result.verdict.findings
        if f.rule_snapshot.rule_id == rule_id and f.field is field
    )


def spacious() -> Label:
    return (
        Label()
        .write(QUANTITY, (250, 300), span_id="s-quantity")
        .write("MRP Rs. 45.00", (250, 480), span_id="s-mrp")
    )


def test_rule_8_free_space_is_evaluated_from_measured_margins() -> None:
    """``measure_margins`` runs around the bound quantity declaration, and Rule 8(1) decides."""
    found = finding_for(scan(spacious()), "R8-1-FREE-SPACE")
    assert found.state is FieldState.PASS
    assert "numeral height 3.90 mm" in found.observed_value
    assert found.expected_value == (
        "above and below at least 3.90 mm; left and right at least 7.80 mm"
    )
    assert found.evidence_span_ids == ("s-quantity",)


def test_print_crowding_the_quantity_is_a_potential_violation_naming_the_side() -> None:
    """A line 1.5 mm under a 3.9 mm numeral breaches the proviso, and the finding says where."""
    crowded = spacious().write("Best before 12 months", (250, 371), span_id="s-crowd")
    found = finding_for(scan(crowded), "R8-1-FREE-SPACE")
    assert found.state is FieldState.FAIL
    assert "below" in found.reason
    assert "above" not in found.reason


def test_without_a_calibration_rule_8_is_insufficient_evidence_and_carries_no_millimetre() -> None:
    """An uncalibrated photograph supports no figure and no shortfall, however crowded."""
    crowded = spacious().write("Best before 12 months", (250, 371), span_id="s-crowd")
    result = scan(crowded, calibration=Calibration(method=CalibrationMethod.NONE))
    for rule_id in ("R8-1-FREE-SPACE", "R7-3-WIDTH-RATIO", "R7-2-TABLE-I"):
        found = finding_for(result, rule_id)
        assert found.state is FieldState.INSUFFICIENT_EVIDENCE, rule_id
        assert found.state is not FieldState.FAIL
        assert found.observed_value is None
        assert "mm" not in found.reason.replace("millimetre", "")
    assert "reference object" in finding_for(result, "R8-1-FREE-SPACE").reason


def test_table_i_bands_the_numeral_against_the_detected_panel_not_the_frame() -> None:
    """70 cm2 of panel asks for 1.5 mm. The 108 cm2 frame it sits in would ask for 2.5."""
    found = finding_for(scan(spacious()), "R7-2-TABLE-I")
    assert found.expected_value == "1.5 mm"
    assert float(found.observed_value.split()[0]) == pytest.approx(3.9)
    assert found.state is FieldState.PASS


def test_a_height_measured_on_the_quantity_answers_for_no_other_declaration() -> None:
    found = finding_for(scan(spacious()), "R7-2-TABLE-I", DeclarationField.RETAIL_SALE_PRICE)
    assert found.state is FieldState.INSUFFICIENT_EVIDENCE
    assert "quantity declaration only" in found.reason


def test_rule_7_3_passes_ordinary_print_and_exempts_the_characters_the_rule_names() -> None:
    """The "i" is a fifth as wide as it is tall and the "1" a third. Both are exempt by name."""
    found = finding_for(scan(spacious()), "R7-3-WIDTH-RATIO")
    assert found.state is FieldState.PASS
    assert "i=0.2" in found.observed_value


def test_rule_7_3_flags_condensed_print_and_names_the_characters() -> None:
    condensed = (
        Label()
        .write(QUANTITY, (250, 300), span_id="s-quantity", squeeze=0.4)
        .write("MRP Rs. 45.00", (250, 480), span_id="s-mrp")
    )
    found = finding_for(scan(condensed), "R7-3-WIDTH-RATIO")
    assert found.state is FieldState.FAIL
    assert "'0' at" in found.reason
    assert "'1' at" not in found.reason, "Rule 7(3) exempts the numeral 1 by name"


def test_touching_print_is_insufficient_evidence_not_a_guess() -> None:
    """When glyphs cannot be paired with characters, nothing says which one is the "1"."""
    misread = Label().write(QUANTITY, (250, 300), span_id="s-quantity")
    misread.spans[0] = misread.spans[0].model_copy(update={"text": "Net Quantity: 1000 g"})
    found = finding_for(scan(misread), "R7-3-WIDTH-RATIO")
    assert found.state is FieldState.INSUFFICIENT_EVIDENCE
    assert "17 characters and 16 separate glyphs" in found.reason


def test_a_declaration_that_cannot_be_located_says_why() -> None:
    """``get_declaration_bbox`` refuses, and the officer-facing reason reaches the finding."""
    # A panel under half the frame, so no deskew runs and the polygon arrives exactly as
    # the provider emitted it.
    broken = Label(panel=(100, 100, 800, 500)).write(QUANTITY, (250, 300), span_id="s-quantity")
    (x0, y0), *rest = broken.spans[0].polygon
    broken.spans[0] = broken.spans[0].model_copy(update={"polygon": ((float("nan"), y0), *rest)})
    found = finding_for(scan(broken), "R8-1-FREE-SPACE")
    assert found.state is FieldState.INSUFFICIENT_EVIDENCE
    assert "non-finite coordinate" in found.reason


def test_placement_inside_a_model_detection_passes_and_outside_it_goes_to_an_officer() -> None:
    inside = finding_for(scan(spacious()), "R8-1-PDP-PLACEMENT")
    assert inside.state is FieldState.PASS
    assert inside.expected_value == "principal_display_panel"

    class Elsewhere(Detection):
        bbox = (100, 600, 1000, 200)

    outside = finding_for(scan(spacious(), detection=Elsewhere), "R8-1-PDP-PLACEMENT")
    assert outside.state is FieldState.REVIEW_REQUIRED
    assert outside.state is not FieldState.FAIL


def test_a_heuristic_region_never_passes_placement() -> None:
    class Heuristic(Detection):
        method = "heuristic"

    found = finding_for(scan(spacious(), detection=Heuristic), "R8-1-PDP-PLACEMENT")
    assert found.state is FieldState.REVIEW_REQUIRED


def test_a_heuristic_region_cannot_band_table_i_but_the_height_is_still_reported() -> None:
    """The largest block of print is not a measured panel, so no band; the numeral is real."""

    class Heuristic(Detection):
        method = "heuristic"

    result = scan(spacious(), detection=Heuristic)
    table = finding_for(result, "R7-2-TABLE-I")
    assert table.state is FieldState.INSUFFICIENT_EVIDENCE
    assert table.state is not FieldState.FAIL
    assert "panel was not detected" in table.reason
    assert table.expected_value is None
    assert float(table.observed_value.split()[0]) == pytest.approx(3.9)
    # Rule 8(1)'s clearances are measured from the declaration's own ink, not the panel.
    assert finding_for(result, "R8-1-FREE-SPACE").state is FieldState.PASS


def test_rule_9_contrast_is_measured_and_judged_by_nobody() -> None:
    found = finding_for(scan(spacious()), "R9-1-MANNER")
    assert found.state is FieldState.REVIEW_REQUIRED
    assert found.observed_value.startswith("contrast ratio 11.")


def test_rule_7_5_disapplies_sizing_to_a_declaration_it_does_not_preserve() -> None:
    confirmed = PackageConfirmations(declarations_required_under_other_law=True)
    result = scan(spacious(), confirmations=confirmed)
    name = finding_for(result, "R7-2-TABLE-I", DeclarationField.COMMON_OR_GENERIC_NAME)
    assert name.state is FieldState.NOT_APPLICABLE
    assert "Rule 7(5)" in name.reason
    assert finding_for(result, "R7-2-TABLE-I").state is FieldState.PASS, "net quantity is preserved"


def test_a_recorded_rule_33_relaxation_sends_a_shortfall_to_an_officer() -> None:
    crowded = spacious().write("Best before 12 months", (250, 371), span_id="s-crowd")
    relaxed = PackageConfirmations(rule_33_relaxation_granted=True)
    found = finding_for(scan(crowded, confirmations=relaxed), "R8-1-FREE-SPACE")
    assert found.state is FieldState.REVIEW_REQUIRED
    assert "Rule 33" in found.reason


def test_the_other_shape_limb_takes_the_detected_panel_as_the_identified_area() -> None:
    other = PackageConfirmations(shape=PackageShape.OTHER)
    assert finding_for(scan(spacious(), confirmations=other), "R7-2-TABLE-I").expected_value == (
        "1.5 mm"
    )


def test_a_cylinder_photographed_face_on_has_no_panel_area() -> None:
    cylinder = PackageConfirmations(shape=PackageShape.CYLINDRICAL)
    found = finding_for(scan(spacious(), confirmations=cylinder), "R7-2-TABLE-I")
    assert found.state is FieldState.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize(
    ("shape", "unwarped"),
    [(PackageShape.RECTANGULAR, False), (PackageShape.CYLINDRICAL, True)],
)
def test_ocr_reads_the_prepared_frame_and_spans_return_to_the_photograph(shape, unwarped) -> None:
    """The deskew fires on this label's outline; the unwarp only for a confirmed cylinder."""
    label = spacious()
    seen = {}

    def read(image, *_):
        seen["shape"] = image.shape
        return as_ocr_reports_them(label)

    with (
        patch("app.pipeline.orchestrator.detect_pdp", return_value=Detection()),
        patch("app.pipeline.orchestrator.extract_panel_text", side_effect=read),
        patch(
            "app.modules.vision.preprocess.remap_curvature", side_effect=lambda image: image
        ) as remap,
    ):
        result = run_image_scan(
            label.frame,
            calibration=ARTWORK,
            product_category=ProductCategory.FOOD,
            evaluated_at=NOW,
            subject_ref="scan-prepared",
            confirmations=PackageConfirmations(shape=shape),
        )
    assert seen["shape"][:2] != label.frame.shape[:2], "OCR was handed the undeskewed frame"
    assert remap.called is unwarped
    if not unwarped:
        # The unwarp's own way back is proved against the real remap in
        # tests/modules/vision; here it is stubbed out, so only the deskew is undone.
        quantity = next(span for span in result.spans if span.span_id == "s-quantity")
        assert quantity.polygon[0] == pytest.approx((250.0, 300.0), abs=2.0)


def test_an_officer_marked_panel_bands_table_i_where_the_heuristic_could_not() -> None:
    """The officer states where the panel is; Table-I bands against that, not the frame."""

    class Heuristic(Detection):
        method = "heuristic"

    marked = PackageConfirmations(panel_bbox=PANEL)
    result = scan(spacious(), detection=Heuristic, confirmations=marked)
    assert result.panel.method == "officer"
    assert result.panel.bbox == PANEL
    table = finding_for(result, "R7-2-TABLE-I")
    assert table.state is FieldState.PASS
    assert table.expected_value == "1.5 mm", "70 cm2 is the 50-100 band, not the frame's"
    assert "70.0 cm²" in table.reason
    assert float(table.observed_value.split()[0]) == pytest.approx(3.9)


def test_an_officer_mark_without_a_calibration_is_still_no_millimetre() -> None:
    """A stated boundary is pixels. Without a reference object it has no area in cm².

    Asserted at ``_panel_area`` as well as on the finding: on the finding alone the
    character height refuses first and hides whatever the panel measurement did, so a
    panel measured in pixels and called exact would still read as a clean refusal.
    """
    uncalibrated = Calibration(method=CalibrationMethod.NONE)
    marked_panel = OfficerMarkedPanel(bbox=PANEL, area=float(PANEL[2] * PANEL[3]))
    area = _panel_area(spacious().frame, marked_panel, uncalibrated, PackageShape.RECTANGULAR)
    assert isinstance(area, MeasurementRefusal)
    assert "reference object" in area.reason

    marked = PackageConfirmations(panel_bbox=PANEL)
    result = scan(spacious(), calibration=uncalibrated, confirmations=marked)
    assert result.panel.method == "officer"
    table = finding_for(result, "R7-2-TABLE-I")
    assert table.state is FieldState.INSUFFICIENT_EVIDENCE
    assert table.state is not FieldState.FAIL
    assert table.observed_value is None
    assert table.expected_value is None
    assert "mm" not in table.reason.replace("millimetre", "")
    assert "cm²" not in table.reason


def test_placement_inside_an_officer_mark_passes_and_outside_it_goes_to_an_officer() -> None:
    inside = finding_for(
        scan(spacious(), confirmations=PackageConfirmations(panel_bbox=PANEL)),
        "R8-1-PDP-PLACEMENT",
    )
    assert inside.state is FieldState.PASS
    assert "officer marked" in inside.reason
    assert "(officer)" in inside.observed_value

    elsewhere = PackageConfirmations(panel_bbox=(100, 600, 1000, 200))
    outside = finding_for(scan(spacious(), confirmations=elsewhere), "R8-1-PDP-PLACEMENT")
    assert outside.state is FieldState.REVIEW_REQUIRED
    assert outside.state is not FieldState.FAIL
    assert "officer marked" in outside.reason
