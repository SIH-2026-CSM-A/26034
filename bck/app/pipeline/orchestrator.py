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

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TypeVar

import numpy as np

from app.contracts import (
    CatalogueRecord,
    CategoryProposal,
    CompetingReadings,
    ContractModel,
    DeclarationField,
    EvidenceProvider,
    ExtractedSpan,
    FieldFinding,
    FieldState,
    MeasurementCalibrated,
    MeasurementExact,
    MeasurementMarginOverlapCalibrated,
    MeasurementMarginOverlapExact,
    MeasurementRefusal,
    MeasurementResult,
    NormalisedField,
    VerdictRecord,
)
from app.core import CalibrationMethod, get_settings
from app.modules.extraction import bind_spans, propose_category
from app.modules.extraction.binder import (
    BboxRefusal,
    bbox_refusal_officer_reason,
    get_declaration_bbox,
)
from app.modules.extraction.category import DisplayCategoryTaxonomy, classify_display_category
from app.modules.extraction.unit_sale_price import normalise_unit_sale_price
from app.modules.measurement import (
    MeasurementMarginSet,
    PackageShape,
    calculate_artwork_pdp_area,
    measure_artwork_ink_extent,
    measure_declaration_contrast,
    measure_ink_extent,
    measure_margins,
    measure_panel_dimensions,
    measure_width_to_height_ratio,
    parse_pdf_geometry,
    parse_svg_geometry,
    rasterise_artwork,
    segment_declaration_glyphs,
)
from app.modules.rules import (
    FreeSpaceMeasurement,
    ProductCategory,
    RuleDefinition,
    SideClearance,
    SideOverlap,
    Verdict,
    WidthRatioResult,
    calculate_cylindrical_pdp_area,
    calculate_other_shape_pdp_area,
    calculate_rectangular_pdp_area,
    chapter_ii_scope,
    declarations_governed_by_rule,
    default_rule_set_version,
    evaluate_rule7_width,
    evaluate_rule8_free_space,
    evaluate_unit_sale_price_basis,
    known_unit_sale_price_bases,
    load_rules,
    not_for_retail_sale_declared,
    pdp_declaration_mandatory,
    required_declaration_location,
    rule7_governs_field,
    rule_33_relaxation_applies,
    select_effective_rule,
)
from app.modules.tamper import detect_tampering
from app.modules.tamper.domain import TamperDetectionResult
from app.modules.vision.ocr import arbitrate_field_declaration, extract_panel_text
from app.modules.vision.pdp import ArtworkPanel, OfficerMarkedPanel, PDPDetection, detect_pdp
from app.modules.vision.preprocess import prepare_panel, quality_gate
from app.pipeline.capture import CAPTURE_INSTRUCTIONS, QualityRejection
from app.pipeline.dispositions import FIELD_STATE_FROM_VERDICT, required_declarations
from app.pipeline.findings import build_findings
from app.pipeline.normalisation import normalise_declaration
from app.pipeline.rule_findings import EvidenceContext, finding, scope_findings, sector_findings
from app.pipeline.verdict import assemble_verdict

UNBOUND_DECLARATION_REASON = (
    "the panel was read, and no text on it was bound to this declaration. That is not the "
    "same as the declaration being absent: it may be present and unreadable — glared, cut "
    "off by the crop, or too small to resolve — and an officer should look before anything "
    "follows from it."
)
"""What a declaration with no bound field means on the image path.

Binding is real, so this is a statement about the photograph rather than about a missing
pipeline stage. It stays INSUFFICIENT_EVIDENCE rather than becoming FAIL for a reason that
survives the binder being good: nothing here can tell a declaration that was never printed
from one that was printed and not read, and only the first of those can support
enforcement.

The unbound text is not thrown away. Every span the binder could not place travels on
:attr:`ImageScanResult.unclassified_spans` and into the evidence record, because it is
exactly what an officer needs when the system says a declaration is missing.
"""


class PanelDetection(ContractModel):
    """Where the principal display panel was found, and how sure the detector was."""

    bbox: tuple[int, int, int, int]
    area_px: int
    confidence: float
    method: str
    """Where the box came from: a model, the largest block of print, artwork, or an officer."""


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
    """Every span vision read, whether the binder placed it or not."""

    unclassified_spans: tuple[ExtractedSpan, ...] = ()
    """The spans the binder could not place against any declaration.

    Kept, and written into the evidence record. Text that was read and bound to nothing is
    evidence in its own right, and it is precisely what an officer needs when the system
    reports a declaration missing: the answer to "then what does the label actually say
    there?" Discarding it would leave an INSUFFICIENT_EVIDENCE finding with nothing behind
    it.
    """

    panel: PanelDetection

    tamper_signals: tuple[TamperDetectionResult, ...] = ()
    """Every tamper signal raised on this capture, whether or not it touched a finding.

    **Evidence, never a conclusion.** A signal can move a declaration that read as present
    to REVIEW_REQUIRED and can do nothing else — see :func:`_doubted`. Both detectors are
    uncalibrated heuristics, and the sticker one is loud: on the four untampered captures in
    ``datasets/raw`` it raised between 6 and 22 signals each (2026-09-17). Most of those sit
    on text bound to no declaration and so change no finding; they are all kept here because
    an officer looking at a suspected overlay needs to see where the detector looked.
    """

    category_proposal: CategoryProposal | None = None
    """A product category read off the label, offered to an officer and acted on by nothing.

    **Not a confirmation, and it never becomes one.** The confirmed category reaches this
    chain as :func:`run_image_scan`'s own ``product_category`` parameter, which comes from
    the request boundary and from nowhere else; this field is a separate value that travels
    beside it. Nothing downstream reads it — not the sector gate, not
    :class:`~app.pipeline.rule_findings.EvidenceContext`, not the verdict — because an
    obligation a sector override could move stays INSUFFICIENT_EVIDENCE until a person says
    which Act governs the package, and a reading that routed itself would answer that
    question on their behalf.

    ``None`` where the evidence is missing, sparse, ambiguous or conflicting across
    categories. That is :func:`~app.modules.extraction.propose_category` abstaining, which
    is a reading in its own right and not a failure to produce one.
    """

    display_category: DisplayCategoryTaxonomy | None = None
    """Where this package belongs in a browsing taxonomy. A presentation axis, nothing more.

    **This is not** :class:`~app.modules.rules.ProductCategory` **and it never becomes one.**
    They answer different questions. ``ProductCategory`` says which Act governs the package,
    and the sector gate dispatches obligations on it; this says which shelf a person would
    look on. ``packaged_food`` and ``food`` are not the same claim, and letting a display
    label reach the sector gate would change which rules apply on the strength of the word
    "shampoo".

    So nothing downstream reads it — not the sector gate, not
    :class:`~app.pipeline.rule_findings.EvidenceContext`, not the verdict. It travels beside
    ``category_proposal`` and is subject to the same rule as that field: an obligation a
    sector override could move stays INSUFFICIENT_EVIDENCE until a person confirms the
    category, and neither of these readings is that person.

    ``None`` where no display signal was read, or where two branches of the taxonomy scored
    equally. That is
    :func:`~app.modules.extraction.category.classify_display_category` abstaining, which is a
    reading in its own right and not a failure to produce one.
    """


