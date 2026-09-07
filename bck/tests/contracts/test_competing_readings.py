"""CTR-006 — the contract for two readings of one declaration that do not agree.

Three properties, each with a defect it was falsified against: a disagreement of one
reading cannot be constructed, a disagreement whose readings answer another obligation
cannot be constructed, and no obligation appears in both ``ExtractionResult`` collections.

The last of those reaches into ``app.modules.extraction`` for ``ExtractionResult``, which
is where the type lives — it is not a contract. CTR-006 adds the ``disagreements`` field
and this invariant to it under a crossing authorised for that ticket alone.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.contracts import (
    CompetingReadings,
    DeclarationField,
    DisagreementReason,
    NormalisedField,
)
from app.modules.extraction import ExtractionResult


def reading(
    value: str,
    *,
    span: str,
    numeric: str | None = None,
    unit: str | None = None,
    field_type: DeclarationField = DeclarationField.NET_QUANTITY,
) -> NormalisedField:
    """One reading of one declaration, of the shape the binder emits."""
    return NormalisedField(
        field_type=field_type,
        span_refs=(span,),
        normalised_value=value,
        numeric_value=None if numeric is None else Decimal(numeric),
        unit=unit,
        parse_confidence=0.9,
    )


LATIN = reading("500 g", span="lat1", numeric="500", unit="g")
DEVANAGARI = reading("250 g", span="dev1", numeric="250", unit="g")


def disagreement(*readings: NormalisedField) -> CompetingReadings:
    return CompetingReadings(
        field_type=DeclarationField.NET_QUANTITY,
        readings=readings,
        reason=DisagreementReason.BILINGUAL_VALUE_MISMATCH,
    )


# --------------------------------------------------------------------------------------
# Two or more readings. One reading is a NormalisedField.
# --------------------------------------------------------------------------------------


def test_two_readings_that_disagree_construct() -> None:
    """The shape the binder will emit for "500 g" against "२५० ग्राम"."""
    competing = disagreement(LATIN, DEVANAGARI)

    assert competing.field_type is DeclarationField.NET_QUANTITY
    assert competing.readings == (LATIN, DEVANAGARI)
    assert competing.reason is DisagreementReason.BILINGUAL_VALUE_MISMATCH


def test_a_single_reading_is_not_a_disagreement() -> None:
    """One reading is a NormalisedField, and must not be expressible as a disagreement.

    Letting it construct would put a resolved declaration inside the collection whose
    whole meaning is that no declaration was resolved — and PIP-004 routes everything in
    that collection to REVIEW_REQUIRED, so a package would be sent to an officer over a
    declaration nothing contested.
    """
    with pytest.raises(ValidationError):
        disagreement(LATIN)


def test_no_readings_at_all_is_not_a_disagreement() -> None:
    with pytest.raises(ValidationError):
        disagreement()


def test_a_disagreement_is_frozen() -> None:
    """A record of what was read, not a working set. Nothing narrows it after the fact."""
    competing = disagreement(LATIN, DEVANAGARI)

    with pytest.raises(ValidationError):
        competing.readings = (LATIN,)  # type: ignore[misc]


# --------------------------------------------------------------------------------------
# field_type on the container is the same fact as field_type on every reading.
# --------------------------------------------------------------------------------------


def test_a_reading_of_another_obligation_is_refused() -> None:
    """Every consumer keys on the container's field_type, so a mismatch would route a
    real disagreement to the wrong obligation without anything noticing."""
    other = reading("India", span="lat2", field_type=DeclarationField.COUNTRY_OF_ORIGIN)

    with pytest.raises(ValidationError):
        disagreement(LATIN, other)


# --------------------------------------------------------------------------------------
# An obligation is either resolved or contested. Never both.
# --------------------------------------------------------------------------------------


def test_an_extraction_result_may_hold_both_collections() -> None:
    """The two coexist as long as they name different obligations."""
    origin = reading("India", span="lat2", field_type=DeclarationField.COUNTRY_OF_ORIGIN)
    result = ExtractionResult(
        fields=[origin],
        unclassified_spans=[],
        disagreements=[disagreement(LATIN, DEVANAGARI)],
    )

    assert {field.field_type for field in result.fields} == {DeclarationField.COUNTRY_OF_ORIGIN}
    assert {d.field_type for d in result.disagreements} == {DeclarationField.NET_QUANTITY}


def test_a_field_in_disagreements_is_never_also_in_fields() -> None:
    """The double-count. Two collections mean a consumer can count one declaration twice.

    ``rule_findings._one_declaration`` decides a declaration is present on the truthiness
    of its entry in ``declared``, which is built from ``fields`` alone. An obligation in
    both collections is therefore a PASS on a package that contradicts itself — the
    wrongful PASS CTR-006 exists to make unrepresentable.
    """
    with pytest.raises(ValidationError):
        ExtractionResult(
            fields=[LATIN],
            unclassified_spans=[],
            disagreements=[disagreement(LATIN, DEVANAGARI)],
        )


def test_the_disagreements_collection_defaults_empty() -> None:
    """Every existing construction site predates the field and supplies neither it nor a
    conflict, so the default has to keep all of them valid."""
    result = ExtractionResult(fields=[LATIN], unclassified_spans=[])

    assert result.disagreements == []
