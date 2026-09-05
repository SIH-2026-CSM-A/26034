"""OCR-Text normalisation layer for Legal Metrology Rule 6 field declarations."""

from app.modules.extraction.address import normalise_address
from app.modules.extraction.consumer_care import normalise_consumer_care
from app.modules.extraction.date import normalise_date
from app.modules.extraction.mrp import normalise_mrp
from app.modules.extraction.net_quantity import normalise_net_quantity
from app.modules.extraction.types import (
    AddressRole,
    AddressValue,
    ConsumerCareValue,
    DateType,
    DateValue,
    MRPValue,
    NetQuantityValue,
    NormalizationResult,
    ReasonCode,
)

__all__ = [
    "AddressRole",
    "AddressValue",
    "ConsumerCareValue",
    "DateType",
    "DateValue",
    "MRPValue",
    "NetQuantityValue",
    "NormalizationResult",
    "ReasonCode",
    "normalise_address",
    "normalise_consumer_care",
    "normalise_date",
    "normalise_mrp",
    "normalise_net_quantity",
]