@dataclass(frozen=True)
class Calibration:
    """What basis, if any, exists for measuring this scan in millimetres."""

    method: CalibrationMethod
    reference_type: str | None = None
    """The reference object in frame — as ``app.modules.measurement`` names it."""

    artwork_dpi: float | None = None
    """Resolution of supplied pre-print artwork, where the basis is artwork."""


Region = tuple[int, int, int, int]
"""``(x, y, width, height)`` on the frame as photographed."""

GLYPH_PADDING_PX = 2
"""Background left around a segmented glyph before it is measured. A glyph cut exactly to
its ink — the stem of an "l" — is a uniform crop, and no threshold can find ink in one."""

TABLE_HEIGHT_CLAUSE = "Rule 7(2), Table-I"
WIDTH_RATIO_CLAUSE = "Rule 7(3)"
PLACEMENT_CLAUSE = "Rule 8(1)"
FREE_SPACE_CLAUSE = "Rule 8(1) proviso"
MANNER_CLAUSE = "Rule 9(1)"
UNIT_SALE_PRICE_CLAUSE = "Rule 6(11)"
"""The clauses this module evaluates from geometry, as the store names them. Looked up by
clause and date through :func:`~app.modules.rules.select_effective_rule` rather than by
rule id, so an amended version of any of them is picked up without an edit here."""


@dataclass(frozen=True)
class PackageConfirmations:
    """What an officer has confirmed about the package that no photograph establishes.

    Every field defaults to confirming nothing. The same shape, and the same reason, as
    ``product_category``: each of these is a determination about the package, and a
    pipeline that guessed one would be making it.
    """

    shape: PackageShape = PackageShape.RECTANGULAR
    """Which limb of Rule 7(4) computes the principal display panel area."""

    declarations_required_under_other_law: bool = False
    """Rule 7(5): the package's declarations are also required by or under another law."""

    rule_33_relaxation_granted: bool = False
    """An order under Rule 33 relaxing these Rules for this package has been recorded."""

    panel_bbox: tuple[int, int, int, int] | None = None
    """Where the officer marked the principal display panel on the capture, as ``(x, y, w, h)``
    in the photograph's own pixels. Rule 7(2) Table-I bands against its area, measured
    through the same calibration as every other millimetre. ``None`` marks nothing, and the
    panel is then whatever ``detect_pdp`` reports."""


NOTHING_CONFIRMED = PackageConfirmations()
"""The default for every scan: a rectangular package about which nothing has been confirmed."""


@dataclass(frozen=True)
class _Geometry:
    """Everything measured around the quantity declaration and the detected panel."""

    quantity_region: Region | MeasurementRefusal
    numeral_height: MeasurementResult
    panel_area: MeasurementResult
    margins: MeasurementMarginSet | MeasurementRefusal
    glyph_ratios: tuple[tuple[str, MeasurementResult], ...] | MeasurementRefusal
    regions: Mapping[DeclarationField, Region]
    contrast: Mapping[DeclarationField, MeasurementResult]


def _region_of(
    field: NormalisedField, spans: Sequence[ExtractedSpan]
) -> Region | MeasurementRefusal:
    box = get_declaration_bbox(field, spans)
    if isinstance(box, BboxRefusal):
        return MeasurementRefusal(
            reason=(
                "the declaration could not be located on the frame, so there is nothing to "
                f"measure around: {bbox_refusal_officer_reason(box)}."
            )
        )
    min_x, min_y, max_x, max_y = box
    x, y = math.floor(min_x), math.floor(min_y)
    return x, y, math.ceil(max_x) - x, math.ceil(max_y) - y


def _calibration_arguments(image: np.ndarray, calibration: Calibration) -> dict:
    return {
        "ref_image": image if calibration.method is CalibrationMethod.REFERENCE_OBJECT else None,
        "ref_type": calibration.reference_type,
        "is_artwork": calibration.method is CalibrationMethod.ARTWORK,
        "artwork_dpi": calibration.artwork_dpi,
    }


def _quantity_glyphs(
    image: np.ndarray, field: NormalisedField, spans: Sequence[ExtractedSpan]
) -> tuple[tuple[str, Region], ...] | MeasurementRefusal:
    """Every printed character of the quantity declaration, span by span.

    Segmented per span rather than over the declaration's whole box: glyphs are paired with
    characters left to right, which only means something along one line of print.
    """
    by_id = {span.span_id: span for span in spans}
    glyphs: list[tuple[str, Region]] = []
    for span_id in field.span_refs:
        span = by_id[span_id]
        region = _region_of(field.model_copy(update={"span_refs": (span_id,)}), spans)
        if isinstance(region, MeasurementRefusal):
            return region
        found = segment_declaration_glyphs(image, region, span.text)
        if isinstance(found, MeasurementRefusal):
            return found
        glyphs.extend(found)
    return tuple(glyphs)


def _padded(region: Region) -> Region:
    x, y, w, h = region
    return (
        x - GLYPH_PADDING_PX,
        y - GLYPH_PADDING_PX,
        w + 2 * GLYPH_PADDING_PX,
        h + 2 * GLYPH_PADDING_PX,
    )


def _panel_area(
    image: np.ndarray,
    detection: PDPDetection,
    calibration: Calibration,
    shape: PackageShape,
) -> MeasurementResult:
    """Rule 7(4): the area of the panel ``detect_pdp`` found, by the limb for this shape.

    The panel, not the frame. Table-I bands a character height against this figure, and a
    photograph is always larger than the panel in it, so the frame's area moved every
    package into a higher band and demanded taller print than the rule does.

    Measurement supplies the dimensions and the rule store supplies the formula, including
    the 40 per cent of limbs (b) and (c): a multiplier written into this file would be one
    no gazette backs.
    """
    if shape is PackageShape.CYLINDRICAL:
        return MeasurementRefusal(
            reason=(
                "Rule 7(4)(b) computes a cylindrical package's panel area from the height of "
                "the package and its circumference, and a photograph of one face shows "
                "neither."
            )
        )
    if detection.method == "heuristic":
        # The heuristic region is the largest block of print, which on a tabletop capture
        # is the frame with the coin in it. Table-I's band is a legal threshold, so an area
        # the system did not measure must not select one. The character height is still
        # measured and reported; only the band is refused. An officer's mark is not this
        # case: it is a stated boundary, measured below like a model's.
        return MeasurementRefusal(
            reason=(
                "the principal display panel was not detected: no trained panel detector is "
                "configured, and the largest block of print is not a measured panel, so its "
                "area cannot band the requirement."
            )
        )
    height, width = measure_panel_dimensions(
        image, detection.bbox, **_calibration_arguments(image, calibration)
    )
    if isinstance(height, MeasurementRefusal):
        return height
    if isinstance(width, MeasurementRefusal):
        return width
    rectangle_cm2 = calculate_rectangular_pdp_area(
        Decimal(str(height.value)) / 10, Decimal(str(width.value)) / 10
    )
    if shape is PackageShape.RECTANGULAR:
        area, limb = rectangle_cm2, "rectangular"
    else:
        area = calculate_other_shape_pdp_area(legally_applicable_pdp_area=rectangle_cm2)
        limb = "other: the area considered to be the principal display panel"
    if isinstance(height, MeasurementCalibrated) and isinstance(width, MeasurementCalibrated):
        relative = (
            height.confidence_interval / height.value + width.confidence_interval / width.value
        )
        return MeasurementCalibrated(
            value=float(area),
            confidence_interval=float(area) * relative,
            unit="cm²",
            reference_object=height.reference_object,
            rule_limb=limb,
        )
    return MeasurementExact(value=float(area), unit="cm²", rule_limb=limb)


