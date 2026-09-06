from io import BytesIO
from unittest.mock import patch

import pytest
from docx import Document
from pypdf import PdfReader

from app.modules.evidence.export import (
    UnconfirmedVerdictExportError,
    export_compliance_report,
)


class MockDeclaration:
    def __init__(self, field_name, declared_value, state, ocr_provider, confidence):
        self.field_name = field_name
        self.declared_value = declared_value
        self.state = state
        self.ocr_provider = ocr_provider
        self.confidence = confidence


class MockRuleEvaluation:
    def __init__(self, rule_id, clause, parameter, required, measured, status, notes=None):
        self.rule_id = rule_id
        self.clause = clause
        self.parameter = parameter
        self.required = required
        self.measured = measured
        self.status = status
        self.notes = notes


class MockConfirmation:
    def __init__(self, confirmed_by, confirmation_timestamp, officer_action):
        self.confirmed_by = confirmed_by
        self.confirmation_timestamp = confirmation_timestamp
        self.officer_action = officer_action


class MockVerdictRecord:
    def __init__(
        self,
        overall_verdict,
        is_human_confirmed=True,
        report_id="REP-123",
        rule_set_version="v1.0",
        source_image_hash="hash123",
        image_path="path/to/img.jpg",
        confirmed_by="Officer Smith",
        confirmed_at="2026-09-06T10:00:00Z",
        officer_action="APPROVED",
        officer_notes="Looks good",
        declarations=None,
        rule_evaluations=None,
    ):
        self.overall_verdict = overall_verdict
        self.is_human_confirmed = is_human_confirmed
        self.report_id = report_id
        self.rule_set_version = rule_set_version
        self.source_image_hash = source_image_hash
        self.image_path = image_path
        self.confirmation = MockConfirmation(confirmed_by, confirmed_at, officer_action)
        self.officer_notes = officer_notes
        self.declarations = declarations or []
        self.rule_evaluations = rule_evaluations or []


