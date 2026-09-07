"""Declaration binder — classifies and groups OCR spans into NormalisedField records.

Statutory Corpus Citation:
  Legal Metrology (Packaged Commodities) Rules, 2011 (as amended up to 2021-10-31):
  Compilation for Maharashtra State Metrology Department.
  Source: rules-corpus/LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf
  Rule 9(4):
    "(4) The particulars of the declarations required to be specified under this
    rule on a package shall either be in Hindi in Devanagiri script or in English:
    Provided that nothing contained in this sub-rule shall prevent the use of any
    other language in addition to Hindi or English language."

Engineering Priors & Calibration Note:
  1. Spatial Bounding Multipliers:
     - MAX_VERTICAL_GAP_MULTIPLIER = 3.0
     - MAX_HORIZONTAL_OFFSET_MULTIPLIER = 3.0
     These multipliers define spatial proximity boundaries for pairing Devanagari
     and Latin declaration spans. They are empirical engineering heuristics (priors)
     and NOT statutory thresholds specified in LMPC Rule 9(4).
  2. Confidence Prior:
     - Paired parse_confidence = min(f1.parse_confidence, f2.parse_confidence)
     This represents a conservative lower-bound confidence estimate for combined
     bilingual extraction fields.

Bilingual declarations in Hindi (Devanagari) and English (Latin) representing the same
declaration field are spatially paired into single NormalisedField records with plural span_refs.
"""

import math
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, Field, model_validator

from app.contracts import (
    CompetingReadings,
    DeclarationField,
    DisagreementReason,
    ExtractedSpan,
    NormalisedField,
)
from app.modules.extraction.commodity_name import normalise_commodity_name
from app.modules.extraction.consumer_care import normalise_consumer_care
from app.modules.extraction.country_of_origin import normalise_country_of_origin
from app.modules.extraction.date import normalise_date
from app.modules.extraction.dimensions import normalise_dimensions
from app.modules.extraction.mrp import normalise_mrp
from app.modules.extraction.net_quantity import normalise_net_quantity
from app.modules.extraction.types import DateType
from app.modules.extraction.unit_sale_price import normalise_unit_sale_price


class ExtractionResult(BaseModel):
    """Resolved declaration fields, unclassified spans, and declarations read two ways
    that do not agree."""

    fields: list[NormalisedField] = Field(default_factory=list)
    unclassified_spans: list[ExtractedSpan] = Field(default_factory=list)
    disagreements: list[CompetingReadings] = Field(default_factory=list)
    """Declarations read more than once, in readings that contradict each other.

    Separate from :attr:`fields` because a contradicted declaration is not a resolved one:
    an obligation listed here has not been satisfied, and a consumer that reads only
    :attr:`fields` cannot mistake it for one.
    """

    @model_validator(mode="after")
    def _a_disagreement_is_never_also_a_field(self) -> "ExtractionResult":
        """No obligation appears in both collections.

        Two collections mean a consumer can count one declaration twice, and someone
        forgets exactly once. Refused at construction rather than asserted downstream,
        because the consumers are in another layer and there is no single place there to
        assert it.
        """
        both = {field.field_type for field in self.fields} & {
            disagreement.field_type for disagreement in self.disagreements
        }
        if both:
            raise ValueError(
                f"{sorted(field.value for field in both)} appears in both fields and "
                f"disagreements. A declaration is either resolved or contested, never "
                f"both, and counting it twice is what this refuses."
            )
        return self


MAX_VERTICAL_GAP_MULTIPLIER: Final[float] = 3.0
MAX_HORIZONTAL_OFFSET_MULTIPLIER: Final[float] = 3.0

_DEVANAGARI_RE: Final[re.Pattern[str]] = re.compile(r"[\u0900-\u097F\uA8E0-\uA8FF\u1CD0-\u1CFF]")
_LATIN_RE: Final[re.Pattern[str]] = re.compile(r"[a-zA-Z]")
_TAMIL_RE: Final[re.Pattern[str]] = re.compile(r"[\u0B80-\u0BFF]")
_BENGALI_RE: Final[re.Pattern[str]] = re.compile(r"[\u0980-\u09FF]")

_DEVANAGARI_DIGITS: Final[dict[str, str]] = {
    "०": "0",
    "१": "1",
    "२": "2",
    "३": "3",
    "४": "4",
    "५": "5",
    "६": "6",
    "७": "7",
    "८": "8",
    "९": "9",
}

_DEVANAGARI_TOKEN_MAP: Final[list[tuple[re.Pattern[str], str]]] = [
    (re.compile(rf"(?<![\u0900-\u097F\w]){k}(?![\u0900-\u097F\w])"), v)
    for k, v in [
        ("शुद्ध मात्रा", "Net Qty"),
        ("निवल मात्रा", "Net Qty"),
        ("एमआरपी", "MRP"),
        ("रुपये", "Rs."),
        ("रु.", "Rs."),
        ("किलोग्राम", "kg"),
        ("मिलीग्राम", "mg"),
        ("मिलीलीटर", "ml"),
        ("किग्रा", "kg"),
        ("मिग्रा", "mg"),
        ("एमएल", "ml"),
        ("लीटर", "l"),
        ("ग्राम", "g"),
        ("सेमी", "cm"),
        ("मिमी", "mm"),
        ("मीटर", "m"),
    ]
]


