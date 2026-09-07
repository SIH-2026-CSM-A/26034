"""What was read off a package, and what it normalised to.

Two stages, kept as two types. :class:`ExtractedSpan` is what an OCR provider saw and
where it saw it. :class:`NormalisedField` is what that text resolved to as a declaration.
Keeping them apart is what lets a finding cite the pixels behind a value rather than
just the value.

:class:`CompetingReadings` is what the second stage produces when it cannot produce one
value: a package bearing the same declaration twice, in two scripts, saying two different
things. It is a fourth shape rather than a flag on :class:`NormalisedField` because it is
not a declaration — it is the absence of one, held together with the evidence that there
should have been one.

:class:`CategoryProposal` is a third shape and not a third stage: it is what a reader
inferred about the package as a whole rather than about one declaration, and it stays a
proposal until an officer confirms it.
"""

from decimal import Decimal

from pydantic import Field, model_validator

from app.contracts.base import ContractModel
from app.contracts.enums import (
    DeclarationField,
    DisagreementReason,
    EvidenceProvider,
    ProductCategory,
)

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


class CompetingReadings(ContractModel):
    """Two or more readings of one declaration that do not agree, recorded as read.

    Rule 9(4) lets a package bear its declarations in Hindi in Devanagari script or in
    English, and packages frequently bear both. Where the two agree they are one
    declaration read twice and merge into a single :class:`NormalisedField`. Where they
    disagree — "500 g" against "२५० ग्राम" — no declaration has been resolved at all, and
    which of them the package actually declares is a question about the package rather
    than about our reading of it.

    **This type arbitrates nothing.** There is no primary reading, no confidence ordering
    that implies a winner and no first-is-best convention, because nothing in this
    pipeline has grounds to prefer one script's reading over the other's. That is
    ``ARCHITECTURE.md``'s data-flow step 5: providers that disagree surface both readings
    rather than arbitrating. Every reading here sits on the same footing and an officer
    is shown all of them.

    **A field recorded here is not a satisfied declaration**, and a consumer that treats
    it as one produces a PASS on a package that contradicts itself. It routes to
    :attr:`~app.contracts.enums.FieldState.REVIEW_REQUIRED` — not
    :attr:`~app.contracts.enums.FieldState.INSUFFICIENT_EVIDENCE`, because both readings
    were read perfectly well and the failure is not in our reading; and not
    :attr:`~app.contracts.enums.FieldState.FAIL`, because which reading is wrong is an
    officer's call and asserting it here would be a finding we cannot support.
    """

    field_type: DeclarationField
    """The obligation every reading here answers.

    Carried on the container as well as on each reading so a consumer can ask which
    obligation is unresolved without unpacking the tuple — the question every consumer
    actually has. The two cannot drift: a reading of another obligation is refused at
    construction.
    """

    readings: tuple[NormalisedField, ...] = Field(min_length=2)
    """Every reading, in no significant order.

    At least two, enforced at construction rather than discouraged by convention. A
    :class:`CompetingReadings` holding one reading *is* a :class:`NormalisedField`, and
    letting it construct would put a resolved declaration inside the collection whose
    whole meaning is that no declaration was resolved.
    """

    reason: DisagreementReason
    """What the reader distinguished.

    An enum rather than free text. A prose reason is something no consumer can branch on,
    and it drifts between call sites until two readers describe the same disagreement in
    two ways and neither can be counted.
    """

    @model_validator(mode="after")
    def _every_reading_answers_this_obligation(self) -> "CompetingReadings":
        """Refuse readings of an obligation other than :attr:`field_type`.

        Without this, :attr:`field_type` is a second copy of a fact the readings already
        carry, and a second copy that can disagree with the first is worse than no copy:
        every consumer keys on the container's value, so a mismatch routes a real
        disagreement to the wrong obligation silently.
        """
        wrong = {reading.field_type for reading in self.readings} - {self.field_type}
        if wrong:
            raise ValueError(
                f"readings of {sorted(field.value for field in wrong)} in a "
                f"CompetingReadings for {self.field_type.value}. Every reading here "
                f"answers the same obligation; two obligations are two disagreements."
            )
        return self


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
