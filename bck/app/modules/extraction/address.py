"""Address normaliser for Legal Metrology declarations.

Confidence values in this module represent uncalibrated priors. They MUST be
recalibrated once DAT-001's evaluation set exists.
"""

import re

from app.modules.extraction.types import (
    AddressRole,
    AddressValue,
    NormalizationResult,
    ReasonCode,
)

CONFIDENCE_ADDRESS_WITH_PINCODE = 0.95
CONFIDENCE_ADDRESS_WITHOUT_PINCODE = 0.85

ROLE_PATTERNS: list[tuple[AddressRole, list[str]]] = [
    (
        AddressRole.MANUFACTURER,
        [
            "manufactured by",
            "mfd. by",
            "mfd by",
            "mfg by",
            "mfg. by",
            "manufactured & packed by",
            "mfd & packed by",
            "mfd and packed by",
        ],
    ),
    (
        AddressRole.PACKER,
        ["packed by", "pkd. by", "pkd by"],
    ),
    (
        AddressRole.MARKETER,
        ["marketed by", "mkd. by", "mkd by", "mktg by"],
    ),
    (
        AddressRole.IMPORTER,
        ["imported by", "imp. by", "imp by"],
    ),
    (
        AddressRole.BRAND_OWNER,
        ["brand owner", "owned by", "trademark owner"],
    ),
]


def normalise_address(text: str) -> NormalizationResult[AddressValue]:
    """Normalise raw OCR text into a deterministic Address declaration."""
    if not text or not text.strip():
        return NormalizationResult[AddressValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.EMPTY_INPUT,
            raw_text=text or "",
        )

    raw = text.strip()
    lower_raw = raw.lower()

    detected_role: AddressRole | None = None
    matched_prefix = ""

    for role, prefixes in ROLE_PATTERNS:
        for prefix in prefixes:
            if prefix in lower_raw:
                detected_role = role
                matched_prefix = prefix
                break
        if detected_role:
            break

    # Address normalisation requires an explicit role declaration header
    if not detected_role:
        return NormalizationResult[AddressValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Strip prefix header
    idx = lower_raw.find(matched_prefix) + len(matched_prefix)
    body_text = raw[idx:].lstrip(" :-=,\t\r\n")

    # Clean OCR whitespace and noise
    cleaned_address = re.sub(r"\s+", " ", body_text).strip()
    cleaned_address = re.sub(r"^[,\.\:\-\s]+", "", cleaned_address).strip()

    if not cleaned_address:
        return NormalizationResult[AddressValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Detect 6-digit PIN code (Indian postal code: 6 digits, first digit 1-9)
    pin_match = re.search(r"\b([1-9][0-9]{5})\b", cleaned_address)
    pincode = pin_match.group(1) if pin_match else None

    # Deterministic entity name heuristic: text before first comma if it ends
    # with a company indicator
    first_part = cleaned_address.split(",")[0].strip()
    # Named comment for regex over 80 characters:
    # Matches common legal company indicators like Pvt Ltd, Private Limited, Inc, Corp, LLP, Ltd
    # cannot reasonably be split as it defines a unified company suffix pattern.
    suffix_pat = (
        r"\b(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Co\.\s*Ltd\.?|Inc\.?|Corp\.?|Ltd\.?|LLP)\.?"
    )
    entity_name = first_part if re.search(suffix_pat, first_part, re.IGNORECASE) else None

    confidence = CONFIDENCE_ADDRESS_WITH_PINCODE if pincode else CONFIDENCE_ADDRESS_WITHOUT_PINCODE

    return NormalizationResult[AddressValue](
        value=AddressValue(
            role=detected_role,
            entity_name=entity_name,
            address_text=cleaned_address,
            pincode=pincode,
        ),
        confidence=confidence,
        success=True,
        reason_code=None,
        raw_text=raw,
    )
