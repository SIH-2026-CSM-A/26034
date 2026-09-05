"""Country of Origin normaliser for Legal Metrology declarations.

Confidence values in this module represent uncalibrated priors. They MUST be
recalibrated once DAT-001's evaluation set exists.
"""

import re

from app.modules.extraction.iso3166_data import (
    ALPHA2_MAP,
    ALPHA3_MAP,
    CANONICAL_NAME_MAP,
    COMMON_VARIANTS,
)
from app.modules.extraction.types import (
    CountryOfOriginValue,
    CountryOriginMode,
    NormalizationResult,
    ReasonCode,
)

CONFIDENCE_EXPLICIT_CANONICAL_DECLARATION = 0.95
CONFIDENCE_EXPLICIT_ISO_VARIANT = 0.90
CONFIDENCE_BOUNDED_OCR_CORRECTION = 0.85


def _is_url_or_web(text: str) -> bool:
    """Detect if string contains URL or domain indicators."""
    lower = text.lower()
    return "http://" in lower or "https://" in lower or "www." in lower or ".com" in lower


def _has_role_or_prose_context(text: str) -> bool:
    """Detect non-origin role headers, address indicators, or prose context."""
    lower = text.lower()
    role_phrases = [
        "made by",
        "mfd by",
        "mfd. by",
        "mfg by",
        "mfg. by",
        "manufactured by",
        "imported by",
        "packed by",
        "pkd by",
        "marketed by",
        "mkd by",
        "brand owner",
        "address:",
        "manufacturer:",
        "importer:",
        "made inside",
        "available in",
        "visit",
        "sold in",
        "producer",
    ]
    return any(phrase in lower for phrase in role_phrases)


def _resolve_candidate(cand: str) -> tuple[dict[str, str] | None, str | None]:
    """Resolve candidate token string against ISO 3166-1 maps and bounded OCR aliases."""
    c_strip = cand.strip()
    c_lower = c_strip.lower()
    c_upper = c_strip.upper()

    # 1. Bounded OCR alias ("inda" -> "India")
    if c_lower == "inda":
        return CANONICAL_NAME_MAP.get("india"), "ocr"

    # 2. Canonical Name
    if c_lower in CANONICAL_NAME_MAP:
        return CANONICAL_NAME_MAP[c_lower], "canonical"

    # 3. Common Variants ("USA", "UK", "UAE")
    if c_lower in COMMON_VARIANTS:
        canonical_name = COMMON_VARIANTS[c_lower]
        return CANONICAL_NAME_MAP.get(canonical_name.lower()), "variant"

    # 4. Alpha-3 Code (e.g. "AND", "IND", "DEU")
    if c_upper in ALPHA3_MAP:
        return ALPHA3_MAP[c_upper], "alpha3"

    # 5. Alpha-2 Code (e.g. "IN", "DE", "US")
    if c_upper in ALPHA2_MAP:
        return ALPHA2_MAP[c_upper], "alpha2"

    # 6. Clean trailing punctuation (like '.' or ';') if not matching directly
    c_clean = c_strip.rstrip(".,;:").lower()
    if c_clean in CANONICAL_NAME_MAP:
        return CANONICAL_NAME_MAP[c_clean], "canonical"
    if c_clean in COMMON_VARIANTS:
        canonical_name = COMMON_VARIANTS[c_clean]
        return CANONICAL_NAME_MAP.get(canonical_name.lower()), "variant"

    return None, None


def normalise_country_of_origin(
    text: str,
    mode: CountryOriginMode = CountryOriginMode.WORLDWIDE,
) -> NormalizationResult[CountryOfOriginValue]:
    """Normalise raw OCR text into a canonical Country of Origin declaration."""
    if not text or not text.strip():
        return NormalizationResult[CountryOfOriginValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.EMPTY_INPUT,
            raw_text=text or "",
        )

    raw = text.strip()

    # Reject URLs, web addresses, and role/prose contamination
    if _is_url_or_web(raw) or _has_role_or_prose_context(raw):
        return NormalizationResult[CountryOfOriginValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Match explicit origin declaration header
    # Named comment for regex over 80 characters:
    # Full regex matching explicit origin prefix header followed by candidate country name string.
    # Intentionally long to enforce start boundary, colon/hyphen flexibility, and header variants.
    full_header_pat = r"^(?:Made\s+in|Country\s+of\s+Orig(?:in|m))\s*[:\-]?\s*(.+)$"
    match = re.match(full_header_pat, raw, re.IGNORECASE)

    if not match:
        return NormalizationResult[CountryOfOriginValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    country_candidate = match.group(1).strip()
    if not country_candidate:
        return NormalizationResult[CountryOfOriginValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.UNPARSEABLE_FORMAT,
            raw_text=raw,
        )

    # Attempt Direct Single-Country Resolution First
    resolved_record, match_kind = _resolve_candidate(country_candidate)

    if resolved_record:
        # Enforce Mode restriction for India
        if mode == CountryOriginMode.INDIA and resolved_record["alpha_2"] != "IN":
            return NormalizationResult[CountryOfOriginValue](
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.UNPARSEABLE_FORMAT,
                raw_text=raw,
            )

        has_header_ocr = bool(re.search(r"Country\s+of\s+Origm", raw, re.IGNORECASE))
        if match_kind == "ocr" or has_header_ocr:
            confidence = CONFIDENCE_BOUNDED_OCR_CORRECTION
        elif match_kind in ("variant", "alpha3", "alpha2"):
            confidence = CONFIDENCE_EXPLICIT_ISO_VARIANT
        else:
            confidence = CONFIDENCE_EXPLICIT_CANONICAL_DECLARATION

        return NormalizationResult[CountryOfOriginValue](
            value=CountryOfOriginValue(
                country_name=resolved_record["name"],
                iso_alpha2=resolved_record["alpha_2"],
                iso_alpha3=resolved_record["alpha_3"],
                raw_declaration=raw,
            ),
            confidence=confidence,
            success=True,
            reason_code=None,
            raw_text=raw,
        )

    # If candidate did NOT match a single ISO country directly:
    # 1. Multi-header ambiguity check
    headers = list(
        re.finditer(
            r"\b(?:Made\s+in|Country\s+of\s+Orig(?:in|m))\b\s*[:\-]?\s*",
            raw,
            re.IGNORECASE,
        )
    )
    if len(headers) > 1:
        extracted_countries = set()
        for i, h_match in enumerate(headers):
            start = h_match.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(raw)
            chunk = raw[start:end].strip().strip("/,.- ")
            chunk_token = re.split(r"[\/,;\s]+", chunk)[0].strip()
            if chunk_token:
                cand_res, _ = _resolve_candidate(chunk_token)
                if cand_res:
                    extracted_countries.add(cand_res["alpha_2"])
        if len(extracted_countries) > 1:
            return NormalizationResult[CountryOfOriginValue](
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.AMBIGUOUS_VALUE,
                raw_text=raw,
            )

    # 2. Conjunction / Slash Ambiguity Check (e.g. "Made in India and Germany")
    if re.search(r"\b(and|or|\/)\b", country_candidate, re.IGNORECASE):
        return NormalizationResult[CountryOfOriginValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.AMBIGUOUS_VALUE,
            raw_text=raw,
        )

    # 3. Unparseable format (unknown country or trailing garbage)
    return NormalizationResult[CountryOfOriginValue](
        value=None,
        confidence=0.0,
        success=False,
        reason_code=ReasonCode.UNPARSEABLE_FORMAT,
        raw_text=raw,
    )