class ScriptType(StrEnum):
    """Primary script classification of an OCR text span."""

    DEVANAGARI = "DEVANAGARI"
    LATIN = "LATIN"
    TAMIL = "TAMIL"
    BENGALI = "BENGALI"
    UNSUPPORTED = "UNSUPPORTED"
    MIXED = "MIXED"
    NEITHER = "NEITHER"


def detect_script(text: str) -> ScriptType:
    """Detect whether text is Devanagari, Latin, Tamil, Bengali, Unsupported, Mixed,
    or Neither script.

    Statutory Corpus Citation:
      Legal Metrology (Packaged Commodities) Rules, 2011, Rule 9(4).
      Rule 9(4) permits the use of other languages in addition to Hindi or English.
      EXT-008 distinguishes recognized additional scripts from unidentified/noise spans.
    """
    has_dev = False
    has_lat = False
    has_tam = False
    has_ben = False
    has_unsupported = False

    for char in text:
        cat = unicodedata.category(char)
        if not (cat.startswith("L") or cat.startswith("M")):
            continue

        name = unicodedata.name(char, "")
        if _DEVANAGARI_RE.search(char) or "DEVANAGARI" in name:
            has_dev = True
        elif _TAMIL_RE.search(char) or "TAMIL" in name:
            has_tam = True
        elif _BENGALI_RE.search(char) or "BENGALI" in name:
            has_ben = True
        elif _LATIN_RE.search(char) or name.startswith("LATIN "):
            has_lat = True
        elif cat.startswith("L"):
            has_unsupported = True

    matching_scripts: list[ScriptType] = []
    if has_dev:
        matching_scripts.append(ScriptType.DEVANAGARI)
    if has_lat:
        matching_scripts.append(ScriptType.LATIN)
    if has_tam:
        matching_scripts.append(ScriptType.TAMIL)
    if has_ben:
        matching_scripts.append(ScriptType.BENGALI)
    if has_unsupported:
        matching_scripts.append(ScriptType.UNSUPPORTED)

    if len(matching_scripts) > 1:
        return ScriptType.MIXED
    if len(matching_scripts) == 1:
        return matching_scripts[0]
    return ScriptType.NEITHER


def _preprocess_devanagari_text(text: str) -> str:
    """Normalize Devanagari numerals and equivalent unit tokens for structured numeric parsing."""
    if not _DEVANAGARI_RE.search(text):
        return text

    cleaned = text
    for dev_digit, ascii_digit in _DEVANAGARI_DIGITS.items():
        cleaned = cleaned.replace(dev_digit, ascii_digit)
    for pattern, repl in _DEVANAGARI_TOKEN_MAP:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned


_BBox = tuple[float, float, float, float]


def _get_bbox(polygon: tuple[tuple[float, float], ...]) -> _BBox:
    """Calculate (min_x, min_y, max_x, max_y) from polygon coordinates."""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return min(xs), min(ys), max(xs), max(ys)


class BboxRefusalReason(StrEnum):
    """The specific reason a declaration bounding box could not be computed.

    Seven values across two semantic categories:

    **Category A — declaration/evidence not present.**  The evidence chain upstream
    of geometry did not resolve: either the field carries no span citations at all, or a
    cited span ID is absent from the scan result.  An officer reading this should
    understand that the declaration was not established for this observation — the failure
    is in what was captured, not in how the pixel coordinates read.

    **Category B — span present, geometry cannot be used.**  The declaration was
    identified and its span was located in the scan; the bounding box could not be
    computed because the span's reported polygon data is structurally or numerically
    invalid.  An officer reading this should understand that the measurement could not be
    taken from an otherwise-found declaration — the failure is in the geometry, not in
    the evidence.
    """

    # -- Category A ----------------------------------------------------------
    NO_SPAN_REFS = "NO_SPAN_REFS"
    """The field carries no span_refs — no evidence was cited for this obligation."""

    UNKNOWN_SPAN_ID = "UNKNOWN_SPAN_ID"
    """A span_id cited by the field is not present in the supplied span sequence."""

    # -- Category B ----------------------------------------------------------
    EMPTY_POLYGON = "EMPTY_POLYGON"
    """A span's polygon is an empty tuple: the provider located a text region but
    emitted no vertices."""

    INSUFFICIENT_VERTICES = "INSUFFICIENT_VERTICES"
    """A span's polygon has fewer than 3 vertices and cannot bound a region."""

    MALFORMED_VERTEX = "MALFORMED_VERTEX"
    """A polygon has ≥3 elements, but one vertex cannot be unpacked to ``(x, y)`` —
    the element is not a valid coordinate pair.

    Distinct from :attr:`INSUFFICIENT_VERTICES`: the polygon's *count* is adequate,
    but the *shape* of an individual element is wrong.  This preserves data-quality
    provenance: a provider that emits the right number of vertices with one malformed
    coordinate is a different kind of defect than a provider that emits too few."""

    NON_FINITE_COORDINATE = "NON_FINITE_COORDINATE"
    """A polygon vertex contains a non-finite coordinate (``NaN`` or ``Inf``)."""

    DEGENERATE_ENVELOPE = "DEGENERATE_ENVELOPE"
    """All x-coordinates or all y-coordinates in the polygon are equal, producing a
    zero-area bounding envelope that carries no spatial information."""


