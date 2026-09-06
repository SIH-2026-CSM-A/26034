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

import numpy as np
import pytest

from app.contracts import CatalogueRecord, DeclarationField, FieldState, Verdict
from app.core import CalibrationMethod
from app.modules.vision.preprocess import QualityReason
from app.pipeline.capture import CAPTURE_INSTRUCTIONS, QualityRejection
from app.pipeline.orchestrator import (
    EXT_004_REASON,
    Calibration,
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


def test_the_ext_004_refusal_names_the_stage_that_is_not_built() -> None:
    """The reason distinguishes an unreadable label from an unbuilt pipeline stage.

    **This test is deleted the day EXT-004 lands**, and it goes red that day, which is the
    signal. An officer or a court reading INSUFFICIENT_EVIDENCE must be able to tell "we
    could not read this package" from "this system does not do that yet".
    """
    assert "EXT-004" in EXT_004_REASON
    assert "not a finding about the package" in EXT_004_REASON


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
