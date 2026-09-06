"""Domain models for the tamper detection module."""

from pydantic import Field

from app.contracts import ContractModel, Point


class TamperDetectionResult(ContractModel):
    """Result of tamper detection analysis on package scans."""

    probability: float = Field(ge=0.0, le=1.0)
    region: tuple[Point, ...] | tuple[float, float, float, float]
    reason: str
