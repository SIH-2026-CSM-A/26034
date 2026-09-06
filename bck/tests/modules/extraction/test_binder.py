"""Comprehensive unit test suite for OCR span classification and spatial role binder."""

from decimal import Decimal

from app.contracts import (
    DeclarationField,
    EvidenceProvider,
    ExtractedSpan,
)
from app.modules.extraction import ExtractionResult, bind_spans
from app.modules.extraction.binder import extract_valid_pincodes


def _make_span(
    span_id: str,
    text: str,
    y_min: float = 0.0,
    y_max: float = 20.0,
    x_min: float = 0.0,
    x_max: float = 100.0,
    confidence: float = 0.95,
    region_id: str = "pdp",
    provider: EvidenceProvider = EvidenceProvider.PADDLEOCR,
) -> ExtractedSpan:
    """Helper to construct ExtractedSpan with quadrilateral polygon."""
    polygon = (
        (x_min, y_min),
        (x_max, y_min),
        (x_max, y_max),
        (x_min, y_max),
    )
    return ExtractedSpan(
        span_id=span_id,
        text=text,
        polygon=polygon,
        confidence=confidence,
        source_provider=provider,
        region_id=region_id,
    )


# -----------------------------------------------------------------------------
# 1. Span Count Conservation Tests
# -----------------------------------------------------------------------------


def test_span_conservation_empty_input():
    """Empty span input returns empty fields and empty unclassified list."""
    res = bind_spans([])
    assert isinstance(res, ExtractionResult)
    assert res.fields == []
    assert res.unclassified_spans == []


def test_span_conservation_all_spans_bound():
    """All valid declaration spans are bound; conservation holds with 0 unclassified."""
    spans = [
        _make_span("s1", "MRP Rs 150.00", y_min=10, y_max=30),
        _make_span("s2", "Net Qty: 500 g", y_min=40, y_max=60),
        _make_span("s3", "MFG 03/2026", y_min=70, y_max=90),
        _make_span("s4", "Country of Origin: India", y_min=100, y_max=120),
    ]
    res = bind_spans(spans)
    bound_refs = set(ref for f in res.fields for ref in f.span_refs)
    unclassified_ids = set(s.span_id for s in res.unclassified_spans)

    assert len(res.fields) == 4
    assert len(unclassified_ids) == 0
    assert bound_refs == {"s1", "s2", "s3", "s4"}
    assert len(bound_refs) + len(res.unclassified_spans) == len(spans)


def test_span_conservation_mixed_bound_and_unclassified():
    """Mixed label with bound fields and unclassified metadata preserves all spans."""
    spans = [
        _make_span("s1", "Generic Name: Toothpaste", y_min=10, y_max=30),
        _make_span("s2", "Batch No: B-9921", y_min=40, y_max=60),
        _make_span("s3", "MRP Rs 99.00", y_min=70, y_max=90),
        _make_span("s4", "Store in a cool dry place", y_min=100, y_max=120),
        _make_span("s5", "Net Qty: 100 g", y_min=130, y_max=150),
    ]
    res = bind_spans(spans)
    bound_refs = set(ref for f in res.fields for ref in f.span_refs)
    unclassified_ids = set(s.span_id for s in res.unclassified_spans)

    assert bound_refs.isdisjoint(unclassified_ids)
    assert bound_refs.union(unclassified_ids) == {"s1", "s2", "s3", "s4", "s5"}
    assert len(bound_refs) + len(res.unclassified_spans) == len(spans)
    assert "s2" in unclassified_ids
    assert "s4" in unclassified_ids


def test_span_conservation_all_unclassified():
    """Non-declaration spans are entirely preserved in unclassified_spans."""
    spans = [
        _make_span("u1", "Batch No: 123", y_min=10, y_max=30),
        _make_span("u2", "Barcode 8901234567890", y_min=40, y_max=60),
        _make_span("u3", "Keep away from direct sunlight", y_min=70, y_max=90),
    ]
    res = bind_spans(spans)
    assert len(res.fields) == 0
    assert len(res.unclassified_spans) == 3
    assert {s.span_id for s in res.unclassified_spans} == {"u1", "u2", "u3"}


# -----------------------------------------------------------------------------
# 2. Rule 6(1)(a) Address Binding: Manufactured-by and Marketed-by Both Present
# -----------------------------------------------------------------------------


