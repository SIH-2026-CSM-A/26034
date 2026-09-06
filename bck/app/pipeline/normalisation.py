"""Declared text to the canonical value a rule can be evaluated against.

The extraction module normalises nine kinds of declaration, each into its own result type
with its own value shape. Rules and findings speak one shape,
:class:`~app.contracts.NormalisedField`. This is the translation, and the only place it
happens — the same role :mod:`app.pipeline.rule_snapshot` plays for rules.

``numeric_value`` is lifted as ``Decimal`` wherever the declaration has one, never
re-parsed out of the text later. These values are compared against tolerances — a retail
sale price against a money figure, a net quantity against the First Schedule's maximum
permissible error — and re-parsing a number at each comparison site is how binary float
error gets back into a comparison that decides a finding.

**The two ingestion paths establish a declaration's identity differently, and the
normalisers only know one of them.** ``normalise_address``, ``normalise_consumer_care``
and ``normalise_country_of_origin`` all require a role keyword or prose context *inside
the text* — "Manufactured by …", "Made in India" — because on a package they are handed an
unlabelled run of OCR text and have to establish for themselves which obligation it
answers. That is right for a photograph and wrong for a listing, where the platform has
already told us the role: ``CatalogueRecord.declared_fields`` is keyed by obligation, so
``{COUNTRY_OF_ORIGIN: "India"}`` has stated the role in the key. Passing that bare value
to a parser that demands prose returns UNPARSEABLE_FORMAT for a perfectly clear
declaration.

:func:`normalise_declaration` therefore takes ``identity_established``. Where the identity
came from the source — a listing key — a parse failure still yields a field carrying the
text as declared, because the declaration is demonstrably present and only its canonical
*form* is unresolved. Where it did not — OCR text — a parse failure yields ``None``,
because neither the identity nor the value has been established and claiming the
declaration is present would be inventing it.
"""

from collections.abc import Callable
from decimal import Decimal

from app.contracts import DeclarationField, NormalisedField
from app.modules.extraction.normalise import (
    NormalizationResult,
    normalise_address,
    normalise_commodity_name,
    normalise_consumer_care,
    normalise_country_of_origin,
    normalise_date,
    normalise_dimensions,
    normalise_mrp,
    normalise_net_quantity,
    normalise_unit_sale_price,
)

NORMALISERS: dict[DeclarationField, Callable[[str], NormalizationResult]] = {
    DeclarationField.NAME_AND_ADDRESS: normalise_address,
    DeclarationField.COUNTRY_OF_ORIGIN: normalise_country_of_origin,
    DeclarationField.COMMON_OR_GENERIC_NAME: normalise_commodity_name,
    DeclarationField.NET_QUANTITY: normalise_net_quantity,
    DeclarationField.MANUFACTURE_DATE: normalise_date,
    DeclarationField.BEST_BEFORE_DATE: normalise_date,
    DeclarationField.RETAIL_SALE_PRICE: normalise_mrp,
    DeclarationField.DIMENSIONS: normalise_dimensions,
    DeclarationField.CONSUMER_CARE: normalise_consumer_care,
    DeclarationField.UNIT_SALE_PRICE: normalise_unit_sale_price,
}
"""Which extraction normaliser answers each declaration.

:attr:`~app.contracts.DeclarationField.OTHER_PRESCRIBED_MATTER` has none, deliberately.
Rule 6(1)(g) is the catch-all limb for matter specified elsewhere in the Rules; it has no
single canonical form to normalise into, and inventing one would mean deciding what the
declaration says. Text under that limb is carried through verbatim.
"""

_NUMERIC_ATTRIBUTES = ("amount", "value", "unit_price")
"""Where each extraction value type keeps its number. Checked in order; the first present
wins, and a value type with none simply has no numeric form."""


def _numeric(value: object) -> tuple[Decimal | None, str | None]:
    """The numeric form and canonical unit of an extraction value, where it has one."""
    for attribute in _NUMERIC_ATTRIBUTES:
        number = getattr(value, attribute, None)
        if isinstance(number, Decimal):
            unit = getattr(value, "unit", None) or getattr(value, "currency", None)
            return number, unit
    return None, None


def normalise_declaration(
    field: DeclarationField,
    text: str,
    span_refs: tuple[str, ...],
    *,
    identity_established: bool,
) -> NormalisedField | None:
    """Resolve one declared string into a canonical field.

    Returns ``None`` only where nothing has been established — the text did not parse and
    its identity as this declaration was not given by the source. That is not the same as
    the declaration being absent, and a caller must not treat it as such: present but
    unreadable says something about our reading, absent may say something about the
    package, and the two carry different consequences.

    See the module docstring for why ``identity_established`` exists.
    """
    normaliser = NORMALISERS.get(field)
    if normaliser is None:
        return NormalisedField(
            field_type=field,
            span_refs=span_refs,
            normalised_value=text,
            parse_confidence=1.0,
        )

    result = normaliser(text)
    if not result.success or result.value is None:
        if not identity_established:
            return None
        # Declared, and demonstrably this obligation, but not canonicalised. Zero parse
        # confidence states exactly that: the value is carried as the source gave it, and
        # nothing downstream may treat it as a parsed figure.
        return NormalisedField(
            field_type=field,
            span_refs=span_refs,
            normalised_value=text,
            parse_confidence=0.0,
        )

    numeric, unit = _numeric(result.value)
    return NormalisedField(
        field_type=field,
        span_refs=span_refs,
        normalised_value=text,
        numeric_value=numeric,
        unit=unit,
        parse_confidence=result.confidence,
    )
