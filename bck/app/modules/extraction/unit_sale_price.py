"""DAT-005: Unit Sale Price normalisation layer for Legal Metrology Rule 6(11).

Extracts declared unit sale prices and validates declaration format and statutory unit basis
requirements against NetQuantityValue under Rule 6(11). This is a statutory format rule.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Final

from app.modules.extraction.types import (
    NetQuantityValue,
    NormalizationResult,
    ReasonCode,
    UnitSalePriceValue,
)

# Uncalibrated priors representing relative confidence levels for unit sale price extraction.
CONFIDENCE_EXPLICIT_UNIT_SALE_PRICE: Final[float] = 0.95
CONFIDENCE_PARSED_UNIT_SALE_PRICE: Final[float] = 0.90

# Matches explicit USP prefix labels, e.g. "Unit Sale Price:", "USP:", "Unit Price:"
_PREFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:unit\s+sale\s+price|usp|unit\s+price)\s*[:\-]?\s*",
    re.IGNORECASE,
)

# Matches currency symbols and codes: Rs., Rs, INR, ₹, Re., Re
_CURRENCY_RE: Final[str] = r"(?:rs\.?|inr|₹|re\.?)\s*"

# Canonical basis lookup table
_BASIS_NORM_MAP: Final[dict[str, str]] = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "ml": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "l": "litre",
    "litre": "litre",
    "litres": "litre",
    "liter": "litre",
    "liters": "litre",
    "cm": "cm",
    "centimetre": "cm",
    "centimetres": "cm",
    "m": "metre",
    "metre": "metre",
    "metres": "metre",
    "meter": "metre",
    "meters": "metre",
    "n": "N",
    "pc": "N",
    "pcs": "N",
    "piece": "N",
    "pieces": "N",
    "number": "N",
    "no": "N",
    "nos": "N",
}


def get_statutory_basis(net_q: NetQuantityValue) -> set[str]:
    """Determine statutory unit basis for a given NetQuantityValue under Rule 6(11)."""
    unit = net_q.unit.lower()
    val = net_q.value

    # Weight
    if unit in ("g", "gram", "grams"):
        return {"g"} if val < Decimal("1000") else {"kg"}
    elif unit in ("kg", "kilogram", "kilograms"):
        return {"g"} if val < Decimal("1") else {"kg"}

    # Volume
    elif unit in ("ml", "millilitre", "millilitres", "milliliter", "milliliters"):
        return {"ml"} if val < Decimal("1000") else {"litre"}
    elif unit in ("l", "litre", "litres", "liter", "liters"):
        return {"ml"} if val < Decimal("1") else {"litre"}

    # Length
    elif unit in ("cm", "centimetre", "centimetres"):
        return {"cm"} if val < Decimal("100") else {"metre"}
    elif unit in ("m", "metre", "metres", "meter", "meters"):
        return {"cm"} if val < Decimal("1") else {"metre"}

    # Count / Number
    elif unit in ("n", "pc", "pcs", "piece", "pieces", "number", "no", "nos"):
        return {"N"}

    return set()


def normalise_unit_sale_price(
    text: str, net_quantity: NetQuantityValue | None = None
) -> NormalizationResult[UnitSalePriceValue]:
    """Normalise raw text declaration into UnitSalePriceValue under Rule 6(11)."""
    if not text or not text.strip():
        return NormalizationResult(
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.EMPTY_INPUT,
            raw_text=text,
        )

    clean_text = text.strip()
    working_text = clean_text
    has_prefix = False

    prefix_match = _PREFIX_RE.search(working_text)
    if prefix_match:
        has_prefix = True
        working_text = working_text[prefix_match.end() :].strip()

    # Matches currency (optional), numeric amount, slash or "per", and unit basis
    usp_pattern = re.compile(
        rf"^(?:{_CURRENCY_RE})?(\d+(?:\.\d+)?)\s*(?:/|per|\s+per\s+)\s*([a-zA-Z]+)$",
        re.IGNORECASE,
    )

    match = usp_pattern.match(working_text)
    if not match:
        return NormalizationResult(
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=text,
        )

    price_str, raw_basis = match.group(1), match.group(2).lower()

    if raw_basis not in _BASIS_NORM_MAP:
        return NormalizationResult(
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNRECOGNIZED_UNIT,
            raw_text=text,
        )

    canonical_basis = _BASIS_NORM_MAP[raw_basis]

    try:
        price_val = Decimal(price_str)
    except InvalidOperation:
        return NormalizationResult(
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=text,
        )

    # Validate against statutory basis if NetQuantityValue provided
    if net_quantity is not None:
        required_bases = get_statutory_basis(net_quantity)
        if not required_bases or canonical_basis not in required_bases:
            return NormalizationResult(
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.INVALID_VALUE,
                raw_text=text,
            )

    conf = CONFIDENCE_EXPLICIT_UNIT_SALE_PRICE if has_prefix else CONFIDENCE_PARSED_UNIT_SALE_PRICE

    return NormalizationResult(
        value=UnitSalePriceValue(
            unit_price=price_val,
            unit_basis=canonical_basis,
            currency="INR",
            raw_declaration=clean_text,
        ),
        confidence=conf,
        success=True,
        reason_code=None,
        raw_text=text,
    )