def test_manufactured_by_and_marketed_by_both_present():
    """Manufactured-by and Marketed-by both present, each bound to its downward address block."""
    spans = [
        _make_span("mfg_anchor", "Manufactured by:", y_min=100, y_max=120),
        _make_span("mfg_addr1", "Apex Foods Pvt Ltd", y_min=125, y_max=145),
        _make_span("mfg_addr2", "Industrial Area, Pune - 411001", y_min=150, y_max=170),
        _make_span("mkt_anchor", "Marketed by:", y_min=200, y_max=220),
        _make_span("mkt_addr1", "Global Brands Retail Ltd", y_min=225, y_max=245),
        _make_span("mkt_addr2", "Connaught Place, New Delhi - 110001", y_min=250, y_max=270),
    ]
    res = bind_spans(spans)
    addr_fields = [f for f in res.fields if f.field_type == DeclarationField.NAME_AND_ADDRESS]

    assert len(addr_fields) == 2
    assert addr_fields[0].span_refs == ("mfg_anchor", "mfg_addr1", "mfg_addr2")
    assert "411001" in addr_fields[0].normalised_value
    assert addr_fields[1].span_refs == ("mkt_anchor", "mkt_addr1", "mkt_addr2")
    assert "110001" in addr_fields[1].normalised_value

    # Check conservation
    bound_refs = set(ref for f in res.fields for ref in f.span_refs)
    assert bound_refs == {
        "mfg_anchor",
        "mfg_addr1",
        "mfg_addr2",
        "mkt_anchor",
        "mkt_addr1",
        "mkt_addr2",
    }
    assert len(res.unclassified_spans) == 0


# -----------------------------------------------------------------------------
# 3. Only Marketed-by Present With Valid Address
# -----------------------------------------------------------------------------


def test_only_marketed_by_present_with_valid_address():
    """Only Marketed-by present with valid address binds to NAME_AND_ADDRESS."""
    spans = [
        _make_span("mkt1", "Marketed by:", y_min=50, y_max=70),
        _make_span("mkt2", "Health Foods Pvt Ltd", y_min=75, y_max=95),
        _make_span("mkt3", "MG Road, Bengaluru 560001", y_min=100, y_max=120),
    ]
    res = bind_spans(spans)
    assert len(res.fields) == 1
    field = res.fields[0]
    assert field.field_type == DeclarationField.NAME_AND_ADDRESS
    assert field.span_refs == ("mkt1", "mkt2", "mkt3")
    assert "560001" in field.normalised_value
    assert len(res.unclassified_spans) == 0


# -----------------------------------------------------------------------------
# 4. Address Block Positioned ABOVE Keyword Anchor Must NOT Bind
# -----------------------------------------------------------------------------


def test_address_block_positioned_above_keyword_anchor_rejected():
    """Address block positioned ABOVE its keyword anchor MUST NOT bind."""
    spans = [
        # Address sits above (y: 50..95)
        _make_span("addr1", "Sun Enterprises Ltd", y_min=50, y_max=70),
        _make_span("addr2", "Sector 18, Noida 201301", y_min=75, y_max=95),
        # Keyword anchor sits below (y: 200..220)
        _make_span("anchor", "Manufactured by:", y_min=200, y_max=220),
    ]
    res = bind_spans(spans)
    addr_fields = [f for f in res.fields if f.field_type == DeclarationField.NAME_AND_ADDRESS]
    assert len(addr_fields) == 0
    # All spans must be preserved in unclassified_spans
    assert len(res.unclassified_spans) == 3
    assert {s.span_id for s in res.unclassified_spans} == {"addr1", "addr2", "anchor"}


# -----------------------------------------------------------------------------
# 5. Phone Numbers Containing 6 Consecutive Digits Must NOT Be PIN Codes
# -----------------------------------------------------------------------------


def test_phone_number_1800_with_six_digits_not_treated_as_pincode():
    """A toll-free phone number containing 6 digits (1800-110001) is NOT a PIN code."""
    pins = extract_valid_pincodes("Customer Care Helpline: 1800-110001")
    assert pins == []

    # If anchor only has a phone number candidate below it, it must NOT bind as address
    spans = [
        _make_span("a1", "Marketed by:", y_min=100, y_max=120),
        _make_span("a2", "Care Cell: 1800-110001", y_min=130, y_max=150),
    ]
    res = bind_spans(spans)
    addr_fields = [f for f in res.fields if f.field_type == DeclarationField.NAME_AND_ADDRESS]
    assert len(addr_fields) == 0


