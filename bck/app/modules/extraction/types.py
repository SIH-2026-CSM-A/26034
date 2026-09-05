"""Data transfer objects and result schemas for extraction normalisation."""

from decimal import Decimal
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


class ReasonCode(StrEnum):
    """Explicit failure reason codes for unparseable or unresolved extractions."""

    EMPTY_INPUT = "EMPTY_INPUT"
    UNPARSEABLE_FORMAT = "UNPARSEABLE_FORMAT"
    MISSING_PACKING_DATE = "MISSING_PACKING_DATE"
    UNRECOGNIZED_UNIT = "UNRECOGNIZED_UNIT"
    AMBIGUOUS_VALUE = "AMBIGUOUS_VALUE"
    INVALID_VALUE = "INVALID_VALUE"


T = TypeVar("T")


class NormalizationResult(BaseModel, Generic[T]):
    """Standard container for all normalisation outputs."""

    value: T | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    success: bool = False
    reason_code: ReasonCode | None = None
    raw_text: str = ""


class MRPValue(BaseModel):
    """Normalized Maximum Retail Price declaration."""

    amount: Decimal
    currency: str = "INR"
    inclusive_of_taxes: bool = False


class NetQuantityValue(BaseModel):
    """Normalized Net Quantity declaration."""

    value: Decimal
    unit: str  # Canonical unit: g, kg, ml, l, N, pcs
    has_emark: bool = False


class DateType(StrEnum):
    """Type of date declaration on packaged commodity."""

    MANUFACTURED = "MANUFACTURED"
    PACKED = "PACKED"
    BEST_BEFORE = "BEST_BEFORE"
    EXPIRY = "EXPIRY"


class DateValue(BaseModel):
    """Normalized Date declaration (supports absolute ISO dates and relative expressions)."""

    date_type: DateType | None = None
    iso_date: str | None = None  # Formats: YYYY-MM-DD or YYYY-MM
    is_relative: bool = False
    relative_months: int | None = None
    raw_expression: str | None = None


class AddressRole(StrEnum):
    """Legal metrology entity roles for address declarations."""

    MANUFACTURER = "MANUFACTURER"
    PACKER = "PACKER"
    MARKETER = "MARKETER"
    IMPORTER = "IMPORTER"
    BRAND_OWNER = "BRAND_OWNER"


class AddressValue(BaseModel):
    """Normalized Address declaration."""

    role: AddressRole | None = None
    entity_name: str | None = None
    address_text: str
    pincode: str | None = None


class ConsumerCareValue(BaseModel):
    """Normalized Consumer Care declaration."""

    phone: str | None = None
    email: str | None = None
    address_block: str | None = None
