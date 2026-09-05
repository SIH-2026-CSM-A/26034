"""MRP (Maximum Retail Price) normaliser for Legal Metrology declarations.

Confidence values in this module represent uncalibrated priors. They MUST be
recalibrated once DAT-001's evaluation set exists.
"""

import re
from decimal import Decimal, InvalidOperation

from app.modules.extraction.types import (
    MRPValue,
    NormalizationResult,
    ReasonCode,
)

CONFIDENCE_EXPLICIT_CURRENCY_HEADER = 0.95
CONFIDENCE_IMPLICIT_CURRENCY_HEADER = 0.85


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

    # Reject if no explicit MRP indicator or currency indicator is present in raw text
    # Named comment for regex over 80 characters:
    # Matches currency or MRP tokens (MRP, M.R.P., Rs, Rupees, INR, ₹) to reject standalone numbers.
    # Intentionally long to include all Legal Metrology currency/MRP prefix variants.
    if not re.search(r"(?:MRP|M\.R\.P\.|Rs\.?|Rupees|INR|₹)", raw, re.IGNORECASE):
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Reject negative signs preceding numeric declarations
    if re.search(r"-\s*[0-9]", raw):
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.INVALID_VALUE,
            raw_text=raw,
        )

    # Reject garbled digit OCR noise like "MRP 50O"
    # Named comment for regex over 80 characters:
    # Rejects OCR noise where letters are directly attached to number tokens following MRP headers.
    # Intentionally long to enforce clean word boundary isolation.
    if re.search(r"\bMRP\s+[0-9]+[oOa-zA-Z]\b", raw, re.IGNORECASE):
        return NormalizationResult[MRPValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Extract numeric amounts specifically associated with MRP or currency indicators
    # Named comment for regex over 80 characters:
    # Captures numeric amounts prefixed by MRP/currency tokens or postfixed by Rupees/-.
    # Intentionally long to avoid extracting unrelated numbers like phone numbers or quantities.
    mrp_candidate_pat = (
        r"(?:MRP|M\.R\.P\.|Rs\.?|INR|₹)\s*:?\s*(?:Rs\.?|₹)?\s*"
        r"([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)|"
        r"([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\s*"
        r"(?:Rupees|Rupees\s+Only|/-)"
    )
    mrp_candidate_matches = re.findall(mrp_candidate_pat, raw, re.IGNORECASE)

    clean_amounts: list[Decimal] = []
    for g1, g2 in mrp_candidate_matches:
        am = g1 or g2
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

    # Flexible MRP regex supporting prefix headers (MRP, Rs, INR, ₹) and postfix headers
    # Named comment for regex over 80 characters:
    # Full regex matching MRP declaration with prefix/postfix currency tokens and tax indicators.
    # Intentionally long to combine header options, numeric formatting, and tax tail expressions.
    mrp_regex = (
        r"^(?:\([^\)]*\)\s*)?"
        r"(?:MRP|M\.R\.P\.|Rs\.?|Rupees|INR|₹|\s|:)*"
        r"([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\s*"
        r"(?:Rupees|Rupees\s+Only|/-|only|\([^\)]*\)|incl\.?\s*(?:of\s*all\s*)?taxes?|\s)*$"
    )
    match = re.search(mrp_regex, raw, re.IGNORECASE)

    if not match:
        # Fallback regex for sub-expression matching within noisy text
        # Named comment for regex over 80 characters:
        # Fallback sub-expression matching MRP token and numeric amount when surrounded by context.
        # Intentionally long to handle embedded declarations without full string boundaries.
        sub_regex = (
            r"(?:MRP|M\.R\.P\.|Rs\.?|Rupees|INR|₹)\s*:?\s*"
            r"(?:Rs\.?|₹)?\s*"
            r"([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)"
        )
        sub_match = re.search(sub_regex, raw, re.IGNORECASE)

        # Check postfix matching for cases like "45 Rupees Only"
        # Named comment for regex over 80 characters:
        # Postfix currency sub-expression matching numeric amount followed by Rupees keyword.
        # Intentionally long to catch currency postfixes when no prefix MRP label is present.
        post_regex = r"([0-9]+(?:\.[0-9]{1,2})?)\s*(?:Rupees|Rupees\s+Only|Rs\.?)"
        post_match = re.search(post_regex, raw, re.IGNORECASE)

        if sub_match:
            tail = raw[sub_match.end() :].strip().lower()
            allowed_tail = [
                "only",
                "rupees",
                "rupees only",
                "incl. of all taxes",
                "inclusive of all taxes",
                "incl taxes",
                "incl. taxes",
                "/-",
            ]
            if (
                tail
                and not any(tail.startswith(t) for t in allowed_tail)
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
        elif post_match:
            val_str = post_match.group(1).replace(",", "").replace(" ", "")
        else:
            return NormalizationResult[MRPValue](
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.UNPARSEABLE_FORMAT,
                raw_text=raw,
            )
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

    confidence = (
        CONFIDENCE_EXPLICIT_CURRENCY_HEADER
        if re.search(r"(?:MRP|M\.R\.P\.|Rs|INR|₹|Rupees)", raw, re.IGNORECASE)
        else CONFIDENCE_IMPLICIT_CURRENCY_HEADER
    )

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