def _measure(
    image: np.ndarray,
    *,
    calibration: Calibration,
    detection: PDPDetection,
    declared: Mapping[DeclarationField, tuple[NormalisedField, ...]],
    spans: Sequence[ExtractedSpan],
    shape: PackageShape,
    panel_area: MeasurementResult | None = None,
) -> _Geometry:
    """Run every measurement the rules need, around the declaration each rule is about.

    Every measurement runs. None is skipped on the grounds that it will probably refuse:
    the measurement module decides whether a basis exists, and it decides it the same way
    every time by looking at what it was actually given. Without a reference object or
    artwork each of these returns a :class:`~app.contracts.MeasurementRefusal`, which
    carries a reason and has no field that could hold a millimetre figure.

    All of it is taken from the frame as photographed. The prepared image OCR read may have
    been deskewed; spans are mapped back before they reach here, so a box and the pixels
    under it are always the same picture.

    ``panel_area`` is supplied where the panel's area is known better than the frame can
    say — from vector artwork — and otherwise measured from the detected panel.
    """
    common = _calibration_arguments(image, calibration)
    if panel_area is None:
        panel_area = _panel_area(image, detection, calibration, shape)
    regions: dict[DeclarationField, Region] = {}
    for field_type, fields in declared.items():
        region = _region_of(fields[0], spans)
        if not isinstance(region, MeasurementRefusal):
            regions[field_type] = region

    quantity = declared.get(DeclarationField.NET_QUANTITY, ())
    quantity_region: Region | MeasurementRefusal = (
        _region_of(quantity[0], spans)
        if quantity
        else MeasurementRefusal(
            reason=(
                "no net quantity declaration was bound on this capture, so there is no "
                "declaration to measure."
            )
        )
    )
    if isinstance(quantity_region, MeasurementRefusal):
        return _Geometry(
            quantity_region=quantity_region,
            numeral_height=quantity_region,
            panel_area=panel_area,
            margins=quantity_region,
            glyph_ratios=quantity_region,
            regions=regions,
            contrast={f: measure_declaration_contrast(image, r) for f, r in regions.items()},
        )

    glyphs = _quantity_glyphs(image, quantity[0], spans)
    numeral_height: MeasurementResult
    glyph_ratios: tuple[tuple[str, MeasurementResult], ...] | MeasurementRefusal
    if isinstance(glyphs, MeasurementRefusal):
        numeral_height, glyph_ratios = glyphs, glyphs
    else:
        heights = [
            measure_ink_extent(image, region=_padded(region), **common)
            for character, region in glyphs
            if character.isdigit()
        ]
        measured = [h for h in heights if not isinstance(h, MeasurementRefusal)]
        if measured:
            # The shortest numeral: "the height of any numeral" is met only if every one is.
            numeral_height = min(measured, key=lambda h: h.value)
        else:
            numeral_height = next(
                iter(heights),
                MeasurementRefusal(reason="the quantity declaration was read with no numeral."),
            )
        glyph_ratios = tuple(
            (character, measure_width_to_height_ratio(image, region=_padded(region), **common))
            for character, region in glyphs
            if character.isalnum()
        )

    return _Geometry(
        quantity_region=quantity_region,
        numeral_height=numeral_height,
        panel_area=panel_area,
        margins=measure_margins(image, quantity_region, **common),
        glyph_ratios=glyph_ratios,
        regions=regions,
        contrast={f: measure_declaration_contrast(image, r) for f, r in regions.items()},
    )


def _cited(context: EvidenceContext, field: DeclarationField) -> tuple[str, ...]:
    """The spans behind the declaration a geometric finding was measured on."""
    declared = context.declared.get(field, ())
    return declared[0].span_refs if declared else ()


def _describe(result: MeasurementResult) -> str:
    """A measured figure with its unit and, where it has one, its interval."""
    if isinstance(result, (MeasurementMarginOverlapExact, MeasurementMarginOverlapCalibrated)):
        text = f"overlap {result.overlap:.2f} {result.unit}"
    else:
        text = f"{result.value:.2f} {result.unit}"
    interval = getattr(result, "confidence_interval", None)
    return text if interval is None else f"{text} (±{interval:.2f})"


def _straddles(value: float, interval: float | None, threshold: float) -> bool:
    """Whether a calibrated figure's interval contains the threshold it is compared with."""
    return interval is not None and abs(value - threshold) <= interval


WITHIN_UNCERTAINTY = (
    " The measured figure is within the calibration's own uncertainty of the requirement, "
    "so which side of it the package falls on is not established by this capture."
)


def _free_space_finding(
    rule: RuleDefinition, context: EvidenceContext, geometry: _Geometry
) -> FieldFinding:
    """Rule 8(1) proviso, from four measured clearances and the numeral's own height."""
    field = DeclarationField.NET_QUANTITY
    margins, numeral = geometry.margins, geometry.numeral_height
    # The clearances before the numeral: with no calibration both refuse, and "there is no
    # reference object" is the reason an officer can act on.
    candidates: tuple[MeasurementResult, ...] = (
        (margins,)
        if isinstance(margins, MeasurementRefusal)
        else (margins.above, margins.below, margins.left, margins.right)
    )
    refused = next((r for r in (*candidates, numeral) if isinstance(r, MeasurementRefusal)), None)
    if refused is not None:
        return finding(
            rule,
            field,
            FieldState.INSUFFICIENT_EVIDENCE,
            f"the measurement this rule needs was not made: {refused.reason}",
            context,
        )

    def side(result: MeasurementResult) -> SideClearance | SideOverlap:
        if isinstance(result, (MeasurementMarginOverlapExact, MeasurementMarginOverlapCalibrated)):
            return SideOverlap(overlap_mm=Decimal(str(result.overlap)))
        return SideClearance(distance_mm=Decimal(str(result.value)))

    sides = {
        "above": margins.above,
        "below": margins.below,
        "left": margins.left,
        "right": margins.right,
    }
    evaluation = evaluate_rule8_free_space(
        FreeSpaceMeasurement(
            numeral_height_mm=Decimal(str(numeral.value)),
            space_above=side(margins.above),
            space_below=side(margins.below),
            space_left=side(margins.left),
            space_right=side(margins.right),
        )
    )
    required = {
        "above": evaluation.required_above_below_mm,
        "below": evaluation.required_above_below_mm,
        "left": evaluation.required_left_right_mm,
        "right": evaluation.required_left_right_mm,
    }
    uncertain = any(
        _straddles(
            result.value, getattr(result, "confidence_interval", None), float(required[name])
        )
        for name, result in sides.items()
        if hasattr(result, "value")
    )
    state = FIELD_STATE_FROM_VERDICT[evaluation.verdict]
    if evaluation.deficient_sides:
        reason = (
            "the free space around the quantity declaration was measured and falls short of "
            f"the proviso on: {', '.join(evaluation.deficient_sides)}."
        )
        if evaluation.overlapping_sides:
            reason += (
                " Printed information crosses into the declaration's own space on: "
                f"{', '.join(evaluation.overlapping_sides)}."
            )
    else:
        reason = (
            "the free space around the quantity declaration was measured on all four sides "
            "and meets the proviso."
        )
    if uncertain and not evaluation.overlapping_sides:
        state, reason = FieldState.REVIEW_REQUIRED, reason + WITHIN_UNCERTAINTY
    return finding(
        rule,
        field,
        state,
        reason,
        context,
        observed_value="; ".join(
            [f"numeral height {_describe(numeral)}"]
            + [f"{name} {_describe(result)}" for name, result in sides.items()]
        ),
        expected_value=(
            f"above and below at least {evaluation.required_above_below_mm:.2f} mm; "
            f"left and right at least {evaluation.required_left_right_mm:.2f} mm"
        ),
        evidence_span_ids=_cited(context, field),
    )


