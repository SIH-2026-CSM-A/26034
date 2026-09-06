import pytest

from app.modules.evidence.report import (
    BSAReport,
    EvidenceAuditTrail,
    FieldDeclaration,
    HumanConfirmation,
    UnconfirmedVerdictExportError,
    generate_bsa_report,
)


def test_confirmation_gate_enforcement():
    """Verify that report generation fails if the verdict is not human-confirmed."""
    # Case 1: is_human_confirmed is False
    with pytest.raises(UnconfirmedVerdictExportError, match="Verdict has not been human-confirmed"):
        generate_bsa_report(
            source_image_hash="hash123",
            rule_set_version="v1.0",
            audit_trail=EvidenceAuditTrail(
                root_entry_hash="root", latest_entry_hash="latest", total_sequence_count=10
            ),
            declarations=[],
            confirmation=HumanConfirmation(
                confirmed_by="OFFICER_001",
                confirmation_timestamp="2026-09-05T10:00:00Z",
                officer_action="CONFIRM",
            ),
            is_human_confirmed=False,
        )

    # Case 2: confirmation details are missing
    with pytest.raises(UnconfirmedVerdictExportError, match="Verdict has not been human-confirmed"):
        generate_bsa_report(
            source_image_hash="hash123",
            rule_set_version="v1.0",
            audit_trail=EvidenceAuditTrail(
                root_entry_hash="root", latest_entry_hash="latest", total_sequence_count=10
            ),
            declarations=[],
            confirmation=None,
            is_human_confirmed=True,
        )


def test_valid_report_generation():
    """Verify that a confirmed verdict produces a complete BSA §63(4) report."""
    source_hash = "img_sha256_abc"
    rules_ver = "v2026.1"

    audit = EvidenceAuditTrail(
        root_entry_hash="root_hash", latest_entry_hash="latest_hash", total_sequence_count=5
    )

    decls = [
        FieldDeclaration(
            field_name="Net Quantity",
            declared_value="500g",
            measured_value="502g",
            required_value="500g",
            ocr_provider="PaddleOCR",
            confidence=0.98,
        ),
        FieldDeclaration(
            field_name="MRP",
            declared_value="100 INR",
            measured_value="100 INR",
            required_value="100 INR",
            ocr_provider="Tesseract",
            confidence=0.95,
        ),
    ]

    conf = HumanConfirmation(
        confirmed_by="Officer Shiva",
        confirmation_timestamp="2026-09-05T12:00:00Z",
        officer_action="CONFIRM",
    )

    # Test with explicit model versions
    model_vers = {"ocr": "Paddle-v4", "pdp": "YOLO-v8"}
    report = generate_bsa_report(
        source_image_hash=source_hash,
        rule_set_version=rules_ver,
        audit_trail=audit,
        declarations=decls,
        confirmation=conf,
        is_human_confirmed=True,
        model_versions=model_vers,
    )

    assert isinstance(report, BSAReport)
    assert report.source_image_hash == source_hash
    assert report.rule_set_version == rules_ver
    assert report.statute_citation == "BSA §63(4) Part A"
    assert report.model_versions == model_vers
    assert isinstance(report.model_versions, dict)
    assert len(report.model_versions) > 0

    # Test with default model versions
    report_default = generate_bsa_report(
        source_image_hash=source_hash,
        rule_set_version=rules_ver,
        audit_trail=audit,
        declarations=decls,
        confirmation=conf,
        is_human_confirmed=True,
        model_versions=None,
    )
    assert report_default.model_versions is not None
    assert isinstance(report_default.model_versions, dict)
    assert len(report_default.model_versions) > 0
    assert "ocr_engine" in report_default.model_versions

    # Verify field comparisons
    assert len(report.declarations) == 2
    assert report.declarations[0].field_name == "Net Quantity"
    assert report.declarations[0].ocr_provider == "PaddleOCR"
    assert report.declarations[0].confidence == 0.98

    # Verify audit trail
    assert report.audit_trail.total_sequence_count == 5
    assert report.audit_trail.root_entry_hash == "root_hash"
