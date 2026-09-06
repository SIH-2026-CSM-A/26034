"""Deterministic category proposal for extracted packaging declarations (EXT-005 / PIP-002).

Infers product categories (FOOD, COSMETICS, MEDICAL_DEVICE) from label declarations
grounded strictly in Legal Metrology corpus sources (FSS Act 2006, Drugs & Cosmetics
Rules 1945, Medical Devices Rules 2017 / G.S.R. 778(E)).
"""

from __future__ import annotations

import re
from typing import Final

from app.contracts import (
    CategoryProposal,
    DeclarationField,
    ProductCategory,
)
from app.modules.extraction.binder import ExtractionResult

# --- Statutory Regulatory Patterns Grounded in Legal Corpus ----------------------------

# Food: FSSAI Licence (14-digit) or Food Safety and Standards Act 2006
# Sourced: LMPC 2011 Rule 2(r), Rule 6(1)(a) Explanation III (FSS Act 2006)
_FOOD_STATUTORY_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:FSSAI|LIC(?:\.|\s*NO)?\s*:\s*[12]\d{13}|[12]\d{13}|FOOD\s+SAFETY\s+(?:AND|&)\s+STANDARDS)\b",
    re.IGNORECASE,
)

# Food Lexical Commodities: Explicitly grounded in LMPC 2011 Second Schedule & G.S.R. 881(E)
# Sourced: LMPC 2011 Second Schedule (biscuits, milk, tea, coffee,
# edible oil, vanaspati, ghee, butter)
# & G.S.R. 881(E) (pan masala)
_FOOD_LEXICAL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:BISCUITS?|MILK|TEA|COFFEE|EDIBLE\s+OIL|VANASPATI|GHEE|BUTTER|PAN\s+MASALA)\b",
    re.IGNORECASE,
)

# Cosmetics: Drugs & Cosmetics Rules 1945 or M.L. / Mfg Lic references
# Sourced: LMPC 2011 Rule 6(1)(d) third proviso (Drugs and Cosmetics Rules, 1945)
_COSMETICS_STATUTORY_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:DRUGS?\s*(?:AND|&)\s*COSMETICS|D\s*&\s*C\s*RULES|M\.L\.|MFG(?:\.|\s*)LIC(?:\.|\s*NO)?\s*:\s*C(?:OS)?[-/])\b",
    re.IGNORECASE,
)

# Cosmetics Lexical Commodities: Explicitly grounded in LMPC 2011 Rule 6(8) & Second/Third Schedule
# Sourced: Rule 6(8) (soap, shampoo, tooth paste, toothpaste, toiletries) & Third Schedule (creams)
_COSMETICS_LEXICAL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:SOAP|SHAMPOO|TOOTH\s*PASTE|TOOTHPASTE|CREAM|CREAMS|TOILETRIES)\b",
    re.IGNORECASE,
)

# Medical Device: Medical Devices Rules 2017 / G.S.R. 778(E) / CDSCO / MFG/MD license
# Sourced: G.S.R. 778(E) (Medical Devices Rules, 2017) & Rule 26(d)
# proviso (medical devices declared as drugs)
_MEDICAL_DEVICE_STATUTORY_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:MEDICAL\s*DEVICES?\s*RULES|MDR\s*2017|CDSCO|MFG/MD/\d+|MD-\d+)\b",
    re.IGNORECASE,
)

# Medical Device Lexical Term: Explicitly grounded in G.S.R. 778(E) and Rule 26(d)
_MEDICAL_DEVICE_LEXICAL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:MEDICAL\s+DEVICES?)\b",
    re.IGNORECASE,
)