_BBOX_REFUSAL_CATEGORY_A: frozenset[BboxRefusalReason] = frozenset(
    {BboxRefusalReason.NO_SPAN_REFS, BboxRefusalReason.UNKNOWN_SPAN_ID}
)
_BBOX_REFUSAL_CATEGORY_B: frozenset[BboxRefusalReason] = frozenset(
    {
        BboxRefusalReason.EMPTY_POLYGON,
        BboxRefusalReason.INSUFFICIENT_VERTICES,
        BboxRefusalReason.MALFORMED_VERTEX,
        BboxRefusalReason.NON_FINITE_COORDINATE,
        BboxRefusalReason.DEGENERATE_ENVELOPE,
    }
)


@dataclass(frozen=True)
class BboxRefusal:
    """``get_declaration_bbox`` could not produce a bounding box.

    The exact reason is recorded in :attr:`reason`.  Callers should not compare
    against ``None``; use ``isinstance(result, BboxRefusal)`` to detect refusal.

    :attr:`span_id` is set for Category B causes — it names the span whose polygon
    triggered the refusal, aiding traceability.  It is ``None`` for Category A causes
    because the failure precedes any span being resolved.
    """

    reason: BboxRefusalReason
    span_id: str | None = None


def bbox_refusal_officer_reason(refusal: BboxRefusal) -> str:
    """Return a human-readable, officer-facing explanation for a bbox refusal.

    Category A causes describe an evidence gap (the declaration was not established).
    Category B causes describe a geometry defect (the declaration was found but its
    pixel data cannot produce a measurement).

    These two categories must produce distinct strings so that an officer's
    INSUFFICIENT_EVIDENCE finding says the right thing about the observation.
    """
    match refusal.reason:
        case BboxRefusalReason.NO_SPAN_REFS:
            return (
                "the declaration field has no cited spans — "
                "no evidence was extracted for this obligation"
            )
        case BboxRefusalReason.UNKNOWN_SPAN_ID:
            return "a span cited by this declaration field does not exist in the scan result"
        case BboxRefusalReason.EMPTY_POLYGON:
            return (
                "a span's polygon is empty — "
                "the provider located a text region but emitted no vertices"
            )
        case BboxRefusalReason.INSUFFICIENT_VERTICES:
            return "a span's polygon has fewer than 3 vertices and cannot form a bounding box"
        case BboxRefusalReason.MALFORMED_VERTEX:
            return "a polygon vertex does not contain a valid (x, y) coordinate pair"
        case BboxRefusalReason.NON_FINITE_COORDINATE:
            return "a polygon vertex contains a non-finite coordinate (NaN or Inf)"
        case BboxRefusalReason.DEGENERATE_ENVELOPE:
            return (
                "the polygon's bounding envelope is degenerate — "
                "all x or all y coordinates are equal"
            )


def get_declaration_bbox(
    field: NormalisedField,
    spans: Sequence[ExtractedSpan],
) -> tuple[float, float, float, float] | BboxRefusal:
    """Calculate the exact ``(min_x, min_y, max_x, max_y)`` enclosing bounding box
    for a field's referenced spans, or refuse with a typed reason.

    Returns a :class:`BboxRefusal` — never ``None`` — when the bounding box cannot
    be computed.  The refusal carries one of seven :class:`BboxRefusalReason` values
    that callers must not collapse: two describe an evidence gap (the declaration was
    not established in this scan), and five describe a geometry defect (the declaration
    was located but its pixel data is unusable).

    Callers: ``isinstance(result, BboxRefusal)`` to detect refusal.
    """
    if not field.span_refs:
        return BboxRefusal(reason=BboxRefusalReason.NO_SPAN_REFS)

    span_map = {s.span_id: s for s in spans}
    xs: list[float] = []
    ys: list[float] = []

    for span_id in field.span_refs:
        span = span_map.get(span_id)
        if span is None:
            return BboxRefusal(reason=BboxRefusalReason.UNKNOWN_SPAN_ID)

        poly = span.polygon
        if not poly:
            return BboxRefusal(reason=BboxRefusalReason.EMPTY_POLYGON, span_id=span_id)
        if len(poly) < 3:
            return BboxRefusal(reason=BboxRefusalReason.INSUFFICIENT_VERTICES, span_id=span_id)

        for pt in poly:
            try:
                x, y = pt[0], pt[1]
            except (IndexError, TypeError):
                return BboxRefusal(reason=BboxRefusalReason.MALFORMED_VERTEX, span_id=span_id)

            try:
                fx = float(x)
                fy = float(y)
            except (ValueError, TypeError):
                return BboxRefusal(reason=BboxRefusalReason.MALFORMED_VERTEX, span_id=span_id)

            if not (math.isfinite(fx) and math.isfinite(fy)):
                return BboxRefusal(reason=BboxRefusalReason.NON_FINITE_COORDINATE, span_id=span_id)

            xs.append(fx)
            ys.append(fy)

    min_x, min_y = min(xs), min(ys)
    max_x, max_y = max(xs), max(ys)

    if min_x >= max_x or min_y >= max_y:
        return BboxRefusal(reason=BboxRefusalReason.DEGENERATE_ENVELOPE)

    return (min_x, min_y, max_x, max_y)