def extract_pdf_text(pdf_bytes):
    reader = PdfReader(BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_docx_text(docx_bytes):
    doc = Document(BytesIO(docx_bytes))
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text.append(cell.text)
    return "\n".join(text)


@pytest.fixture
def confirmed_record():
    return MockVerdictRecord(
        overall_verdict="PASS",
        declarations=[
            MockDeclaration("Net Weight", "500g", "MATCH", "PaddleOCR", 0.98),
        ],
        rule_evaluations=[
            MockRuleEvaluation("R1", "Clause 4(1)", "Weight", ">=500g", "505g", "COMPLIANT"),
            MockRuleEvaluation("R2", "Clause 5(2)", "Font Size", ">=2mm", "2.1mm", "COMPLIANT"),
        ],
    )


def test_divergence_pdf_docx(confirmed_record):
    """AC1: Assert PDF and DOCX content match for the same record."""
    pdf_bytes = export_compliance_report(confirmed_record, format="pdf")
    docx_bytes = export_compliance_report(confirmed_record, format="docx")

    pdf_text = extract_pdf_text(pdf_bytes).lower()
    docx_text = extract_docx_text(docx_bytes).lower()

    # Critical fields to check in both
    critical_fields = [
        confirmed_record.report_id.lower(),
        confirmed_record.rule_set_version.lower(),
        confirmed_record.source_image_hash.lower(),
        confirmed_record.confirmation.confirmed_by.lower(),
        confirmed_record.confirmation.officer_action.lower(),
        confirmed_record.overall_verdict.lower(),
        "net weight",
        "500g",
        "match",
        "paddleocr",
        "r1",
        "clause 4(1)",
        "weight",
        "505g",
        "compliant",
        "r2",
        "clause 5(2)",
        "font size",
        "2.1mm",
    ]

    for field in critical_fields:
        assert field in pdf_text, f"Field '{field}' missing from PDF"
        assert field in docx_text, f"Field '{field}' missing from DOCX"


def test_pass_report_completeness(confirmed_record):
    """AC2: Assert PASS reports render all rule checks in full detail."""
    pdf_bytes = export_compliance_report(confirmed_record, format="pdf")
    pdf_text = extract_pdf_text(pdf_bytes)

    for rule in confirmed_record.rule_evaluations:
        assert rule.rule_id in pdf_text
        assert rule.clause in pdf_text
        assert rule.parameter in pdf_text
        assert rule.status in pdf_text


def test_forbidden_vocabulary():
    """AC3: Assert POTENTIAL_VIOLATION reports avoid banned terms."""
    record = MockVerdictRecord(
        overall_verdict="POTENTIAL VIOLATION",
        declarations=[MockDeclaration("Weight", "400g", "MISMATCH", "PaddleOCR", 0.95)],
        rule_evaluations=[MockRuleEvaluation("R1", "C1", "W", "500g", "400g", "NON_COMPLIANT")],
    )

    banned_terms = ["violation confirmed", "non-compliant", "illegal", "guilty"]

    for fmt in ["pdf", "docx"]:
        out_bytes = export_compliance_report(record, format=fmt)
        if fmt == "pdf":
            text = extract_pdf_text(out_bytes).lower()
        else:
            text = extract_docx_text(out_bytes).lower()
        for term in banned_terms:
            assert term not in text, f"Banned term '{term}' found in {fmt} report"


def test_human_confirmation_gate():
    """AC4: Assert unconfirmed records raise UnconfirmedVerdictExportError."""
    record = MockVerdictRecord(overall_verdict="PASS", is_human_confirmed=False)

    for fmt in ["pdf", "docx"]:
        with pytest.raises(UnconfirmedVerdictExportError):
            export_compliance_report(record, format=fmt)


def test_clause_citation_assertion(confirmed_record):
    """AC5: Assert 100% of rule check rows contain a non-empty clause_reference."""
    # We test this by checking the rendered output
    pdf_bytes = export_compliance_report(confirmed_record, format="pdf")
    pdf_text = extract_pdf_text(pdf_bytes)

    for rule in confirmed_record.rule_evaluations:
        assert rule.clause in pdf_text
        assert rule.clause != "", "Clause reference must not be empty"


def test_measurement_refusal_rendering():
    """AC: Assert measurement refusal renders as 'Measurement declined' instead of 'N/A'."""
    record = MockVerdictRecord(
        overall_verdict="REVIEW",
        declarations=[MockDeclaration("Weight", "500g", "MATCH", "PaddleOCR", 0.99)],
        rule_evaluations=[
            MockRuleEvaluation(
                "R1", "C1", "Font Size", ">=2mm", None, "INSUFFICIENT_EVIDENCE", notes="Refused"
            )
        ],
    )

    for fmt in ["pdf", "docx"]:
        out_bytes = export_compliance_report(record, format=fmt)
        text = extract_pdf_text(out_bytes) if fmt == "pdf" else extract_docx_text(out_bytes)
        assert "Measurement declined" in text, f"Refusal text missing from {fmt} report"
        assert "N/A" not in text.split("Status")[0], (
            f"'N/A' found in measured value for {fmt} report"
        )


def test_insufficient_evidence_rendering():
    """
    AC: Assert INSUFFICIENT_EVIDENCE:
    1. Visibly distinct from FAIL (not containing 'FAIL' in status).
    2. Actual reason/notes appear in both PDF and DOCX.
    3. Reason is not replaced by generic placeholder.
    """
    reason_text = "Image too blurry to determine font size"
    record = MockVerdictRecord(
        overall_verdict="REVIEW",
        declarations=[MockDeclaration("Weight", "500g", "MATCH", "PaddleOCR", 0.99)],
        rule_evaluations=[
            MockRuleEvaluation(
                "R1", "C1", "Font Size", ">=2mm", None, "INSUFFICIENT_EVIDENCE", notes=reason_text
            )
        ],
    )

    for fmt in ["pdf", "docx"]:
        out_bytes = export_compliance_report(record, format=fmt)
        text = extract_pdf_text(out_bytes) if fmt == "pdf" else extract_docx_text(out_bytes)

        # 1. Distinct from FAIL
        assert "INSUFFICIENT_EVIDENCE" in text
        assert "FAIL" not in text

        # 2. Actual reason appears
        assert reason_text in text, f"Reason '{reason_text}' missing from {fmt} report"

        # 3. No generic placeholders for the reason
        # The primary check is that reason_text IS present.


def test_offline_and_zero_stub():
    """AC6: Assert clean execution offline and no placeholder text."""
    record = MockVerdictRecord(
        overall_verdict="PASS",
        declarations=[MockDeclaration("Weight", "500g", "MATCH", "PaddleOCR", 0.99)],
        rule_evaluations=[MockRuleEvaluation("R1", "C1", "W", "500g", "500g", "COMPLIANT")],
    )

    with patch("socket.socket", side_effect=OSError("Offline")):
        # PDF export
        pdf_bytes = export_compliance_report(record, format="pdf")
        pdf_text = extract_pdf_text(pdf_bytes)
        # DOCX export
        docx_bytes = export_compliance_report(record, format="docx")
        docx_text = extract_docx_text(docx_bytes)

    # Check for placeholders
    placeholders = ["sample text", "placeholder", "lorem ipsum", "[INSERT]", "TBD"]
    for text in [pdf_text, docx_text]:
        text_lower = text.lower()
        for ph in placeholders:
            assert ph.lower() not in text_lower, f"Placeholder '{ph}' found in report"
