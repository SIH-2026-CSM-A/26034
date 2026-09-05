"""Table-driven unit tests for OCR-text normalisation layer."""

from decimal import Decimal

import pytest

from app.modules.extraction.normalise import (
    AddressRole,
    DateType,
    ReasonCode,
    normalise_address,
    normalise_consumer_care,
    normalise_date,
    normalise_mrp,
    normalise_net_quantity,
)

# -----------------------------------------------------------------------------
# 1. MRP Normaliser Tests
# -----------------------------------------------------------------------------

MRP_TEST_CASES = [
    ("₹120/-", Decimal("120"), "INR", False, True, None),
    ("Rs. 50.00", Decimal("50.00"), "INR", False, True, None),
    ("Rs 1,250.00 incl. of all taxes", Decimal("1250.00"), "INR", True, True, None),
    ("MRP Rs 99.00 only", Decimal("99.00"), "INR", False, True, None),
    ("M.R.P. : 499.00", Decimal("499.00"), "INR", False, True, None),
    ("INR 250.00", Decimal("250.00"), "INR", False, True, None),
    ("Rs.199/- (Inclusive of all taxes)", Decimal("199"), "INR", True, True, None),
    ("MRP ₹ 1,500.00 ONLY", Decimal("1500.00"), "INR", False, True, None),
    ("Rs 2 500.00", Decimal("2500.00"), "INR", False, True, None),
    ("₹50", Decimal("50"), "INR", False, True, None),
    ("M.R.P. Rs. 75/- incl. taxes", Decimal("75"), "INR", True, True, None),
    ("₹ 3,499.50", Decimal("3499.50"), "INR", False, True, None),
    # Adversarial / Malformed / Failure inputs
    ("", None, "INR", False, False, ReasonCode.EMPTY_INPUT),
    ("   ", None, "INR", False, False, ReasonCode.EMPTY_INPUT),
    ("abc 123 xyz", None, "INR", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    ("MRP", None, "INR", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    ("MRP free", None, "INR", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    ("MRP ₹500 ₹600", None, "INR", False, False, ReasonCode.AMBIGUOUS_VALUE),
    ("MRP 50O", None, "INR", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    ("Rs. -10.00", None, "INR", False, False, ReasonCode.INVALID_VALUE),
    ("₹0.00", None, "INR", False, False, ReasonCode.INVALID_VALUE),
    (
        "MRP Rs 100 extra garbage text",
        None,
        "INR",
        False,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
]


@pytest.mark.parametrize(
    ("input_text", "exp_amount", "exp_curr", "exp_tax", "exp_success", "exp_reason"),
    MRP_TEST_CASES,
)
def test_normalise_mrp(input_text, exp_amount, exp_curr, exp_tax, exp_success, exp_reason):
    res = normalise_mrp(input_text)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    if exp_success:
        assert 0.0 < res.confidence <= 1.0
        assert res.value is not None
        assert res.value.amount == exp_amount
        assert res.value.currency == exp_curr
        assert res.value.inclusive_of_taxes is exp_tax
    else:
        assert res.confidence == 0.0
        assert res.value is None


# -----------------------------------------------------------------------------
# 2. Net Quantity Normaliser Tests
# -----------------------------------------------------------------------------

NET_QTY_TEST_CASES = [
    ("500 g", 500.0, "g", False, True, None),
    ("1.5 kg", 1.5, "kg", False, True, None),
    ("750 ml", 750.0, "ml", False, True, None),
    ("2 l", 2.0, "l", False, True, None),
    ("2 N", 2.0, "N", False, True, None),
    ("10 pieces", 10.0, "pcs", False, True, None),
    ("Net Qty: kg 1.5", 1.5, "kg", False, True, None),
    ("Net Quantity: ml 500", 500.0, "ml", False, True, None),
    ("Qty: N 10", 10.0, "N", False, True, None),
    ("500g ℮", 500.0, "g", True, True, None),
    ("e 500 g", 500.0, "g", True, True, None),
    ("1.5kg", 1.5, "kg", False, True, None),
    ("2.5 Litres", 2.5, "l", False, True, None),
    ("10 units", 10.0, "pcs", False, True, None),
    ("100 grams", 100.0, "g", False, True, None),
    # Adversarial / Malformed / Failure inputs
    ("", None, "", False, False, ReasonCode.EMPTY_INPUT),
    ("Net Qty: 500 cubits", None, "", False, False, ReasonCode.UNRECOGNIZED_UNIT),
    ("500", None, "", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    ("Net Qty: -5 kg", None, "", False, False, ReasonCode.INVALID_VALUE),
    ("abc xyz", None, "", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    (
        "Net Qty: 500 g extra garbage",
        None,
        "",
        False,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    ("Net Qty: 500 g 600 g", None, "", False, False, ReasonCode.AMBIGUOUS_VALUE),
]


@pytest.mark.parametrize(
    ("input_text", "exp_val", "exp_unit", "exp_emark", "exp_success", "exp_reason"),
    NET_QTY_TEST_CASES,
)
def test_normalise_net_quantity(input_text, exp_val, exp_unit, exp_emark, exp_success, exp_reason):
    res = normalise_net_quantity(input_text)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    if exp_success:
        assert 0.0 < res.confidence <= 1.0
        assert res.value is not None
        assert res.value.value == exp_val
        assert res.value.unit == exp_unit
        assert res.value.has_emark is exp_emark
    else:
        assert res.confidence == 0.0
        assert res.value is None


def test_normalise_net_quantity_emark_scoping():
    """Verify arbitrary letter 'e' elsewhere in text does NOT trigger e-mark."""
    res = normalise_net_quantity("Net Qty: 500 g extra")
    # Trailing garbage "extra" causes parse failure
    assert res.success is False
    assert res.confidence == 0.0

    res_valid = normalise_net_quantity("Net Qty: 500 g")
    assert res_valid.success is True
    assert res_valid.value is not None
    assert res_valid.value.has_emark is False


# -----------------------------------------------------------------------------
# 3. Date Normaliser Tests
# -----------------------------------------------------------------------------

DATE_TEST_CASES = [
    ("MFG 03/2026", DateType.MANUFACTURED, "2026-03", False, None, True, None),
    ("PKD 03/26", DateType.PACKED, "2026-03", False, None, True, None),
    ("15.03.2026", None, "2026-03-15", False, None, True, None),
    ("15/03/2026", None, "2026-03-15", False, None, True, None),
    ("15-03-2026", None, "2026-03-15", False, None, True, None),
    ("MAR 2026", None, "2026-03", False, None, True, None),
    ("March 2026", None, "2026-03", False, None, True, None),
    ("15 MAR 2026", None, "2026-03-15", False, None, True, None),
    ("EXP 12/2028", DateType.EXPIRY, "2028-12", False, None, True, None),
    ("MFG 10.11.2025", DateType.MANUFACTURED, "2025-11-10", False, None, True, None),
    ("PKD MAY 2025", DateType.PACKED, "2025-05", False, None, True, None),
    ("BEST BEFORE 06/2027", DateType.BEST_BEFORE, "2027-06", False, None, True, None),
    # Relative expressions without packing date -> MUST BE UNRESOLVED
    (
        "Best before 6 months from packing",
        DateType.BEST_BEFORE,
        None,
        True,
        6,
        False,
        ReasonCode.MISSING_PACKING_DATE,
    ),
    (
        "Use within 12 months from pkd",
        DateType.BEST_BEFORE,
        None,
        True,
        12,
        False,
        ReasonCode.MISSING_PACKING_DATE,
    ),
    # Adversarial / Invalid Calendar dates
    ("31.02.2026", None, None, False, None, False, ReasonCode.INVALID_VALUE),
    ("29.02.2025", None, None, False, None, False, ReasonCode.INVALID_VALUE),
    ("32.01.2026", None, None, False, None, False, ReasonCode.INVALID_VALUE),
    (
        "MFG 03/2026 EXP 04/2027",
        None,
        None,
        False,
        None,
        False,
        ReasonCode.AMBIGUOUS_VALUE,
    ),
    ("", None, None, False, None, False, ReasonCode.EMPTY_INPUT),
    (
        "INVALID DATE TEXT",
        None,
        None,
        False,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
]


@pytest.mark.parametrize(
    (
        "input_text",
        "exp_type",
        "exp_iso",
        "exp_rel",
        "exp_rel_months",
        "exp_success",
        "exp_reason",
    ),
    DATE_TEST_CASES,
)
def test_normalise_date(
    input_text,
    exp_type,
    exp_iso,
    exp_rel,
    exp_rel_months,
    exp_success,
    exp_reason,
):
    res = normalise_date(input_text)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    if exp_success:
        assert 0.0 < res.confidence <= 1.0
        assert res.value is not None
        assert res.value.date_type == exp_type
        assert res.value.iso_date == exp_iso
        assert res.value.is_relative is exp_rel
        assert res.value.relative_months == exp_rel_months
    elif exp_reason == ReasonCode.MISSING_PACKING_DATE:
        assert res.confidence == 0.0
        assert res.value is not None
        assert res.value.is_relative is True
        assert res.value.relative_months == exp_rel_months
    else:
        assert res.confidence == 0.0
        assert res.value is None


def test_normalise_date_relative_with_packing_date():
    """Verify relative date is deterministically resolved when packing date is supplied."""
    res = normalise_date("Best before 6 months from packing", packing_date="2026-03")
    assert res.success is True
    assert 0.0 < res.confidence <= 1.0
    assert res.value is not None
    assert res.value.iso_date == "2026-09"
    assert res.value.is_relative is True
    assert res.value.relative_months == 6


# -----------------------------------------------------------------------------
# 4. Address Normaliser Tests
# -----------------------------------------------------------------------------

ADDRESS_TEST_CASES = [
    (
        "Manufactured by ACME Corp Pvt Ltd, Plot 12, Industrial Area, Mumbai 400001",
        AddressRole.MANUFACTURER,
        "ACME Corp Pvt Ltd",
        "400001",
        True,
        None,
    ),
    (
        "Mfd by: Globex Pvt Ltd, Tech Park, Bengaluru 560001",
        AddressRole.MANUFACTURER,
        "Globex Pvt Ltd",
        "560001",
        True,
        None,
    ),
    (
        "Packed by Apex Logistics, Sector 4, Gurgaon 122001",
        AddressRole.PACKER,
        None,
        "122001",
        True,
        None,
    ),
    (
        "Marketed by Stark Industries Ltd, Tower A, Delhi 110001",
        AddressRole.MARKETER,
        "Stark Industries Ltd",
        "110001",
        True,
        None,
    ),
    (
        "Imported by Wayne Enterprises Inc, Port Road, Chennai 600001",
        AddressRole.IMPORTER,
        "Wayne Enterprises Inc",
        "600001",
        True,
        None,
    ),
    (
        "Brand Owner: Umbrella Corp, Cyber City, Hyderabad 500081",
        AddressRole.BRAND_OWNER,
        "Umbrella Corp",
        "500081",
        True,
        None,
    ),
    (
        "Mfg. by Zenith Pvt. Ltd., Pune 411001",
        AddressRole.MANUFACTURER,
        "Zenith Pvt. Ltd.",
        "411001",
        True,
        None,
    ),
    (
        "Mfd & Packed by Cyberdyne Systems, Plot 45, Noida 201301",
        AddressRole.MANUFACTURER,
        None,
        "201301",
        True,
        None,
    ),
    (
        "Pkd by Omega Foods, MIDC, Nagpur 440001",
        AddressRole.PACKER,
        None,
        "440001",
        True,
        None,
    ),
    (
        "Mkd by: Horizon Marketing Ltd, Salt Lake, Kolkata 700091",
        AddressRole.MARKETER,
        "Horizon Marketing Ltd",
        "700091",
        True,
        None,
    ),
    (
        "Imported by: Alpha Imports, Fort, Mumbai 400023",
        AddressRole.IMPORTER,
        None,
        "400023",
        True,
        None,
    ),
    (
        "Brand Owner: Titan Brands, MG Road, Bengaluru 560025",
        AddressRole.BRAND_OWNER,
        None,
        "560025",
        True,
        None,
    ),
    ("Mfd by Beta Chemicals, Surat", AddressRole.MANUFACTURER, None, None, True, None),
    (
        "Packed by Delta Goods, Jaipur 302001",
        AddressRole.PACKER,
        None,
        "302001",
        True,
        None,
    ),
    (
        "Marketed by Alpha Retailers, Sector 18, Noida 201301",
        AddressRole.MARKETER,
        None,
        "201301",
        True,
        None,
    ),
    # Adversarial / Failure inputs without role declaration evidence
    (
        "Industrial Estate, Ahmedabad 380001",
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    ("", None, None, None, False, ReasonCode.EMPTY_INPUT),
    ("::--,,", None, None, None, False, ReasonCode.UNPARSEABLE_FORMAT),
]


@pytest.mark.parametrize(
    ("input_text", "exp_role", "exp_entity", "exp_pin", "exp_success", "exp_reason"),
    ADDRESS_TEST_CASES,
)
def test_normalise_address(input_text, exp_role, exp_entity, exp_pin, exp_success, exp_reason):
    res = normalise_address(input_text)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    if exp_success:
        assert 0.0 < res.confidence <= 1.0
        assert res.value is not None
        assert res.value.role == exp_role
        if exp_entity:
            assert res.value.entity_name == exp_entity
        assert res.value.pincode == exp_pin
    else:
        assert res.confidence == 0.0
        assert res.value is None


# -----------------------------------------------------------------------------
# 5. Consumer Care Normaliser Tests
# -----------------------------------------------------------------------------

CONSUMER_CARE_TEST_CASES = [
    (
        "For complaints call 1800-123-4567 or email care@example.com",
        "1800-123-4567",
        "care@example.com",
        None,
        True,
        None,
    ),
    ("Customer Care: 18001234567", "18001234567", None, None, True, None),
    (
        "Contact us at +91 9876543210 or care@brand.co.in",
        "+91 9876543210",
        "care@brand.co.in",
        None,
        True,
        None,
    ),
    ("Email: support@company.com", None, "support@company.com", None, True, None),
    ("Call 022-12345678", "022-12345678", None, None, True, None),
    (
        "Customer Care Executive, Write to: Manager, Customer Care at ACME Plaza, Mumbai 400001",
        None,
        None,
        "Manager, Customer Care at ACME Plaza, Mumbai 400001",
        True,
        None,
    ),
    (
        "Helpdesk: 1800-425-0000 / help@domain.org",
        "1800-425-0000",
        "help@domain.org",
        None,
        True,
        None,
    ),
    ("Toll free: 1800 888 9999", "1800 888 9999", None, None, True, None),
    ("Reach us at care@store.in", None, "care@store.in", None, True, None),
    ("Call +91-9123456789", "+91-9123456789", None, None, True, None),
    (
        "Address: Consumer Cell, Building B, Sector 5, Noida 201301",
        None,
        None,
        "Consumer Cell, Building B, Sector 5, Noida 201301",
        True,
        None,
    ),
    ("Customer Care No: 1800-200-3000", "1800-200-3000", None, None, True, None),
    (
        "Email complaints to: customercare@brand.com",
        None,
        "customercare@brand.com",
        None,
        True,
        None,
    ),
    ("Phone: 1800-111-2222", "1800-111-2222", None, None, True, None),
    ("Support email: info@test.com", None, "info@test.com", None, True, None),
    # Adversarial / Failure inputs without consumer care context
    ("", None, None, None, False, ReasonCode.EMPTY_INPUT),
    ("No contact info here", None, None, None, False, ReasonCode.UNPARSEABLE_FORMAT),
    (
        "Random text with number 9876543210 but no care context",
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Random text with email@domain.com but no care context",
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
]


@pytest.mark.parametrize(
    ("input_text", "exp_phone", "exp_email", "exp_addr", "exp_success", "exp_reason"),
    CONSUMER_CARE_TEST_CASES,
)
def test_normalise_consumer_care(
    input_text, exp_phone, exp_email, exp_addr, exp_success, exp_reason
):
    res = normalise_consumer_care(input_text)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    if exp_success:
        assert 0.0 < res.confidence <= 1.0
        assert res.value is not None
        if exp_phone:
            assert res.value.phone == exp_phone
        if exp_email:
            assert res.value.email == exp_email
        if exp_addr:
            assert res.value.address_block == exp_addr
    else:
        assert res.confidence == 0.0
        assert res.value is None