_ANCHOR_RE: Final[re.Pattern[str]] = re.compile(
    r"\b("
    r"manufactured\s*(?:&|and)?\s*packed\s*by|"
    r"mfd\.?\s*(?:&|and)?\s*packed\s*by|"
    r"manufactured\s*by|mfd\.?\s*by|mfg\.?\s*by|"
    r"packed\s*by|pkd\.?\s*by|"
    r"marketed\s*by|mkd\.?\s*by|mktg?\.?\s*by|mkt\.?\s*by|"
    r"imported\s*by|imp\.?\s*by|"
    r"brand\s*owner|trademark\s*owner|owned\s*by"
    r")\b",
    re.IGNORECASE,
)
_PINCODE_CANDIDATE_RE: Final[re.Pattern[str]] = re.compile(r"\b([1-9][0-9]{5})\b")
_PHONE_LABEL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:phone|ph|tel|telephone|mob|mobile|call|toll\s*free|tollfree|helpline|fax|contact)\b",
    re.IGNORECASE,
)
_PHONE_PREFIX_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:\+91|1800|1860|0\d{2,4})[\s\-]*$",
    re.IGNORECASE,
)
_USP_INDICATOR_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:unit\s*sale\s*price|\busp\b|unit\s*price|\bper\s*(?:g|ml|piece|kg|l|unit|item))\b",
    re.IGNORECASE,
)
_USP_REGEX: Final[re.Pattern[str]] = re.compile(
    r"(?:(?:unit\s*sale\s*price|\busp\b|unit\s*price)\s*[:\-]?\s*)?"
    r"(?:rs\.?|inr|₹|re\.?)?\s*(\d+(?:\.\d+)?)\s*"
    r"(?:/|\bper\b)\s*"
    r"(100\s*g|100\s*ml|kg|l|g|ml|piece|unit|item)\b",
    re.IGNORECASE,
)
_EXPLICIT_COMMODITY_RE: Final[re.Pattern[str]] = re.compile(
    r"\b("
    r"commodity(?:\s+name)?|"
    r"generic\s+name|"
    r"common\s+name|"
    r"product(?:\s+name)?|"
    r"name\s+of\s+(?:the\s+)?commodity|"
    r"combination\s+package|"
    r"multi-pack|"
    r"package\s+contains"
    r")\s*[:\-]",
    re.IGNORECASE,
)
_NON_COMMODITY_RE: Final[re.Pattern[str]] = re.compile(
    r"\b("
    r"store\s+in|store\s+away|store\s+below|keep\s+in|keep\s+away|keep\s+cool|"
    r"sunlight|cool\s*(?:and|&)?\s*dry|cool\s*dry\s*place|do\s+not\s+freeze|"
    r"refrigerat(?:e|ion)|room\s+temperature|dry\s+place|protect\s+from|"
    r"directions?(?:\s+for\s+use)?|instructions?|how\s+to\s+use|usage\b|"
    r"for\s+external\s+use|external\s+use\s+only|shake\s+well|serve\s+chilled|"
    r"tear\s+here|open\s+here|warning|caution|allergens?|allergy\s+advice|"
    r"may\s+contain|not\s+for\s+medicinal\s+use|keep\s+out\s+of\s+reach|"
    r"ingredients?|nutritional|nutrition\s+facts|per\s+100\s*g|"
    r"batch(?:\s*no\.?)?|lot(?:\s*no\.?)?|b\.?\s*no\.?|barcode|code\b|ref\b|"
    r"fssai|lic(?:ense|ence)?(?:\s*no\.?)?|regd?\.?\s*(?:no\.?)?|"
    r"pvt\.?\s*ltd\.?|private\s+limited|ltd\.?|limited\b|inc\.?|corp\.?|"
    r"corporation|enterprises?|industries|"
    r"industrial\s+area|sector\b|phase\b|road\b|street\b|lane\b|marg\b|"
    r"nagar\b|plot\b|floor\b|building\b|post\s*box|p\.?o\.?\s*box|"
    r"pin\s*code|pincode|village\b|taluk\b|dist(?:rict)?\.?\b|"
    r"customer\s*care|consumer\s*care|helpline|toll\s*free|feedback|contact\s*us"
    r")\b",
    re.IGNORECASE,
)
_LABEL_COPY_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:store|keep|see|visit|enjoy|serve|consume|apply|protect|avoid|wash|open|tear|recycle)\b|"
    r"https?://|www\.|\.com\b",
    re.IGNORECASE,
)


