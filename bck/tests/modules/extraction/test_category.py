"""Unit tests for deterministic category proposal (EXT-005 / PIP-002).

Validates propose_category against statutory evidence (FSSAI, Drugs & Cosmetics Rules,
Medical Devices Rules 2017) and corpus-grounded commodity signals using the actual
NormalisedField and ExtractedSpan contracts.
"""

from __future__ import annotations

from decimal import Decimal

from app.contracts import (
    DeclarationField,
    EvidenceProvider,
    ExtractedSpan,
    NormalisedField,
    ProductCategory,
)
from app.modules.extraction.binder import ExtractionResult
from app.modules.extraction.category import (
    CONFIDENCE_LEXICAL_SIGNAL,
    CONFIDENCE_MUTUALLY_REINFORCING,
    CONFIDENCE_STATUTORY_SIGNAL,
    propose_category,
)


def _make_span(span_id: str, text: str) -> ExtractedSpan:
    """Helper to construct a valid ExtractedSpan matching full contract API."""
    return ExtractedSpan(
        span_id=span_id,
        text=text,
        polygon=(
            (0.0, 0.0),
            (10.0, 0.0),
            (10.0, 5.0),
            (0.0, 5.0),
        ),
        confidence=0.95,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="region_pdp_1",
    )


def _make_field(
    field_type: DeclarationField,
    normalised_value: str,
    span_refs: tuple[str, ...],
    numeric_value: Decimal | None = None,
    unit: str | None = None,
    parse_confidence: float = 0.95,
) -> NormalisedField:
    """Helper to construct a valid NormalisedField matching full contract API."""
    return NormalisedField(
        field_type=field_type,
        span_refs=span_refs,
        normalised_value=normalised_value,
        numeric_value=numeric_value,
        unit=unit,
        parse_confidence=parse_confidence,
    )


