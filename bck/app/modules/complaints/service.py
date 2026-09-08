from app.contracts.records import VerdictRecord
from app.core.models import ReviewRow

from .domain import (
    ComplaintRecord,
    ComplaintStatus,
    create_complaint_from_verdict,
)


class ComplaintService:
    """
    High-level coordinator for compliance complaint lifecycles.
    Orchestrates domain logic for raising, advancing, and reopening complaints.
    """

    def raise_complaint(
        self, record: VerdictRecord, review: ReviewRow, manufacturer_id: str
    ) -> ComplaintRecord:
        """Raises a new complaint against a manufacturer based on a confirmed verdict."""
        return create_complaint_from_verdict(record, review, manufacturer_id)

    def advance_status(
        self, complaint: ComplaintRecord, target_status: ComplaintStatus
    ) -> ComplaintRecord:
        """Transitions a complaint to a new status."""
        return complaint.transition_to(target_status)

    def reopen_resolved(
        self, complaint: ComplaintRecord, review: ReviewRow, reason: str
    ) -> ComplaintRecord:
        """
        Re-opens a resolved complaint by creating a new record that supersedes the old one.
        The reason for reopening is appended to the original complaint text.
        """
        if complaint.status != ComplaintStatus.RESOLVED:
            # The requirement specifically says "reopen_resolved",
            # we assume it's only for RESOLVED status.
            raise ValueError("Only resolved complaints can be reopened.")

        # Note: review here is likely the review that triggers the reopen
        new_text = f"{complaint.complaint_text}\nReopened: {reason}"

        return ComplaintRecord(
            verdict_id=complaint.verdict_id,
            review_id=review.id,
            manufacturer_id=complaint.manufacturer_id,
            status=ComplaintStatus.RAISED,
            complaint_text=new_text,
            supersedes_id=complaint.id,
        )