def extract_valid_pincodes(text: str) -> list[str]:
    """Extract valid 6-digit Indian postal PIN codes from text.

    Strictly rejects numbers that are part of phone numbers (e.g. +91 9811000123,
    1800-110001), STD codes, toll-free lines, or longer digit runs.
    """
    if not text or not text.strip():
        return []
    valid_pins: list[str] = []
    for match in _PINCODE_CANDIDATE_RE.finditer(text):
        start, end = match.start(), match.end()
        pin_candidate = match.group(1)
        prefix_text, suffix_text = text[:start], text[end:]
        if re.search(r"\d[\-\/\.]+\s*$", prefix_text) or re.match(r"^\s*[\-\/\.]\d", suffix_text):
            continue
        if _PHONE_PREFIX_RE.search(prefix_text):
            continue
        recent_prefix = prefix_text[-25:] if len(prefix_text) >= 25 else prefix_text
        if _PHONE_LABEL_RE.search(recent_prefix):
            label_match = list(_PHONE_LABEL_RE.finditer(recent_prefix))[-1]
            between = recent_prefix[label_match.end() :]
            if re.fullmatch(r"[\s:.\-,]*", between):
                continue
        phone_matches = re.finditer(
            r"(?:\+91[\s-]*)?(?:"
            r"1800[\s-]*\d{3}[\s-]*\d{3,4}|"
            r"1800[\s-]*\d{6}|"
            r"[6-9]\d{9}|"
            r"0\d{2,4}[\s-]*\d{6,8}"
            r")",
            text,
            re.IGNORECASE,
        )
        if any(pm.start() <= start and end <= pm.end() for pm in phone_matches):
            continue
        valid_pins.append(pin_candidate)
    return valid_pins


def _is_anchor_span(span: ExtractedSpan) -> bool:
    """Check if a span acts as a keyword anchor for Rule 6(1)(a)."""
    if span.confidence <= 0.0 or not span.text.strip():
        return False
    if normalise_consumer_care(span.text).success:
        return False
    return bool(_ANCHOR_RE.search(span.text))


