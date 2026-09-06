"""The scan chain: what runs, in what order, and what each stage is allowed to conclude.

Two entry points, not one function with a mode flag. A catalogue listing is not an image
that failed to be an image — it arrives as fields rather than pixels, and modelling it as
its own path is what keeps a marketplace adapter an adapter rather than a rewrite. What
they share is the tail: the same rule evaluation, the same assembly, the same evidence.

Both are pure. No session, no clock, no identifier generation — ``evaluated_at`` is a
parameter, the way :func:`~app.pipeline.verdict.assemble_verdict` already takes one — so
replaying a scan returns the same record. A verdict an officer acted on has to be
reproducible on demand, and anything that reads the world at assembly time makes it not.

**The quality gate returns and stops.** A blurred, glared or incomplete capture yields a
:class:`QualityRejection` carrying an instruction to the officer, and nothing downstream
runs. There is no verdict for a package we could not photograph properly, and producing
one from a bad capture is how "we could not see it" becomes "it is not there".
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app.contracts import (
    CatalogueRecord,
    ContractModel,
    DeclarationField,
    EvidenceProvider,
    ExtractedSpan,
    MeasurementResult,
    NormalisedField,
    VerdictRecord,
)
from app.core import CalibrationMethod, get_settings
from app.modules.measurement import (
    calculate_pdp_area,
    measure_ink_extent,
    measure_width_to_height_ratio,
)
from app.modules.rules import ProductCategory, default_rule_set_version, load_rules
from app.modules.vision.ocr import extract_panel_text
from app.modules.vision.pdp import detect_pdp
from app.modules.vision.preprocess import quality_gate
from app.pipeline.capture import CAPTURE_INSTRUCTIONS, QualityRejection
from app.pipeline.findings import build_findings
from app.pipeline.normalisation import normalise_declaration
from app.pipeline.rule_findings import EvidenceContext
from app.pipeline.verdict import assemble_verdict

EXT_004_REASON = (
    "spans were read from the panel but not bound to a declaration: extraction span "
    "classification and spatial role binding (EXT-004) is not built. This is a gap in "
    "this system, not a finding about the package."
)
"""What a missing declaration means on the image path today.

``app.modules.extraction`` normalises nine kinds of declaration and exposes nothing that
maps OCR spans to the obligation each answers, so every declaration on the image path is
INSUFFICIENT_EVIDENCE carrying this text. It names the ticket and the stage deliberately:
an officer or a court reading the output can tell "we could not read this label" apart
from "this pipeline stage is not built yet", and those are different statements.

