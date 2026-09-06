"""What was read off a package, and what it normalised to.

Two stages, kept as two types. :class:`ExtractedSpan` is what an OCR provider saw and
where it saw it. :class:`NormalisedField` is what that text resolved to as a declaration.
Keeping them apart is what lets a finding cite the pixels behind a value rather than
just the value.

:class:`CategoryProposal` is a third shape and not a third stage: it is what a reader
inferred about the package as a whole rather than about one declaration, and it stays a
proposal until an officer confirms it.
"""

from decimal import Decimal

from pydantic import Field

from app.contracts.base import ContractModel
from app.contracts.enums import DeclarationField, EvidenceProvider, ProductCategory

Point = tuple[float, float]
"""A single polygon vertex in image pixel coordinates, ``(x, y)``."""


class ExtractedSpan(ContractModel):
    """One run of text located on an image, as reported by a text provider.

    Raw observation. No interpretation of what the text means has happened yet.
    """

    span_id: str = Field(min_length=1)
    """Stable identifier for this span within its scan. Findings cite it."""

    text: str
    """The text exactly as the provider reported it, uncorrected. May be empty where a
    provider located a region but resolved no characters."""

    polygon: tuple[Point, ...] = Field(min_length=3)
    """The span's outline in image pixel coordinates. At least three vertices — a
    quadrilateral for most providers, more for curved surfaces. Not a bounding box:
    labels on cylindrical packages are not axis-aligned, and the crop an officer is shown
    has to match what was actually read."""

    confidence: float = Field(ge=0.0, le=1.0)
    """The provider's own confidence in this reading. Provider-relative and not
    comparable across providers without calibration."""

    source_provider: EvidenceProvider
    """Which provider produced this span."""

    region_id: str = Field(min_length=1)
    """The image region this span was found in — a principal display panel, a side panel,
    a detected declaration block. Spatial binding of spans to fields depends on it."""


class NormalisedField(ContractModel):
    """A declaration resolved from one or more spans into a canonical value.

    This is the shape every extraction result normalises into, whatever product category
    it came from and whichever parser produced it.
    """

    field_type: DeclarationField
    """Which declaration obligation this value answers."""

    span_refs: tuple[str, ...] = Field(min_length=1)
    """The :attr:`ExtractedSpan.span_id` values this was resolved from.

    Plural because a real declaration frequently is: an address runs over several lines
    and is read as several spans. A single reference would leave the evidence chain
    unable to point at the whole of what was used.
    """

    normalised_value: str
    """The canonical text form of the declaration — the value as it should be displayed
    and compared as text. Never the raw OCR text; that stays on the spans."""

    numeric_value: Decimal | None = None
    """The numeric form, for the fields that have one, as ``Decimal``.

    ``Decimal`` rather than ``float`` because these values are compared against
    tolerances: retail sale price against a money figure, net quantity against the
    First Schedule maximum permissible error. Re-parsing a number out of
    :attr:`normalised_value` at each comparison site is how binary float error gets back
    into a comparison that decides a finding.
    """

    unit: str | None = None
    """The canonical unit of :attr:`numeric_value` where the field has one — ``g``,
    ``kg``, ``ml``, ``l``, ``mm``, ``INR``. ``None`` for fields with no unit."""

    parse_confidence: float = Field(ge=0.0, le=1.0)
    """Confidence that the spans were resolved into this value correctly.

    Distinct from :attr:`ExtractedSpan.confidence`, which is confidence that the
    characters were read correctly. Text can be read perfectly and still be parsed into
    the wrong declaration.
    """


class CategoryProposal(ContractModel):
    """A product category a reader inferred, with the evidence it inferred it from.

    **A proposal is not a confirmation, and this type exists so the two cannot be
    confused.** :class:`~app.contracts.enums.ProductCategory` on its own is the officer's
    confirmed category — the thing the sector dispatch keys on, which moves obligations
    to another Act. Nothing here may be passed where that is expected. An extraction
    reader proposes; an officer confirms; only the confirmation routes.

    Every field is required and every one is constrained, so a proposal that cites no
    evidence cannot be constructed at all rather than being discouraged by convention. A
    category assertion with nothing behind it is the input that would let a guess reach
    routing by looking like a reading.
    """

    category: ProductCategory
    """The category being proposed. The same closed vocabulary a confirmation uses, so a
    proposal the sector dispatch could never act on cannot be expressed."""

    confidence: float = Field(ge=0.0, le=1.0)
    """The reader's own confidence in the proposal. Never a threshold for acting on it:
    no value here confirms a category, because confirmation is an officer action."""

    span_refs: tuple[str, ...] = Field(min_length=1)
    """The :attr:`ExtractedSpan.span_id` values the proposal was inferred from.

    At least one, enforced at construction. An officer asked to confirm a category has to
    be shown what it was read off, and a proposal with an empty tuple could not answer
    that question — so it is not a valid proposal, it is an unsourced assertion.
    """

    reason: str = Field(min_length=1)
    """Why those spans support this category, in words an officer can weigh.

    Constrained the same way :attr:`~app.contracts.records.FieldFinding.reason` is, and
    with the same known gap: a single space satisfies it. Consistency with the rest of
    this package is worth more here than closing a hole no caller in the codebase reaches
    for.
    """
