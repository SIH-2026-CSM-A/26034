"""Net Quantity normaliser for Legal Metrology declarations."""

import re

from app.modules.extraction.types import (
    NetQuantityValue,
    NormalizationResult,
    ReasonCode,
)

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

    # Strip prefix labels like Net Qty, Net Quantity, Qty, etc.
    cleaned = re.sub(r"^(?:Net\s*Quantity|Net\s*Qty|Qty)\s*:?\s*", "", raw, flags=re.IGNORECASE)

    # Scoped e-mark detection: check if ℮ or 'e' is directly preceding or trailing quantity/unit
    has_emark = bool(
        re.search(r"℮|\b[0-9]+(?:\.[0-9]+)?\s*[a-zA-Z]+\s*℮|\b℮\s*[0-9]+", raw)
        or re.search(r"^\s*e\s+[0-9]|\b[0-9]+(?:\.[0-9]+)?\s*[a-zA-Z]+\s+e\b", raw, re.IGNORECASE)
    )

    # Strip leading e-mark prefix if present
    cleaned = re.sub(r"^(?:℮|\be\b|\be-)\s*", "", cleaned, flags=re.IGNORECASE).strip()

    # Detect multiple quantity expressions -> AMBIGUOUS_VALUE
    # Named comment for regex over 80 characters:
    # Matches all numeric quantity and unit occurrences to detect multiple conflicting
    # quantity declarations
    all_qty_matches = re.findall(
        r"\b[0-9]+(?:\.[0-9]+)?\s*(?:g|gram|grams|gm|gms|kg|kilogram|kilograms|ml|millilitre|milliliter|l|liter|litre|litres|N|num|pcs|pieces|units)\b",
        cleaned,
        re.IGNORECASE,
    )
    if len(all_qty_matches) > 1:
        return NormalizationResult[NetQuantityValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.AMBIGUOUS_VALUE,
            raw_text=raw,
        )

    # Named comment for regex over 80 characters:
    # Pattern 1: Number followed by unit string, e.g. "500 g", "-5 kg", "1.5 kg", "2 N", "10 pcs"
    num_then_unit_pat = (
        r"^([+-]?[0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z\.\u212E]+(?:\s+[a-zA-Z]+)?)\s*(?:℮|\be\b)?$"
    )
    # Pattern 2: Unit string followed by number, e.g. "kg 1.5", "ml 500", "N 10"
    unit_then_num_pat = r"^([a-zA-Z\.\u212E]+)\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*(?:℮|\be\b)?$"

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

    # Clean e-mark or punctuation noise from unit token
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
        val = float(val_str)
    except ValueError:
        return NormalizationResult[NetQuantityValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.INVALID_VALUE,
            raw_text=raw,
        )

    if val <= 0:
        return NormalizationResult[NetQuantityValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.INVALID_VALUE,
            raw_text=raw,
        )

    confidence = 0.95 if m1 else 0.85

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
