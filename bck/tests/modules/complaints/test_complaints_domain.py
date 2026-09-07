"""Unit tests for manufacturer complaint domain models and service rules (CMP-001)."""

import contextlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.contracts.enums import (
    DeclarationField,
    FieldState,
    RuleSeverity,
    RuleStatus,
    Verdict,
)
from app.contracts.records import FieldFinding, RuleParameterSnapshot, VerdictRecord
from app.core.enums import ReviewAction
from app.core.models import ReviewRow
from app.modules.complaints import (
    ComplaintService,
    ComplaintStatus,
    ConfirmedVerdict,
    InvalidStatusTransitionError,
    UnconfirmedVerdictError,
    build_issue_summary,
)


def _make_verdict_record(verdict: Verdict = Verdict.POTENTIAL_VIOLATION) -> VerdictRecord:
    """Helper to construct a valid VerdictRecord for testing."""
    scan_id = uuid4()
    snapshot = RuleParameterSnapshot(
        rule_id="R2",
        clause_ref="Clause 5(2)",
        gazette_ref="LMPC-2011.pdf",
        source_text="Net quantity obligation",
        status=RuleStatus.VERIFIED,
        severity=RuleSeverity.MANDATORY,
        rule_set_version="1.0",
        parameters={},
        rounding_increment=None,
        tolerance=None,
        tolerance_basis=None,
    )
    finding = FieldFinding(
        field=DeclarationField.NET_QUANTITY,
        state=FieldState.FAIL if verdict == Verdict.POTENTIAL_VIOLATION else FieldState.PASS,
        rule_snapshot=snapshot,
        observed_value="150 g",
        expected_value="200 g",
        reason="Net quantity non-compliant",
    )
    return VerdictRecord(
        subject_ref=f"SCAN-{scan_id}",
        verdict=verdict,
        rule_set_version="1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding,),
    )


def _make_review_row(
    record: VerdictRecord,
    action: ReviewAction = ReviewAction.CONFIRM,
    overridden_verdict: Verdict | None = None,
) -> ReviewRow:
    """Helper to construct a ReviewRow for testing."""
    scan_id = uuid4()
    if record.subject_ref.startswith("SCAN-"):
        with contextlib.suppress(ValueError):
            scan_id = UUID(record.subject_ref.replace("SCAN-", ""))
    return ReviewRow(
        id=uuid4(),
        scan_id=scan_id,
        verdict_id=uuid4(),
        officer_id="OFFICER-001",
        action=action,
        note="Audit approved",
        overridden_verdict=overridden_verdict,
        created_at=datetime.now(UTC),
    )


class TestComplaintStatus:
    def test_complaint_status_values(self) -> None:
        """Test enum string representation."""
        assert ComplaintStatus.RAISED == "raised"
        assert ComplaintStatus.ACKNOWLEDGED == "acknowledged"
        assert ComplaintStatus.RESOLVED == "resolved"
        assert ComplaintStatus.REJECTED == "rejected"


class TestValidTransitions:
    def test_valid_transitions_from_raised(self) -> None:
        """Test permitted transitions from RAISED."""
        service = ComplaintService()
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review = _make_review_row(record, ReviewAction.CONFIRM)
        cv = ConfirmedVerdict(record, review)

        c = service.raise_complaint(
            confirmed_verdict=cv,
            manufacturer_name="Acme Corp",
            rule_id="rule7",
            field="net_quantity",
            measured_value="150 g",
            required_value="200 g",
            officer_id="OFFICER-001",
        )

        c_ack = service.transition_complaint(c, ComplaintStatus.ACKNOWLEDGED, "OFFICER-002")
        assert c_ack.status == ComplaintStatus.ACKNOWLEDGED

        c_res = service.transition_complaint(c, ComplaintStatus.RESOLVED, "OFFICER-002")
        assert c_res.status == ComplaintStatus.RESOLVED

        c_rej = service.transition_complaint(c, ComplaintStatus.REJECTED, "OFFICER-002")
        assert c_rej.status == ComplaintStatus.REJECTED

    def test_valid_transitions_from_acknowledged(self) -> None:
        """Test permitted transitions from ACKNOWLEDGED."""
        service = ComplaintService()
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review = _make_review_row(record, ReviewAction.CONFIRM)
        cv = ConfirmedVerdict(record, review)

        c = service.raise_complaint(
            confirmed_verdict=cv,
            manufacturer_name="Acme Corp",
            rule_id="rule7",
            field="net_quantity",
            measured_value="150 g",
            required_value="200 g",
            officer_id="OFFICER-001",
        )
        c_ack = service.transition_complaint(c, ComplaintStatus.ACKNOWLEDGED, "OFFICER-002")

        c_res = service.transition_complaint(c_ack, ComplaintStatus.RESOLVED, "OFFICER-003")
        assert c_res.status == ComplaintStatus.RESOLVED

        c_rej = service.transition_complaint(c_ack, ComplaintStatus.REJECTED, "OFFICER-003")
        assert c_rej.status == ComplaintStatus.REJECTED