def _width_ratio_finding(
    rule: RuleDefinition, context: EvidenceContext, geometry: _Geometry
) -> FieldFinding:
    """Rule 7(3), one printed character at a time, with its named exemptions applied."""
    field = DeclarationField.NET_QUANTITY
    ratios = geometry.glyph_ratios
    refused = (
        ratios
        if isinstance(ratios, MeasurementRefusal)
        else next((r for _, r in ratios if isinstance(r, MeasurementRefusal)), None)
    )
    if refused is not None or not ratios:
        reason = refused.reason if refused is not None else "no letter or numeral was isolated."
        return finding(
            rule,
            field,
            FieldState.INSUFFICIENT_EVIDENCE,
            f"the measurement this rule needs was not made: {reason}",
            context,
        )

    minimum = float(rule.conditions.minimum_width_to_height_ratio)
    narrow: list[str] = []
    uncertain = False
    verdicts: list[Verdict] = []
    for character, ratio in ratios:
        evaluation = evaluate_rule7_width(
            character=character,
            width=Decimal(str(ratio.value)),
            height=Decimal(1),
            product_category=context.product_category,
            evaluation_date=context.evaluation_date,
        )
        verdicts.append(evaluation.verdict)
        if evaluation.ratio_result is WidthRatioResult.EXEMPT:
            continue
        if evaluation.ratio_result is WidthRatioResult.DOES_NOT_MEET:
            narrow.append(f"{character!r} at {ratio.value:.2f}")
        uncertain = uncertain or _straddles(
            ratio.value, getattr(ratio, "confidence_interval", None), minimum
        )

    if any(v is Verdict.POTENTIAL_VIOLATION for v in verdicts):
        verdict = Verdict.POTENTIAL_VIOLATION
    elif any(v is Verdict.REVIEW for v in verdicts):
        verdict = Verdict.REVIEW
    else:
        verdict = Verdict.PASS
    state = FIELD_STATE_FROM_VERDICT[verdict]
    reason = (
        f"each letter and numeral of the quantity declaration was measured; narrower than "
        f"one third of its height: {', '.join(narrow)}."
        if narrow
        else "each letter and numeral of the quantity declaration was measured, and every "
        "one not exempted by name is at least one third as wide as it is tall."
    )
    if uncertain:
        state, reason = FieldState.REVIEW_REQUIRED, reason + WITHIN_UNCERTAINTY
    return finding(
        rule,
        field,
        state,
        reason,
        context,
        observed_value=", ".join(f"{character}={ratio.value:.2f}" for character, ratio in ratios),
        expected_value=(
            f"width at least {minimum:.2f} of height, except "
            f"{', '.join(rule.conditions.exempt_characters)}"
        ),
        evidence_span_ids=_cited(context, field),
    )


def _placement_finding(
    rule: RuleDefinition,
    field: DeclarationField,
    context: EvidenceContext,
    region: Region,
    detection: PDPDetection,
) -> FieldFinding:
    """Rule 8(1): whether a located declaration lies inside the detected panel.

    Never FAIL. A detector's box is where a model or a heuristic drew the panel, not where
    the panel is, so a declaration outside it is a reason for an officer to look and not
    evidence that the package is wrong. Inside a *model's* box, inside artwork submitted
    as the panel, or inside the panel an officer marked, supports PASS; the heuristic finds
    the largest block of print, which is frequently the panel and sometimes the
    ingredients list, so it supports nothing on its own.
    """
    x, y, w, h = region
    px, py, pw, ph = detection.bbox
    inside = px <= x and py <= y and x + w <= px + pw and y + h <= py + ph
    if inside and detection.method == "artwork":
        state = FIELD_STATE_FROM_VERDICT[Verdict.PASS]
        reason = "the declaration lies within the artwork submitted as the principal display panel."
    elif inside and detection.method == "model":
        state = FIELD_STATE_FROM_VERDICT[Verdict.PASS]
        reason = "the declaration lies within the principal display panel the detector located."
    elif inside and detection.method == "officer":
        state = FIELD_STATE_FROM_VERDICT[Verdict.PASS]
        reason = "the declaration lies within the principal display panel the officer marked."
    elif detection.method == "officer":
        state = FieldState.REVIEW_REQUIRED
        reason = (
            "the declaration was read outside the panel the officer marked. The mark is the "
            "officer's own, so this is a reason to look at the package and at the mark, and "
            "not a finding that the declaration is misplaced."
        )
    elif inside:
        state = FieldState.REVIEW_REQUIRED
        reason = (
            "the declaration lies within the largest block of print on the frame. No trained "
            "panel detector is configured, so whether that block is the principal display "
            "panel is for an officer to say."
        )
    else:
        state = FieldState.REVIEW_REQUIRED
        reason = (
            "the declaration was read outside the region located as the principal display "
            "panel. That region is a detection and not a determination, so this is a reason "
            "to look at the package and not a finding that the declaration is misplaced."
        )
    return finding(
        rule,
        field,
        state,
        reason,
        context,
        observed_value=(
            f"declaration at {region}; panel at {tuple(detection.bbox)} ({detection.method})"
        ),
        expected_value=required_declaration_location(),
        evidence_span_ids=_cited(context, field),
    )


def _contrast_finding(
    rule: RuleDefinition,
    field: DeclarationField,
    context: EvidenceContext,
    contrast: MeasurementResult,
) -> FieldFinding | None:
    """Rule 9(1)(b): the measured contrast, handed to an officer and judged by nobody here.

    "Contrasts conspicuously" is the gazette's whole test and it states no figure, so no
    ratio can be compared against the rule. The measurement is evidence; REVIEW_REQUIRED is
    the only state it can support, in either direction.
    """
    if isinstance(contrast, MeasurementRefusal):
        return None
    return finding(
        rule,
        field,
        FieldState.REVIEW_REQUIRED,
        "the contrast between this declaration's print and its background was measured. "
        "Rule 9(1)(b) requires a colour that contrasts conspicuously and states no figure, so "
        "whether this one does is an officer's judgement. The ratio depends on the lighting of "
        "the capture.",
        context,
        observed_value=f"contrast ratio {contrast.value:.2f}:1 (relative luminance)",
        evidence_span_ids=_cited(context, field),
    )


