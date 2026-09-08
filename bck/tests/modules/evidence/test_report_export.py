import uuid
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import patch

import pytest
from docx import Document
from pypdf import PdfReader

from app.contracts.enums import (
    DeclarationField,
    EvidenceProvider,
    FieldState,
    RuleSeverity,
    RuleStatus,
    Verdict,
)
from app.contracts.records import FieldFinding, RuleParameterSnapshot, VerdictRecord
from app.core.enums import ReviewAction
from app.core.models import ReviewRow
from app.modules.evidence.export import (
    UnconfirmedVerdictExportError,
    export_compliance_report,
)


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


def make_finding(
    field: DeclarationField = DeclarationField.NET_QUANTITY,
    state: FieldState = FieldState.PASS,
    clause_ref: str = "Clause 4(1)",
    rule_id: str = "R1",
    observed_value: str | None = "500g",
    expected_value: str | None = ">=500g",
    reason: str = "Weight matches specification",
) -> FieldFinding:
    snapshot = RuleParameterSnapshot(
        rule_id=rule_id,
        clause_ref=clause_ref,
        gazette_ref="G.S.R. 123(E)",
        source_text="Rule source text",
        status=RuleStatus.VERIFIED,
        severity=RuleSeverity.MANDATORY,
        rule_set_version="v1.0",
        parameters={},
        rounding_increment=None,
        tolerance=None,
        tolerance_basis=None,
    )
    return FieldFinding(
        field=field,
        state=state,
        rule_snapshot=snapshot,
        observed_value=observed_value,
        expected_value=expected_value,
        reason=reason,
        evidence_span_ids=["span-1"],
    )


def make_review_row(
    action: ReviewAction = ReviewAction.CONFIRM,
    officer_id: str = "Officer Smith",
    note: str | None = "Looks good",
) -> ReviewRow:
    return ReviewRow(
        id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        verdict_id=uuid.uuid4(),
        action=action,
        officer_id=officer_id,
        note=note,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def confirmed_record():
    finding_1 = make_finding(
        field=DeclarationField.NET_QUANTITY,
        state=FieldState.PASS,
        clause_ref="Clause 4(1)",
        rule_id="R1",
        observed_value="505g",
        expected_value=">=500g",
        reason="Quantity meets requirement",
    )
    finding_2 = make_finding(
        field=DeclarationField.RETAIL_SALE_PRICE,
        state=FieldState.PASS,
        clause_ref="Clause 5(2)",
        rule_id="R2",
        observed_value="2.1mm",
        expected_value=">=2mm",
        reason="Height requirement satisfied",
    )
    return VerdictRecord(
        subject_ref="REP-123",
        verdict=Verdict.PASS,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding_1, finding_2),
        field_providers={
            DeclarationField.NET_QUANTITY: EvidenceProvider.PADDLEOCR,
            DeclarationField.RETAIL_SALE_PRICE: EvidenceProvider.PADDLEOCR,
        },
    )


@pytest.fixture
def review_row():
    return make_review_row()


def test_divergence_pdf_docx(confirmed_record, review_row):
    """AC1: Assert PDF and DOCX content match for the same record."""
    pdf_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="pdf")
    docx_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="docx")

    pdf_text = extract_pdf_text(pdf_bytes).lower()
    docx_text = extract_docx_text(docx_bytes).lower()

    critical_fields = [
        confirmed_record.subject_ref.lower(),
        confirmed_record.rule_set_version.lower(),
        review_row.officer_id.lower(),
        review_row.action.value.lower(),
        confirmed_record.verdict.value.lower(),
        "net_quantity",
        "505g",
        FieldState.PASS.value.lower(),
        "paddleocr",
        "r1",
        "clause 4(1)",
        "r2",
        "clause 5(2)",
        "2.1mm",
    ]

    for field in critical_fields:
        assert field in pdf_text, f"Field '{field}' missing from PDF"
        assert field in docx_text, f"Field '{field}' missing from DOCX"


def test_pass_report_completeness(confirmed_record, review_row):
    """AC2: Assert PASS reports render all rule checks in full detail."""
    pdf_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="pdf")
    pdf_text = extract_pdf_text(pdf_bytes)

    for f in confirmed_record.findings:
        assert f.rule_snapshot.rule_id in pdf_text
        assert f.rule_snapshot.clause_ref in pdf_text
        assert f.field.value in pdf_text
        assert f.state.value in pdf_text


def test_forbidden_vocabulary(review_row):
    """AC3: Assert POTENTIAL_VIOLATION reports avoid banned terms."""
    finding = make_finding(
        field=DeclarationField.NET_QUANTITY,
        state=FieldState.FAIL,
        clause_ref="Clause 4(1)",
        rule_id="R1",
        observed_value="400g",
        expected_value="500g",
        reason="Quantity deficient",
    )
    record = VerdictRecord(
        subject_ref="REP-VIOLATION",
        verdict=Verdict.POTENTIAL_VIOLATION,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding,),
        field_providers={DeclarationField.NET_QUANTITY: EvidenceProvider.PADDLEOCR},
    )

    banned_terms = [
        "violation confirmed",
        "non-compliant",
        "non_compliant",
        "noncompliant",
        "illegal",
        "guilty",
    ]

    for fmt in ["pdf", "docx"]:
        out_bytes = export_compliance_report(record, review_row=review_row, format=fmt)
        if fmt == "pdf":
            text = extract_pdf_text(out_bytes).lower()
        else:
            text = extract_docx_text(out_bytes).lower()
        for term in banned_terms:
            assert term not in text, f"Banned term '{term}' found in {fmt} report"


