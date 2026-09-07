"""Physical measurement results — the three-provenance policy as a type.

Rule 7 bands minimum letter and numeral height in millimetres. A millimetre figure read
off an uncalibrated photograph is not a measurement; it is pixels with a unit attached,
and an officer cannot act on it. So there are exactly three ways a measurement can have
come about and no fourth. The ``mode`` discriminator carries more values than that,
because a quantity's zero and a quantity's sign each need their own shape, but every one
of them is one of these three provenances:

* **exact** — read from pre-print artwork, where the physical size is known from the
  source file and no calibration is involved.
* **calibrated** — derived from an image containing a reference object of known
  dimensions, and therefore always accompanied by a confidence interval and the identity
  of that reference object.
* **refusal** — no basis for a figure. Carries a reason and no value.
  :class:`MeasurementRefusal`.

The first two each come in more than one variant, because a *margin* is the one quantity
where zero is a reading rather than a failure:

* :class:`MeasurementExact` / :class:`MeasurementCalibrated` — every quantity whose zero
  means the detector found nothing: a letter height, a panel area, a contrast ratio.
  ``value`` is ``gt=0``, so a zero cannot be reported as a measurement.
* :class:`MeasurementMarginExact` / :class:`MeasurementMarginCalibrated` — free space
  between a declaration and what surrounds it, where ``value`` is ``ge=0`` because a
  declaration flush against the panel edge has a margin of exactly 0.0.

A margin has one further outcome, and it is not a refusal:

* :class:`MeasurementMarginOverlapExact` / :class:`MeasurementMarginOverlapCalibrated` —
  the surrounding ink crosses *into* the free space, so the clearance came back negative.
  The measurement succeeded; what it found is the intrusion. Routing that to a refusal
  would say "we could not obtain the evidence" about the one reading where the evidence is
  the finding. The distance is kept, as a positive magnitude under the name ``overlap`` so
  that nothing reading ``value`` off a measurement can mistake it for a clearance. What an
  overlap *means* is the rule engine's question and is not encoded here.

**The margin and overlap variants are siblings, not subclasses.** A subclass relaxing its
parent's constraint would make ``isinstance(margin, MeasurementExact)`` true while no
longer guaranteeing what :class:`MeasurementExact` promises, and every ``isinstance`` check
written against the strict type would start passing vacuously. An overlap subclassing a
margin would be worse still: the check would keep passing while the number underneath it
came to mean the opposite. They share their fields through a private base that declares no
value field at all, and each concrete type states its own constraint under its own name.

The union is discriminated on ``mode``, so the enforcement is structural rather than
conventional: there is no shape in which a millimetre figure exists without either the
exact-artwork provenance or a named calibration source. A refusal has no ``value`` field at
all and an overlap has none either — it carries ``overlap`` instead — and
``extra="forbid"`` stops one being smuggled into either.

``app.modules.measurement`` proved these shapes locally under MEA-001 and swapped its own
definitions for these imports in MEA-002, with the constraints tightened on the way across.
It is the only producer of a measurement, so a shape added here is inert until that module
returns it.
"""

from typing import Annotated, Literal

from pydantic import Field

from app.contracts.base import ContractModel


class _MeasurementExactBase(ContractModel):
    """Fields shared by the two artwork-derived shapes. Declares no ``value``.

    Exists so :class:`MeasurementExact` and :class:`MeasurementMarginExact` can be
    siblings rather than parent and child. Not exported: nothing outside this module
    constructs one, and it is not a member of :data:`MeasurementResult`.
    """

    unit: str = Field(min_length=1)
    rule_limb: str | None = None
    """Which limb of the rule the figure is to be compared against, where the rule has
    more than one — Rule 7(4) computes principal display panel area differently for
    rectangular, cylindrical and other packages."""