When EXT-004 lands, :func:`run_image_scan` binds spans and passes the reason a real
absence deserves instead. The test asserting this exact string goes red that day, which is
the signal to delete it.
"""


class PanelDetection(ContractModel):
    """Where the principal display panel was found, and how sure the detector was."""

    bbox: tuple[int, int, int, int]
    area_px: int
    confidence: float


class ImageScanResult(ContractModel):
    """A completed image scan: the verdict, and the evidence it was reached from.

    The spans travel with the record deliberately. Every declaration is currently
    INSUFFICIENT_EVIDENCE because nothing binds spans to obligations, and an officer
    reading that finding should still be able to see what the panel actually said — the
    text was read, and withholding it because we could not classify it would throw away
    the one piece of evidence the scan did produce.

    **The spans are exactly what vision returned, field for field.** ``app.modules.vision``
    mints every ``span_id`` and sets every ``source_provider``, and this package changes
    neither — a second identifier minted here would make ``evidence_span_ids`` cite a span
    that nothing else in the record can find. Nothing in ``app.pipeline`` constructs an
    :class:`~app.contracts.ExtractedSpan` at all, and a structural test asserts that it
    stays that way.

    ``region_id`` is left alone too, including the constant ``"panel"`` vision currently
    writes. See :func:`run_image_scan` for why overwriting it would put a false statement
    into the evidence chain rather than a more precise one.
    """

    verdict: VerdictRecord
    spans: tuple[ExtractedSpan, ...]
    panel: PanelDetection


@dataclass(frozen=True)
class Calibration:
    """What basis, if any, exists for measuring this scan in millimetres."""

    method: CalibrationMethod
    reference_type: str | None = None
    """The reference object in frame — as ``app.modules.measurement`` names it."""

    artwork_dpi: float | None = None
    """Resolution of supplied pre-print artwork, where the basis is artwork."""


def _measurements(image: np.ndarray, calibration: Calibration) -> Mapping[str, MeasurementResult]:
    """Run every measurement the rules need, keyed by the condition kind that needs it.

    Every measurement runs. None is skipped on the grounds that it will probably refuse:
    the measurement module decides whether a basis exists, and it decides it the same way
    every time by looking at what it was actually given. Without a reference object or
    artwork each of these returns a
    :class:`~app.contracts.MeasurementRefusal`, which carries a reason and has no field
    that could hold a millimetre figure.
    """
    is_artwork = calibration.method is CalibrationMethod.ARTWORK
    reference = image if calibration.method is CalibrationMethod.REFERENCE_OBJECT else None
    common = {
        "ref_image": reference,
        "ref_type": calibration.reference_type,
        "is_artwork": is_artwork,
        "artwork_dpi": calibration.artwork_dpi,
    }
    return {
        "table_height": measure_ink_extent(image, **common),
        "width_ratio": measure_width_to_height_ratio(image, **common),
        "pdp_area": calculate_pdp_area(image, **common),
        # Rule 8(1)'s proviso compares four clearances against the numeral's own height.
        # measure_margins needs a declaration bounding box to measure around, and binding
        # a declaration to a box is EXT-004. Until then there is nothing to measure from,
        # which the rule's finding reports as INSUFFICIENT_EVIDENCE rather than as a pass.
    }


def run_image_scan(
    image: np.ndarray,
    *,
    calibration: Calibration,
    product_category: ProductCategory | None,
    evaluated_at: datetime,
    subject_ref: str,
) -> QualityRejection | ImageScanResult:
    """Evaluate a photographed package, or refuse the capture and say why.

    Runs the whole chain in order — quality gate, panel detection, OCR, declaration
    binding, normalisation, measurement, rule evaluation, assembly. No stage is skipped
    and no stage is substituted; where a stage has nothing to give, the findings say so in
    their own words rather than the chain routing around it.

    **Why this does not overwrite ``region_id``.** Vision writes the constant ``"panel"``
    on every span, which is less specific than a reference to the detected panel — but
    replacing it with one would be a *false* statement rather than a sharper one, because
    ``extract_panel_text`` is handed the whole frame and not a crop of the detection below.
    The spans have not been read off the principal display panel; they have been read off
    the photograph. Stamping the panel's identity on them would assert a provenance the
    pipeline did not establish, in the one field an evidence bundle uses to show an officer
    which crop a value came from.

    Two further reasons to leave it, either of which would be enough on its own. The field
    belongs to vision, which is the only layer that knows which image it read; and the
    moment vision emits spans from more than one region — a side panel, a separate
    declaration block, which is what ``ExtractedSpan.region_id`` exists for — a pipeline
    that overwrote every span with a single value would erase exactly the distinction the
    field was added to carry, silently and at the point it started to matter.

    Where the panel *was* detected is recorded once, on
    :attr:`ImageScanResult.panel`, which is the honest place for it: that is a statement
    about the detection, not about where each run of text was found. Making ``"panel"``
    true means cropping the frame to the detection before the OCR call and translating the
    resulting polygons back into full-image coordinates so an overlay still lines up. That
    is vision's work, and it is written up in ``TODO.md`` rather than half-done here.
    """
    quality = quality_gate(image)
    if not quality.is_valid:
        return QualityRejection(
            reason_code=quality.reason_code,
            instruction=CAPTURE_INSTRUCTIONS[quality.reason_code],
            blur_score=quality.blur_score,
            glare_ratio=quality.glare_ratio,
            coverage_ratio=quality.coverage_ratio,
        )

    settings = get_settings()
    detection = detect_pdp(image, str(settings.pdp_weights_path))
    # Positional, deliberately: VIS-003 renamed these to text_detection_model_dir and
    # text_recognition_model_dir without changing their order or meaning, so a positional
    # call is correct against both signatures.
    spans = tuple(
        extract_panel_text(image, str(settings.ocr_det_model_dir), str(settings.ocr_rec_model_dir))
    )

    # The extraction seam. `spans` is what the panel actually says; nothing yet resolves
    # which declaration each run of text answers, so no declaration is established and
    # every one of them is INSUFFICIENT_EVIDENCE below. One line changes when EXT-004
    # lands: `declared = _bind(spans)`.
    declared: dict[DeclarationField, NormalisedField] = {}

    context = EvidenceContext(
        rule_set_version=default_rule_set_version(),
        evaluation_date=evaluated_at.date(),
        declared=declared,
        measurements=_measurements(image, calibration),
        product_category=product_category,
        source_is_listing=False,
        unreadable_reason=EXT_004_REASON,
    )
    findings = build_findings(load_rules(), context)
    return ImageScanResult(
        verdict=assemble_verdict(
            subject_ref=subject_ref,
            findings=findings,
            rule_set_version=context.rule_set_version,
            evaluated_at=evaluated_at,
            field_providers=dict.fromkeys(declared, EvidenceProvider.PADDLEOCR),
        ),
        spans=spans,
        panel=PanelDetection(
            bbox=detection.bbox, area_px=detection.area, confidence=detection.confidence
        ),
    )


def run_catalogue_scan(
    record: CatalogueRecord,
    *,
    product_category: ProductCategory | None,
    evaluated_at: datetime,
    subject_ref: str,
) -> VerdictRecord:
    """Evaluate a structured listing.

    No quality gate, no panel detection, no OCR and no measurement — a listing has no
    pixels, and running a blur check over a dictionary would be theatre. Those stages are
    absent rather than stubbed, and the rules that depend on them report
    INSUFFICIENT_EVIDENCE with the reason that a listing carries no pixels, which is true.

    ``unreadable_reason`` is ``None`` here, and that is the substantive difference from
    the image path: a declaration absent from ``declared_fields`` was not declared in the
    listing, which is a finding about the listing rather than a gap in our reading of it.
    """
    declared: dict[DeclarationField, NormalisedField] = {}
    for field, text in record.declared_fields.items():
        span_ref = f"listing:{record.listing_id}:{field.value}"
        value = normalise_declaration(field, text, (span_ref,), identity_established=True)
        if value is not None:
            declared[field] = value

    context = EvidenceContext(
        rule_set_version=default_rule_set_version(),
        evaluation_date=evaluated_at.date(),
        declared=declared,
        measurements={},
        product_category=product_category,
        source_is_listing=True,
        unreadable_reason=None,
    )
    findings = build_findings(load_rules(), context)
    return assemble_verdict(
        subject_ref=subject_ref,
        findings=findings,
        rule_set_version=context.rule_set_version,
        evaluated_at=evaluated_at,
        field_providers=dict.fromkeys(declared, EvidenceProvider.CATALOGUE),
    )