def test_phone_number_10_digit_mobile_with_plus91_not_treated_as_pincode():
    """A 10-digit mobile number (+91 9811000123) is NOT a PIN code."""
    pins = extract_valid_pincodes("Contact us at +91 9811000123")
    assert pins == []

    spans = [
        _make_span("a1", "Manufactured by:", y_min=100, y_max=120),
        _make_span("a2", "Phone: +91 9811000123", y_min=130, y_max=150),
    ]
    res = bind_spans(spans)
    addr_fields = [f for f in res.fields if f.field_type == DeclarationField.NAME_AND_ADDRESS]
    assert len(addr_fields) == 0


# -----------------------------------------------------------------------------
# 6. Unclassifiable Spans Retained in unclassified_spans
# -----------------------------------------------------------------------------


def test_unclassifiable_span_retained_in_unclassified():
    """A span the parsers cannot classify must be retained in unclassified_spans."""
    span = _make_span("batch_span", "Batch No: B-88129", y_min=50, y_max=70)
    res = bind_spans([span])
    assert len(res.fields) == 0
    assert len(res.unclassified_spans) == 1
    assert res.unclassified_spans[0].span_id == "batch_span"


# -----------------------------------------------------------------------------
# 7. Two "Marketed by" Blocks Both Returned as Separate Fields
# -----------------------------------------------------------------------------


def test_two_marketed_by_blocks_both_returned_as_separate_fields():
    """Two 'Marketed by' blocks are both returned as separate NormalisedField entries."""
    spans = [
        # Block 1 (North Marketer)
        _make_span("mkt1_anchor", "Marketed by:", y_min=100, y_max=120),
        _make_span("mkt1_body", "North Distribution Ltd, Delhi - 110020", y_min=125, y_max=145),
        # Block 2 (South Marketer)
        _make_span("mkt2_anchor", "Marketed by:", y_min=200, y_max=220),
        _make_span("mkt2_body", "South Retail Pvt Ltd, Chennai - 600001", y_min=225, y_max=245),
    ]
    res = bind_spans(spans)
    mkt_fields = [f for f in res.fields if f.field_type == DeclarationField.NAME_AND_ADDRESS]

    assert len(mkt_fields) == 2
    assert mkt_fields[0].span_refs == ("mkt1_anchor", "mkt1_body")
    assert "110020" in mkt_fields[0].normalised_value
    assert mkt_fields[1].span_refs == ("mkt2_anchor", "mkt2_body")
    assert "600001" in mkt_fields[1].normalised_value
    assert len(res.unclassified_spans) == 0


# -----------------------------------------------------------------------------
# 8. Downward Binding With Polygon Vertices (y Increases Downwards)
# -----------------------------------------------------------------------------


def test_downward_binding_polygon_vertices_y_increases_downward():
    """Verify polygon coordinates where y increases downwards bind correctly."""
    anchor_polygon = ((10.0, 100.0), (150.0, 100.0), (150.0, 120.0), (10.0, 120.0))
    addr_polygon = ((10.0, 130.0), (200.0, 130.0), (200.0, 160.0), (10.0, 160.0))

    anchor = ExtractedSpan(
        span_id="a1",
        text="Manufactured by:",
        polygon=anchor_polygon,
        confidence=0.98,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="pdp",
    )
    address = ExtractedSpan(
        span_id="a2",
        text="ABC Foods, Mumbai 400001",
        polygon=addr_polygon,
        confidence=0.92,
        source_provider=EvidenceProvider.PADDLEOCR,
        region_id="pdp",
    )

    res = bind_spans([anchor, address])
    assert len(res.fields) == 1
    assert res.fields[0].field_type == DeclarationField.NAME_AND_ADDRESS
    assert res.fields[0].span_refs == ("a1", "a2")
    assert len(res.unclassified_spans) == 0


# -----------------------------------------------------------------------------
# 9. Edge Cases: Empty Spans, Zero Confidence, Multiple Fields
# -----------------------------------------------------------------------------


def test_edge_case_zero_confidence_spans():
    """Zero confidence spans are not parsed into fields and conserved in unclassified."""
    spans = [
        _make_span("z1", "MRP Rs 100", y_min=10, y_max=30, confidence=0.0),
        _make_span("z2", "Net Qty 1 kg", y_min=40, y_max=60, confidence=0.0),
    ]
    res = bind_spans(spans)
    assert len(res.fields) == 0
    assert len(res.unclassified_spans) == 2
    assert {s.span_id for s in res.unclassified_spans} == {"z1", "z2"}


