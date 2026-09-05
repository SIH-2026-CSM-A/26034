"""Net Quantity normaliser for Legal Metrology declarations.

Confidence values in this module represent uncalibrated priors. They MUST be
recalibrated once DAT-001's evaluation set exists.
"""

import re
from decimal import Decimal, InvalidOperation

from app.modules.extraction.types import (
    NetQuantityValue,
    NormalizationResult,
    ReasonCode,
)

CONFIDENCE_EXPLICIT_QUANTITY_LABEL = 0.95
CONFIDENCE_STANDARD_QUANTITY_PATTERN = 0.85

CANONICAL_UNITS: dict[str, str] = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "gm": "g",
    "gms": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "kg.": "kg",
    "ml": "ml",
    "millilitre": "ml",
    "milliliters": "ml",
    "milliliter": "ml",
    "ml.": "ml",
    "l": "l",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "l.": "l",
    "n": "N",
    "num": "N",
    "number": "N",
    "no": "N",
    "pcs": "pcs",
    "pieces": "pcs",
    "piece": "pcs",
    "pkt": "pcs",
    "pkts": "pcs",
    "units": "pcs",
    "u": "pcs",
}


def normalise_net_quantity(text: str) -> NormalizationResult[NetQuantityValue]:
    """Normalise raw OCR text into a canonical Net Quantity declaration."""
    if not text or not text.strip():
        return NormalizationResult[NetQuantityValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.EMPTY_INPUT,
            raw_text=text or "",
        )

    raw = text.strip()

    # Detect e-mark prefix/suffix or token
    # Named comment for regex over 80 characters:
    # Detects e-mark symbols (℮, e) in prefix, suffix, or token positions
    # relative to quantity numbers. Intentionally long for ℮ and 'e' variations.
    has_emark = bool(
        re.search(
            r"℮|\b℮\b|^\s*e\s+[0-9]|\b[0-9]+(?:\.[0-9]+)?\s*[a-zA-Z]+\s+e\b|^\s*e-",
            raw,
            re.IGNORECASE,
        )
    )

    # Strip prefix labels like Net Qty, Net Quantity, Qty, etc.
    cleaned = re.sub(r"^(?:Net\s*Quantity|Net\s*Qty|Qty)\s*:?\s*", "", raw, flags=re.IGNORECASE)

    # Strip leading e-mark prefix if present
    cleaned = re.sub(r"^(?:℮|e\s+|e-)\s*", "", cleaned, flags=re.IGNORECASE).strip()

    # Detect multiple quantity expressions -> AMBIGUOUS_VALUE
    # Named comment for regex over 80 characters:
    # Captures all quantity and unit occurrences across text for ambiguity detection.
    # Intentionally long to check for multiple conflicting unit declarations in single string.
    all_qty_matches = re.findall(
        r"\b[0-9]+(?:\.[0-9]+)?\s*(?:g|gram|grams|gm|gms|kg|kilogram|kilograms|ml|millilitre|milliliter|l|liter|litre|litres|N|num|pcs|pieces|units)\b",
        cleaned,
        re.IGNORECASE,
    )
    if len(all_qty_matches) > 1 and len(set(all_qty_matches)) > 1:
        return NormalizationResult[NetQuantityValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.AMBIGUOUS_VALUE,
            raw_text=raw,
        )

    # Patterns for numeric quantity parsing
    # Named comment for regex over 80 characters:
    # Pattern 1: Number followed by unit string (e.g. "500 g", "-5 kg", "1.5 kg", "2 N", "10 pcs")
    # Intentionally long to support optional e-mark and unit space variations.
    num_then_unit_pat = r"^([+-]?[0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z\.℮]+(?:\s+[a-zA-Z]+)?)\s*(?:℮|e)?$"
    # Named comment for regex over 80 characters:
    # Pattern 2: Unit string followed by number (e.g. "kg 1.5", "ml 500", "N 10")
    # Intentionally long to support optional e-mark and unit space variations.
    unit_then_num_pat = r"^([a-zA-Z\.℮]+(?:\s+[a-zA-Z]+)?)\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*(?:℮|e)?$"

    m1 = re.match(num_then_unit_pat, cleaned, re.IGNORECASE)
    m2 = re.match(unit_then_num_pat, cleaned, re.IGNORECASE)

    if m1:
        val_str, unit_raw = m1.group(1), m1.group(2).strip().lower()
    elif m2:
        unit_raw, val_str = m2.group(1).strip().lower(), m2.group(2)
    else:
        return NormalizationResult[NetQuantityValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Clean e-mark or trailing punctuation noise from unit token
    unit_raw = re.sub(r"[\s℮\.]+$", "", unit_raw).strip()
    if unit_raw.startswith("e ") or unit_raw.startswith("e-"):
        unit_raw = unit_raw[2:].strip()

    canonical_unit = CANONICAL_UNITS.get(unit_raw)
    if not canonical_unit:
        return NormalizationResult[NetQuantityValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNRECOGNIZED_UNIT,
            raw_text=raw,
        )

    try:
        val = Decimal(val_str)
    except InvalidOperation:
        return NormalizationResult[NetQuantityValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.INVALID_VALUE,
            raw_text=raw,
        )

    if val <= Decimal("0"):
        return NormalizationResult[NetQuantityValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.INVALID_VALUE,
            raw_text=raw,
        )

    confidence = CONFIDENCE_EXPLICIT_QUANTITY_LABEL if m1 else CONFIDENCE_STANDARD_QUANTITY_PATTERN

    return NormalizationResult[NetQuantityValue](
        value=NetQuantityValue(
            value=val,
            unit=canonical_unit,
            has_emark=has_emark,
        ),
        confidence=confidence,
        success=True,
        reason_code=None,
        raw_text=raw,
    )
