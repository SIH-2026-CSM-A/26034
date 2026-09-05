"""Date normaliser for Legal Metrology declarations."""

import re
from datetime import date

from app.modules.extraction.types import (
    DateType,
    DateValue,
    NormalizationResult,
    ReasonCode,
)

MONTH_MAP: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _parse_packing_iso(packing_date: DateValue | str | None) -> tuple[int, int] | None:
    """Extract and validate (year, month) from a packing date argument."""
    if not packing_date:
        return None
    iso_str = packing_date.iso_date if isinstance(packing_date, DateValue) else str(packing_date)
    if not iso_str:
        return None
    parts = iso_str.split("-")
    if len(parts) >= 2:
        try:
            y, m = int(parts[0]), int(parts[1])
            if 1 <= m <= 12 and 1900 <= y <= 2100:
                return y, m
        except ValueError:
            return None
    return None


def _add_months(year: int, month: int, months_to_add: int) -> tuple[int, int]:
    """Add months to year-month deterministically."""
    total_months = (year * 12) + (month - 1) + months_to_add
    new_year = total_months // 12
    new_month = (total_months % 12) + 1
    return new_year, new_month


def normalise_date(
    text: str,
    packing_date: DateValue | str | None = None,
) -> NormalizationResult[DateValue]:
    """Normalise raw OCR text into a Date declaration."""
    if not text or not text.strip():
        return NormalizationResult[DateValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.EMPTY_INPUT,
            raw_text=text or "",
        )

    raw = text.strip()
    upper_raw = raw.upper()

    # Determine Date Type
    date_type = None
    if "MFG" in upper_raw or "MANUFACTURE" in upper_raw:
        date_type = DateType.MANUFACTURED
    elif "PKD" in upper_raw or "PACKED" in upper_raw:
        date_type = DateType.PACKED
    elif "BEST BEFORE" in upper_raw or "USE BY" in upper_raw:
        date_type = DateType.BEST_BEFORE
    elif "EXP" in upper_raw or "EXPIRY" in upper_raw:
        date_type = DateType.EXPIRY

    # Check for relative expressions, e.g., "Best before 6 months from packing"
    # Named comment for regex over 80 characters:
    # Captures relative period expressions such as "Best before 6 months from packing/pkd"
    relative_pat = (
        r"(?:best\s+before|use\s+within|expiry\s+within)\s+(\d+)\s+months?"
        r"(?:\s+from\s+(?:packing|mfg|manufacture|pkd))?"
    )
    rel_match = re.search(relative_pat, raw, re.IGNORECASE)

    if rel_match:
        rel_months = int(rel_match.group(1))
        packing_ym = _parse_packing_iso(packing_date)

        val = DateValue(
            date_type=date_type or DateType.BEST_BEFORE,
            iso_date=None,
            is_relative=True,
            relative_months=rel_months,
            raw_expression=raw,
        )

        if not packing_ym:
            return NormalizationResult[DateValue](
                value=val,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.MISSING_PACKING_DATE,
                raw_text=raw,
            )

        calc_y, calc_m = _add_months(packing_ym[0], packing_ym[1], rel_months)
        val.iso_date = f"{calc_y:04d}-{calc_m:02d}"

        return NormalizationResult[DateValue](
            value=val,
            confidence=0.9,
            success=True,
            reason_code=None,
            raw_text=raw,
        )

    # Check for 3-part numeric date candidates (DD.MM.YYYY, DD/MM/YYYY, etc.)
    # and validate calendar correctness before ambiguity or MM/YYYY parsing
    three_part_pat = r"\b(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{2,4})\b"
    three_part_matches = list(re.finditer(three_part_pat, raw))
    for match in three_part_matches:
        d_str, m_str, y_str = match.group(1), match.group(2), match.group(3)
        d, m = int(d_str), int(m_str)
        y = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
        if m < 1 or m > 12 or d < 1 or d > 31:
            return NormalizationResult[DateValue](
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.INVALID_VALUE,
                raw_text=raw,
            )
        try:
            date(y, m, d)
        except ValueError:
            return NormalizationResult[DateValue](
                value=None,
                confidence=0.0,
                success=False,
                reason_code=ReasonCode.INVALID_VALUE,
                raw_text=raw,
            )

    # Detect multiple conflicting date occurrences (full dates, MM/YYYY, MM/YY, text months)
    # -> AMBIGUOUS_VALUE
    full_dates = [m.group(0) for m in three_part_matches]
    raw_without_full = re.sub(three_part_pat, "___FULL_DATE___", raw)

    my_pat = r"\b(?:0?[1-9]|1[012])[\.\/\-](?:20\d{2}|\d{2})\b"
    my_dates = re.findall(my_pat, raw_without_full)

    text_month_pat_all = (
        r"\b(?:0?[1-9]|[12][0-9]|3[01])?\s*"
        r"(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|"
        r"aug|august|sep|september|oct|october|nov|november|dec|december)\s*"
        r"(?:20\d{2}|\d{2})\b"
    )
    text_dates = re.findall(text_month_pat_all, raw_without_full, re.IGNORECASE)

    all_found_dates = full_dates + my_dates + text_dates
    if len(all_found_dates) > 1 and len(set(all_found_dates)) > 1:
        return NormalizationResult[DateValue](
            value=None,
            confidence=0.0,
            success=False,
            reason_code=ReasonCode.AMBIGUOUS_VALUE,
            raw_text=raw,
        )

    # Absolute Date Formats
    # 1. Full numeric dates DD.MM.YYYY / DD/MM/YYYY / DD-MM-YYYY
    if three_part_matches:
        m_full = three_part_matches[0]
        d_str, m_str, y_str = m_full.group(1), m_full.group(2), m_full.group(3)
        d, m = int(d_str), int(m_str)
        y = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
        iso_str = f"{y:04d}-{m:02d}-{d:02d}"
        return NormalizationResult[DateValue](
            value=DateValue(
                date_type=date_type,
                iso_date=iso_str,
                is_relative=False,
            ),
            confidence=0.95,
            success=True,
            reason_code=None,
            raw_text=raw,
        )

    # 2. Textual month e.g. "15 MAR 2026" or "MAR 2026" or "March 2026"
    text_month_pat = r"\b(?:(0?[1-9]|[12][0-9]|3[01])\s+)?([a-zA-Z]{3,9})\s+(20\d{2})\b"
    m_text = re.search(text_month_pat, raw)
    if m_text:
        day_str, month_str, year_str = (
            m_text.group(1),
            m_text.group(2).lower(),
            m_text.group(3),
        )
        month_num = MONTH_MAP.get(month_str)
        if month_num:
            y = int(year_str)
            if day_str:
                d = int(day_str)
                try:
                    date(y, month_num, d)
                except ValueError:
                    return NormalizationResult[DateValue](
                        value=None,
                        confidence=0.0,
                        success=False,
                        reason_code=ReasonCode.INVALID_VALUE,
                        raw_text=raw,
                    )
                iso_str = f"{y:04d}-{month_num:02d}-{d:02d}"
            else:
                iso_str = f"{y:04d}-{month_num:02d}"
            return NormalizationResult[DateValue](
                value=DateValue(
                    date_type=date_type,
                    iso_date=iso_str,
                    is_relative=False,
                ),
                confidence=0.9,
                success=True,
                reason_code=None,
                raw_text=raw,
            )

    # 3. MM/YYYY or MM/YY
    m_my = re.search(r"\b(0?[1-9]|1[012])[\.\/\-](20\d{2}|\d{2})\b", raw)
    if m_my:
        m, y_str = int(m_my.group(1)), m_my.group(2)
        y = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
        iso_str = f"{y:04d}-{m:02d}"
        return NormalizationResult[DateValue](
            value=DateValue(
                date_type=date_type,
                iso_date=iso_str,
                is_relative=False,
            ),
            confidence=0.9,
            success=True,
            reason_code=None,
            raw_text=raw,
        )

    return NormalizationResult[DateValue](
        value=None,
        confidence=0.0,
        success=False,
        reason_code=ReasonCode.UNPARSEABLE_FORMAT,
        raw_text=raw,
    )