def test_multiple_declaration_fields_on_same_label():
    """Multiple declaration fields on same label are resolved and conserved."""
    spans = [
        _make_span("s_name", "Generic Name: Peanut Butter", y_min=10, y_max=30),
        _make_span("s_mrp", "MRP Rs 299.00 incl. of all taxes", y_min=40, y_max=60),
        _make_span("s_qty", "Net Qty: 400 g", y_min=70, y_max=90),
        _make_span("s_mfg", "MFG 04/2026", y_min=100, y_max=120),
        _make_span("s_exp", "BEST BEFORE 10/2026", y_min=130, y_max=150),
        _make_span("s_origin", "Country of Origin: India", y_min=160, y_max=180),
        _make_span("s_dim", "Dimensions: 10 cm x 15 cm", y_min=190, y_max=210),
        _make_span("s_usp", "USP: Rs 0.75 / g", y_min=220, y_max=240),
        _make_span("s_care", "Customer Care: 18001234567, care@example.com", y_min=250, y_max=270),
        _make_span("s_addr_anc", "Manufactured by:", y_min=280, y_max=300),
        _make_span("s_addr_val", "Organic Mills Ltd, Jaipur - 302001", y_min=305, y_max=325),
        _make_span("s_batch", "Batch No: 99120", y_min=330, y_max=350),
    ]
    res = bind_spans(spans)

    # Check field types created
    field_types = {f.field_type for f in res.fields}
    assert DeclarationField.COMMON_OR_GENERIC_NAME in field_types
    assert DeclarationField.RETAIL_SALE_PRICE in field_types
    assert DeclarationField.NET_QUANTITY in field_types
    assert DeclarationField.MANUFACTURE_DATE in field_types
    assert DeclarationField.BEST_BEFORE_DATE in field_types
    assert DeclarationField.COUNTRY_OF_ORIGIN in field_types
    assert DeclarationField.DIMENSIONS in field_types
    assert DeclarationField.UNIT_SALE_PRICE in field_types
    assert DeclarationField.CONSUMER_CARE in field_types
    assert DeclarationField.NAME_AND_ADDRESS in field_types

    # Batch number unclassified
    assert len(res.unclassified_spans) == 1
    assert res.unclassified_spans[0].span_id == "s_batch"

    # Strict span conservation
    bound_refs = set(ref for f in res.fields for ref in f.span_refs)
    assert bound_refs.isdisjoint({"s_batch"})
    assert len(bound_refs) + len(res.unclassified_spans) == len(spans)


# -----------------------------------------------------------------------------
# 10. Additional Test Cases: Abbreviated Anchors & Role Variations
# -----------------------------------------------------------------------------


def test_abbreviated_mfg_pkd_mkt_imp_anchors():
    """Abbreviations 'Mfg by', 'Pkd by', 'Mkt by', 'Imp by' are recognized as anchors."""
    for prefix, pin in [
        ("Mfg by", "110001"),
        ("Pkd by", "400001"),
        ("Mkt by", "560001"),
        ("Imp by", "600001"),
    ]:
        spans = [
            _make_span("anc", f"{prefix}:", y_min=50, y_max=70),
            _make_span("body", f"Traders Ltd, City {pin}", y_min=75, y_max=95),
        ]
        res = bind_spans(spans)
        assert len(res.fields) == 1
        assert res.fields[0].field_type == DeclarationField.NAME_AND_ADDRESS
        assert pin in res.fields[0].normalised_value


def test_brand_owner_keyword_anchor():
    """'Brand Owner' and 'Owned by' anchors are recognized and bound."""
    spans = [
        _make_span("bo_anc", "Brand Owner:", y_min=100, y_max=120),
        _make_span("bo_body", "Prime Goods Inc, Mumbai - 400001", y_min=125, y_max=145),
    ]
    res = bind_spans(spans)
    assert len(res.fields) == 1
    assert res.fields[0].field_type == DeclarationField.NAME_AND_ADDRESS
    assert "400001" in res.fields[0].normalised_value


def test_anchor_itself_containing_address_and_pincode():
    """Anchor span containing address and PIN code in a single line binds cleanly."""
    span = _make_span(
        "single_span",
        "Manufactured by: Tasty Foods Pvt Ltd, Delhi 110020",
        y_min=100,
        y_max=120,
    )
    res = bind_spans([span])
    assert len(res.fields) == 1
    assert res.fields[0].field_type == DeclarationField.NAME_AND_ADDRESS
    assert res.fields[0].span_refs == ("single_span",)
    assert len(res.unclassified_spans) == 0


