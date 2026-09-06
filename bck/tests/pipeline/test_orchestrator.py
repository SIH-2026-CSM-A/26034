"""What the chain does with a real capture, and what it refuses to do.

These run without model weights and without a database. The quality gate sits ahead of
panel detection and OCR, so the rejection path is fully exercisable here; the catalogue
path touches no model at all. A scan that reaches YOLO and PaddleOCR needs the cached
weights and is marked ``models``, the way the persistence tests are marked ``postgres``.

**A trap worth knowing before adding a test here.** With no confirmed product category,
every rule in ``SECTOR_GOVERNED_RULES`` is settled by the sector gate before its own
builder runs. A test that asserts something about Rule 7's measurement handling while
leaving the category unconfirmed passes whether or not that handling exists. Either
confirm a category that carves nothing out — food, for Rule 7 — or assert against a rule
the gate does not touch.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from app.contracts import (
    CatalogueRecord,
    DeclarationField,
    EvidenceProvider,
    ExtractedSpan,
    FieldState,
    NormalisedField,
    Verdict,
)
from app.core import CalibrationMethod
from app.modules.rules import ProductCategory
from app.modules.vision.preprocess import QualityReason
from app.pipeline.capture import CAPTURE_INSTRUCTIONS, QualityRejection
from app.pipeline.orchestrator import (
    UNBOUND_DECLARATION_REASON,
    Calibration,
    ImageScanResult,
    by_obligation,
    run_catalogue_scan,
    run_image_scan,
)

NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)


def blurred_image() -> np.ndarray:
    """A uniform grey frame: no edges, so Laplacian variance is zero and it reads blurred."""
    return np.full((480, 640, 3), 128, dtype=np.uint8)


def listing(**fields: str) -> CatalogueRecord:
    return CatalogueRecord(
        listing_id="B0TEST",
        platform="test-marketplace",
        retrieved_at=NOW,
        title="A packaged commodity",
        declared_fields={DeclarationField(k): v for k, v in fields.items()},
    )


def test_every_failing_quality_reason_carries_a_capture_instruction() -> None:
    """An officer told only that the image was rejected will submit the same photograph."""
    failing = set(QualityReason) - {QualityReason.PASS}
    assert failing == set(CAPTURE_INSTRUCTIONS)


def test_a_blurred_capture_returns_an_instruction_and_no_verdict() -> None:
    """The gate returns and stops. Nothing downstream runs and no record is built.

    This is the whole of the guarantee: a photograph we could not read produces no
    ``VerdictRecord`` of any kind, because a verdict assembled from a bad capture turns
    "we could not see it" into "it is not there".
    """
    outcome = run_image_scan(
        blurred_image(),
        calibration=Calibration(method=CalibrationMethod.NONE),
        product_category=None,
        evaluated_at=NOW,
        subject_ref="scan-blurred",
    )
    assert isinstance(outcome, QualityRejection)
    assert outcome.reason_code is QualityReason.BLUR_EXCEEDED
    assert "capture again" in outcome.instruction
    assert not hasattr(outcome, "verdict")
    assert not hasattr(outcome, "findings")


def test_a_quality_rejection_cannot_carry_a_verdict() -> None:
    """Structural, not behavioural: the type has nowhere to put one.

    ``extra="forbid"`` means a rejection cannot acquire a verdict field by being handed
    one, so there is no shape in which a refused capture reaches an officer looking like
    a conclusion.
    """
    with pytest.raises(ValueError):
        QualityRejection(
            reason_code=QualityReason.BLUR_EXCEEDED,
            instruction="x",
            blur_score=0.0,
            glare_ratio=0.0,
            coverage_ratio=0.0,
            verdict=Verdict.PASS,
        )


def test_a_catalogue_scan_evaluates_declared_fields() -> None:
    """The listing path is a first-class input, not an adapter over the image path."""
    record = run_catalogue_scan(
        listing(
            NET_QUANTITY="100 g",
            RETAIL_SALE_PRICE="Rs. 45.00",
            COMMON_OR_GENERIC_NAME="Biscuits",
        ),
        product_category=None,
        evaluated_at=NOW,
        subject_ref="scan-listing",
    )
    passed = {f.field for f in record.findings if f.state is FieldState.PASS}
    assert DeclarationField.NET_QUANTITY in passed
    assert DeclarationField.RETAIL_SALE_PRICE in passed
    assert record.verdict in set(Verdict)
    assert record.rule_set_version


def test_a_catalogue_scan_never_reports_a_measurement_as_passing() -> None:
    """A listing has no pixels, so no sizing rule may resolve from it.

    INSUFFICIENT_EVIDENCE rather than NOT_APPLICABLE: the obligation still exists on the
    package, we simply cannot see the package.

    Uses Rule 8(1)'s proviso rather than Rule 7(3) on purpose. Rule 7(3) is sector-gated,
    so with no confirmed category the gate settles it before the measurement builder runs
    and this test would pass against a pipeline that had none. Free space is gated by
    nothing, so the assertion lands on the code it names.
    """
    record = run_catalogue_scan(
        listing(NET_QUANTITY="100 g"),
        product_category=None,
        evaluated_at=NOW,
        subject_ref="scan-listing-measure",
    )
    sizing = [f for f in record.findings if f.rule_snapshot.rule_id == "R8-1-FREE-SPACE"]
    assert sizing
    assert FieldState.PASS not in {f.state for f in sizing}
    assert FieldState.NOT_APPLICABLE not in {f.state for f in sizing}


def test_a_listing_field_whose_role_the_key_establishes_is_not_discarded() -> None:
    """A bare country name in a listing is a declaration, not an unreadable value.

    The extraction normalisers demand prose context because on a package they are handed
    unlabelled OCR text. A catalogue record states the role in the key, so requiring
    "Made in India" of a field already keyed COUNTRY_OF_ORIGIN would report a perfectly
    clear declaration as missing.
    """
    record = run_catalogue_scan(
        listing(COUNTRY_OF_ORIGIN="India"),
        product_category=None,
        evaluated_at=NOW,
        subject_ref="scan-origin",
    )
    origin = [
        f
        for f in record.findings
        if f.field is DeclarationField.COUNTRY_OF_ORIGIN and f.rule_snapshot.rule_id == "R6-1-AA"
    ]
    assert {f.state for f in origin} == {FieldState.PASS}
    assert all(f.observed_value == "India" for f in origin)


def test_replaying_a_catalogue_scan_returns_the_same_record() -> None:
    """Deterministic by design: no clock, no model, no agent loop in the verdict path.

    A verdict an officer acted on has to be reproducible on demand, and anything reading
    the world at assembly time makes it not.
    """
    args = dict(product_category=None, evaluated_at=NOW, subject_ref="scan-repeat")
    first = run_catalogue_scan(listing(NET_QUANTITY="100 g"), **args)
    second = run_catalogue_scan(listing(NET_QUANTITY="100 g"), **args)
    assert first.model_dump_json() == second.model_dump_json()


def a_span(text: str, span_id: str, top: int) -> ExtractedSpan:
    """One line of panel text at a given vertical position."""
    return ExtractedSpan(
        span_id=span_id,
        region_id="panel",
        polygon=(
            (60.0, float(top)),
            (620.0, float(top)),
            (620.0, float(top + 34)),
            (60.0, float(top + 34)),
        ),
        text=text,
        confidence=0.93,
        source_provider=EvidenceProvider.PADDLEOCR,
    )


PANEL_SPANS = (
    a_span("Manufactured by", "s-anchor", 40),
    a_span("Acme Foods Pvt Ltd, 12 MG Road, Pune 411001", "s-address", 80),
    a_span("Net Quantity: 100 g", "s-quantity", 130),
    a_span("MRP Rs. 45.00", "s-mrp", 180),
    a_span("Best before 12 months from packing", "s-bestbefore", 230),
    a_span("Batch code XY-7741", "s-batch", 280),
)
"""A panel as vision would report it, in the shape EXT-004's binder expects: a keyword
anchor with the address cluster below it, and one line — the batch code — that answers no
Rule 6 obligation and must therefore come back unclassified."""


def scan_panel(spans=PANEL_SPANS, **overrides):
    """Run the image path over supplied spans, past the gate and the models."""
    frame = np.full((600, 800, 3), 200, dtype=np.uint8)
    cv2.rectangle(frame, (60, 60), (740, 540), (40, 40, 40), -1)
    for index in range(3):
        cv2.putText(
            frame,
            "DECLARATION TEXT",
            (90, 160 + index * 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.6,
            (230, 230, 230),
            4,
        )

    class _Detection:
        bbox = (60, 60, 680, 480)
        area = 326400
        confidence = 0.81

    kwargs = dict(
        calibration=Calibration(method=CalibrationMethod.NONE),
        product_category=None,
        evaluated_at=NOW,
        subject_ref="scan-image",
    )
    kwargs.update(overrides)
    with (
        patch("app.pipeline.orchestrator.detect_pdp", return_value=_Detection()),
        patch("app.pipeline.orchestrator.extract_panel_text", return_value=list(spans)),
    ):
        return run_image_scan(frame, **kwargs)


def test_the_image_path_binds_declarations_for_real() -> None:
    """Spans off the panel become findings about the package, not about the pipeline."""
    result = scan_panel()
    assert isinstance(result, ImageScanResult)
    passed = {f.field for f in result.verdict.findings if f.state is FieldState.PASS}
    assert DeclarationField.NET_QUANTITY in passed
    assert DeclarationField.RETAIL_SALE_PRICE in passed


def test_a_bound_address_reaches_a_finding_once_the_category_is_confirmed() -> None:
    """Rule 6(1)(a) is sector-gated, so the address only reaches a finding after routing.

    Asserted with a confirmed category on purpose. With none, the sector gate settles
    R6-1-A as INSUFFICIENT_EVIDENCE before the declaration builder runs, and this would
    pass whether or not the address was ever bound. Medical device is the category to use:
    G.S.R. 778(E) routes height, width and the panel declaration away from the packaged
    rules and leaves the name-and-address obligation exactly where it was.
    """
    result = scan_panel(product_category=ProductCategory.MEDICAL_DEVICE)
    address = next(
        f
        for f in result.verdict.findings
        if f.field is DeclarationField.NAME_AND_ADDRESS and f.rule_snapshot.rule_id == "R6-1-A"
    )
    assert address.state is FieldState.PASS
    assert "Acme Foods" in (address.observed_value or "")
    assert "s-address" in address.evidence_span_ids


def test_a_bound_finding_cites_the_spans_it_was_read_from() -> None:
    """The evidence chain points at pixels, using the ids vision minted and nothing else."""
    result = scan_panel()
    quantity = next(
        f
        for f in result.verdict.findings
        if f.field is DeclarationField.NET_QUANTITY and f.state is FieldState.PASS
    )
    assert quantity.evidence_span_ids
    minted = {span.span_id for span in PANEL_SPANS}
    assert set(quantity.evidence_span_ids) <= minted


def test_text_that_was_bound_to_nothing_is_kept() -> None:
    """Unclassified text is evidence, and is what an officer needs for a missing field.

    The batch code answers no Rule 6 obligation. Dropping it would leave every
    INSUFFICIENT_EVIDENCE finding with nothing behind it, and no way to answer "then what
    does the label actually say there?"
    """
    result = scan_panel()
    unclassified = {span.span_id for span in result.unclassified_spans}
    assert "s-batch" in unclassified
    assert result.unclassified_spans, "the binder placed everything; this proves nothing"


def test_every_span_is_conserved_across_the_stage() -> None:
    """Nothing vision read is lost: each span is cited by a finding or returned unplaced.

    Run with a confirmed category so that no declaration rule is settled by the sector gate
    before its spans can be cited — otherwise a bound address would count as neither cited
    nor unclassified, and this would be asserting something weaker than it appears to.
    """
    result = scan_panel(product_category=ProductCategory.MEDICAL_DEVICE)
    cited = {ref for f in result.verdict.findings for ref in f.evidence_span_ids}
    unplaced = {span.span_id for span in result.unclassified_spans}
    assert {span.span_id for span in PANEL_SPANS} == cited | unplaced
    assert cited and unplaced, "one side is empty; this would pass trivially"


def test_an_unbound_declaration_says_so_about_the_photograph() -> None:
    """INSUFFICIENT_EVIDENCE, and the reason no longer names an unbuilt pipeline stage."""
    result = scan_panel()
    dimensions = [
        f
        for f in result.verdict.findings
        if f.field is DeclarationField.DIMENSIONS and f.rule_snapshot.rule_id == "R6-1-F"
    ]
    assert {f.state for f in dimensions} == {FieldState.INSUFFICIENT_EVIDENCE}
    assert all(f.reason == UNBOUND_DECLARATION_REASON for f in dimensions)
    assert "EXT-004" not in UNBOUND_DECLARATION_REASON
    assert "not built" not in UNBOUND_DECLARATION_REASON


def test_two_addresses_against_one_obligation_are_both_kept() -> None:
    """Rule 6(1)(a) is one obligation, and both blocks are evidence for it.

    ``bind_spans`` returns a field per address block and says not to pick one. Grouping
    them into a single-valued mapping would drop an address an officer may need to see, so
    the finding carries both values and cites the spans behind both.
    """
    manufactured = NormalisedField(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        span_refs=("s-a",),
        normalised_value="Acme Foods Pvt Ltd, Pune 411001",
        parse_confidence=0.9,
    )
    marketed = NormalisedField(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        span_refs=("s-b",),
        normalised_value="Zenith Brands Ltd, Mumbai 400001",
        parse_confidence=0.8,
    )
    grouped = by_obligation([manufactured, marketed])
    assert grouped[DeclarationField.NAME_AND_ADDRESS] == (manufactured, marketed)
