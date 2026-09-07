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
    DisplayCategory,
    classify_display_category,
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
    assert proposal.confidence == 0.95
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
    assert proposal.confidence == 0.95
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
    assert proposal.confidence == 0.95
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
    assert proposal.confidence == 0.80
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
    assert proposal.confidence == 0.98
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
    assert proposal.confidence == 0.95


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
    assert proposal.confidence == 0.95


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


def test_pan_masala_without_fssai_does_not_trigger_food_lexical_signal() -> None:
    """Regression Test 18: 'Pan Masala' alone (without statutory FSSAI licence evidence)
    does not trigger a deterministic food category proposal from lexical signals.
    """
    field = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Pan Masala",
        span_refs=("span_pan_masala",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    assert propose_category(result) is None


def test_equal_confidence_tie_returns_none() -> None:
    """Test 19: Tie abstention when two active categories have equal non-zero confidence."""
    field1 = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Edible Oil",
        span_refs=("span_oil",),
    )
    field2 = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Shampoo",
        span_refs=("span_shampoo",),
    )
    result = ExtractionResult(fields=[field1, field2], unclassified_spans=[])

    assert propose_category(result) is None


# --- Display Taxonomy Unit & Invariant Tests (EXT-011) ----------------------------------


def test_display_taxonomy_packaged_food() -> None:
    """Test A: Packaged food evidence maps to packaged_food display category."""
    field = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Edible Oil",
        span_refs=("span_oil",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    display_prop = classify_display_category(result)
    assert display_prop is not None
    assert display_prop.category == DisplayCategory.PACKAGED_FOOD
    assert display_prop.parent_category is None
    assert display_prop.path == ("packaged_goods", "packaged_food")
    assert display_prop.confidence == 0.80


def test_display_taxonomy_cosmetics() -> None:
    """Test B: Shampoo/cosmetic evidence maps to cosmetics display category."""
    field = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Herbal Shampoo",
        span_refs=("span_shampoo",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    display_prop = classify_display_category(result)
    assert display_prop is not None
    assert display_prop.category == DisplayCategory.COSMETICS
    assert display_prop.parent_category is None
    assert display_prop.path == ("packaged_goods", "cosmetics")
    assert display_prop.confidence == 0.80


def test_display_taxonomy_electronics() -> None:
    """Test C & E: Phone/electronics packaging maps to electronics branch."""
    field = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Smartphone Charger",
        span_refs=("span_phone",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    display_prop = classify_display_category(result)
    assert display_prop is not None
    assert display_prop.category == DisplayCategory.ELECTRONICS
    assert display_prop.parent_category == DisplayCategory.NON_FOOD_PACKAGED_GOODS
    assert display_prop.path == (
        "packaged_goods",
        "non_food_packaged_goods",
        "electronics",
    )
    assert display_prop.confidence == 0.80


def test_display_taxonomy_household() -> None:
    """Test D & E: Household product maps to household branch."""
    field = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Liquid Detergent",
        span_refs=("span_det",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    display_prop = classify_display_category(result)
    assert display_prop is not None
    assert display_prop.category == DisplayCategory.HOUSEHOLD
    assert display_prop.parent_category == DisplayCategory.NON_FOOD_PACKAGED_GOODS
    assert display_prop.path == (
        "packaged_goods",
        "non_food_packaged_goods",
        "household",
    )
    assert display_prop.confidence == 0.80


def test_display_taxonomy_missing_evidence_returns_none() -> None:
    """Test F: Missing or sparse evidence returns None for display taxonomy."""
    result = ExtractionResult(fields=[], unclassified_spans=[])
    assert classify_display_category(result) is None


def test_display_taxonomy_competing_signals_abstain() -> None:
    """Test G & H: Conflicting or equal-confidence display signals abstain cleanly."""
    field1 = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Smartphone",
        span_refs=("span_phone",),
    )
    field2 = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Detergent",
        span_refs=("span_det",),
    )
    result = ExtractionResult(fields=[field1, field2], unclassified_spans=[])

    assert classify_display_category(result) is None


def test_product_category_enum_remains_strictly_three_members() -> None:
    """Test I: ProductCategory enum remains strictly food, cosmetics, medical_device."""
    assert len(ProductCategory) == 3
    assert set(ProductCategory) == {
        ProductCategory.FOOD,
        ProductCategory.COSMETICS,
        ProductCategory.MEDICAL_DEVICE,
    }


def test_category_proposal_unexported_from_extraction_init() -> None:
    """Test K: CategoryProposal is still NOT exported from app.modules.extraction.__init__."""
    import app.modules.extraction as ext_mod

    assert not hasattr(ext_mod, "CategoryProposal")
    assert hasattr(ext_mod, "propose_category")


def test_electronics_and_household_do_not_produce_legal_sector_proposals() -> None:
    """Test L & M: Electronics/Household display items return None for legal sector proposal."""
    field = _make_field(
        field_type=DeclarationField.COMMON_OR_GENERIC_NAME,
        normalised_value="Smartphone",
        span_refs=("span_phone",),
    )
    result = ExtractionResult(fields=[field], unclassified_spans=[])

    assert propose_category(result) is None
    disp = classify_display_category(result)
    assert disp is not None
    assert disp.category == DisplayCategory.ELECTRONICS


def test_all_demo_signals_classified() -> None:
    """Verify each required demo commodity signal is correctly classified."""
    for s in ["Biscuits", "Edible Oil", "Ghee", "Butter"]:
        res = ExtractionResult(
            fields=[_make_field(DeclarationField.COMMON_OR_GENERIC_NAME, s, ("s1",))],
            unclassified_spans=[],
        )
        d = classify_display_category(res)
        assert d is not None and d.category == DisplayCategory.PACKAGED_FOOD

    for s in ["Shampoo", "Soap", "Lotion", "Toothpaste", "Cream", "Perfume"]:
        res = ExtractionResult(
            fields=[_make_field(DeclarationField.COMMON_OR_GENERIC_NAME, s, ("s1",))],
            unclassified_spans=[],
        )
        d = classify_display_category(res)
        assert d is not None and d.category == DisplayCategory.COSMETICS

    for s in ["Phone", "Smartphone", "Charger", "Headphones", "Earbuds", "Electronics"]:
        res = ExtractionResult(
            fields=[_make_field(DeclarationField.COMMON_OR_GENERIC_NAME, s, ("s1",))],
            unclassified_spans=[],
        )
        d = classify_display_category(res)
        assert d is not None and d.category == DisplayCategory.ELECTRONICS

    for s in ["Detergent", "Cleaner", "Disinfectant", "Dishwash"]:
        res = ExtractionResult(
            fields=[_make_field(DeclarationField.COMMON_OR_GENERIC_NAME, s, ("s1",))],
            unclassified_spans=[],
        )
        d = classify_display_category(res)
        assert d is not None and d.category == DisplayCategory.HOUSEHOLD