def _bind_rule_6_1_a_addresses(
    spans: Sequence[ExtractedSpan],
) -> tuple[list[NormalisedField], set[str]]:
    """Spatial Role Binding for Rule 6(1)(a) (DeclarationField.NAME_AND_ADDRESS).

    Identifies keyword anchor spans: 'Manufactured by', 'Packed by', 'Imported by',
    'Marketed by', 'Brand Owner', and their abbreviations ('Mfg by', 'Pkd by',
    'Mkt by', 'Imp by').

    Target address cluster must sit DOWNWARD relative to the anchor (candidate y >=
    anchor y; strictly reject clusters where the bounding box sits above the keyword
    anchor).

    Target address cluster must contain a valid 6-digit Indian PIN code (regex
    `\\b[1-9][0-9]{5}\\b` that is NOT part of a phone number or longer digit run).

    If multiple 'Marketed by' blocks exist, return both as separate NormalisedField
    entries. Do not arbitrarily pick one.

    Note: A complete brand-owner name and address with 'Marketed by' or 'Brand Owner'
    satisfying Rule 6(1)(a) rests on the DoCA FAQ of 11.11.2025 via secondary reports
    and is marked [SOURCED], not [VERIFIED] in rules-corpus/README.md. Do not restate
    it as settled law.
    """
    fields: list[NormalisedField] = []
    consumed_ids: set[str] = set()
    anchors = [s for s in spans if s.confidence > 0.0 and _is_anchor_span(s)]
    if not anchors:
        return fields, consumed_ids

    anchor_ids: set[str] = {a.span_id for a in anchors}
    sorted_anchors = sorted(anchors, key=lambda a: _get_bbox(a.polygon)[1])
    non_address_ids: set[str] = set()
    for s in spans:
        if s.confidence <= 0.0 or _is_anchor_span(s):
            continue
        txt = s.text.strip()
        if (
            normalise_mrp(txt).success
            or normalise_unit_sale_price(txt).success
            or bool(_USP_REGEX.search(txt))
            or normalise_net_quantity(txt).success
            or normalise_date(txt).success
            or normalise_country_of_origin(txt).success
            or normalise_consumer_care(txt).success
            or normalise_dimensions(txt).success
        ):
            non_address_ids.add(s.span_id)

    for anchor in sorted_anchors:
        a_min_x, a_min_y, a_max_x, _ = _get_bbox(anchor.polygon)
        a_center_x = (a_min_x + a_max_x) / 2.0
        if extract_valid_pincodes(anchor.text):
            fields.append(
                NormalisedField(
                    field_type=DeclarationField.NAME_AND_ADDRESS,
                    span_refs=(anchor.span_id,),
                    normalised_value=anchor.text.strip(),
                    numeric_value=None,
                    unit=None,
                    parse_confidence=anchor.confidence,
                )
            )
            consumed_ids.add(anchor.span_id)
            continue

        cluster_spans: list[ExtractedSpan] = [anchor]
        found_pin = False
        candidates: list[ExtractedSpan] = []

        for s in spans:
            # An anchor span must NEVER be added to another anchor's address cluster
            if s.span_id in consumed_ids or s.span_id in anchor_ids or s.span_id in non_address_ids:
                continue
            if s.confidence <= 0.0 or s.region_id != anchor.region_id:
                continue
            c_min_x, c_min_y, c_max_x, c_max_y = _get_bbox(s.polygon)
            if c_max_y <= a_min_y or c_min_y < a_min_y:
                continue

            c_center_x = (c_min_x + c_max_x) / 2.0
            dist_to_anchor = abs(c_center_x - a_center_x)

            belongs_to_anchor = True
            for other_a in sorted_anchors:
                if other_a.span_id == anchor.span_id:
                    continue
                oa_min_x, oa_min_y, oa_max_x, _ = _get_bbox(other_a.polygon)
                oa_center_x = (oa_min_x + oa_max_x) / 2.0
                dist_to_other = abs(c_center_x - oa_center_x)

                # For side-by-side columns: candidate must be closer to this anchor than
                # to any other horizontal anchor.
                if dist_to_anchor > dist_to_other:
                    belongs_to_anchor = False
                    break
                if dist_to_anchor == dist_to_other and a_center_x != oa_center_x:
                    belongs_to_anchor = False
                    break

                # For vertically aligned / stacked anchors:
                # If other anchor is between this anchor and the candidate vertically,
                # the candidate belongs to the lower anchor.
                if oa_min_y > a_min_y and c_min_y >= oa_min_y:
                    a_overlap = max(0.0, min(a_max_x, c_max_x) - max(a_min_x, c_min_x))
                    oa_overlap = max(0.0, min(oa_max_x, c_max_x) - max(oa_min_x, c_min_x))
                    if oa_overlap >= a_overlap:
                        belongs_to_anchor = False
                        break

            if belongs_to_anchor:
                candidates.append(s)

        candidates.sort(key=lambda c: _get_bbox(c.polygon)[1])
        for cand in candidates:
            cluster_spans.append(cand)
            if extract_valid_pincodes(cand.text):
                found_pin = True
                break

        if found_pin:
            if min(_get_bbox(s.polygon)[1] for s in cluster_spans) < a_min_y:
                continue
            cluster_text = ", ".join(s.text.strip() for s in cluster_spans if s.text.strip())
            avg_conf = sum(s.confidence for s in cluster_spans) / len(cluster_spans)
            fields.append(
                NormalisedField(
                    field_type=DeclarationField.NAME_AND_ADDRESS,
                    span_refs=tuple(s.span_id for s in cluster_spans),
                    normalised_value=cluster_text,
                    numeric_value=None,
                    unit=None,
                    parse_confidence=round(avg_conf, 4),
                )
            )
            for s in cluster_spans:
                consumed_ids.add(s.span_id)

    return fields, consumed_ids