class TestInvalidTransitions:
    def test_invalid_transitions(self) -> None:
        """Test illegal status transitions raise InvalidStatusTransitionError."""
        service = ComplaintService()
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review = _make_review_row(record, ReviewAction.CONFIRM)
        cv = ConfirmedVerdict(record, review)

        c = service.raise_complaint(
            confirmed_verdict=cv,
            manufacturer_name="Acme Corp",
            rule_id="rule7",
            field="net_quantity",
            measured_value="150 g",
            required_value="200 g",
            officer_id="OFFICER-001",
        )
        ack = service.transition_complaint(c, ComplaintStatus.ACKNOWLEDGED, "OFFICER-002")
        res = service.transition_complaint(ack, ComplaintStatus.RESOLVED, "OFFICER-003")
        rej = service.transition_complaint(c, ComplaintStatus.REJECTED, "OFFICER-002")

        # Cannot transition back to RAISED
        with pytest.raises(InvalidStatusTransitionError, match="Illegal status transition"):
            service.transition_complaint(ack, ComplaintStatus.RAISED, "OFFICER-003")

        # RESOLVED terminal state transitions
        with pytest.raises(InvalidStatusTransitionError, match="Illegal status transition"):
            service.transition_complaint(res, ComplaintStatus.RAISED, "OFFICER-003")

        with pytest.raises(InvalidStatusTransitionError, match="Illegal status transition"):
            service.transition_complaint(res, ComplaintStatus.ACKNOWLEDGED, "OFFICER-003")

        with pytest.raises(InvalidStatusTransitionError, match="Illegal status transition"):
            service.transition_complaint(res, ComplaintStatus.REJECTED, "OFFICER-003")

        # REJECTED terminal state transitions
        with pytest.raises(InvalidStatusTransitionError, match="Illegal status transition"):
            service.transition_complaint(rej, ComplaintStatus.RAISED, "OFFICER-003")

        with pytest.raises(InvalidStatusTransitionError, match="Illegal status transition"):
            service.transition_complaint(rej, ComplaintStatus.ACKNOWLEDGED, "OFFICER-003")

        with pytest.raises(InvalidStatusTransitionError, match="Illegal status transition"):
            service.transition_complaint(rej, ComplaintStatus.RESOLVED, "OFFICER-003")


class TestConfirmationGate:
    def test_unconfirmed_machine_verdict_fails(self) -> None:
        """Machine verdict with no ReviewRow fails confirmation gate."""
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        with pytest.raises(UnconfirmedVerdictError, match="non-null officer ReviewRow"):
            ConfirmedVerdict(record=record, review_row=None)  # type: ignore[arg-type]

    def test_non_finalising_review_action_fails(self) -> None:
        """Non-finalising review actions (ANNOTATE, REQUEST_RECAPTURE) fail confirmation gate."""
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review_ann = _make_review_row(record, action=ReviewAction.ANNOTATE)
        with pytest.raises(UnconfirmedVerdictError, match="non-finalising"):
            ConfirmedVerdict(record, review_ann)

        review_recap = _make_review_row(record, action=ReviewAction.REQUEST_RECAPTURE)
        with pytest.raises(UnconfirmedVerdictError, match="non-finalising"):
            ConfirmedVerdict(record, review_recap)

    def test_effective_pass_or_review_fails(self) -> None:
        """Effective verdicts of PASS or REVIEW fail confirmation gate."""
        record_pass = _make_verdict_record(Verdict.PASS)
        review_pass = _make_review_row(record_pass, action=ReviewAction.CONFIRM)
        with pytest.raises(UnconfirmedVerdictError, match="requires POTENTIAL_VIOLATION"):
            ConfirmedVerdict(record_pass, review_pass)

        record_rev = _make_verdict_record(Verdict.REVIEW)
        review_rev = _make_review_row(record_rev, action=ReviewAction.CONFIRM)
        with pytest.raises(UnconfirmedVerdictError, match="requires POTENTIAL_VIOLATION"):
            ConfirmedVerdict(record_rev, review_rev)

    def test_override_to_non_violation_fails(self) -> None:
        """Officer OVERRIDE to PASS fails confirmation gate."""
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review_override_pass = _make_review_row(
            record, action=ReviewAction.OVERRIDE, overridden_verdict=Verdict.PASS
        )
        with pytest.raises(UnconfirmedVerdictError, match="requires POTENTIAL_VIOLATION"):
            ConfirmedVerdict(record, review_override_pass)

    def test_override_missing_verdict_fails(self) -> None:
        """Officer OVERRIDE without overridden_verdict raises ValueError."""
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review = _make_review_row(record, action=ReviewAction.OVERRIDE, overridden_verdict=None)
        with pytest.raises(ValueError, match="OVERRIDE action requires overridden_verdict"):
            ConfirmedVerdict(record, review)

    def test_override_to_review_fails(self) -> None:
        """Officer OVERRIDE to REVIEW fails confirmation gate."""
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review_override_rev = _make_review_row(
            record, action=ReviewAction.OVERRIDE, overridden_verdict=Verdict.REVIEW
        )
        with pytest.raises(UnconfirmedVerdictError, match="requires POTENTIAL_VIOLATION"):
            ConfirmedVerdict(record, review_override_rev)

    def test_valid_confirm_and_override_to_violation_succeeds(self) -> None:
        """Officer CONFIRM on POTENTIAL_VIOLATION or OVERRIDE to POTENTIAL_VIOLATION succeeds."""
        # CONFIRM
        record1 = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review1 = _make_review_row(record1, action=ReviewAction.CONFIRM)
        cv1 = ConfirmedVerdict(record1, review1)
        assert cv1.record.verdict == Verdict.POTENTIAL_VIOLATION

        # OVERRIDE from REVIEW to POTENTIAL_VIOLATION
        record2 = _make_verdict_record(Verdict.REVIEW)
        review2 = _make_review_row(
            record2, action=ReviewAction.OVERRIDE, overridden_verdict=Verdict.POTENTIAL_VIOLATION
        )
        cv2 = ConfirmedVerdict(record2, review2)
        assert cv2.review_row.overridden_verdict == Verdict.POTENTIAL_VIOLATION


