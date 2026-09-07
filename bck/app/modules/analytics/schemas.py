"""Typed read-only response shapes for analytics aggregates."""

from datetime import date

from pydantic import BaseModel, Field


class RuleAggregateCell(BaseModel):
    """A privacy-eligible count of scans with a failing finding for one rule."""

    rule_id: str = Field(min_length=1)
    count: int = Field(ge=0)


class CategoryAggregateCell(BaseModel):
    """A privacy-eligible count of scans for a confirmed-category display bucket."""

    product_category: str = Field(min_length=1)
    count: int = Field(ge=0)


class DailyAggregateCell(BaseModel):
    """A privacy-eligible count of scans evaluated on one calendar day."""

    day: date
    count: int = Field(ge=0)


class JurisdictionAggregateCell(BaseModel):
    """A privacy-eligible jurisdiction aggregate with a relative density band."""

    state: str = Field(min_length=1)
    region: str | None = None
    district: str | None = None
    count: int = Field(ge=0)
    density_band: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
