"""DAT-004: Dimensions normalisation layer for Legal Metrology Rule 6(1)(f).

Extracts dimension declarations (length, width, height, diameter, unit) and supports
explicit non-applicability states under Legal Metrology Rule 6(1)(f).
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Final

from app.modules.extraction.types import (
    DimensionsValue,
    NormalizationResult,
    ReasonCode,
)

# Uncalibrated priors representing relative confidence levels for dimensions extraction.
CONFIDENCE_EXPLICIT_DIMENSIONS: Final[float] = 0.95
CONFIDENCE_PARSED_DIMENSIONS: Final[float] = 0.90
CONFIDENCE_NOT_APPLICABLE: Final[float] = 1.0

# Matches explicit prefix labels for dimension declarations
_PREFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:dimensions?|sizes?|overall\s+dimensions?)\s*[:\-]\s*",
    re.IGNORECASE,
)

# Matches explicit Not-Applicable declarations, e.g. "N/A", "Not Applicable", "NA"
_NA_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:n/?a|not\s+applicable|none|nil)$",
    re.IGNORECASE,
)

# Matches valid metric and customary dimension units
_VALID_UNITS: Final[set[str]] = {
    "cm",
    "mm",
    "m",
    "meter",
    "meters",
    "metre",
    "metres",
    "inch",
    "inches",
    "in",
}


def normalise_dimensions(
    text: str, is_applicable: bool = True
) -> NormalizationResult[DimensionsValue]:
    """Normalise raw text declaration into structured DimensionsValue under Rule 6(1)(f)."""
    if not is_applicable:
        return NormalizationResult(
            value=DimensionsValue(is_applicable=False, raw_expression=text),
            confidence=CONFIDENCE_NOT_APPLICABLE,
            success=True,
            reason_code=ReasonCode.NOT_APPLICABLE,
            raw_text=text,
        )

    if not text or not text.strip():
        return NormalizationResult(
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.EMPTY_INPUT,
            raw_text=text,
        )

    clean_text = text.strip()

    if _NA_RE.match(clean_text):
        return NormalizationResult(
            value=DimensionsValue(is_applicable=False, raw_expression=text),
            confidence=CONFIDENCE_NOT_APPLICABLE,
            success=True,
            reason_code=ReasonCode.NOT_APPLICABLE,
            raw_text=text,
        )

    working_text = clean_text
    has_prefix = False
    prefix_match = _PREFIX_RE.search(working_text)
    if prefix_match:
        has_prefix = True
        working_text = working_text[prefix_match.end() :].strip()

    # Check for diameter declaration e.g. "Diameter: 10 cm" or "Dia 5 cm"
    dia_match = re.match(
        r"^(?:dia(?:meter)?\s*[:\-]?\s*)?(\d+(?:\.\d+)?)\s*([a-zA-Z]+)(?:\s*dia(?:meter)?)?$",
        working_text,
        re.IGNORECASE,
    )
    if dia_match and ("dia" in clean_text.lower() or "diameter" in clean_text.lower()):
        val_str, unit_str = dia_match.group(1), dia_match.group(2).lower()
        if unit_str not in _VALID_UNITS:
            return NormalizationResult(
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.UNRECOGNIZED_UNIT,
                raw_text=text,
            )
        try:
            val = Decimal(val_str)
            is_explicit = has_prefix or bool(
                re.match(r"^(?:dia(?:meter)?\s*[:\-])", clean_text, re.IGNORECASE)
            )
            conf = CONFIDENCE_EXPLICIT_DIMENSIONS if is_explicit else CONFIDENCE_PARSED_DIMENSIONS
            return NormalizationResult(
                value=DimensionsValue(
                    is_applicable=True,
                    diameter=val,
                    unit=unit_str,
                    raw_expression=working_text,
                ),
                confidence=conf,
                success=True,
                reason_code=None,
                raw_text=text,
            )
        except InvalidOperation:
            pass

    # Check multi-dimensional format e.g. "10 cm x 20 cm x 5 cm" or "10 x 20 x 5 cm"
    delimiters = [r"\s*x\s*", r"\s*\*\s*", r"\s+by\s+"]
    parts = re.split("|".join(delimiters), working_text, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) in (2, 3):
        dims: list[Decimal] = []
        found_unit: str | None = None

        for part in parts:
            m = re.match(r"^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?$", part)
            if not m:
                return NormalizationResult(
                    value=None,
                    confidence=0.0,
                    success=False,
                    reason_code=ReasonCode.UNPARSEABLE_FORMAT,
                    raw_text=text,
                )
            num_str, unit_part = m.group(1), m.group(2)
            try:
                dims.append(Decimal(num_str))
            except InvalidOperation:
                return NormalizationResult(
                    value=None,
                    confidence=0.0,
                    success=False,
                    reason_code=ReasonCode.UNPARSEABLE_FORMAT,
                    raw_text=text,
                )
            if unit_part:
                if unit_part.lower() not in _VALID_UNITS:
                    return NormalizationResult(
                        value=None,
                        confidence=0.0,
                        success=False,
                        reason_code=ReasonCode.UNRECOGNIZED_UNIT,
                        raw_text=text,
                    )
                found_unit = unit_part.lower()

        if not found_unit:
            return NormalizationResult(
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.UNRECOGNIZED_UNIT,
                raw_text=text,
            )

        conf = CONFIDENCE_EXPLICIT_DIMENSIONS if has_prefix else CONFIDENCE_PARSED_DIMENSIONS
        if len(dims) == 2:
            return NormalizationResult(
                value=DimensionsValue(
                    is_applicable=True,
                    length=dims[0],
                    width=dims[1],
                    unit=found_unit,
                    raw_expression=working_text,
                ),
                confidence=conf,
                success=True,
                reason_code=None,
                raw_text=text,
            )
        elif len(dims) == 3:
            return NormalizationResult(
                value=DimensionsValue(
                    is_applicable=True,
                    length=dims[0],
                    width=dims[1],
                    height=dims[2],
                    unit=found_unit,
                    raw_expression=working_text,
                ),
                confidence=conf,
                success=True,
                reason_code=None,
                raw_text=text,
            )

    # Single dimension format e.g. "10 cm" or "Length 10 cm"
    single_match = re.match(
        r"^(?:(length|width|height)\s*[:\-]?\s*)?(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$",
        working_text,
        re.IGNORECASE,
    )
    if single_match:
        dim_label = single_match.group(1)
        val_str = single_match.group(2)
        unit_str = single_match.group(3).lower()

        if unit_str not in _VALID_UNITS:
            return NormalizationResult(
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.UNRECOGNIZED_UNIT,
                raw_text=text,
            )

        try:
            val = Decimal(val_str)
            is_explicit = has_prefix or bool(
                dim_label and re.match(rf"^{dim_label}\s*[:\-]", clean_text, re.IGNORECASE)
            )
            conf = CONFIDENCE_EXPLICIT_DIMENSIONS if is_explicit else CONFIDENCE_PARSED_DIMENSIONS
            kw: dict[str, Decimal | str | bool] = {
                "is_applicable": True,
                "unit": unit_str,
                "raw_expression": working_text,
            }
            if dim_label and dim_label.lower() == "width":
                kw["width"] = val
            elif dim_label and dim_label.lower() == "height":
                kw["height"] = val
            else:
                kw["length"] = val

            return NormalizationResult(
                value=DimensionsValue(**kw),
                confidence=conf,
                success=True,
                reason_code=None,
                raw_text=text,
            )
        except InvalidOperation:
            pass

    return NormalizationResult(
        value=None,
        confidence=0.0,
        success=False,
        reason_code=ReasonCode.UNPARSEABLE_FORMAT,
        raw_text=text,
    )