def _dispatch_single_span(span: ExtractedSpan) -> NormalisedField | None:
    """Attempt to parse an unbound span using specialized Rule 6 normalisers."""
    if span.confidence <= 0.0 or not span.text.strip():
        return None
    raw = span.text.strip()
    processed_raw = _preprocess_devanagari_text(raw)

    mrp_res = normalise_mrp(processed_raw)
    if mrp_res.success and mrp_res.confidence > 0.0 and mrp_res.value is not None:
        return NormalisedField(
            field_type=DeclarationField.RETAIL_SALE_PRICE,
            span_refs=(span.span_id,),
            normalised_value=f"₹ {mrp_res.value.amount}",
            numeric_value=mrp_res.value.amount,
            unit="INR",
            parse_confidence=min(span.confidence, mrp_res.confidence),
        )

    usp_res = normalise_unit_sale_price(processed_raw)
    if usp_res.success and usp_res.confidence > 0.0 and usp_res.value is not None:
        return NormalisedField(
            field_type=DeclarationField.UNIT_SALE_PRICE,
            span_refs=(span.span_id,),
            normalised_value=f"₹ {usp_res.value.unit_price} / {usp_res.value.unit_basis}",
            numeric_value=usp_res.value.unit_price,
            unit="INR",
            parse_confidence=min(span.confidence, usp_res.confidence),
        )

    usp_match = _USP_REGEX.search(processed_raw)
    if usp_match:
        price_str = usp_match.group(1)
        basis_str = usp_match.group(2).strip()
        has_indicator = bool(_USP_INDICATOR_RE.search(processed_raw))
        usp_conf = 0.95 if has_indicator else 0.90
        return NormalisedField(
            field_type=DeclarationField.UNIT_SALE_PRICE,
            span_refs=(span.span_id,),
            normalised_value=f"₹ {price_str} / {basis_str}",
            numeric_value=price_str,
            unit="INR",
            parse_confidence=min(span.confidence, usp_conf),
        )

    nq_res = normalise_net_quantity(processed_raw)
    if nq_res.success and nq_res.confidence > 0.0 and nq_res.value is not None:
        return NormalisedField(
            field_type=DeclarationField.NET_QUANTITY,
            span_refs=(span.span_id,),
            normalised_value=f"{nq_res.value.value} {nq_res.value.unit}",
            numeric_value=nq_res.value.value,
            unit=nq_res.value.unit,
            parse_confidence=min(span.confidence, nq_res.confidence),
        )

    date_res = normalise_date(processed_raw)
    if date_res.success and date_res.confidence > 0.0 and date_res.value is not None:
        is_bb = date_res.value.date_type in (DateType.BEST_BEFORE, DateType.EXPIRY)
        field_type = (
            DeclarationField.BEST_BEFORE_DATE if is_bb else DeclarationField.MANUFACTURE_DATE
        )
        return NormalisedField(
            field_type=field_type,
            span_refs=(span.span_id,),
            normalised_value=date_res.value.iso_date or raw,
            numeric_value=None,
            unit=None,
            parse_confidence=min(span.confidence, date_res.confidence),
        )

    origin_res = normalise_country_of_origin(processed_raw)
    if origin_res.success and origin_res.confidence > 0.0 and origin_res.value is not None:
        return NormalisedField(
            field_type=DeclarationField.COUNTRY_OF_ORIGIN,
            span_refs=(span.span_id,),
            normalised_value=origin_res.value.country_name,
            numeric_value=None,
            unit=None,
            parse_confidence=min(span.confidence, origin_res.confidence),
        )

    care_res = normalise_consumer_care(processed_raw)
    if care_res.success and care_res.confidence > 0.0 and care_res.value is not None:
        parts = [f"Phone: {care_res.value.phone}"] if care_res.value.phone else []
        if care_res.value.email:
            parts.append(f"Email: {care_res.value.email}")
        if care_res.value.address_block:
            parts.append(f"Address: {care_res.value.address_block}")
        return NormalisedField(
            field_type=DeclarationField.CONSUMER_CARE,
            span_refs=(span.span_id,),
            normalised_value=", ".join(parts) if parts else raw,
            numeric_value=None,
            unit=None,
            parse_confidence=min(span.confidence, care_res.confidence),
        )

    dim_res = normalise_dimensions(processed_raw)
    if dim_res.success and dim_res.confidence > 0.0 and dim_res.value is not None:
        num_val = dim_res.value.length if dim_res.value.width is None else None
        if num_val is None and dim_res.value.diameter is not None:
            num_val = dim_res.value.diameter
        return NormalisedField(
            field_type=DeclarationField.DIMENSIONS,
            span_refs=(span.span_id,),
            normalised_value=dim_res.value.raw_expression or raw,
            numeric_value=num_val,
            unit=dim_res.value.unit,
            parse_confidence=min(span.confidence, dim_res.confidence),
        )

    # 8) COMMON_OR_GENERIC_NAME
    # Bound only if:
    # a) Explicit keywords present, OR
    # b) Does NOT match known non-commodity phrasing / label copy and has concise name structure.
    is_explicit_comm = bool(_EXPLICIT_COMMODITY_RE.search(processed_raw))
    is_non_commodity = (
        bool(_NON_COMMODITY_RE.search(raw))
        or bool(_NON_COMMODITY_RE.search(processed_raw))
        or bool(_LABEL_COPY_RE.search(raw))
        or bool(_LABEL_COPY_RE.search(processed_raw))
        or len(processed_raw.split()) > 6
    )

    if is_explicit_comm or not is_non_commodity:
        comm_res = normalise_commodity_name(processed_raw)
        if comm_res.success and comm_res.confidence > 0.0 and comm_res.value is not None:
            return NormalisedField(
                field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
                span_refs=(span.span_id,),
                normalised_value=comm_res.value.primary_name,
                numeric_value=None,
                unit=None,
                parse_confidence=min(span.confidence, comm_res.confidence),
            )
    return None


def _are_spans_spatially_adjacent(s1: ExtractedSpan, s2: ExtractedSpan) -> bool:
    """Deterministic spatial-adjacency predicate using polygon bounding-box geometry."""
    b1_min_x, b1_min_y, b1_max_x, b1_max_y = _get_bbox(s1.polygon)
    b2_min_x, b2_min_y, b2_max_x, b2_max_y = _get_bbox(s2.polygon)

    h1 = max(1.0, b1_max_y - b1_min_y)
    h2 = max(1.0, b2_max_y - b2_min_y)
    max_h = max(h1, h2)

    w1 = max(1.0, b1_max_x - b1_min_x)
    w2 = max(1.0, b2_max_x - b2_min_x)
    max_w = max(w1, w2)

    v_gap = max(0.0, max(b1_min_y, b2_min_y) - min(b1_max_y, b2_max_y))
    if v_gap > MAX_VERTICAL_GAP_MULTIPLIER * max_h:
        return False

    h_offset = abs(b1_min_x - b2_min_x)
    return h_offset <= MAX_HORIZONTAL_OFFSET_MULTIPLIER * max_w