def _refine(
    findings: tuple[FieldFinding, ...],
    rules: Sequence[RuleDefinition],
    context: EvidenceContext,
    geometry: _Geometry,
    detection: PDPDetection,
    confirmations: PackageConfirmations,
) -> tuple[FieldFinding, ...]:
    """Replace the findings geometry can now answer, and leave every other one alone.

    :func:`~app.pipeline.findings.build_findings` answers a geometric rule with what it can
    see from a condition kind and one scalar: that no observation was gathered, or that a
    figure exists and needs a person. This holds the declarations' boxes, the panel and the
    per-character measurements, so it can evaluate those rules — but only where the two
    applicability gates left them open. A finding Rule 3 or a sector override settled is
    about which law governs the package, and no measurement outranks that.
    """
    on_date = context.evaluation_date
    scope = chapter_ii_scope(
        net_quantity=context.declared.get(DeclarationField.NET_QUANTITY, ()),
        not_for_retail_sale_observed=context.not_for_retail_sale_observed,
        institutional_or_industrial_confirmed=context.institutional_or_industrial_confirmed,
    )
    required = required_declarations([r for r in rules if _in_force(r, on_date)])
    replaced: dict[tuple[str, DeclarationField], FieldFinding] = {}

    def open_fields(clause: str) -> tuple[RuleDefinition | None, tuple[DeclarationField, ...]]:
        rule = select_effective_rule(tuple(rules), clause, on_date)
        if rule is None:
            return None, ()
        fields = declarations_governed_by_rule(rule, required)
        if scope_findings(rule, fields, scope, context) is not None:
            return rule, ()
        if sector_findings(rule, fields, context) is not None:
            return rule, ()
        return rule, fields

    rule, fields = open_fields(FREE_SPACE_CLAUSE)
    if rule is not None and DeclarationField.NET_QUANTITY in fields:
        replaced[rule.rule_id, DeclarationField.NET_QUANTITY] = _free_space_finding(
            rule, context, geometry
        )

    for clause in (TABLE_HEIGHT_CLAUSE, WIDTH_RATIO_CLAUSE):
        rule, fields = open_fields(clause)
        if rule is None:
            continue
        for field in fields:
            if not rule7_governs_field(
                field,
                required_under_other_law=confirmations.declarations_required_under_other_law,
            ):
                replaced[rule.rule_id, field] = finding(
                    rule,
                    field,
                    FieldState.NOT_APPLICABLE,
                    "an officer has confirmed this package's declarations are also required "
                    "by or under another law. Rule 7(5) then disapplies Rule 7's sizing to "
                    "every declaration but net quantity, retail sale price, the expiry or "
                    "best-before date and consumer care details, and this is none of those.",
                    context,
                )
            elif field is not DeclarationField.NET_QUANTITY:
                # One height was measured, on the quantity declaration. Letting it answer
                # for the address or the date would report print nobody measured as passing.
                replaced[rule.rule_id, field] = finding(
                    rule,
                    field,
                    FieldState.INSUFFICIENT_EVIDENCE,
                    "the measurement this rule needs was not made: character size is measured "
                    "on the quantity declaration only, and this declaration's print was not "
                    "measured.",
                    context,
                )
            elif clause == WIDTH_RATIO_CLAUSE:
                replaced[rule.rule_id, field] = _width_ratio_finding(rule, context, geometry)

    rule, fields = open_fields(PLACEMENT_CLAUSE)
    if rule is not None and pdp_declaration_mandatory(context.product_category, on_date):
        for field in fields:
            if field in geometry.regions:
                replaced[rule.rule_id, field] = _placement_finding(
                    rule, field, context, geometry.regions[field], detection
                )

    rule, fields = open_fields(MANNER_CLAUSE)
    if rule is not None:
        for field in fields:
            if field in geometry.contrast:
                found = _contrast_finding(rule, field, context, geometry.contrast[field])
                if found is not None:
                    replaced[rule.rule_id, field] = found

    refined = tuple(replaced.get((f.rule_snapshot.rule_id, f.field), f) for f in findings)
    if confirmations.rule_33_relaxation_granted and rule_33_relaxation_applies(
        context.product_category, on_date
    ):
        refined = tuple(_relaxed(f) for f in refined)
    return refined


def _unit_sale_price_finding(rule: RuleDefinition, context: EvidenceContext) -> FieldFinding | None:
    """Rule 6(11): is the unit sale price declared on the basis its net quantity calls for?

    A format rule, evaluated from two declarations and no arithmetic. It does not say
    whether a unit sale price must be declared — that is another obligation, not encoded
    — so a package bearing none is not in breach of it. On the image path an absent
    declaration may simply be unread and stays INSUFFICIENT_EVIDENCE with the path's own
    reason; on the listing path, where absence is a fact about the listing, the rule has
    nothing to apply to and says so as NOT_APPLICABLE.

    ``None`` leaves the builder's own finding in place.
    """
    field = DeclarationField.UNIT_SALE_PRICE
    prices = context.declared.get(field, ())
    quantities = context.declared.get(DeclarationField.NET_QUANTITY, ())
    if not prices:
        if context.unreadable_reason is not None:
            return finding(
                rule, field, FieldState.INSUFFICIENT_EVIDENCE, context.unreadable_reason, context
            )
        return finding(
            rule,
            field,
            FieldState.NOT_APPLICABLE,
            "no unit sale price is declared. Rule 6(11) prescribes the basis of one where "
            "it is declared and does not itself require one, so it has nothing to apply to.",
            context,
        )
    cited = tuple(dict.fromkeys(ref for price in prices for ref in price.span_refs))
    quantity = next((q for q in quantities if q.numeric_value is not None and q.unit), None)
    if quantity is None:
        return finding(
            rule,
            field,
            FieldState.INSUFFICIENT_EVIDENCE,
            "a unit sale price was read, but the basis Rule 6(11) requires depends on the "
            "net quantity, and no net quantity with a figure and a unit was resolved.",
            context,
            observed_value=prices[0].normalised_value,
            evidence_span_ids=cited,
        )
    # The basis is read off the canonical value by the same normaliser that produced it,
    # whichever path it came by: the binder writes "₹ 12.50 / g", a listing carries what
    # it said. A value the normaliser cannot place — "per 100 g" — is for a person to read.
    parsed = normalise_unit_sale_price(prices[0].normalised_value)
    declared_basis = parsed.value.unit_basis if parsed.success and parsed.value else ""
    if declared_basis not in known_unit_sale_price_bases():
        return finding(
            rule,
            field,
            FieldState.REVIEW_REQUIRED,
            "the unit sale price is declared on a basis that could not be read as one Rule "
            "6(11) names, so whether it is the prescribed one is for an officer to read.",
            context,
            observed_value=prices[0].normalised_value,
            evidence_span_ids=cited,
        )
    evaluation = evaluate_unit_sale_price_basis(
        declared_basis, quantity.numeric_value, quantity.unit
    )
    if evaluation is None:
        return finding(
            rule,
            field,
            FieldState.INSUFFICIENT_EVIDENCE,
            f"the net quantity is declared in {quantity.unit!r}, a unit Rule 6(11) has no "
            "limb for, so the basis it requires cannot be determined.",
            context,
            observed_value=prices[0].normalised_value,
            evidence_span_ids=cited,
        )
    matched = evaluation.verdict is Verdict.PASS
    return finding(
        rule,
        field,
        FIELD_STATE_FROM_VERDICT[evaluation.verdict],
        (
            "the unit sale price is declared on the basis Rule 6(11) prescribes for a net "
            f"quantity of {quantity.numeric_value} {quantity.unit}."
            if matched
            else "the unit sale price is declared per "
            f"{evaluation.declared_basis!r}; for a net quantity of "
            f"{quantity.numeric_value} {quantity.unit} Rule 6(11) prescribes per "
            f"{evaluation.required_basis!r}."
        ),
        context,
        observed_value=prices[0].normalised_value,
        expected_value=f"per {evaluation.required_basis}",
        evidence_span_ids=cited,
    )