def test_clear_food_proposal_from_fssai_licence() -> None:
    """Test 1: Clear FOOD proposal from explicit FSSAI licence statutory evidence."""
    field = _make_field(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        normalised_value="Manufactured by ABC Foods Ltd. FSSAI Lic. No. 10012022000123",
        span_refs=("span_food_1",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    proposal = propose_category(result)
    assert proposal is not None
    assert proposal.category is ProductCategory.FOOD
    assert proposal.confidence == CONFIDENCE_STATUTORY_SIGNAL
    assert proposal.span_refs == ("span_food_1",)
    assert "food" in proposal.reason
    assert "span_food_1" in proposal.reason


def test_clear_cosmetics_proposal_from_d_and_c_rules() -> None:
    """Test 2: Clear COSMETICS proposal from Drugs and Cosmetics Rules statutory evidence."""
    field = _make_field(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        normalised_value="Marketed by Beauty Corp under Drugs & Cosmetics Rules M.L. C-1234",
        span_refs=("span_cosm_1",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    proposal = propose_category(result)
    assert proposal is not None
    assert proposal.category is ProductCategory.COSMETICS
    assert proposal.confidence == CONFIDENCE_STATUTORY_SIGNAL
    assert proposal.span_refs == ("span_cosm_1",)
    assert "cosmetics" in proposal.reason


def test_clear_medical_device_proposal_from_mdr_2017() -> None:
    """Test 3: Clear MEDICAL_DEVICE proposal from Medical Devices Rules 2017 evidence."""
    field = _make_field(
        field_type=DeclarationField.OTHER_PRESCRIBED_MATTER,
        normalised_value="Complies with Medical Devices Rules 2017. Reg No: MFG/MD/2021/001",
        span_refs=("span_md_1",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    proposal = propose_category(result)
    assert proposal is not None
    assert proposal.category is ProductCategory.MEDICAL_DEVICE
    assert proposal.confidence == CONFIDENCE_STATUTORY_SIGNAL
    assert proposal.span_refs == ("span_md_1",)
    assert "medical_device" in proposal.reason


def test_lexical_commodity_name_signal() -> None:
    """Test 4: Category signal inferred from corpus-grounded commodity name."""
    field = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Butter Biscuits",
        span_refs=("span_lex_1",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    proposal = propose_category(result)
    assert proposal is not None
    assert proposal.category is ProductCategory.FOOD
    assert proposal.confidence == CONFIDENCE_LEXICAL_SIGNAL
    assert proposal.span_refs == ("span_lex_1",)


def test_reinforcing_statutory_and_lexical_evidence_boosts_confidence() -> None:
    """Test 5: Both statutory and lexical evidence present boost confidence to 0.98."""
    field1 = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Herbal Shampoo",
        span_refs=("span_shampoo",),
    )
    field2 = _make_field(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        normalised_value="Mfg under Drugs & Cosmetics Rules M.L. C-999",
        span_refs=("span_lic",),
    )
    result = ExtractionResult(fields=[field1, field2], unclassified_spans=[])

    proposal = propose_category(result)
    assert proposal is not None
    assert proposal.category is ProductCategory.COSMETICS
    assert proposal.confidence == CONFIDENCE_MUTUALLY_REINFORCING
    assert proposal.span_refs == ("span_shampoo", "span_lic")


def test_sparse_or_irrelevant_evidence_returns_none() -> None:
    """Test 6: Sparse/generic declarations return None without guessing."""
    field = _make_field(
        field_type=DeclarationField.RETAIL_SALE_PRICE,
        normalised_value="MRP Rs. 100.00 incl. of all taxes",
        span_refs=("span_mrp",),
        numeric_value=Decimal("100.00"),
        unit="INR",
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    assert propose_category(result) is None


def test_empty_result_returns_none() -> None:
    """Test 7: Empty ExtractionResult returns None."""
    result = ExtractionResult(fields=[], unclassified_spans=[])
    assert propose_category(result) is None


def test_conflicting_category_evidence_returns_none() -> None:
    """Test 8: Conflicting evidence from two categories returns None."""
    field1 = _make_field(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        normalised_value="FSSAI Lic. No. 10012022000123",
        span_refs=("span_food",),
    )
    field2 = _make_field(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        normalised_value="Drugs & Cosmetics Rules M.L. C-123",
        span_refs=("span_cosm",),
    )
    result = ExtractionResult(fields=[field1, field2], unclassified_spans=[])

    assert propose_category(result) is None


def test_proposal_cites_valid_span_refs_and_deduplicates() -> None:
    """Test 9: span_refs are deduplicated in order and only contain valid IDs."""
    field1 = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Medical Devices Rules 2017",
        span_refs=("span_t1", "span_t2"),
    )
    field2 = _make_field(
        field_type=DeclarationField.OTHER_PRESCRIBED_MATTER,
        normalised_value="Medical Devices Rules 2017",
        span_refs=("span_t2", "span_t3"),
    )
    result = ExtractionResult(fields=[field1, field2], unclassified_spans=[])

    proposal = propose_category(result)
    assert proposal is not None
    assert proposal.category is ProductCategory.MEDICAL_DEVICE
    assert proposal.span_refs == ("span_t1", "span_t2", "span_t3")


def test_unclassified_spans_can_provide_category_signal() -> None:
    """Test 10: Unclassified spans are evaluated when fields have no category signal."""
    unclass_span = _make_span(span_id="unclass_1", text="FSSAI Lic. No. 10012022000555")
    result = ExtractionResult(fields=[], unclassified_spans=[unclass_span])

    proposal = propose_category(result)
    assert proposal is not None
    assert proposal.category is ProductCategory.FOOD
    assert proposal.span_refs == ("unclass_1",)


def test_deterministic_repeated_invocation() -> None:
    """Test 11: propose_category is strictly deterministic across repeated calls."""
    field = _make_field(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        normalised_value="FSSAI Lic. No. 10012022000123",
        span_refs=("span_repeat",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    p1 = propose_category(result)
    p2 = propose_category(result)
    assert p1 == p2


def test_confidence_bounds() -> None:
    """Test 12: Confidence score is bounded in [0.0, 1.0]."""
    field = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Biscuits FSSAI Lic. No. 10012022000123",
        span_refs=("span_b1",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    proposal = propose_category(result)
    assert proposal is not None
    assert 0.0 <= proposal.confidence <= 1.0


# --- Review Regression Tests -----------------------------------------------------------


def test_bare_md_batch_code_does_not_trigger_medical_device() -> None:
    """Regression Test 13: Bare 'MD-2024' batch code does not trigger medical device proposal."""
    field = _make_field(
        field_type=DeclarationField.OTHER_PRESCRIBED_MATTER,
        normalised_value="Batch No: MD-2024 Exp: 2027",
        span_refs=("span_batch",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    assert propose_category(result) is None


def test_legitimate_mfg_md_license_triggers_medical_device() -> None:
    """Regression Test 14: Anchored MFG/MD licence triggers medical device proposal."""
    field = _make_field(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        normalised_value="Licence No: MFG/MD/2021/001",
        span_refs=("span_mfg_md",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    proposal = propose_category(result)
    assert proposal is not None
    assert proposal.category is ProductCategory.MEDICAL_DEVICE
    assert proposal.confidence == CONFIDENCE_STATUTORY_SIGNAL


def test_arbitrary_14_digit_number_does_not_trigger_food() -> None:
    """Regression Test 15: Arbitrary 14-digit GTIN/number does not trigger food proposal."""
    field = _make_field(
        field_type=DeclarationField.OTHER_PRESCRIBED_MATTER,
        normalised_value="GTIN-14: 12345678901234",
        span_refs=("span_gtin",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    assert propose_category(result) is None


def test_anchored_fssai_14_digit_licence_triggers_food() -> None:
    """Regression Test 16: FSSAI-anchored 14-digit licence triggers food proposal."""
    field = _make_field(
        field_type=DeclarationField.NAME_AND_ADDRESS,
        normalised_value="FSSAI Lic. No. 10012022000123",
        span_refs=("span_fssai",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    proposal = propose_category(result)
    assert proposal is not None
    assert proposal.category is ProductCategory.FOOD
    assert proposal.confidence == CONFIDENCE_STATUTORY_SIGNAL


def test_competing_food_and_cosmetics_lexical_signals_safely_abstain() -> None:
    """Regression Test 17: Competing food (Butter) & cosmetics (Cream) Category A
    lexical signals safely abstain by returning None.
    """
    field = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Butter Body Cream",
        span_refs=("span_butter_cream",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    assert propose_category(result) is None