def propose_category(result: ExtractionResult) -> CategoryProposal | None:
    """Propose a product category based deterministically on extracted evidence.

    Inspects normalized fields and unclassified spans for statutory references and
    corpus-grounded commodity signals. Returns ``None`` if evidence is missing, sparse,
    ambiguous, or conflicting across categories.

    Deterministic scores:
    - 0.95: Explicit statutory regulatory reference match
    - 0.80: Corpus-grounded commodity name match
    - 0.98: Statutory reference and commodity name mutually reinforcing

    Note: Scores are deterministic evidence-strength values, not statistical probabilities.

    Args:
        result: The ExtractionResult emitted by the extraction binder.

    Returns:
        CategoryProposal if evidence deterministically supports a category, else None.
    """
    if not result.fields and not result.unclassified_spans:
        return None

    category_spans: dict[ProductCategory, list[str]] = {
        ProductCategory.FOOD: [],
        ProductCategory.COSMETICS: [],
        ProductCategory.MEDICAL_DEVICE: [],
    }

    category_has_statutory: dict[ProductCategory, bool] = {
        ProductCategory.FOOD: False,
        ProductCategory.COSMETICS: False,
        ProductCategory.MEDICAL_DEVICE: False,
    }
    category_has_lexical: dict[ProductCategory, bool] = {
        ProductCategory.FOOD: False,
        ProductCategory.COSMETICS: False,
        ProductCategory.MEDICAL_DEVICE: False,
    }

    def _evaluate_text(
        text: str,
        span_ids: tuple[str, ...],
        field_type: DeclarationField | None = None,
    ) -> None:
        if not text or not span_ids:
            return

        # 1. Food evaluation (statutory outranks/excludes lexical on the same text string)
        if _FOOD_STATUTORY_RE.search(text):
            category_has_statutory[ProductCategory.FOOD] = True
            category_spans[ProductCategory.FOOD].extend(span_ids)
        elif _FOOD_LEXICAL_RE.search(text) and (
            field_type is None or field_type == DeclarationField.COMMON_OR_GENERIC_NAME
        ):
            category_has_lexical[ProductCategory.FOOD] = True
            category_spans[ProductCategory.FOOD].extend(span_ids)

        # 2. Cosmetics evaluation (statutory outranks/excludes lexical on the same text string)
        if _COSMETICS_STATUTORY_RE.search(text):
            category_has_statutory[ProductCategory.COSMETICS] = True
            category_spans[ProductCategory.COSMETICS].extend(span_ids)
        elif _COSMETICS_LEXICAL_RE.search(text) and (
            field_type is None or field_type == DeclarationField.COMMON_OR_GENERIC_NAME
        ):
            category_has_lexical[ProductCategory.COSMETICS] = True
            category_spans[ProductCategory.COSMETICS].extend(span_ids)

        # 3. Medical Device evaluation (statutory outranks/excludes lexical on the same text string)
        if _MEDICAL_DEVICE_STATUTORY_RE.search(text):
            category_has_statutory[ProductCategory.MEDICAL_DEVICE] = True
            category_spans[ProductCategory.MEDICAL_DEVICE].extend(span_ids)
        elif _MEDICAL_DEVICE_LEXICAL_RE.search(text) and (
            field_type is None or field_type == DeclarationField.COMMON_OR_GENERIC_NAME
        ):
            category_has_lexical[ProductCategory.MEDICAL_DEVICE] = True
            category_spans[ProductCategory.MEDICAL_DEVICE].extend(span_ids)

    # Scan normalized fields using actual contract attributes:
    # norm_field.normalised_value and norm_field.field_type
    for norm_field in result.fields:
        _evaluate_text(
            norm_field.normalised_value,
            norm_field.span_refs,
            norm_field.field_type,
        )

    # Scan unclassified spans using span.text and (span.span_id,)
    for unclass_span in result.unclassified_spans:
        _evaluate_text(unclass_span.text, (unclass_span.span_id,), None)

    category_scores: dict[ProductCategory, float] = {}

    for cat in (
        ProductCategory.FOOD,
        ProductCategory.COSMETICS,
        ProductCategory.MEDICAL_DEVICE,
    ):
        has_stat = category_has_statutory[cat]
        has_lex = category_has_lexical[cat]

        if has_stat and has_lex:
            category_scores[cat] = 0.98
        elif has_stat:
            category_scores[cat] = 0.95
        elif has_lex:
            category_scores[cat] = 0.80
        else:
            category_scores[cat] = 0.0

    active_categories = [cat for cat, score in category_scores.items() if score > 0.0]

    if not active_categories:
        return None

    # Sort categories deterministically by score descending, then by enum name
    # for tie-breaker safety
    active_categories.sort(key=lambda cat: (category_scores[cat], cat.value), reverse=True)
    top_cat = active_categories[0]
    top_score = category_scores[top_cat]

    # Conflict check: If a second category has an equal or comparable score, abstain (return None)
    if len(active_categories) > 1:
        second_score = category_scores[active_categories[1]]
        if second_score >= top_score:
            return None

    # Deduplicate span references deterministically preserving original order
    raw_spans = category_spans[top_cat]
    unique_spans = tuple(dict.fromkeys(raw_spans))

    if not unique_spans:
        return None

    stat_flag = category_has_statutory[top_cat]
    lex_flag = category_has_lexical[top_cat]
    signal_desc = (
        "statutory regulatory wording and commodity signals"
        if stat_flag and lex_flag
        else "statutory regulatory wording"
        if stat_flag
        else "corpus-grounded commodity signal"
    )

    reason = (
        f"Category proposed as '{top_cat.value}' with confidence {top_score:.2f} based on "
        f"{signal_desc} (evidence spans: {', '.join(unique_spans)})."
    )

    return CategoryProposal(
        category=top_cat,
        confidence=top_score,
        span_refs=unique_spans,
        reason=reason,
    )