class TestComplaintWording:
    def test_build_issue_summary_format_and_forbidden_words(self) -> None:
        """Test issue summary contains rule details and avoids forbidden words."""
        summary = build_issue_summary(
            rule_id="rule7",
            field="net_quantity",
            measured_value="150 g",
            required_value="200 g",
        )
        assert "rule7" in summary
        assert "net_quantity" in summary
        assert "150 g" in summary
        assert "200 g" in summary
        assert "potential violation" in summary.lower()

        # Case-insensitive forbidden word checks
        summary_lower = summary.lower()
        assert "violation confirmed" not in summary_lower
        assert "illegal" not in summary_lower
        assert "non-compliant" not in summary_lower

    def test_build_issue_summary_rejects_forbidden_text(self) -> None:
        """Test build_issue_summary raises ValueError if forbidden text is present."""
        with pytest.raises(ValueError, match="forbidden"):
            build_issue_summary(
                rule_id="illegal",
                field="net_quantity",
                measured_value="150 g",
                required_value="200 g",
            )
        with pytest.raises(ValueError, match="forbidden"):
            build_issue_summary(
                rule_id="rule7",
                field="net_quantity",
                measured_value="violation confirmed",
                required_value="200 g",
            )
        with pytest.raises(ValueError, match="forbidden"):
            build_issue_summary(
                rule_id="rule7",
                field="net_quantity",
                measured_value="150 g",
                required_value="non-compliant",
            )


class TestAppendOnlyBehavior:
    def test_transition_leaves_previous_complaint_unchanged(self) -> None:
        """Test status transition creates a new event without mutating historical complaint."""
        service = ComplaintService()
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review = _make_review_row(record, ReviewAction.CONFIRM)
        cv = ConfirmedVerdict(record, review)

        initial = service.raise_complaint(
            confirmed_verdict=cv,
            manufacturer_name="Acme Corp",
            rule_id="rule7",
            field="net_quantity",
            measured_value="150 g",
            required_value="200 g",
            officer_id="OFFICER-001",
        )

        ack = service.transition_complaint(initial, ComplaintStatus.ACKNOWLEDGED, "OFFICER-002")

        # Initial object is completely unchanged
        assert initial.status == ComplaintStatus.RAISED
        assert initial.supersedes_id is None

        # Ack object is a new record referencing initial
        assert ack.status == ComplaintStatus.ACKNOWLEDGED
        assert ack.supersedes_id == initial.id
        assert ack.id != initial.id

    def test_new_complaint_after_resolution_references_prior_complaint(self) -> None:
        """Test creating a new complaint thread after resolution links prior complaint."""
        service = ComplaintService()
        record = _make_verdict_record(Verdict.POTENTIAL_VIOLATION)
        review = _make_review_row(record, ReviewAction.CONFIRM)
        cv = ConfirmedVerdict(record, review)

        initial = service.raise_complaint(
            confirmed_verdict=cv,
            manufacturer_name="Acme Corp",
            rule_id="rule7",
            field="net_quantity",
            measured_value="150 g",
            required_value="200 g",
            officer_id="OFFICER-001",
        )

        resolved = service.transition_complaint(initial, ComplaintStatus.RESOLVED, "OFFICER-002")

        # Creating a NEW complaint thread following resolved complaint
        reopened_thread = service.raise_complaint(
            confirmed_verdict=cv,
            manufacturer_name="Acme Corp",
            rule_id="rule7",
            field="net_quantity",
            measured_value="140 g",
            required_value="200 g",
            officer_id="OFFICER-003",
            prior_complaint=resolved,
        )

        assert reopened_thread.status == ComplaintStatus.RAISED
        assert reopened_thread.supersedes_id == resolved.id
        assert resolved.status == ComplaintStatus.RESOLVED
