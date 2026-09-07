from enum import StrEnum

from pydantic import BaseModel

from app.contracts import MeasurementResult


class PackageShape(StrEnum):
    RECTANGULAR = "rectangular"
    CYLINDRICAL = "cylindrical"
    OTHER = "other"


class MeasurementMarginSet(BaseModel):
    """Compound shape for the 4-directional margins."""

    above: MeasurementResult
    below: MeasurementResult
    left: MeasurementResult
    right: MeasurementResult
