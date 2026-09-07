"""Service-level validation for review product identifiers."""

import pytest

from app.modules.reviews.service import PRODUCT_IDENTIFIER_MAX_LENGTH, normalize_product_identifier


def test_product_identifier_trims_outer_whitespace_and_preserves_leading_zeroes() -> None:
    """Normalize only surrounding whitespace while retaining barcode digits exactly."""
    assert normalize_product_identifier("  0012345678905  ") == "0012345678905"


def test_product_identifier_rejects_empty_after_trimming() -> None:
    """Reject an identifier that contains no usable product value."""
    with pytest.raises(ValueError, match="must not be empty"):
        normalize_product_identifier("   ")


def test_product_identifier_rejects_values_over_the_existing_storage_limit() -> None:
    """Reject values longer than the CORE-004 column can store."""
    with pytest.raises(ValueError, match="at most"):
        normalize_product_identifier("x" * (PRODUCT_IDENTIFIER_MAX_LENGTH + 1))


def test_product_identifier_accepts_the_existing_storage_limit() -> None:
    """Accept exactly the length supported by the CORE-004 storage column."""
    identifier = "x" * PRODUCT_IDENTIFIER_MAX_LENGTH

    assert normalize_product_identifier(identifier) == identifier


def test_product_identifier_does_not_require_ean13_length_or_checksum() -> None:
    """Accept a valid non-EAN-13 identifier because CORE-004 stores generic strings."""
    identifier = "vendor-code-7"

    assert normalize_product_identifier(identifier) == identifier
