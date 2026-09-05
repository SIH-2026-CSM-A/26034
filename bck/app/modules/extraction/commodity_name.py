"""DAT-003: Commodity Name normalisation layer for Legal Metrology Rule 6(1)(b).

Extracts generic/common commodity names for single products as well as multi-product
combination packages, preserving individual item names and quantities.
"""

import re
from typing import Final

from app.modules.extraction.types import (
    CommodityItem,
    CommodityNameValue,
    NormalizationResult,
    ReasonCode,
)

# Uncalibrated priors representing relative confidence levels for commodity name extraction.
CONFIDENCE_EXPLICIT_NAME_DECLARATION: Final[float] = 0.95
CONFIDENCE_PARSED_COMMODITY_NAME: Final[float] = 0.90
CONFIDENCE_MULTI_PRODUCT_COMBINATION: Final[float] = 0.85

# Matches explicit commodity name prefix labels followed by colon or dash
_PREFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:generic\s+name|commodity(?:\s+name)?|product(?:\s+name)?|"
    r"name\s+of\s+(?:the\s+)?commodity)\s*[:\-]\s*",
    re.IGNORECASE,
)

# Matches combination package header phrases like "Combination Package:", "Contains:"
_MULTI_HEADER_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:combination\s+package|multi-pack|package\s+contains|contains|contents)"
    r"\s*[:\-]\s*",
    re.IGNORECASE,
)


def normalise_commodity_name(text: str) -> NormalizationResult[CommodityNameValue]:
    """Normalise raw text declaration into structured CommodityNameValue under Rule 6(1)(b)."""
    if not text or not text.strip():
        return NormalizationResult(
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.EMPTY_INPUT,
            raw_text=text,
        )

    clean_text = text.strip()

    # Reject obvious address / legal prose non-commodity inputs
    if any(
        kw in clean_text.lower()
        for kw in [
            "manufactured by",
            "marketed by",
            "consumer care",
            "mrp rs",
            "expiry date",
        ]
    ):
        return NormalizationResult(
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=text,
        )

    # Check for multi-product / combination package header
    header_match = _MULTI_HEADER_RE.search(clean_text)
    is_explicit_multi_header = header_match is not None

    working_text = clean_text
    has_explicit_prefix = False

    if is_explicit_multi_header and header_match:
        working_text = clean_text[header_match.end() :].strip()
    else:
        prefix_match = _PREFIX_RE.search(working_text)
        if prefix_match:
            has_explicit_prefix = True
            working_text = working_text[prefix_match.end() :].strip()

    if not working_text:
        return NormalizationResult(
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=text,
        )

    # Check if working_text contains multi-product separators like '+' or ',' or ';'
    delimiters = [r"\+", r";", r",", r"\band\b"]
    split_pattern = re.compile(r"|".join(delimiters), re.IGNORECASE)
    parts = [p.strip() for p in split_pattern.split(working_text) if p.strip()]

    if len(parts) > 1 or is_explicit_multi_header:
        items: list[CommodityItem] = []
        for part in parts:
            item_res = _parse_single_item(part)
            if item_res:
                items.append(item_res)

        if items:
            primary_name = ", ".join(it.name for it in items)
            is_multi = len(items) > 1 or is_explicit_multi_header

            # Rule 6(1)(b) second limb: Multi-product packages require every product
            # to be accompanied by its number or quantity.
            if is_multi and len(items) > 1 and any(not it.quantity_or_count for it in items):
                return NormalizationResult(
                    value=None,
                    confidence=0.0,
                    success=False,
                    reason_code=ReasonCode.UNPARSEABLE_FORMAT,
                    raw_text=text,
                )

            conf = (
                CONFIDENCE_MULTI_PRODUCT_COMBINATION
                if is_multi
                else (
                    CONFIDENCE_EXPLICIT_NAME_DECLARATION
                    if has_explicit_prefix
                    else CONFIDENCE_PARSED_COMMODITY_NAME
                )
            )
            return NormalizationResult(
                value=CommodityNameValue(
                    primary_name=primary_name,
                    items=items,
                    is_multi_product=is_multi,
                ),
                confidence=conf,
                success=True,
                reason_code=None,
                raw_text=text,
            )

    # Single item fallback
    item = _parse_single_item(working_text)
    if not item or not item.name:
        return NormalizationResult(
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=text,
        )

    conf = (
        CONFIDENCE_EXPLICIT_NAME_DECLARATION
        if has_explicit_prefix
        else CONFIDENCE_PARSED_COMMODITY_NAME
    )
    return NormalizationResult(
        value=CommodityNameValue(
            primary_name=item.name,
            items=[item],
            is_multi_product=False,
        ),
        confidence=conf,
        success=True,
        reason_code=None,
        raw_text=text,
    )


def _parse_single_item(raw_item_str: str) -> CommodityItem | None:
    """Extract name and optional quantity/count from a single item clause."""
    raw_item_str = raw_item_str.strip()
    if not raw_item_str:
        return None

    # Check for pattern like "1 N Toothpaste (100g)" or "Toothpaste (100 g)"
    paren_match = re.search(r"^(.*?)\s*\(([^()]+)\)$", raw_item_str)
    if paren_match:
        name_part = paren_match.group(1).strip()
        qty_part = paren_match.group(2).strip()
        qty_prefix_match = re.match(
            r"^(\d+(?:\.\d+)?\s*(?:n|pc|pcs|piece|pieces|units?|g|kg|ml|l|litre|litres?))\s+(.+)$",
            name_part,
            re.IGNORECASE,
        )
        if qty_prefix_match:
            leading_qty = qty_prefix_match.group(1).strip()
            item_name = qty_prefix_match.group(2).strip()
            combined_qty = f"{leading_qty}, {qty_part}"
            return CommodityItem(name=item_name, quantity_or_count=combined_qty)
        return CommodityItem(name=name_part, quantity_or_count=qty_part)

    # Match leading count/quantity e.g. "1 N Toothbrush" or "100g Toothpaste"
    leading_qty_match = re.match(
        r"^(\d+(?:\.\d+)?\s*(?:n|pc|pcs|piece|pieces|units?|g|kg|ml|l|litre|litres?))\s+(.+)$",
        raw_item_str,
        re.IGNORECASE,
    )
    if leading_qty_match:
        qty_part = leading_qty_match.group(1).strip()
        item_name = leading_qty_match.group(2).strip()
        return CommodityItem(name=item_name, quantity_or_count=qty_part)

    # Match trailing count/quantity e.g. "Toothpaste 100g"
    trailing_qty_match = re.search(
        r"^(.+?)\s+(\d+(?:\.\d+)?\s*(?:n|pc|pcs|piece|pieces|units?|g|kg|ml|l|litre|litres?))$",
        raw_item_str,
        re.IGNORECASE,
    )
    if trailing_qty_match:
        item_name = trailing_qty_match.group(1).strip()
        qty_part = trailing_qty_match.group(2).strip()
        return CommodityItem(name=item_name, quantity_or_count=qty_part)

    return CommodityItem(name=raw_item_str, quantity_or_count=None)
