from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class PackageShape(StrEnum):
    RECTANGULAR = "rectangular"
    CYLINDRICAL = "cylindrical"
    OTHER = "other"


class MeasurementExact(BaseModel):
    mode: Literal["exact"] = "exact"
    value: float
    unit: str


class MeasurementCalibrated(BaseModel):
    mode: Literal["calibrated"] = "calibrated"
    value: float
    confidence_interval: float
    unit: str
    reference_object: str
    rule_limb: str | None = None


class MeasurementRefusal(BaseModel):
    mode: Literal["refusal"] = "refusal"
    reason: str


MeasurementResult = Annotated[
    MeasurementExact | MeasurementCalibrated | MeasurementRefusal, Field(discriminator="mode")
]