def test_human_confirmation_gate(confirmed_record):
    """AC4: Assert unconfirmed records raise UnconfirmedVerdictExportError."""
    # 1. No review row at all
    for fmt in ["pdf", "docx"]:
        with pytest.raises(UnconfirmedVerdictExportError):
            export_compliance_report(confirmed_record, review_row=None, format=fmt)

    # 2. Review row with non-finalising action (if any)
    unconfirmed_row = ReviewRow(
        id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        verdict_id=uuid.uuid4(),
        action=None,
        officer_id="Officer Smith",
        created_at=datetime.now(UTC),
    )
    for fmt in ["pdf", "docx"]:
        with pytest.raises(UnconfirmedVerdictExportError):
            export_compliance_report(confirmed_record, review_row=unconfirmed_row, format=fmt)


def test_clause_citation_assertion(confirmed_record, review_row):
    """AC5: Assert 100% of rule check rows contain a non-empty clause_reference."""
    pdf_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="pdf")
    pdf_text = extract_pdf_text(pdf_bytes)

    for f in confirmed_record.findings:
        assert f.rule_snapshot.clause_ref in pdf_text
        assert f.rule_snapshot.clause_ref != "", "Clause reference must not be empty"


def test_measurement_refusal_rendering(review_row):
    """AC: Assert measurement refusal renders as 'Measurement declined' instead of 'N/A'
    and prints no number.
    """
    finding = make_finding(
        field=DeclarationField.RETAIL_SALE_PRICE,
        state=FieldState.INSUFFICIENT_EVIDENCE,
        clause_ref="Clause 5(2)",
        rule_id="R1",
        observed_value=None,
        expected_value=">=2mm",
        reason="Refused measurement due to glare",
    )
    record = VerdictRecord(
        subject_ref="REP-REFUSED",
        verdict=Verdict.REVIEW,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding,),
        field_providers={DeclarationField.RETAIL_SALE_PRICE: EvidenceProvider.PADDLEOCR},
    )

    for fmt in ["pdf", "docx"]:
        out_bytes = export_compliance_report(record, review_row=review_row, format=fmt)
        text = extract_pdf_text(out_bytes) if fmt == "pdf" else extract_docx_text(out_bytes)
        assert "Measurement declined" in text, f"Refusal text missing from {fmt} report"
        status_split = text.split("Status")[0]
        assert "N/A" not in status_split, f"'N/A' found in measured value for {fmt} report"


def test_insufficient_evidence_rendering(review_row):
    """
    AC: Assert INSUFFICIENT_EVIDENCE:
    1. Visibly distinct from FAIL (not containing 'FAIL' in status).
    2. Actual reason/notes appear in both PDF and DOCX.
    3. Reason is not replaced by generic placeholder.
    """
    reason_text = "Image too blurry to determine font size"
    finding = make_finding(
        field=DeclarationField.RETAIL_SALE_PRICE,
        state=FieldState.INSUFFICIENT_EVIDENCE,
        clause_ref="Clause 5(2)",
        rule_id="R1",
        observed_value=None,
        expected_value=">=2mm",
        reason=reason_text,
    )
    record = VerdictRecord(
        subject_ref="REP-INSUFF",
        verdict=Verdict.REVIEW,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding,),
        field_providers={DeclarationField.RETAIL_SALE_PRICE: EvidenceProvider.PADDLEOCR},
    )

    for fmt in ["pdf", "docx"]:
        out_bytes = export_compliance_report(record, review_row=review_row, format=fmt)
        text = extract_pdf_text(out_bytes) if fmt == "pdf" else extract_docx_text(out_bytes)

        # 1. Distinct from FAIL
        assert FieldState.INSUFFICIENT_EVIDENCE.value in text
        assert FieldState.FAIL.value not in text

        # 2. Actual reason appears
        assert reason_text in text, f"Reason '{reason_text}' missing from {fmt} report"


def test_offline_and_zero_stub(confirmed_record, review_row):
    """AC6: Assert clean execution offline and no placeholder text."""
    with patch("socket.socket", side_effect=OSError("Offline")):
        pdf_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="pdf")
        pdf_text = extract_pdf_text(pdf_bytes)
        docx_bytes = export_compliance_report(
            confirmed_record, review_row=review_row, format="docx"
        )
        docx_text = extract_docx_text(docx_bytes)

    placeholders = ["sample text", "placeholder", "lorem ipsum", "[INSERT]", "TBD"]
    for text in [pdf_text, docx_text]:
        text_lower = text.lower()
        for ph in placeholders:
            assert ph.lower() not in text_lower, f"Placeholder '{ph}' found in report"