def test_anchor_without_pincode_fails_to_bind():
    """Anchor with candidate spans that lack any valid PIN code does NOT bind."""
    spans = [
        _make_span("anc", "Manufactured by:", y_min=100, y_max=120),
        _make_span("body", "ABC Foods, Industrial Area, Phase 2", y_min=125, y_max=145),
    ]
    res = bind_spans(spans)
    addr_fields = [f for f in res.fields if f.field_type == DeclarationField.NAME_AND_ADDRESS]
    assert len(addr_fields) == 0
    assert len(res.unclassified_spans) == 2


def test_date_dispatch_manufacture_vs_best_before():
    """PKD/MFG dates route to MANUFACTURE_DATE while EXP/Best Before route to BEST_BEFORE_DATE."""
    spans = [
        _make_span("mfg", "PKD 03/2026", y_min=10, y_max=30),
        _make_span("bb", "BEST BEFORE 12/2026", y_min=40, y_max=60),
    ]
    res = bind_spans(spans)
    f_map = {f.field_type: f for f in res.fields}
    assert DeclarationField.MANUFACTURE_DATE in f_map
    assert DeclarationField.BEST_BEFORE_DATE in f_map
    assert f_map[DeclarationField.MANUFACTURE_DATE].span_refs == ("mfg",)
    assert f_map[DeclarationField.BEST_BEFORE_DATE].span_refs == ("bb",)


def test_unit_sale_price_dispatch():
    """Unit sale price text is parsed and mapped to UNIT_SALE_PRICE."""
    span = _make_span("usp", "Unit Sale Price: ₹ 15.00 / 100g", y_min=10, y_max=30)
    res = bind_spans([span])
    assert len(res.fields) == 1
    assert res.fields[0].field_type == DeclarationField.UNIT_SALE_PRICE
    assert res.fields[0].numeric_value == Decimal("15.00")
    assert res.fields[0].unit == "INR"


def test_country_of_origin_dispatch():
    """Country of origin is parsed and mapped to COUNTRY_OF_ORIGIN."""
    span = _make_span("origin", "Made in India", y_min=10, y_max=30)
    res = bind_spans([span])
    assert len(res.fields) == 1
    assert res.fields[0].field_type == DeclarationField.COUNTRY_OF_ORIGIN
    assert res.fields[0].normalised_value == "India"


def test_dimensions_dispatch():
    """Dimensions declaration is parsed and mapped to DIMENSIONS."""
    span = _make_span("dim", "Dimensions: 20 cm x 10 cm x 5 cm", y_min=10, y_max=30)
    res = bind_spans([span])
    assert len(res.fields) == 1
    assert res.fields[0].field_type == DeclarationField.DIMENSIONS
    assert res.fields[0].unit == "cm"


def test_extract_valid_pincodes_unit():
    """Direct verification of extract_valid_pincodes against varied inputs."""
    # Valid PIN codes
    assert extract_valid_pincodes("Delhi 110001") == ["110001"]
    assert extract_valid_pincodes("Pin Code: 400001.") == ["400001"]
    assert extract_valid_pincodes("Kolkata - 700001") == ["700001"]
    # Phone numbers / toll-free numbers / attached digits rejected
    assert extract_valid_pincodes("Call 1800-110001") == []
    assert extract_valid_pincodes("+91 9811000123") == []
    assert extract_valid_pincodes("Ph: 110001") == []
    assert extract_valid_pincodes("Tel: 110001") == []
    assert extract_valid_pincodes("1234567") == []
    assert extract_valid_pincodes("011-234567") == []


def test_side_by_side_column_anchors():
    """Anchors in side-by-side columns at same y coordinate bind to their own columns."""
    spans = [
        # Left column (x: 10..150)
        _make_span(
            "anc_left",
            "Manufactured by:",
            y_min=100,
            y_max=120,
            x_min=10,
            x_max=150,
        ),
        _make_span(
            "body_left",
            "West Foods, Pune 411001",
            y_min=125,
            y_max=145,
            x_min=10,
            x_max=150,
        ),
        # Right column (x: 300..450)
        _make_span(
            "anc_right",
            "Marketed by:",
            y_min=100,
            y_max=120,
            x_min=300,
            x_max=450,
        ),
        _make_span(
            "body_right",
            "East Retail, Kolkata 700001",
            y_min=125,
            y_max=145,
            x_min=300,
            x_max=450,
        ),
    ]
    res = bind_spans(spans)
    addr_fields = [f for f in res.fields if f.field_type == DeclarationField.NAME_AND_ADDRESS]
    assert len(addr_fields) == 2
    f_left = [f for f in addr_fields if "411001" in f.normalised_value][0]
    f_right = [f for f in addr_fields if "700001" in f.normalised_value][0]
    assert f_left.span_refs == ("anc_left", "body_left")
    assert f_right.span_refs == ("anc_right", "body_right")
    assert len(res.unclassified_spans) == 0


