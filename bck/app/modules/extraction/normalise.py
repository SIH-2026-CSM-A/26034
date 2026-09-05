"""OCR-Text normalisation layer for Legal Metrology Rule 6 field declarations."""

from app.modules.extraction.address import normalise_address
from app.modules.extraction.commodity_name import normalise_commodity_name
from app.modules.extraction.consumer_care import normalise_consumer_care
from app.modules.extraction.country_of_origin import normalise_country_of_origin
from app.modules.extraction.date import normalise_date
from app.modules.extraction.dimensions import normalise_dimensions
from app.modules.extraction.mrp import normalise_mrp
from app.modules.extraction.net_quantity import normalise_net_quantity
from app.modules.extraction.types import (
    AddressRole,
    AddressValue,
    CommodityItem,
    CommodityNameValue,
    ConsumerCareValue,
    CountryOfOriginValue,
    CountryOriginMode,
    DateType,
    DateValue,
    DimensionsValue,
    MRPValue,
    NetQuantityValue,
    NormalizationResult,
    ReasonCode,
    UnitSalePriceValue,
)
from app.modules.extraction.unit_sale_price import normalise_unit_sale_price

__all__ = [
    "AddressRole",
    "AddressValue",
    "CommodityItem",
    "CommodityNameValue",
    "ConsumerCareValue",
    "CountryOfOriginValue",
    "CountryOriginMode",
    "DateType",
    "DateValue",
    "DimensionsValue",
    "MRPValue",
    "NetQuantityValue",
    "NormalizationResult",
    "ReasonCode",
    "UnitSalePriceValue",
    "normalise_address",
    "normalise_commodity_name",
    "normalise_consumer_care",
    "normalise_country_of_origin",
    "normalise_date",
    "normalise_dimensions",
    "normalise_mrp",
    "normalise_net_quantity",
    "normalise_unit_sale_price",
]