def _pair_bilingual_fields(
    spans: Sequence[ExtractedSpan],
    consumed_ids: set[str],
) -> tuple[list[NormalisedField], list[CompetingReadings], set[str]]:
    """Spatial pairing of Devanagari and Latin spans representing the same declaration."""
    paired_fields: list[NormalisedField] = []
    disagreements: list[CompetingReadings] = []
    newly_consumed: set[str] = set()

    parsed_candidates: list[tuple[ExtractedSpan, NormalisedField, ScriptType]] = []
    for s in spans:
        if s.span_id in consumed_ids or s.confidence <= 0.0 or not s.text.strip():
            continue
        field = _dispatch_single_span(s)
        if field is not None:
            script = detect_script(s.text)
            parsed_candidates.append((s, field, script))

    paired_span_ids: set[str] = set()
    for i, (s1, f1, script1) in enumerate(parsed_candidates):
        if s1.span_id in paired_span_ids:
            continue
        for j, (s2, f2, script2) in enumerate(parsed_candidates):
            if i >= j or s2.span_id in paired_span_ids:
                continue

            if s1.region_id != s2.region_id:
                continue

            is_valid_bilingual_pair = (
                script1 == ScriptType.LATIN and script2 == ScriptType.DEVANAGARI
            ) or (script1 == ScriptType.DEVANAGARI and script2 == ScriptType.LATIN)

            if not is_valid_bilingual_pair:
                continue

            if f1.field_type != f2.field_type:
                continue

            if not _are_spans_spatially_adjacent(s1, s2):
                continue

            if (
                (f1.numeric_value != f2.numeric_value)
                or (f1.unit != f2.unit)
                or (f1.normalised_value != f2.normalised_value)
            ):
                reading1 = f1 if script1 == ScriptType.LATIN else f2
                reading2 = f2 if script1 == ScriptType.LATIN else f1
                disagreement = CompetingReadings(
                    field_type=f1.field_type,
                    readings=(reading1, reading2),
                    reason=DisagreementReason.BILINGUAL_VALUE_MISMATCH,
                )
                disagreements.append(disagreement)
                paired_span_ids.add(s1.span_id)
                paired_span_ids.add(s2.span_id)
                newly_consumed.add(s1.span_id)
                newly_consumed.add(s2.span_id)
                break

            refs = (
                (s1.span_id, s2.span_id)
                if script1 == ScriptType.LATIN
                else (s2.span_id, s1.span_id)
            )
            pair_conf = min(f1.parse_confidence, f2.parse_confidence)

            paired_field = NormalisedField(
                field_type=f1.field_type,
                span_refs=refs,
                normalised_value=(
                    f1.normalised_value if script1 == ScriptType.LATIN else f2.normalised_value
                ),
                numeric_value=f1.numeric_value,
                unit=f1.unit,
                parse_confidence=pair_conf,
            )
            paired_fields.append(paired_field)
            paired_span_ids.add(s1.span_id)
            paired_span_ids.add(s2.span_id)
            newly_consumed.add(s1.span_id)
            newly_consumed.add(s2.span_id)
            break

    return paired_fields, disagreements, newly_consumed


def bind_spans(spans: Sequence[ExtractedSpan]) -> ExtractionResult:
    """Classify and bind OCR spans into Legal Metrology declaration fields.

    Every input span is conserved: either referenced in at least one field's
    span_refs or returned in unclassified_spans.
    """
    if not spans:
        return ExtractionResult(fields=[], unclassified_spans=[])

    fields: list[NormalisedField] = []
    consumed_span_ids: set[str] = set()

    address_fields, address_consumed = _bind_rule_6_1_a_addresses(spans)
    fields.extend(address_fields)
    consumed_span_ids.update(address_consumed)

    bilingual_fields, bilingual_disagreements, bilingual_consumed = _pair_bilingual_fields(
        spans, consumed_span_ids
    )
    contested_field_types = {d.field_type for d in bilingual_disagreements}

    uncontested_bilingual_fields = [
        f for f in bilingual_fields if f.field_type not in contested_field_types
    ]
    fields.extend(uncontested_bilingual_fields)
    consumed_span_ids.update(bilingual_consumed)

    unclassified_spans: list[ExtractedSpan] = []
    for span in spans:
        if span.span_id in consumed_span_ids:
            continue
        field = _dispatch_single_span(span)
        if field is not None and field.field_type not in contested_field_types:
            fields.append(field)
            consumed_span_ids.add(span.span_id)
        else:
            unclassified_spans.append(span)

    return ExtractionResult(
        fields=fields,
        unclassified_spans=unclassified_spans,
        disagreements=bilingual_disagreements,
    )