def _with_unit_sale_price(
    findings: tuple[FieldFinding, ...], rules: Sequence[RuleDefinition], context: EvidenceContext
) -> tuple[FieldFinding, ...]:
    """Both scan paths share this: a listing declares a unit sale price as readily as a label."""
    rule = select_effective_rule(tuple(rules), UNIT_SALE_PRICE_CLAUSE, context.evaluation_date)
    if rule is None:
        return findings
    scope = chapter_ii_scope(
        net_quantity=context.declared.get(DeclarationField.NET_QUANTITY, ()),
        not_for_retail_sale_observed=context.not_for_retail_sale_observed,
        institutional_or_industrial_confirmed=context.institutional_or_industrial_confirmed,
    )
    fields = (DeclarationField.UNIT_SALE_PRICE,)
    if scope_findings(rule, fields, scope, context) is not None:
        return findings
    if sector_findings(rule, fields, context) is not None:
        return findings
    replacement = _unit_sale_price_finding(rule, context)
    if replacement is None:
        return findings
    return tuple(
        replacement
        if f.rule_snapshot.rule_id == rule.rule_id and f.field is DeclarationField.UNIT_SALE_PRICE
        else f
        for f in findings
    )


def _in_force(rule: RuleDefinition, on_date: date) -> bool:
    return rule.effective_from <= on_date and (
        rule.effective_to is None or on_date <= rule.effective_to
    )


def _relaxed(found: FieldFinding) -> FieldFinding:
    """A shortfall on a package with a recorded Rule 33 relaxation goes to an officer.

    Only FAIL moves, and only to REVIEW_REQUIRED. Which provisions an order relaxes is on the
    order, not on the label, so this cannot clear the finding — it can only decline to
    recommend action on a provision the Central Government may have relaxed.
    """
    if found.state is not FieldState.FAIL:
        return found
    return found.model_copy(
        update={
            "state": FieldState.REVIEW_REQUIRED,
            "reason": found.reason
            + " An order under Rule 33 relaxing these Rules for this package has been "
            "recorded; whether it reaches this provision is on the order.",
        }
    )


SECOND_READ_FIELDS = (DeclarationField.RETAIL_SALE_PRICE, DeclarationField.NET_QUANTITY)
"""The declarations Tesseract re-reads. Its whitelist is digits, separators and the price and
unit tokens, so it is a second opinion on a *figure* and on nothing else."""


def _doubts(
    image: np.ndarray,
    declared: Mapping[DeclarationField, tuple[NormalisedField, ...]],
    spans: Sequence[ExtractedSpan],
    signals: Sequence[TamperDetectionResult],
    tessdata_dir: str,
) -> dict[DeclarationField, tuple[str, ...]]:
    """Reasons to doubt a declaration that was read, by the declaration they bear on.

    Two sources. A tamper signal bears on the declaration whose span it was raised on — and
    a conflicting-price signal on the retail sale price whatever it was raised on, because
    the second price is usually the one the binder did not pick. A second OCR reading that
    disagrees with the first bears on the declaration that was re-read.

    A sticker signal on text bound to nothing bears on no declaration and appears here
    under none. It is still on :attr:`ImageScanResult.tamper_signals`.
    """
    by_id = {span.span_id: span for span in spans}
    cited_by: dict[str, list[DeclarationField]] = {}
    for field_type, fields in declared.items():
        for field in fields:
            for span_id in field.span_refs:
                cited_by.setdefault(span_id, []).append(field_type)

    doubts: dict[DeclarationField, list[str]] = {}
    for signal in signals:
        on_span = next(
            (span.span_id for span in spans if tuple(span.polygon) == tuple(signal.region)), None
        )
        touched = list(cited_by.get(on_span, ()))
        if signal.kind == "conflicting_mrp":
            touched.append(DeclarationField.RETAIL_SALE_PRICE)
        for field_type in dict.fromkeys(touched):
            doubts.setdefault(field_type, []).append(
                f"{signal.reason} (tamper heuristic, uncalibrated prior {signal.probability:.2f})"
            )

    for field_type in SECOND_READ_FIELDS:
        for field in declared.get(field_type, ()):
            for span_id in field.span_refs:
                reading = arbitrate_field_declaration(
                    image, by_id[span_id], tessdata_dir=tessdata_dir
                )
                if reading.needs_review:
                    doubts.setdefault(field_type, []).append(
                        f"a second OCR pass over the same print read "
                        f"{reading.secondary_text!r} where the first read "
                        f"{reading.primary_text!r}, and the figures in them do not agree"
                    )
    return {field_type: tuple(reasons) for field_type, reasons in doubts.items()}


def _doubted(
    findings: tuple[FieldFinding, ...],
    rules: Sequence[RuleDefinition],
    doubts: Mapping[DeclarationField, tuple[str, ...]],
) -> tuple[FieldFinding, ...]:
    """Send a declaration that read as present to an officer when its reading is in doubt.

    **One transition exists, and it is PASS to REVIEW_REQUIRED.** A doubt is evidence about
    our reading of the package, not about the package: it cannot show a declaration is
    missing or wrong, so it can never produce FAIL, and it cannot clear one either. A
    finding in any other state is returned as the same object, reason and all — the sector
    gate's findings are recognised by their exact text, and a shortfall an officer is
    already being sent does not need a second reason to look.

    Only the rules that ask whether the declaration is *borne* are touched. A sticker over
    the price says nothing about the free space around the quantity.
    """
    presence = {rule.rule_id for rule in rules if rule.conditions.kind == "declaration_required"}
    revised = []
    for found in findings:
        reasons = doubts.get(found.field, ())
        if (
            not reasons
            or found.state is not FieldState.PASS
            or found.rule_snapshot.rule_id not in presence
        ):
            revised.append(found)
            continue
        note = " An officer should examine this declaration: " + "; ".join(reasons) + "."
        revised.append(
            found.model_copy(
                update={"state": FieldState.REVIEW_REQUIRED, "reason": found.reason + note}
            )
        )
    return tuple(revised)


