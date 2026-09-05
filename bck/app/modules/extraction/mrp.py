"""MRP (Maximum Retail Price) normaliser for Legal Metrology declarations."""

import re
from decimal import Decimal, InvalidOperation

from app.modules.extraction.types import (
    MRPValue,
    NormalizationResult,
    ReasonCode,
)


def normalise_mrp(text: str) -> NormalizationResult[MRPValue]:
    """Normalise raw OCR text into a structured MRP declaration."""
    if not text or not text.strip():
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.EMPTY_INPUT,
            raw_text=text or "",
        )

    raw = text.strip()

    # Reject if no explicit MRP or currency evidence is present
    if not re.search(r"(?:MRP|M\.R\.P\.|\bRs\.?|\bINR|₹)", raw, re.IGNORECASE):
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Reject negative signs preceding numbers
    if re.search(r"-\s*[0-9]", raw):
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.INVALID_VALUE,
            raw_text=raw,
        )

    # Named comment for regex over 80 characters:
    # Matches currency/MRP declarations and captures all numeric amounts to detect
    # duplicate/conflicting values
    amount_matches = re.findall(
        r"(?:MRP|M\.R\.P\.|\bRs\.?|\bINR|₹)?\s*:?\s*"
        r"([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
        raw,
        re.IGNORECASE,
    )

    # Filter out matches that don't represent actual numbers
    clean_amounts = []
    for am in amount_matches:
        if am.strip():
            clean_str = am.replace(",", "").replace(" ", "")
            try:
                dec_val = Decimal(clean_str)
                if dec_val > Decimal("0"):
                    clean_amounts.append(dec_val)
            except InvalidOperation:
                pass

    if len(clean_amounts) > 1 and len(set(clean_amounts)) > 1:
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.AMBIGUOUS_VALUE,
            raw_text=raw,
        )

    # Reject garbled digit OCR noise like "MRP 50O"
    if re.search(r"\bMRP\s+[0-9]+[oOa-zA-Z]\b", raw):
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Tax inclusivity indicators
    lower_raw = raw.lower()
    tax_patterns = [
        "incl. of all taxes",
        "inclusive of all taxes",
        "incl. taxes",
        "incl taxes",
        "inclusive of taxes",
    ]
    inclusive = any(tp in lower_raw for tp in tax_patterns)

    # Strict full declaration matching
    # Named comment for regex over 80 characters:
    # Captures numeric amount with optional currency symbols (Rs., ₹, INR), thousands separators,
    # optional decimal places, and trailing noise like "/-", "only", "incl. of all taxes".
    mrp_regex = (
        r"^(?:\([^\)]*\)\s*)?"
        r"(?:MRP|M\.R\.P\.|\bRs\.?|\bINR|₹)\s*:?\s*"
        r"(?:Rs\.?|₹)?\s*"
        r"([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\s*"
        r"(?:/-|\bonly\b)?\s*"
        r"(?:\([^\)]*\)|incl\.?\s*(?:of\s*all\s*)?taxes?|\bonly\b)?\s*$"
    )
    match = re.search(mrp_regex, raw, re.IGNORECASE)

    if not match:
        # Fallback search for embedded MRP line without trailing garbage
        # Named comment for regex over 80 characters:
        # Matches embedded MRP string with strict boundary checking to reject trailing garbage
        sub_regex = (
            r"(?:MRP|M\.R\.P\.|\bRs\.?|\bINR|₹)\s*:?\s*"
            r"(?:Rs\.?|₹)?\s*"
            r"([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\s*"
            r"(?:/-|\bonly\b)?"
        )
        sub_match = re.search(sub_regex, raw, re.IGNORECASE)
        if not sub_match:
            return NormalizationResult[MRPValue](
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.UNPARSEABLE_FORMAT,
                raw_text=raw,
            )
        # Verify text trailing sub_match isn't arbitrary garbage
        tail = raw[sub_match.end() :].strip().lower()
        allowed_tail = [
            "only",
            "incl. of all taxes",
            "inclusive of all taxes",
            "incl taxes",
            "incl. taxes",
            "/-",
        ]
        if (
            tail
            and not any(t in tail for t in allowed_tail)
            and not re.match(r"^\([^\)]+\)$", tail)
        ):
            return NormalizationResult[MRPValue](
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.UNPARSEABLE_FORMAT,
                raw_text=raw,
            )
        val_str = sub_match.group(1).replace(",", "").replace(" ", "")
    else:
        val_str = match.group(1).replace(",", "").replace(" ", "")

    try:
        amount = Decimal(val_str)
    except InvalidOperation:
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.INVALID_VALUE,
            raw_text=raw,
        )

    if amount <= Decimal("0"):
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.INVALID_VALUE,
            raw_text=raw,
        )

    has_currency_prefix = bool(re.search(r"(?:MRP|Rs|INR|₹)", raw, re.IGNORECASE))
    confidence = 0.95 if (has_currency_prefix or inclusive) else 0.85

    return NormalizationResult[MRPValue](
        value=MRPValue(
            amount=amount,
            currency="INR",
            inclusive_of_taxes=inclusive,
        ),
        confidence=confidence,
        success=True,
        reason_code=None,
        raw_text=raw,
    )