# -----------------------------------------------------------------------------
# 11. Additional Guard Tests: Dispatch Priority & Non-Commodity Filtering
# -----------------------------------------------------------------------------


def test_usp_evaluated_before_commodity_name():
    """USP text with units like / 100g must map to UNIT_SALE_PRICE, not COMMODITY_NAME."""
    spans = [
        _make_span("s_usp1", "₹ 15.00 / 100g", y_min=10, y_max=30),
        _make_span("s_usp2", "Rs 50.00 / kg", y_min=40, y_max=60),
        _make_span("s_usp3", "Unit Sale Price: ₹ 2.50 / piece", y_min=70, y_max=90),
    ]
    res = bind_spans(spans)
    assert len(res.fields) == 3
    for f in res.fields:
        assert f.field_type == DeclarationField.UNIT_SALE_PRICE


def test_non_commodity_phrasing_rejected():
    """Advisory text, storage instructions, ingredients, and company names remain unclassified."""
    spans = [
        _make_span("u1", "Store in a cool, dry place away from sunlight", y_min=10, y_max=30),
        _make_span("u2", "Directions for use: apply evenly on skin", y_min=40, y_max=60),
        _make_span("u3", "Ingredients: Water, Sugar, Citric Acid", y_min=70, y_max=90),
        _make_span("u4", "Apex Foods Private Limited", y_min=100, y_max=120),
        _make_span("u5", "Industrial Area, Phase 1", y_min=130, y_max=150),
        _make_span("u6", "Caution: Keep out of reach of children", y_min=160, y_max=180),
    ]
    res = bind_spans(spans)
    assert len(res.fields) == 0
    assert len(res.unclassified_spans) == 6


def test_explicit_commodity_keywords_bound():
    """Explicit commodity keywords bind directly to COMMON_OR_GENERIC_NAME."""
    spans = [
        _make_span("c1", "Commodity: Bath Soap", y_min=10, y_max=30),
        _make_span("c2", "Generic Name: Wheat Flour", y_min=40, y_max=60),
        _make_span("c3", "Product: Chocolate Cookies", y_min=70, y_max=90),
        _make_span("c4", "Common Name: Basmati Rice", y_min=100, y_max=120),
    ]
    res = bind_spans(spans)
    assert len(res.fields) == 4
    for f in res.fields:
        assert f.field_type == DeclarationField.COMMON_OR_GENERIC_NAME


def test_anchor_span_never_added_to_other_anchor_cluster():
    """An anchor span is strictly excluded from becoming part of another anchor's address."""
    spans = [
        _make_span("mfg_anc", "Manufactured by:", y_min=100, y_max=120, x_min=10, x_max=150),
        _make_span(
            "mfg_body",
            "Factory One, Industrial Hub 560001",
            y_min=125,
            y_max=145,
            x_min=10,
            x_max=150,
        ),
        # A second anchor slightly lower in the same horizontal column
        _make_span("mkt_anc", "Marketed by:", y_min=150, y_max=170, x_min=10, x_max=150),
        _make_span(
            "mkt_body",
            "Retail Head Office, City 110001",
            y_min=175,
            y_max=195,
            x_min=10,
            x_max=150,
        ),
    ]
    res = bind_spans(spans)
    addr_fields = [f for f in res.fields if f.field_type == DeclarationField.NAME_AND_ADDRESS]
    assert len(addr_fields) == 2
    f_mfg = [f for f in addr_fields if "560001" in f.normalised_value][0]
    f_mkt = [f for f in addr_fields if "110001" in f.normalised_value][0]
    assert "mkt_anc" not in f_mfg.span_refs
    assert "mfg_anc" not in f_mkt.span_refs
    assert f_mfg.span_refs == ("mfg_anc", "mfg_body")
    assert f_mkt.span_refs == ("mkt_anc", "mkt_body")