class _MeasurementCalibratedBase(ContractModel):
    """Fields shared by the two image-derived shapes. Declares no ``value``.

    Deliberately not derived from :class:`_MeasurementExactBase`, though it repeats
    ``unit``: ``rule_limb`` documents a different limb of a different sub-rule on the
    calibrated side, and sharing the field would force one docstring to cover both.
    """

    confidence_interval: float = Field(ge=0)
    """Half-width of the interval around ``value``.

    Zero is permitted and meaningful: a zero-variance observation — a uniform crop in a
    contrast-ratio measurement, say — yields an interval of exactly 0.0. Rejecting that
    would force a genuine measurement to be reported as a refusal. Negative is rejected;
    an interval cannot run backwards. :class:`MeasurementMarginCalibrated` tightens this
    to ``gt=0``; see the reason there."""
    unit: str = Field(min_length=1)
    reference_object: str = Field(min_length=1)
    rule_limb: str | None = None
    """Which limb of the rule the figure is to be compared against, where the rule has
    more than one — Rule 7(2) bands normal and blown, formed or moulded packages
    separately."""


class MeasurementExact(_MeasurementExactBase):
    """A measurement taken from pre-print artwork rather than from a photograph.

    No calibration source is required or meaningful: the artwork states the physical
    size, so the figure is exact by construction. Recorded with
    :attr:`~app.contracts.enums.EvidenceProvider.ARTWORK`.
    """

    mode: Literal["exact"] = "exact"
    value: float = Field(gt=0)
    """Strictly positive. For every quantity but a margin, a zero is the detector having
    found nothing, and reporting that as ``0.0`` would state as a measurement what is
    actually a failure to measure. Margins are the exception and have their own type."""


class MeasurementMarginExact(_MeasurementExactBase):
    """Free space around a declaration, measured from pre-print artwork.

    Identical to :class:`MeasurementExact` but for the ``value`` constraint. It is a
    sibling and not a subclass on purpose: relaxing a parent's constraint in a child
    leaves ``isinstance`` answering yes for an object that no longer holds the parent's
    guarantee.
    """

    mode: Literal["margin_exact"] = "margin_exact"
    value: float = Field(ge=0)
    """Zero is permitted: a declaration flush against the panel edge has a margin of
    exactly 0.0. That is a physical fact about the package, not a failed measurement.
    Negative is still rejected; free space cannot run backwards."""


class MeasurementCalibrated(_MeasurementCalibratedBase):
    """A measurement derived from an image via a reference object of known dimensions.

    Both the interval and the reference object are required. A calibrated figure without
    a stated interval reads as an exact one, and a figure without a named reference
    object cannot be re-derived by anyone checking the work.
    """

    mode: Literal["calibrated"] = "calibrated"
    value: float = Field(gt=0)
    """Strictly positive, for the same reason as :attr:`MeasurementExact.value`."""


class MeasurementMarginCalibrated(_MeasurementCalibratedBase):
    """Free space around a declaration, derived from an image via a reference object.

    Sibling of :class:`MeasurementCalibrated`, not a subclass — see
    :class:`MeasurementMarginExact` for why.
    """

    mode: Literal["margin_calibrated"] = "margin_calibrated"
    value: float = Field(ge=0)
    """Zero is permitted: a declaration flush against the panel edge has a margin of
    exactly 0.0. That is a physical fact about the package, not a failed measurement.
    Negative is still rejected; free space cannot run backwards."""
    confidence_interval: float = Field(gt=0)
    """Strictly positive, tightening the ``ge=0`` this type would otherwise inherit.

    A zero *value* and a zero *interval* answer different questions and only the second
    is constrained here. A margin recovered from a photograph carries pixel quantisation
    and reference-object localisation error, so an interval of exactly 0.0 asserts
    perfect certainty about a physical distance, and this system does not make that
    claim. The artwork variant has no interval to state and is unaffected.

    Tightening in a child is the safe direction: this type guarantees strictly more than
    :class:`MeasurementCalibrated`, so no consumer of the looser one can be surprised by
    an instance of this. It is the inverse of the subclass-relaxation this module's
    sibling shapes exist to prevent."""


