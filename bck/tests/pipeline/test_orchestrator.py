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
from app.modules.extraction.category import DisplayCategory
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
from app.pipeline.rule_findings import UNCONFIRMED_CATEGORY_REASON

from .sector_gate import findings_for_rule

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
    sizing = findings_for_rule(record.findings, "R8-1-FREE-SPACE")
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
        for f in findings_for_rule(record.findings, "R6-1-AA")
        if f.field is DeclarationField.COUNTRY_OF_ORIGIN
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
        for f in findings_for_rule(result.verdict.findings, "R6-1-A")
        if f.field is DeclarationField.NAME_AND_ADDRESS
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
        for f in findings_for_rule(result.verdict.findings, "R6-1-F")
        if f.field is DeclarationField.DIMENSIONS
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


# --- Rule 3 reaches the chain from the spans vision actually returned ---------------------


def replacing(span_id: str, text: str):
    """``PANEL_SPANS`` with one line's text changed, positions untouched."""
    return tuple(
        a_span(text, s.span_id, int(s.polygon[0][1])) if s.span_id == span_id else s
        for s in PANEL_SPANS
    )


def test_a_thirty_kilogram_declaration_takes_the_package_out_of_chapter_ii() -> None:
    """The whole Rule 3(a) chain, from OCR text to verdict, with nothing hand-fed.

    The quantity is read off a span, normalised to a figure and a canonical unit, and
    compared against the stored threshold. Setting the scope inputs on the context directly
    — which the ``test_findings`` cases do — would leave every link between them untested.
    """
    result = scan_panel(spans=replacing("s-quantity", "Net Quantity: 30 kg"))

    assert isinstance(result, ImageScanResult)
    assert {f.state for f in result.verdict.findings} == {FieldState.NOT_APPLICABLE}
    assert result.verdict.verdict is Verdict.REVIEW
    assert result.verdict.verdict is not Verdict.PASS


def test_a_marker_printed_on_the_panel_reaches_the_scope_decision() -> None:
    """The orchestrator reads the marker off the spans vision returned.

    Says only what it proves. The marker on its own line happens to bind to
    COMMON_OR_GENERIC_NAME today, so this case alone does not establish that reading the
    raw spans rather than the bound declarations is necessary — the case that does is
    :func:`test_a_marker_the_binder_did_not_place_still_reaches_the_scope_decision`.
    """
    result = scan_panel(spans=(*PANEL_SPANS, a_span("NOT FOR RETAIL SALE", "s-marker", 330)))

    assert isinstance(result, ImageScanResult)
    assert {f.state for f in result.verdict.findings} == {FieldState.REVIEW_REQUIRED}
    assert all("Rule 3(c)" in f.reason for f in result.verdict.findings)
    assert not any(f.state is FieldState.FAIL for f in result.verdict.findings)


def test_an_ordinary_panel_triggers_no_scope_suspension() -> None:
    """The flag is computed, not stuck on. A 100 g retail pack keeps its ordinary findings.

    Paired with the test above: together they fail if the orchestrator hardcodes the marker
    flag either way, which one of them alone would not catch.
    """
    result = scan_panel()

    assert isinstance(result, ImageScanResult)
    assert not any("Rule 3" in f.reason for f in result.verdict.findings)
    assert any(f.state is FieldState.PASS for f in result.verdict.findings)


def test_an_officer_confirmation_reaches_the_image_path() -> None:
    """The Rule 3(c) confirmation travels the same route the confirmed category does."""
    result = scan_panel(institutional_or_industrial_confirmed=True)

    assert isinstance(result, ImageScanResult)
    assert {f.state for f in result.verdict.findings} == {FieldState.NOT_APPLICABLE}
    assert all("Rule 3(c)" in f.reason for f in result.verdict.findings)


def test_a_marker_the_binder_did_not_place_still_reaches_the_scope_decision() -> None:
    """Why the flag is computed from the spans and not from the bound declarations.

    Printed beside a batch code — which is how packs actually carry it — the marker binds
    to no obligation and appears in no ``NormalisedField``. Reading the flag off
    ``declared`` would miss it entirely and evaluate a bulk supply pack as a retail one,
    which is the failure this whole ticket exists to stop.

    The binder's placement was measured rather than assumed, and it owes Rule 3 nothing:
    it may classify this text differently tomorrow for reasons of its own, and the scope
    decision must not move when it does.
    """
    marker_line = "Batch XY-7741 / not for retail sale"
    result = scan_panel(spans=replacing("s-batch", marker_line))

    assert isinstance(result, ImageScanResult)
    assert marker_line in {s.text for s in result.unclassified_spans}
    assert all(
        marker_line.lower() not in (f.observed_value or "").lower() for f in result.verdict.findings
    )
    assert {f.state for f in result.verdict.findings} == {FieldState.REVIEW_REQUIRED}
    assert all("Rule 3(c)" in f.reason for f in result.verdict.findings)


FSSAI_SPAN = a_span("FSSAI Lic No. 10012345678901", "s-fssai", 330)
"""A statutory food signal, on a line the binder places against no Rule 6 obligation.

``propose_category`` reads it off ``unclassified_spans``, which is why it can propose a
category for a package whose declarations are otherwise unremarkable. The rest of
``PANEL_SPANS`` carries no category signal at all and proposes ``None`` — measured, not
assumed — so this one span is the whole difference between the two states below.
"""


