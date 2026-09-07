"""Physical measurement results — the three-mode policy as a type.

Rule 7 bands minimum letter and numeral height in millimetres. A millimetre figure read
off an uncalibrated photograph is not a measurement; it is pixels with a unit attached,
and an officer cannot act on it. So there are exactly three ways a measurement can have
come about and no fourth:

* **exact** — read from pre-print artwork, where the physical size is known from the
  source file and no calibration is involved.
* **calibrated** — derived from an image containing a reference object of known
  dimensions, and therefore always accompanied by a confidence interval and the identity
  of that reference object.
* **refusal** — no basis for a figure. Carries a reason and no value.
  :class:`MeasurementRefusal`.

The first two each come in two variants, because a *margin* is the one quantity where
zero is a reading rather than a failure:

* :class:`MeasurementExact` / :class:`MeasurementCalibrated` — every quantity whose zero
  means the detector found nothing: a letter height, a panel area, a contrast ratio.
  ``value`` is ``gt=0``, so a zero cannot be reported as a measurement.
* :class:`MeasurementMarginExact` / :class:`MeasurementMarginCalibrated` — free space
  between a declaration and what surrounds it, where ``value`` is ``ge=0`` because a
  declaration flush against the panel edge has a margin of exactly 0.0.

**The margin variants are siblings, not subclasses.** A subclass relaxing its parent's
constraint would make ``isinstance(margin, MeasurementExact)`` true while no longer
guaranteeing what :class:`MeasurementExact` promises, and every ``isinstance`` check
written against the strict type would start passing vacuously. They share their fields
through a private base that declares no ``value`` at all, and each of the four states its
own constraint.

The union is discriminated on ``mode``, so the enforcement is structural rather than
conventional: there is no shape in which a millimetre value exists without either the
exact-artwork mode or a named calibration source. A refusal has no ``value`` field at
all, and ``extra="forbid"`` stops one being smuggled in.

These models match ``app.modules.measurement.schemas`` field for field. That module
proved the shape under MEA-001 and swaps its local definitions for these imports in
MEA-002; the only difference here is that the constraints are tightened.
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
    | MeasurementCalibrated
    | MeasurementMarginCalibrated
    | MeasurementRefusal,
    Field(discriminator="mode"),
]
"""The only type a measurement may cross a module boundary as. Never a bare float."""
