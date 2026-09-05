"""Table-driven test suite for extraction normalisation module (EXT-001)."""

from decimal import Decimal

import pytest

from app.modules.extraction.address import normalise_address
from app.modules.extraction.consumer_care import normalise_consumer_care
from app.modules.extraction.country_of_origin import (
    CONFIDENCE_EXPLICIT_CANONICAL_DECLARATION,
    CONFIDENCE_EXPLICIT_ISO_VARIANT,
    normalise_country_of_origin,
)
from app.modules.extraction.date import normalise_date
from app.modules.extraction.iso3166_data import ISO_3166_1_RECORDS
from app.modules.extraction.mrp import normalise_mrp
from app.modules.extraction.net_quantity import normalise_net_quantity
from app.modules.extraction.types import (
    AddressRole,
    CountryOfOriginValue,
    CountryOriginMode,
    DateType,
    ReasonCode,
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
    ("45 Rupees Only", Decimal("45"), "INR", False, True, None),
    ("45 rupees only", Decimal("45"), "INR", False, True, None),
    ("45 Rupees", Decimal("45"), "INR", False, True, None),
    ("Net quantity 500 g MRP Rs 100", Decimal("100"), "INR", False, True, None),
    ("Phone 9876543210 MRP Rs 100", Decimal("100"), "INR", False, True, None),
    ("Manufactured in 2026 MRP Rs 100", Decimal("100"), "INR", False, True, None),
    # Standalone numbers without currency/MRP evidence -> Rejection
    ("Call us at 45", None, "INR", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    ("500 grams", None, "INR", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    ("Product code 123", None, "INR", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    # Adversarial / Malformed / Failure inputs
    ("", None, "INR", False, False, ReasonCode.EMPTY_INPUT),
    ("   ", None, "INR", False, False, ReasonCode.EMPTY_INPUT),
    ("Rs. -10.00", None, "INR", False, False, ReasonCode.INVALID_VALUE),
    ("MRP Rs 100 or Rs 200", None, "INR", False, False, ReasonCode.AMBIGUOUS_VALUE),
    ("MRP 100 and MRP 120", None, "INR", False, False, ReasonCode.AMBIGUOUS_VALUE),
    ("MRP 50O", None, "INR", False, False, ReasonCode.UNPARSEABLE_FORMAT),
    ("MRP 100 garbage", None, "INR", False, False, ReasonCode.UNPARSEABLE_FORMAT),
]


@pytest.mark.parametrize(
    ("input_text", "exp_amount", "exp_curr", "exp_tax", "exp_success", "exp_reason"),
    MRP_TEST_CASES,
)
def test_normalise_mrp(input_text, exp_amount, exp_curr, exp_tax, exp_success, exp_reason):
    res = normalise_mrp(input_text)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    assert res.reason_code is None or isinstance(res.reason_code, ReasonCode)
    if exp_success:
        assert 0.0 < res.confidence <= 1.0
        assert res.value is not None
        assert res.value.amount == exp_amount
        assert isinstance(res.value.amount, Decimal)
        assert res.value.currency == exp_curr
        assert res.value.inclusive_of_taxes is exp_tax
    else:
        assert res.confidence == 0.0
        assert res.value is None


NET_QTY_TEST_CASES = [
    ("500 g", Decimal("500"), "g", False, True, None),
    ("1.5 kg", Decimal("1.5"), "kg", False, True, None),
    ("750 ml", Decimal("750"), "ml", False, True, None),
    ("2 l", Decimal("2"), "l", False, True, None),
    ("2 N", Decimal("2"), "N", False, True, None),
    ("10 pieces", Decimal("10"), "pcs", False, True, None),
    ("Net Qty: kg 1.5", Decimal("1.5"), "kg", False, True, None),
    ("Net Quantity: ml 500", Decimal("500"), "ml", False, True, None),
    ("Qty: N 10", Decimal("10"), "N", False, True, None),
    ("500g ℮", Decimal("500"), "g", True, True, None),
    ("e 500 g", Decimal("500"), "g", True, True, None),
    ("1.5kg", Decimal("1.5"), "kg", False, True, None),
    ("2.5 Litres", Decimal("2.5"), "l", False, True, None),
    ("10 units", Decimal("10"), "pcs", False, True, None),
    ("100 grams", Decimal("100"), "g", False, True, None),
    # Adversarial / Malformed / Failure inputs
    ("", None, "", False, False, ReasonCode.EMPTY_INPUT),
    ("Net Qty: 500 cubits", None, "", False, False, ReasonCode.UNRECOGNIZED_UNIT),
    ("Net Qty: -5 kg", None, "", False, False, ReasonCode.INVALID_VALUE),
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
    assert res.reason_code is None or isinstance(res.reason_code, ReasonCode)
    if exp_success:
        assert 0.0 < res.confidence <= 1.0
        assert res.value is not None
        assert res.value.value == exp_val
        assert isinstance(res.value.value, Decimal)
        assert res.value.unit == exp_unit
        assert res.value.has_emark is exp_emark
    else:
        assert res.confidence == 0.0
        assert res.value is None


def test_normalise_net_quantity_emark_scoping():
    """Verify that e in normal English words does not trigger has_emark."""
    res_valid = normalise_net_quantity("500 g")
    assert res_valid.success is True
    assert res_valid.value is not None
    assert res_valid.value.has_emark is False
    assert isinstance(res_valid.value.value, Decimal)


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
    # Relative date without packing date -> MISSING_PACKING_DATE
    (
        "Best before 6 months from packing",
        DateType.BEST_BEFORE,
        None,
        True,
        6,
        False,
        ReasonCode.MISSING_PACKING_DATE,
    ),
    # Calendar Invalid dates
    ("31.02.2026", None, None, False, None, False, ReasonCode.INVALID_VALUE),
    ("29.02.2025", None, None, False, None, False, ReasonCode.INVALID_VALUE),
    ("32.01.2026", None, None, False, None, False, ReasonCode.INVALID_VALUE),
    # Ambiguous / Adversarial / Failure inputs
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
]


@pytest.mark.parametrize(
    (
        "input_text",
        "exp_type",
        "exp_iso",
        "exp_relative",
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
    exp_relative,
    exp_rel_months,
    exp_success,
    exp_reason,
):
    res = normalise_date(input_text)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    assert res.reason_code is None or isinstance(res.reason_code, ReasonCode)
    if exp_success:
        assert 0.0 < res.confidence <= 1.0
        assert res.value is not None
        assert res.value.date_type == exp_type
        assert res.value.iso_date == exp_iso
        assert res.value.is_relative is exp_relative
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
    (
        "Contact the manufacturer for details.",
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
    assert res.reason_code is None or isinstance(res.reason_code, ReasonCode)
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
    assert res.reason_code is None or isinstance(res.reason_code, ReasonCode)
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


COUNTRY_OF_ORIGIN_TEST_CASES = [
    # --- Valid India Mode Declarations ---
    ("Made in India", CountryOriginMode.INDIA, "India", "IN", "IND", True, None),
    ("Country of Origin: India", CountryOriginMode.INDIA, "India", "IN", "IND", True, None),
    ("Country of Origin - India", CountryOriginMode.INDIA, "India", "IN", "IND", True, None),
    ("Made in IN", CountryOriginMode.INDIA, "India", "IN", "IND", True, None),
    ("Made in IND", CountryOriginMode.INDIA, "India", "IN", "IND", True, None),
    ("Made in Inda", CountryOriginMode.INDIA, "India", "IN", "IND", True, None),
    ("Country of Origm: India", CountryOriginMode.INDIA, "India", "IN", "IND", True, None),
    # --- India Mode Rejection of non-India countries ---
    (
        "Made in Germany",
        CountryOriginMode.INDIA,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    ("Made in DE", CountryOriginMode.INDIA, None, None, None, False, ReasonCode.UNPARSEABLE_FORMAT),
    (
        "Made in DEU",
        CountryOriginMode.INDIA,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Country of Origin: Japan",
        CountryOriginMode.INDIA,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    # --- Valid Worldwide Mode Declarations ---
    ("Made in India", CountryOriginMode.WORLDWIDE, "India", "IN", "IND", True, None),
    ("Made in Germany", CountryOriginMode.WORLDWIDE, "Germany", "DE", "DEU", True, None),
    ("Country of Origin: Japan", CountryOriginMode.WORLDWIDE, "Japan", "JP", "JPN", True, None),
    ("Made in France", CountryOriginMode.WORLDWIDE, "France", "FR", "FRA", True, None),
    ("Made in Brazil", CountryOriginMode.WORLDWIDE, "Brazil", "BR", "BRA", True, None),
    (
        "Country of Origin: Australia",
        CountryOriginMode.WORLDWIDE,
        "Australia",
        "AU",
        "AUS",
        True,
        None,
    ),
    # --- Alpha-2 / Alpha-3 / Common Variants in Worldwide Mode ---
    ("Made in DE", CountryOriginMode.WORLDWIDE, "Germany", "DE", "DEU", True, None),
    ("Country of Origin: JP", CountryOriginMode.WORLDWIDE, "Japan", "JP", "JPN", True, None),
    ("Country of Origin: IND", CountryOriginMode.WORLDWIDE, "India", "IN", "IND", True, None),
    ("Made in DEU", CountryOriginMode.WORLDWIDE, "Germany", "DE", "DEU", True, None),
    ("Made in USA", CountryOriginMode.WORLDWIDE, "United States", "US", "USA", True, None),
    (
        "Country of Origin: UK",
        CountryOriginMode.WORLDWIDE,
        "United Kingdom",
        "GB",
        "GBR",
        True,
        None,
    ),
    ("Made in UAE", CountryOriginMode.WORLDWIDE, "United Arab Emirates", "AE", "ARE", True, None),
    # --- Failure: Standalone / Missing Prefix / Missing Country Token ---
    ("India", CountryOriginMode.WORLDWIDE, None, None, None, False, ReasonCode.UNPARSEABLE_FORMAT),
    (
        "Germany",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Made in",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Country of Origin:",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Made in Unknownland",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    # --- Failure: Role Prefixes & Non-Standard Phrasing ---
    (
        "Made by India",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Manufactured by ABC, India",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Imported by ABC, India",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Made inside India",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    # --- Failure: Address Contamination, Marketing Prose, URLs ---
    (
        "Manufacturer: ABC Pvt Ltd, India",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Available in India",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "Visit India",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "India is a leading producer",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    (
        "www.madeinindia.com",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.UNPARSEABLE_FORMAT,
    ),
    # --- Canonical ISO Country Names with 'and' ---
    (
        "Made in Antigua and Barbuda",
        CountryOriginMode.WORLDWIDE,
        "Antigua and Barbuda",
        "AG",
        "ATG",
        True,
        None,
    ),
    (
        "Made in Bonaire, Sint Eustatius and Saba",
        CountryOriginMode.WORLDWIDE,
        "Bonaire, Sint Eustatius and Saba",
        "BQ",
        "BES",
        True,
        None,
    ),
    (
        "Made in Bosnia and Herzegovina",
        CountryOriginMode.WORLDWIDE,
        "Bosnia and Herzegovina",
        "BA",
        "BIH",
        True,
        None,
    ),
    (
        "Made in Heard Island and McDonald Islands",
        CountryOriginMode.WORLDWIDE,
        "Heard Island and McDonald Islands",
        "HM",
        "HMD",
        True,
        None,
    ),
    (
        "Made in Saint Helena, Ascension and Tristan da Cunha",
        CountryOriginMode.WORLDWIDE,
        "Saint Helena, Ascension and Tristan da Cunha",
        "SH",
        "SHN",
        True,
        None,
    ),
    (
        "Made in Saint Kitts and Nevis",
        CountryOriginMode.WORLDWIDE,
        "Saint Kitts and Nevis",
        "KN",
        "KNA",
        True,
        None,
    ),
    (
        "Made in Saint Pierre and Miquelon",
        CountryOriginMode.WORLDWIDE,
        "Saint Pierre and Miquelon",
        "PM",
        "SPM",
        True,
        None,
    ),
    (
        "Made in Saint Vincent and the Grenadines",
        CountryOriginMode.WORLDWIDE,
        "Saint Vincent and the Grenadines",
        "VC",
        "VCT",
        True,
        None,
    ),
    (
        "Made in Sao Tome and Principe",
        CountryOriginMode.WORLDWIDE,
        "Sao Tome and Principe",
        "ST",
        "STP",
        True,
        None,
    ),
    (
        "Made in South Georgia and the South Sandwich Islands",
        CountryOriginMode.WORLDWIDE,
        "South Georgia and the South Sandwich Islands",
        "GS",
        "SGS",
        True,
        None,
    ),
    (
        "Made in Svalbard and Jan Mayen",
        CountryOriginMode.WORLDWIDE,
        "Svalbard and Jan Mayen",
        "SJ",
        "SJM",
        True,
        None,
    ),
    (
        "Made in Trinidad and Tobago",
        CountryOriginMode.WORLDWIDE,
        "Trinidad and Tobago",
        "TT",
        "TTO",
        True,
        None,
    ),
    (
        "Made in Turks and Caicos Islands",
        CountryOriginMode.WORLDWIDE,
        "Turks and Caicos Islands",
        "TC",
        "TCA",
        True,
        None,
    ),
    (
        "Made in Wallis and Futuna",
        CountryOriginMode.WORLDWIDE,
        "Wallis and Futuna",
        "WF",
        "WLF",
        True,
        None,
    ),
    # --- Special ISO Codes & Punctuation Names ---
    ("Made in AND", CountryOriginMode.WORLDWIDE, "Andorra", "AD", "AND", True, None),
    (
        "Made in Virgin Islands, U.S.",
        CountryOriginMode.WORLDWIDE,
        "Virgin Islands, U.S.",
        "VI",
        "VIR",
        True,
        None,
    ),
    # --- Failure: Empty / Whitespace Input ---
    ("", CountryOriginMode.WORLDWIDE, None, None, None, False, ReasonCode.EMPTY_INPUT),
    ("   ", CountryOriginMode.WORLDWIDE, None, None, None, False, ReasonCode.EMPTY_INPUT),
    # --- Ambiguity: Multiple Conflicting Declarations ---
    (
        "Made in India / Made in Germany",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.AMBIGUOUS_VALUE,
    ),
    (
        "Made in India and Germany",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.AMBIGUOUS_VALUE,
    ),
    (
        "Made in India or Germany",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.AMBIGUOUS_VALUE,
    ),
    (
        "Country of Origin: India Country of Origin: China",
        CountryOriginMode.WORLDWIDE,
        None,
        None,
        None,
        False,
        ReasonCode.AMBIGUOUS_VALUE,
    ),
]


@pytest.mark.parametrize(
    (
        "input_text",
        "mode",
        "exp_country",
        "exp_a2",
        "exp_a3",
        "exp_success",
        "exp_reason",
    ),
    COUNTRY_OF_ORIGIN_TEST_CASES,
)
def test_normalise_country_of_origin(
    input_text, mode, exp_country, exp_a2, exp_a3, exp_success, exp_reason
):
    res = normalise_country_of_origin(input_text, mode=mode)
    assert res.success is exp_success
    assert res.reason_code == exp_reason
    assert res.reason_code is None or isinstance(res.reason_code, ReasonCode)
    if exp_success:
        assert 0.0 < res.confidence <= 1.0
        assert res.value is not None
        assert isinstance(res.value, CountryOfOriginValue)
        assert res.value.country_name == exp_country
        assert res.value.iso_alpha2 == exp_a2
        assert res.value.iso_alpha3 == exp_a3
        assert isinstance(res.value.raw_declaration, str)
        assert len(res.value.raw_declaration) > 0
    else:
        assert res.confidence == 0.0
        assert res.value is None


def test_iso_3166_dataset_integrity():
    """Verify vendored ISO 3166-1 dataset integrity: 249 unique records with non-empty fields."""
    assert len(ISO_3166_1_RECORDS) == 249, f"Expected 249 records, got {len(ISO_3166_1_RECORDS)}"

    names = set()
    alpha2_codes = set()
    alpha3_codes = set()

    for rec in ISO_3166_1_RECORDS:
        assert "name" in rec and rec["name"]
        assert "alpha_2" in rec and len(rec["alpha_2"]) == 2
        assert "alpha_3" in rec and len(rec["alpha_3"]) == 3

        names.add(rec["name"])
        alpha2_codes.add(rec["alpha_2"].upper())
        alpha3_codes.add(rec["alpha_3"].upper())

    assert len(names) == 249, "Duplicate country names found in ISO dataset"
    assert len(alpha2_codes) == 249, "Duplicate Alpha-2 codes found in ISO dataset"
    assert len(alpha3_codes) == 249, "Duplicate Alpha-3 codes found in ISO dataset"


def test_exhaustive_249_canonical_countries():
    """Verify that all 249 ISO canonical country names succeed in WORLDWIDE mode."""
    for record in ISO_3166_1_RECORDS:
        input_text = f"Made in {record['name']}"
        res = normalise_country_of_origin(input_text, mode=CountryOriginMode.WORLDWIDE)
        assert res.success is True, f"Failed for canonical country: {record['name']}"
        assert res.value is not None
        assert res.value.country_name == record["name"]
        assert res.value.iso_alpha2 == record["alpha_2"]
        assert res.value.iso_alpha3 == record["alpha_3"]
        assert res.confidence == CONFIDENCE_EXPLICIT_CANONICAL_DECLARATION
        assert res.reason_code is None


def test_exhaustive_498_iso_codes():
    """Verify that all 498 Alpha-2 and Alpha-3 codes succeed and resolve to their record."""
    for record in ISO_3166_1_RECORDS:
        # Test Alpha-2
        res_a2 = normalise_country_of_origin(
            f"Made in {record['alpha_2']}", mode=CountryOriginMode.WORLDWIDE
        )
        assert res_a2.success is True, f"Failed for Alpha-2 code: {record['alpha_2']}"
        assert res_a2.value is not None
        assert res_a2.value.country_name == record["name"]
        assert res_a2.value.iso_alpha2 == record["alpha_2"]
        assert res_a2.value.iso_alpha3 == record["alpha_3"]
        assert res_a2.confidence == CONFIDENCE_EXPLICIT_ISO_VARIANT

        # Test Alpha-3
        res_a3 = normalise_country_of_origin(
            f"Made in {record['alpha_3']}", mode=CountryOriginMode.WORLDWIDE
        )
        assert res_a3.success is True, f"Failed for Alpha-3 code: {record['alpha_3']}"
        assert res_a3.value is not None
        assert res_a3.value.country_name == record["name"]
        assert res_a3.value.iso_alpha2 == record["alpha_2"]
        assert res_a3.value.iso_alpha3 == record["alpha_3"]
        assert res_a3.confidence == CONFIDENCE_EXPLICIT_ISO_VARIANT