def test_a_proposed_category_is_offered_to_the_officer_and_routes_nothing() -> None:
    """The load-bearing test: the machine reads "food", and the sector gate does not move.

    Both halves are needed and neither means anything alone. The first shows a live,
    confident proposal is genuinely in hand — without it the second would pass over a
    pipeline that had quietly stopped proposing anything. The second shows that having it
    changed no finding: with the category still unconfirmed, every obligation a sector
    override could move is settled by the gate exactly as it was before this call existed.

    The counts are pinned as literals measured on ``origin/main`` @ ``2817c6b`` before the
    proposal was wired in, not read back out of the code under test. Confirming ``food``
    instead of proposing it takes ``gated`` from 30 to 0 and ``insufficient`` from 53 to
    52, which is what makes this a demonstration rather than an assertion.
    """
    result = scan_panel(spans=PANEL_SPANS + (FSSAI_SPAN,), product_category=None)

    assert isinstance(result, ImageScanResult)

    proposal = result.category_proposal
    assert proposal is not None
    assert proposal.category is ProductCategory.FOOD
    assert proposal.confidence == 0.95
    assert proposal.span_refs == ("s-fssai",)

    findings = result.verdict.findings
    insufficient = [f for f in findings if f.state is FieldState.INSUFFICIENT_EVIDENCE]
    gated = [f for f in insufficient if f.reason == UNCONFIRMED_CATEGORY_REASON]

    assert len(findings) == 65
    assert len(gated) == 30, (
        "the sector gate settled a different number of obligations than it did before a "
        "proposal existed. If this fell to 0, something is routing on the proposal: the "
        "confirmed category is an officer's act and a reading must never stand in for it"
    )
    assert len(insufficient) == 53
    assert result.verdict.verdict is Verdict.REVIEW


def test_a_panel_with_no_category_signal_proposes_nothing() -> None:
    """Abstention is a reading, and it is the one the rest of this module runs under.

    ``propose_category`` returns ``None`` on missing, sparse, ambiguous or conflicting
    evidence. Asserting it here is what lets every other test in this file keep its
    meaning: they all scan ``PANEL_SPANS``, and if that panel started proposing a category
    the proposal would be present throughout without anybody having said so.
    """
    result = scan_panel()

    assert isinstance(result, ImageScanResult)
    assert result.category_proposal is None


DETERGENT_SPAN = a_span("Detergent Powder", "s-detergent", 330)
"""A display signal with no legal counterpart, on a line the binder places nowhere.

Chosen over a food line deliberately. ``household`` sits under
``non_food_packaged_goods`` in the display tree and has **no** ``ProductCategory`` member
at all, so a scan carrying it proposes no legal category while classifying a display one.
That is the pair of states that shows the two axes are independent rather than one derived
from the other — a food span would set both at once and prove nothing about which drove
which.
"""


def test_a_display_category_is_carried_on_the_response_and_routes_nothing() -> None:
    """The machine files the package on a shelf, and the sector gate does not move.

    Both halves are needed. The first shows a live classification is genuinely in hand,
    including the nested branch — ``parent_category`` and a three-segment ``path`` — so
    this cannot pass over a pipeline that had quietly stopped classifying. The second
    shows that having it changed no finding.

    The counts are the same literals
    :func:`test_a_proposed_category_is_offered_to_the_officer_and_routes_nothing` pins,
    measured before either category call was wired in, not read back out of the code under
    test. They hold here for a reason worth stating: a display classification is present
    *and* ``category_proposal`` is ``None`` on this panel, so the thirty sector-gated
    obligations are settled by the officer's unconfirmed category exactly as they are on a
    panel that reads nothing at all. If ``gated`` fell to 0, something would be routing on
    the display taxonomy — which would mean the word "detergent" had just decided which Act
    governs this package.
    """
    result = scan_panel(spans=PANEL_SPANS + (DETERGENT_SPAN,), product_category=None)

    assert isinstance(result, ImageScanResult)

    display = result.display_category
    assert display is not None
    assert display.category is DisplayCategory.HOUSEHOLD
    assert display.parent_category is DisplayCategory.NON_FOOD_PACKAGED_GOODS
    assert display.path == ("packaged_goods", "non_food_packaged_goods", "household")
    assert display.span_refs == ("s-detergent",)

    assert result.category_proposal is None, (
        "the legal axis must abstain here. If it started proposing a category off this "
        "span the two assertions below would no longer be about the display taxonomy"
    )

    findings = result.verdict.findings
    insufficient = [f for f in findings if f.state is FieldState.INSUFFICIENT_EVIDENCE]
    gated = [f for f in insufficient if f.reason == UNCONFIRMED_CATEGORY_REASON]

    assert len(findings) == 65
    assert len(gated) == 30, (
        "the sector gate settled a different number of obligations than it does without a "
        "display classification. A shelf label is not a legal category and must move "
        "nothing: packaged_food is not food, and household is not a ProductCategory at all"
    )
    assert len(insufficient) == 53
    assert result.verdict.verdict is Verdict.REVIEW


def test_a_panel_with_no_display_signal_classifies_nothing() -> None:
    """Abstention is a reading, and it is the one the rest of this module runs under.

    ``classify_display_category`` returns ``None`` where no branch scored, or where two
    scored equally. Asserting it here is what lets every other test in this file keep its
    meaning: they all scan ``PANEL_SPANS``, and if that panel started classifying the
    field would be populated throughout without anybody having said so.
    """
    result = scan_panel()

    assert isinstance(result, ImageScanResult)
    assert result.display_category is None
