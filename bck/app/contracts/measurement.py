"""Physical measurement results — the three-mode policy as a type.

Rule 7 bands minimum letter and numeral height in millimetres. A millimetre figure read
off an uncalibrated photograph is not a measurement; it is pixels with a unit attached,
and an officer cannot act on it. So there are exactly three ways to express a
measurement and no fourth:

* :class:`MeasurementExact` — read from pre-print artwork, where the physical size is
  known from the source file and no calibration is involved.
* :class:`MeasurementCalibrated` — derived from an image containing a reference object
  of known dimensions, and therefore always accompanied by a confidence interval and the
  identity of that reference object.
* :class:`MeasurementRefusal` — no basis for a figure. Carries a reason and no value.

The union is discriminated on ``mode``, so the enforcement is structural rather than
conventional: there is no shape in which a millimetre value exists without either the
exact-artwork mode or a named calibration source. A refusal has no ``value`` field at
all, and ``extra="forbid"`` stops one being smuggled in.

These three models match ``app.modules.measurement.schemas`` field for field. That module
proved the shape under MEA-001 and swaps its local definitions for these imports in
MEA-002; the only difference here is that the constraints are tightened.
"""

from typing import Annotated, Literal

from pydantic import Field

from app.contracts.base import ContractModel


class MeasurementExact(ContractModel):
    """A measurement taken from pre-print artwork rather than from a photograph.

    No calibration source is required or meaningful: the artwork states the physical
    size, so the figure is exact by construction. Recorded with
    :attr:`~app.contracts.enums.EvidenceProvider.ARTWORK`.
    """

    mode: Literal["exact"] = "exact"
    value: float = Field(gt=0)
    unit: str = Field(min_length=1)


class MeasurementCalibrated(ContractModel):
    """A measurement derived from an image via a reference object of known dimensions.

    Both the interval and the reference object are required. A calibrated figure without
    a stated interval reads as an exact one, and a figure without a named reference
    object cannot be re-derived by anyone checking the work.
    """

    mode: Literal["calibrated"] = "calibrated"
    value: float = Field(gt=0)
    confidence_interval: float = Field(gt=0)
    unit: str = Field(min_length=1)
    reference_object: str = Field(min_length=1)
    rule_limb: str | None = None
    """Which limb of the rule the figure is to be compared against, where the rule has
    more than one — Rule 7(2) bands normal and blown, formed or moulded packages
    separately."""


class MeasurementRefusal(ContractModel):
    """No measurement could be made, with the reason recorded.

    Deliberately carries no ``value`` and no ``unit``. A refusal maps to
    :attr:`~app.contracts.enums.FieldState.INSUFFICIENT_EVIDENCE`, never to FAIL: it
    says the measurement could not be taken, not that the package falls short.
    """

    mode: Literal["refusal"] = "refusal"
    reason: str = Field(min_length=1)


MeasurementResult = Annotated[
    MeasurementExact | MeasurementCalibrated | MeasurementRefusal,
    Field(discriminator="mode"),
]
"""The only type a measurement may cross a module boundary as. Never a bare float."""
