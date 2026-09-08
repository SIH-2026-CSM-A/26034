import pytest
from uuid import uuid4
from datetime import UTC, datetime

from app.contracts.enums import DeclarationField, FieldState, RuleSeverity, RuleStatus, Verdict
from app.contracts.records import FieldFinding, RuleParameterSnapshot, VerdictRecord
from app.core.enums import ReviewAction
from app.core.models import ReviewRow
from app.modules.complaints.domain import (
    ComplaintRecord,
    ComplaintStatus,
    IllegalComplaintTransitionError,
    UnconfirmedVerdictComplaintError,
    create_complaint_from_verdict,
)
from app.modules.complaints.service import ComplaintService


def make_finding(
    field: DeclarationField = DeclarationField.NET_QUANTITY,
    state: FieldState = FieldState.FAIL,
    observed_value: str | None = "400g",
    expected_value: str | None = "500g",
) -> FieldFinding:
    snapshot = RuleParameterSnapshot(
        rule_id="R1",
        clause_ref="Clause 4(1)",
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
        reason="Value deficient",
        evidence_span_ids=["span-1"],
    )


@pytest.fixture
def confirmed_record():
    finding = make_finding()
    return VerdictRecord(
        subject_ref="REP-123",
        verdict=Verdict.POTENTIAL_VIOLATION,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding,),
        field_providers={DeclarationField.NET_QUANTITY: "PADDLEOCR"},
    )


@pytest.fixture
def confirmed_review():
    return ReviewRow(
        id=uuid4(),
        scan_id=uuid4(),
        verdict_id=uuid4(),
        action=ReviewAction.CONFIRM,
        officer_id="Officer Smith",
        note="Confirmed",
        created_at=datetime.now(UTC),
    )


def test_legal_transitions():
    """Test RAISED -> ACKNOWLEDGED -> RESOLVED."""
    complaint = ComplaintRecord(
        verdict_id="V1",
        review_id=uuid4(),
        manufacturer_id="M1",
        status=ComplaintStatus.RAISED,
        complaint_text="Text",
    )

    # RAISED -> ACKNOWLEDGED
    c2 = complaint.transition_to(ComplaintStatus.ACKNOWLEDGED)
    assert c2.status == ComplaintStatus.ACKNOWLEDGED

    # ACKNOWLEDGED -> RESOLVED
    c3 = c2.transition_to(ComplaintStatus.RESOLVED)
    assert c3.status == ComplaintStatus.RESOLVED


def test_illegal_transitions():
    """
    Test illegal transitions:
    - RAISED -> RESOLVED raises IllegalComplaintTransitionError
    - RESOLVED -> any raises IllegalComplaintTransitionError
    """
    complaint = ComplaintRecord(
        verdict_id="V1",
        review_id=uuid4(),
        manufacturer_id="M1",
        status=ComplaintStatus.RAISED,
        complaint_text="Text",
    )

    # RAISED -> RESOLVED (Illegal)
    with pytest.raises(IllegalComplaintTransitionError):
        complaint.transition_to(ComplaintStatus.RESOLVED)

    # RESOLVED -> any (Illegal)
    resolved = ComplaintRecord(
        verdict_id="V1",
        review_id=uuid4(),
        manufacturer_id="M1",
        status=ComplaintStatus.RESOLVED,
        complaint_text="Text",
    )
    with pytest.raises(IllegalComplaintTransitionError):
        resolved.transition_to(ComplaintStatus.ACKNOWLEDGED)


def test_unconfirmed_verdict_rejection(confirmed_record):
    """
    Test unconfirmed verdict rejection:
    - review_row=None raises UnconfirmedVerdictComplaintError
    - review_row.action=ANNOTATE/REJECT raises UnconfirmedVerdictComplaintError
    """
    # review_row=None
    with pytest.raises(UnconfirmedVerdictComplaintError):
        create_complaint_from_verdict(confirmed_record, None, "M1") # type: ignore

    # review_row.action=ANNOTATE
    annotate_row = ReviewRow(
        id=uuid4(),
        scan_id=uuid4(),
        verdict_id=uuid4(),
        action=ReviewAction.ANNOTATE,
        officer_id="Officer Smith",
        created_at=datetime.now(UTC),
    )
    with pytest.raises(UnconfirmedVerdictComplaintError):
        create_complaint_from_verdict(confirmed_record, annotate_row, "M1")

    # review_row.action=REJECT
    reject_row = ReviewRow(
        id=uuid4(),
        scan_id=uuid4(),
        verdict_id=uuid4(),
        action=ReviewAction.REJECT,
        officer_id="Officer Smith",
        created_at=datetime.now(UTC),
    )
    with pytest.raises(UnconfirmedVerdictComplaintError):
        create_complaint_from_verdict(confirmed_record, reject_row, "M1")


def test_forbidden_vocabulary(confirmed_record, confirmed_review):
    """Assert forbidden phrases are absent in generated text."""
    complaint = create_complaint_from_verdict(confirmed_record, confirmed_review, "M1")
    text = complaint.complaint_text.lower()

    forbidden = {
        "violation confirmed",
        "illegal",
        "non-compliant",
        "non_compliant",
        "noncompliant",
        "guilty",
    }

    for term in forbidden:
        assert term not in text, f"Forbidden term '{term}' found in complaint text"


def test_reopen_creates_new_record(confirmed_record, confirmed_review):
    """Test reopen creates new record referencing supersedes_id."""
    service = ComplaintService()
    complaint = service.raise_complaint(confirmed_record, confirmed_review, "M1")

    # Advance to RESOLVED
    c_ack = service.advance_status(complaint, ComplaintStatus.ACKNOWLEDGED)
    c_res = service.advance_status(c_ack, ComplaintStatus.RESOLVED)

    # Reopen
    reopened = service.reopen_resolved(
        c_res,
        review=confirmed_review,
        reason="Manufacturer provided new evidence",
    )

    assert reopened.status == ComplaintStatus.RAISED
    assert reopened.supersedes_id == c_res.id
    assert "Reopened:" in reopened.complaint_text
    assert reopened.id != c_res.id
