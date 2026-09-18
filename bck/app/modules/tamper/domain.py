"""Domain models for the tamper detection module."""

from typing import Literal

from pydantic import Field

from app.contracts import ContractModel, Point


class TamperDetectionResult(ContractModel):
    """Result of tamper detection analysis on package scans."""

    kind: Literal["conflicting_mrp", "sticker_overlay"]
    """Which detector raised it. A conflicting price bears on the retail sale price wherever
    on the label it was seen; a sticker bears only on the print it sits over."""

    probability: float = Field(ge=0.0, le=1.0)
    region: tuple[Point, ...] | tuple[float, float, float, float]
    reason: str
