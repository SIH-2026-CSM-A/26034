"""Tamper signals and a disagreeing second reading are evidence, and only ever evidence.

Both run on every image scan and both come after every rule has been evaluated. What they
may do is take a declaration that read as present back to an officer. What they may never
do is produce a FAIL: a sticker, a second price or a garbled re-read says something about
how far our reading can be trusted, and nothing about what the package declares.

Driven through :func:`~app.pipeline.orchestrator.run_image_scan` on print that is really on
the frame, with :func:`~app.modules.tamper.detect_tampering` and
:func:`~app.modules.vision.ocr.arbitrate_field_declaration` both the real ones.
"""

import glob
import shutil
from unittest.mock import patch

import cv2
import pytest

from app.contracts import DeclarationField, FieldState, Verdict
from app.modules.vision import ocr

from .test_geometry_wiring import QUANTITY, Label, finding_for, scan

MRP_RULE = "R6-1-E"
QUANTITY_RULE = "R6-1-C"


@pytest.fixture
def real_second_reading(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Undo the package-wide stand-in: these tests are about the real re-read."""
    monkeypatch.setattr(
        "app.pipeline.orchestrator.arbitrate_field_declaration", ocr.arbitrate_field_declaration
    )
    monkeypatch.setenv("TESSERACT_TESSDATA_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()


def two_prices() -> Label:
    return (
        Label()
        .write(QUANTITY, (250, 250), span_id="s-quantity")
        .write("MRP Rs. 45.00", (250, 420), span_id="s-mrp")
        .write("MRP Rs. 60.00", (250, 600), span_id="s-mrp-second")
    )


def stickered() -> Label:
    """A bright paper rectangle under the price, with the panel's dark surface around it.

    The paper runs 7 px past the print on every side. That is what a sticker looks like to
    the detector — a step that encloses the span — and it is the only shape it reports: a
    bright edge on one side, which is what this fixture used to draw, is a printed rule.
    """
    label = Label().write(QUANTITY, (250, 250), span_id="s-quantity")
    label.write("MRP Rs. 45.00", (250, 420), span_id="s-mrp")
    (x0, y0), _, (x1, y1), _ = (tuple(int(v) for v in pt) for pt in label.spans[-1].polygon)
    print_ = label.frame[y0:y1, x0:x1].copy()
    cv2.rectangle(label.frame, (x0 - 7, y0 - 7), (x1 + 7, y1 + 7), (235, 235, 235), -1)
    label.frame[y0:y1, x0:x1] = print_
    return label


def test_a_clean_label_raises_no_signal_and_the_price_passes() -> None:
    clean = Label().write(QUANTITY, (250, 250), span_id="s-quantity")
    result = scan(clean.write("MRP Rs. 45.00", (250, 420), span_id="s-mrp"))
    assert result.tamper_signals == ()
    assert (
        finding_for(result, MRP_RULE, DeclarationField.RETAIL_SALE_PRICE).state is FieldState.PASS
    )


def test_two_prices_on_one_package_send_the_price_to_an_officer() -> None:
    result = scan(two_prices())
    assert {signal.kind for signal in result.tamper_signals} == {"conflicting_mrp"}
    price = finding_for(result, MRP_RULE, DeclarationField.RETAIL_SALE_PRICE)
    assert price.state is FieldState.REVIEW_REQUIRED
    assert "60.00" in price.reason and "45.00" in price.reason
    assert result.verdict.verdict is Verdict.REVIEW


def test_a_sticker_under_the_price_sends_the_price_and_nothing_else() -> None:
    result = scan(stickered())
    assert [signal.kind for signal in result.tamper_signals] == ["sticker_overlay"]
    assert (
        finding_for(result, MRP_RULE, DeclarationField.RETAIL_SALE_PRICE).state
        is FieldState.REVIEW_REQUIRED
    )
    assert finding_for(result, QUANTITY_RULE).state is FieldState.PASS


@pytest.mark.parametrize("label", [two_prices, stickered])
def test_a_tamper_signal_never_produces_a_potential_violation(label) -> None:
    """The scan with its signals, against the same scan with the detector silenced.

    Not one finding may be FAIL in the first that is not FAIL in the second, and the
    package-level verdict may not become POTENTIAL_VIOLATION on the strength of a signal.
    """
    with_signals = scan(label())
    with patch("app.pipeline.orchestrator.detect_tampering", return_value=[]):
        without = scan(label())
    assert with_signals.tamper_signals and not without.tamper_signals

    def failing(result):
        return {
            (f.rule_snapshot.rule_id, f.field)
            for f in result.verdict.findings
            if f.state is FieldState.FAIL
        }

    assert failing(with_signals) == failing(without)
    changed = [
        (before.state, after.state)
        for before, after in zip(
            without.verdict.findings, with_signals.verdict.findings, strict=True
        )
        if before.state is not after.state
    ]
    assert changed and set(changed) == {(FieldState.PASS, FieldState.REVIEW_REQUIRED)}
    assert with_signals.verdict.verdict is not Verdict.POTENTIAL_VIOLATION


def test_a_signal_on_a_missing_declaration_does_not_turn_absence_into_failure() -> None:
    """INSUFFICIENT_EVIDENCE is returned untouched. A doubt about a reading is not a shortfall."""
    from app.modules.rules import load_rules
    from app.pipeline.orchestrator import _doubted

    baseline = scan(Label().write(QUANTITY, (250, 250), span_id="s-quantity"))
    price = finding_for(baseline, MRP_RULE, DeclarationField.RETAIL_SALE_PRICE)
    assert price.state is FieldState.INSUFFICIENT_EVIDENCE

    doubted = _doubted(
        baseline.verdict.findings,
        load_rules(),
        {DeclarationField.RETAIL_SALE_PRICE: ("a second price was seen",)},
    )
    assert next(f for f in doubted if f.rule_snapshot.rule_id == MRP_RULE) is price


def test_a_second_reading_that_disagrees_sends_the_figure_to_an_officer(
    real_second_reading,
) -> None:
    """The real arbitration, over the real crop, with only the Tesseract process replaced."""
    clean = Label().write(QUANTITY, (250, 250), span_id="s-quantity")
    clean.write("MRP Rs. 45.00", (250, 420), span_id="s-mrp")
    crops = []

    def reads_100(crop, config=""):
        crops.append(crop.shape)
        return "100"

    with patch.object(ocr.pytesseract, "image_to_string", side_effect=reads_100):
        result = scan(clean)

    assert len(crops) == 2, "price and quantity are each re-read once"
    # "100" agrees with "Net Quantity: 100 g" and disagrees with "MRP Rs. 45.00".
    assert finding_for(result, QUANTITY_RULE).state is FieldState.PASS
    price = finding_for(result, MRP_RULE, DeclarationField.RETAIL_SALE_PRICE)
    assert price.state is FieldState.REVIEW_REQUIRED
    assert "second OCR pass" in price.reason and "'100'" in price.reason


TESSDATA = [*glob.glob("/usr/share/tesseract-ocr/*/tessdata"), *glob.glob("/opt/tessdata")]


@pytest.mark.skipif(
    shutil.which("tesseract") is None or not TESSDATA,
    reason="the tesseract binary or its tessdata is not installed",
)
def test_the_real_tesseract_binary_is_reached_on_a_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """No stand-in at all. Runs wherever Tesseract is installed: the image, the VM, a laptop."""
    from app.core.config import get_settings

    monkeypatch.setattr(
        "app.pipeline.orchestrator.arbitrate_field_declaration", ocr.arbitrate_field_declaration
    )
    monkeypatch.setenv("TESSERACT_TESSDATA_DIR", TESSDATA[0])
    get_settings.cache_clear()
    clean = Label().write(QUANTITY, (250, 250), span_id="s-quantity")
    clean.write("MRP Rs. 45.00", (250, 420), span_id="s-mrp")
    with patch.object(
        ocr.pytesseract, "image_to_string", wraps=ocr.pytesseract.image_to_string
    ) as tesseract:
        result = scan(clean)
    assert tesseract.call_count == 2
    price = finding_for(result, MRP_RULE, DeclarationField.RETAIL_SALE_PRICE)
    assert price.state in {FieldState.PASS, FieldState.REVIEW_REQUIRED}