_Read = TypeVar("_Read", NormalisedField, CompetingReadings)
"""A reading of one obligation — resolved, or contested. Both carry ``field_type``.

Constrained to the two concrete types rather than a protocol: they are the whole of what
``bind_spans`` returns, and a protocol would invite a third caller to group something that
has a ``field_type`` and means neither of these.
"""


def by_obligation(
    fields: Sequence[_Read],
) -> dict[DeclarationField, tuple[_Read, ...]]:
    """Group readings by the obligation each answers, keeping every one.

    Rule 6(1)(a) is one obligation covering manufacturer, packer and importer, so a
    package bearing "Manufactured by" and "Marketed by" produces two fields against it.
    ``bind_spans`` returns both deliberately and says not to pick one; this keeps both, in
    the order the binder returned them, and the finding cites the spans behind all of them.

    Serves ``fields`` and ``disagreements`` alike. The same obligation can carry two of
    either, for the same reason, so grouping them two different ways would be one loop and
    one bug waiting to differ from it.
    """
    grouped: dict[DeclarationField, tuple[_Read, ...]] = {}
    for field in fields:
        grouped[field.field_type] = (*grouped.get(field.field_type, ()), field)
    return grouped


def run_image_scan(
    image: np.ndarray,
    *,
    calibration: Calibration,
    product_category: ProductCategory | None,
    evaluated_at: datetime,
    subject_ref: str,
    institutional_or_industrial_confirmed: bool = False,
    confirmations: PackageConfirmations = NOTHING_CONFIRMED,
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
    if confirmations.panel_bbox is not None:
        # The officer has said where the panel is. That statement outranks any detector,
        # trained or not, for the same reason a confirmed category outranks a proposal.
        _, _, marked_w, marked_h = confirmations.panel_bbox
        detection: PDPDetection = OfficerMarkedPanel(
            bbox=confirmations.panel_bbox, area=float(marked_w * marked_h)
        )
    else:
        detection = detect_pdp(image, str(settings.pdp_weights_path))
    return _evaluate_frame(
        image,
        detection=detection,
        calibration=calibration,
        product_category=product_category,
        evaluated_at=evaluated_at,
        subject_ref=subject_ref,
        institutional_or_industrial_confirmed=institutional_or_industrial_confirmed,
        confirmations=confirmations,
    )


ARTWORK_RASTER_DPI = 600.0
"""Resolution vector artwork is rendered at before it is read. High enough that the smallest
print Table-I can require, 1 mm, is 24 pixels tall; the figure itself is arbitrary, because
every measurement is taken at exactly this resolution and none depends on its value."""


@dataclass(frozen=True)
class ArtworkRefusal:
    """Artwork that could not be evaluated, and why. No verdict is produced from it."""

    reason: str


def run_artwork_scan(
    file_bytes: bytes,
    file_type: str,
    *,
    product_category: ProductCategory | None,
    evaluated_at: datetime,
    subject_ref: str,
    institutional_or_industrial_confirmed: bool = False,
    confirmations: PackageConfirmations = NOTHING_CONFIRMED,
) -> ArtworkRefusal | ImageScanResult:
    """Evaluate pre-print artwork of the principal display panel, exactly.

    The one path on which a millimetre is a fact rather than an estimate. The artwork
    states its own physical size, so the panel's area is read off the file, and the file is
    rendered at a known resolution so every character, clearance and box measured on the
    render is exact by construction — :class:`~app.contracts.MeasurementExact`, never
    calibrated.

    No quality gate: blur, glare and a cut-off label are defects of a capture, and there is
    no capture. No panel detection: the artwork *is* the panel, by the submitter's own
    statement, and is reported as an :class:`~app.modules.vision.pdp.ArtworkPanel`.

    Rule 7(4) is applied by the shape an officer confirmed. A rectangular panel's area is
    its height by its width; a cylindrical package's wrap-around label is its
    circumference wide, which is what limb (b) asks for; any other shape takes the artwork
    as the area considered to be the panel under limb (c).
    """
    kind = file_type.lower()
    if kind == "pdf":
        geometry = parse_pdf_geometry(file_bytes)
    elif kind == "svg":
        geometry = parse_svg_geometry(file_bytes)
    else:
        return ArtworkRefusal(reason=f"Unsupported artwork file type: {file_type}")
    if isinstance(geometry, MeasurementRefusal):
        return ArtworkRefusal(reason=geometry.reason)
    height = measure_artwork_ink_extent(file_bytes, kind)
    if isinstance(height, MeasurementRefusal):
        return ArtworkRefusal(reason=height.reason)
    width_mm, _ = geometry
    height_cm, width_cm = Decimal(str(height.value)) / 10, Decimal(str(width_mm)) / 10

    shape = confirmations.shape
    if shape is PackageShape.RECTANGULAR:
        panel_area = calculate_artwork_pdp_area(file_bytes, kind, shape)
    elif shape is PackageShape.CYLINDRICAL:
        panel_area = MeasurementExact(
            value=float(calculate_cylindrical_pdp_area(height_cm, circumference=width_cm)),
            unit="cm²",
            rule_limb="cylindrical: the label's width is the circumference",
        )
    else:
        panel_area = MeasurementExact(
            value=float(
                calculate_other_shape_pdp_area(legally_applicable_pdp_area=height_cm * width_cm)
            ),
            unit="cm²",
            rule_limb="other: the artwork is the area considered to be the panel",
        )

    frame = rasterise_artwork(file_bytes, kind, ARTWORK_RASTER_DPI)
    if isinstance(frame, MeasurementRefusal):
        return ArtworkRefusal(reason=frame.reason)
    frame_h, frame_w = frame.shape[:2]
    return _evaluate_frame(
        frame,
        detection=ArtworkPanel(bbox=(0, 0, frame_w, frame_h), area=float(frame_w * frame_h)),
        calibration=Calibration(method=CalibrationMethod.ARTWORK, artwork_dpi=ARTWORK_RASTER_DPI),
        product_category=product_category,
        evaluated_at=evaluated_at,
        subject_ref=subject_ref,
        institutional_or_industrial_confirmed=institutional_or_industrial_confirmed,
        confirmations=confirmations,
        panel_area=panel_area,
    )


def _evaluate_frame(
    image: np.ndarray,
    *,
    detection: PDPDetection,
    calibration: Calibration,
    product_category: ProductCategory | None,
    evaluated_at: datetime,
    subject_ref: str,
    institutional_or_industrial_confirmed: bool,
    confirmations: PackageConfirmations,
    panel_area: MeasurementResult | None = None,
) -> ImageScanResult:
    """The tail both pixel paths share: read, bind, measure, evaluate, assemble."""
    settings = get_settings()
    # Positional, deliberately: VIS-003 renamed these to text_detection_model_dir and
    # text_recognition_model_dir without changing their order or meaning, so a positional
    # call is correct against both signatures.
    #
    # OCR reads the prepared frame — deskewed where the label's outline was found, unwarped
    # where an officer has said the package is a cylinder — and every polygon is mapped back
    # onto the photograph before anything else sees it. The photograph is what the evidence
    # record stores and what every measurement below is taken from.
    prepared = prepare_panel(image, cylindrical=confirmations.shape is PackageShape.CYLINDRICAL)
    spans = tuple(
        prepared.restore(
            extract_panel_text(
                prepared.image, str(settings.ocr_det_model_dir), str(settings.ocr_rec_model_dir)
            )
        )
    )

    # Classification, spatial role binding and normalisation are one call: extraction
    # normalises internally and hands back canonical fields, so this path has no separate
    # normalisation stage. Every span handed in comes back either cited by a field or in
    # unclassified_spans — the binder conserves them, and so does this.
    extraction = bind_spans(spans)

    # A proposal, and it stops here. It is deliberately not passed to EvidenceContext
    # below: that field is the *confirmed* category the sector gate dispatches on, and
    # handing it a reading would have the pipeline answer the question the architecture
    # reserves for an officer — unmasking every sector-gated obligation at once, silently,
    # on the strength of a regex over OCR text.
    proposal = propose_category(extraction)

    # The display taxonomy, read off the same extraction and stopping in the same place. It
    # is a separate axis from the proposal above rather than a finer grain of it: that one
    # names the Act, this one names the shelf. Both are excluded from EvidenceContext for
    # the same reason, and this one for an additional one — `packaged_food` is not `food`,
    # so routing on it would apply the FSS Act to a package on the strength of a taxonomy
    # built for a filter bar.
    display = classify_display_category(extraction)

    declared = by_obligation(extraction.fields)
    contested = by_obligation(extraction.disagreements)
    geometry = _measure(
        image,
        calibration=calibration,
        detection=detection,
        declared=declared,
        spans=spans,
        shape=confirmations.shape,
        panel_area=panel_area,
    )

    context = EvidenceContext(
        rule_set_version=default_rule_set_version(),
        evaluation_date=evaluated_at.date(),
        declared=declared,
        contested=contested,
        # Table-I is the one geometric rule build_findings evaluates itself, from these two
        # figures. The rest of what was measured is evaluated in _refine, which holds the
        # boxes and the per-character readings this mapping has no shape for.
        measurements={
            "table_height": geometry.numeral_height,
            "pdp_area": geometry.panel_area,
        },
        product_category=product_category,
        source_is_listing=False,
        # Read across every span, not only the bound ones. Whether the binder places the
        # marker is incidental and was measured, not assumed: on its own line it currently
        # binds to COMMON_OR_GENERIC_NAME, and printed beside a batch code — the way packs
        # actually carry it — it binds to nothing and survives only here. The binder is not
        # designed around Rule 3 and owes this nothing, so reading the spans keeps the scope
        # decision independent of a classification that may change for its own reasons.
        not_for_retail_sale_observed=not_for_retail_sale_declared(span.text for span in spans),
        institutional_or_industrial_confirmed=institutional_or_industrial_confirmed,
        unreadable_reason=UNBOUND_DECLARATION_REASON,
    )
    rules = load_rules()
    findings = _refine(
        build_findings(rules, context), rules, context, geometry, detection, confirmations
    )
    findings = _with_unit_sale_price(findings, rules, context)
    # Tamper detection and the second OCR reading run on every scan and come last, after
    # every rule has been evaluated: neither is a rule, and neither may reach one. What
    # they find can only take a PASS back to an officer.
    signals = tuple(detect_tampering(image, list(spans)))
    findings = _doubted(
        findings,
        rules,
        _doubts(image, declared, spans, signals, str(settings.tesseract_tessdata_dir)),
    )
    return ImageScanResult(
        verdict=assemble_verdict(
            subject_ref=subject_ref,
            findings=findings,
            rule_set_version=context.rule_set_version,
            evaluated_at=evaluated_at,
            # Contested obligations belong here too. Each was read — twice, by this
            # provider — so it is a field with readable values behind it, which is the
            # only thing field_providers excludes.
            field_providers=dict.fromkeys((*declared, *contested), EvidenceProvider.PADDLEOCR),
        ),
        spans=spans,
        unclassified_spans=tuple(extraction.unclassified_spans),
        panel=PanelDetection(
            bbox=detection.bbox,
            area_px=detection.area,
            confidence=detection.confidence,
            method=detection.method,
        ),
        tamper_signals=signals,
        category_proposal=proposal,
        display_category=display,
    )


def run_catalogue_scan(
    record: CatalogueRecord,
    *,
    product_category: ProductCategory | None,
    evaluated_at: datetime,
    subject_ref: str,
    institutional_or_industrial_confirmed: bool = False,
) -> VerdictRecord:
    """Evaluate a structured listing.

    No quality gate, no panel detection, no OCR and no measurement — a listing has no
    pixels, and running a blur check over a dictionary would be theatre. Those stages are
    absent rather than stubbed, and the rules that depend on them report
    INSUFFICIENT_EVIDENCE with the reason that a listing carries no pixels, which is true.

    ``unreadable_reason`` is ``None`` here, and that is the substantive difference from
    the image path: a declaration absent from ``declared_fields`` was not declared in the
    listing, which is a finding about the listing rather than a gap in our reading of it.

    ``contested`` is empty for a structural reason rather than an unimplemented one. A
    listing supplies each obligation once, as a dictionary key, so there is no second
    reading for a first to disagree with. Competing readings arise from reading a package
    twice, which only the image path does.
    """
    # The normalisation adapter stays on this path and only this path. A catalogue record
    # supplies the obligation as a dictionary key, so the role is established by the source
    # rather than by prose in the text — which is the whole of what `identity_established`
    # encodes. `bind_spans` is for spans and has no key to read.
    declared: dict[DeclarationField, tuple[NormalisedField, ...]] = {}
    for field, text in record.declared_fields.items():
        span_ref = f"listing:{record.listing_id}:{field.value}"
        value = normalise_declaration(field, text, (span_ref,), identity_established=True)
        if value is not None:
            declared[field] = (value,)

    context = EvidenceContext(
        rule_set_version=default_rule_set_version(),
        evaluation_date=evaluated_at.date(),
        declared=declared,
        contested={},
        measurements={},
        product_category=product_category,
        source_is_listing=True,
        # A listing supplies declarations keyed by obligation and carries no free text to
        # read a marker off. Not observed, which is not the same as absent from the pack —
        # and since nothing is inferred from False, the distinction costs nothing here.
        not_for_retail_sale_observed=False,
        institutional_or_industrial_confirmed=institutional_or_industrial_confirmed,
        unreadable_reason=None,
    )
    rules = load_rules()
    findings = _with_unit_sale_price(build_findings(rules, context), rules, context)
    return assemble_verdict(
        subject_ref=subject_ref,
        findings=findings,
        rule_set_version=context.rule_set_version,
        evaluated_at=evaluated_at,
        field_providers=dict.fromkeys(declared, EvidenceProvider.CATALOGUE),
    )