class MeasurementMarginOverlapExact(_MeasurementExactBase):
    """Neighbouring ink intruding into the free space around a declaration, from artwork.

    Not a failed measurement. The distance was obtained exactly, from the same artwork and
    by the same arithmetic as :class:`MeasurementMarginExact`; what came back was negative,
    which says the surrounding ink crosses into the clearance rather than that the
    clearance could not be read. Reporting that as a
    :class:`MeasurementRefusal` would route it to
    :attr:`~app.contracts.enums.FieldState.INSUFFICIENT_EVIDENCE` — "we could not obtain the
    evidence" — about the one case where the evidence is exactly what we obtained.

    **An observation, not a verdict.** This type carries a distance and nothing else. Whether
    an overlap breaches Rule 8(1)'s proviso is the rule engine's question, and the proviso's
    requirement is a multiple of the *numeral's* height, which this type has never seen. No
    threshold, no multiple, no side name and no severity is recorded here.

    Sibling of :class:`MeasurementMarginExact` off the shared private base, never a subclass
    of it: an overlap satisfying ``isinstance(x, MeasurementMarginExact)`` would let every
    margin check already written accept a figure that means the opposite of a margin.
    """

    mode: Literal["margin_overlap_exact"] = "margin_overlap_exact"
    overlap: float = Field(gt=0)
    """How far the ink intrudes, as a positive magnitude. The direction is carried by the
    type, not by the sign, so a negative here would be a margin wearing the wrong shape.

    Named ``overlap`` and not ``value`` deliberately, and this is the one place these types
    depart from their four siblings. A consumer formatting ``f"{result.value}
    {result.unit}"`` — which is what the millimetre-bearing path does today — would render a
    0.4 mm overlap as the same string a 0.4 mm clearance produces, indistinguishable and
    pointing the other way. Under this name that consumer raises instead of misreporting,
    and the mode has to be handled on purpose. ``extra="forbid"`` closes the other
    direction: one of these cannot be constructed with ``value=`` at all.

    Strictly positive. Zero is not an overlap — a declaration flush against its neighbour
    has a margin of exactly 0.0 and is :class:`MeasurementMarginExact`. Admitting 0.0 here
    would give one physical fact two representations."""


class MeasurementMarginOverlapCalibrated(_MeasurementCalibratedBase):
    """The same intrusion, derived from an image via a reference object of known dimensions.

    Sibling of :class:`MeasurementMarginCalibrated`; see
    :class:`MeasurementMarginOverlapExact` for why an overlap is an outcome rather than a
    refusal, and why it is a sibling rather than a subclass.

    There are two overlap shapes and not one for the reason there are two of every other
    millimetre shape in this module: an overlap arises on the artwork path and on the
    calibrated path alike, and a single type spanning both would have to make the interval
    and the reference object optional. That is precisely the shape this module exists to
    make unrepresentable — a millimetre figure with no stated provenance.
    """

    mode: Literal["margin_overlap_calibrated"] = "margin_overlap_calibrated"
    overlap: float = Field(gt=0)
    """As :attr:`MeasurementMarginOverlapExact.overlap`: a positive magnitude, strictly
    greater than zero, named so that it cannot be read as a clearance."""
    confidence_interval: float = Field(gt=0)
    """Strictly positive, tightening the ``ge=0`` this type would otherwise inherit.

    An overlap recovered from a photograph carries the same pixel quantisation and
    reference-object localisation error as a margin recovered from one, so it has no claim
    to a certainty :class:`MeasurementMarginCalibrated` already refuses to assert. Tightening
    in a child of the private base is the safe direction, for the reason set out on
    :attr:`MeasurementMarginCalibrated.confidence_interval`."""


class MeasurementRefusal(ContractModel):
    """No measurement could be made, with the reason recorded.

    Deliberately carries no ``value`` and no ``unit``. A refusal maps to
    :attr:`~app.contracts.enums.FieldState.INSUFFICIENT_EVIDENCE`, never to FAIL: it
    says the measurement could not be taken, not that the package falls short.
    """

    mode: Literal["refusal"] = "refusal"
    reason: str = Field(min_length=1)


MeasurementResult = Annotated[
    MeasurementExact
    | MeasurementMarginExact
    | MeasurementMarginOverlapExact
    | MeasurementCalibrated
    | MeasurementMarginCalibrated
    | MeasurementMarginOverlapCalibrated
    | MeasurementRefusal,
    Field(discriminator="mode"),
]
"""The only type a measurement may cross a module boundary as. Never a bare float."""
