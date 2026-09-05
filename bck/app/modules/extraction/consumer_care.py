"""Consumer Care normaliser for Legal Metrology declarations.

Confidence values in this module represent uncalibrated priors. They MUST be
recalibrated once DAT-001's evaluation set exists.
"""

import re

from app.modules.extraction.types import (
    ConsumerCareValue,
    NormalizationResult,
    ReasonCode,
)

CONFIDENCE_MULTIPLE_CONTACT_CHANNELS = 0.95
CONFIDENCE_SINGLE_CONTACT_CHANNEL = 0.85


def normalise_consumer_care(text: str) -> NormalizationResult[ConsumerCareValue]:
    """Normalise raw OCR text into a Consumer Care declaration."""
    if not text or not text.strip():
        return NormalizationResult[ConsumerCareValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.EMPTY_INPUT,
            raw_text=text or "",
        )

    raw = text.strip()
    lower_raw = raw.lower()

    # Consumer care extraction requires explicit consumer care context/header
    care_context_keywords = [
        "customer care",
        "consumer care",
        "consumer cell",
        "helpline",
        "toll free",
        "complaint",
        "contact",
        "write to",
        "reach us",
        "helpdesk",
        "support",
        "email:",
        "phone:",
        "call",
        "address:",
    ]
    has_care_context = any(kw in lower_raw for kw in care_context_keywords)

    if not has_care_context:
        return NormalizationResult[ConsumerCareValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Extract Phone Number
    # Named comment for regex over 80 characters:
    # Captures Indian toll-free (1800), landline with STD codes, or 10-digit mobile
    # phone numbers with optional +91 prefix. Intentionally long to match all formats.
    phone_pat = (
        r"(?:(?:\+91[\s-]*)?1800[\s-]*\d{3}[\s-]*\d{4}|"
        r"(?:\+91[\s-]*)?[6-9]\d{9}|"
        r"0\d{2,4}[\s-]*\d{6,8})"
    )
    phone_match = re.search(r"(?:^|[\s:,\(])(" + phone_pat + r")(?=[\s:,\)]|$)", raw)
    phone = phone_match.group(1).strip() if phone_match else None

    # Extract Email Address
    # Named comment for regex over 80 characters:
    # Standard email pattern matching user and domain parts separated by @ symbol.
    # Intentionally long to enforce complete RFC-compliant email structure.
    email_pat = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    email_match = re.search(email_pat, raw)
    email = email_match.group(0).strip() if email_match else None

    # Extract Consumer Care Address Block
    # Named comment for regex over 80 characters:
    # Extracts address block trailing after contact headers like "Write to Manager at:"
    # or "Address:". Intentionally long to cover executive/manager recipient headers.
    addr_match = re.search(
        r"(?:write\s+to\s*:?\s*(?:us\s+at|the\s+executive\s+at|manager\s+at)?|address\s*:)\s*(.+)$",
        raw,
        re.IGNORECASE,
    )
    address_block = addr_match.group(1).strip() if addr_match else None

    if not phone and not email and not address_block:
        return NormalizationResult[ConsumerCareValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    found_count = sum(1 for item in (phone, email, address_block) if item is not None)
    confidence = (
        CONFIDENCE_MULTIPLE_CONTACT_CHANNELS
        if found_count >= 2
        else CONFIDENCE_SINGLE_CONTACT_CHANNEL
    )

    return NormalizationResult[ConsumerCareValue](
        value=ConsumerCareValue(
            phone=phone,
            email=email,
            address_block=address_block,
        ),
        confidence=confidence,
        success=True,
        reason_code=None,
        raw_text=raw,
    )
