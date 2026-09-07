"""Complaint domain service providing escalation workflows (CMP-001)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.complaints.domain import (
    ComplaintRecord,
    ComplaintStatus,
    ConfirmedVerdict,
    build_issue_summary,
)


class ComplaintService:
    """Pure domain service for managing manufacturer complaints."""

    def raise_complaint(
        self,
        confirmed_verdict: ConfirmedVerdict,
        manufacturer_name: str,
        rule_id: str,
        field: str,
        measured_value: str,
        required_value: str,
        officer_id: str,
        prior_complaint: ComplaintRecord | None = None,
        at_time: datetime | None = None,
    ) -> ComplaintRecord:
        """Raise a new complaint for a confirmed officer verdict of POTENTIAL_VIOLATION.

        If prior_complaint is given (e.g. creating a new complaint thread after a previously
        resolved/closed complaint), supersedes_id references prior_complaint.id.
        """
        issue_summary = build_issue_summary(
            rule_id=rule_id,
            field=field,
            measured_value=measured_value,
            required_value=required_value,
        )

        supersedes = prior_complaint.id if prior_complaint is not None else None

        return ComplaintRecord(
            id=uuid4(),
            scan_id=confirmed_verdict.scan_id,
            verdict_id=confirmed_verdict.verdict_id,
            manufacturer_name=manufacturer_name,
            issue_summary=issue_summary,
            status=ComplaintStatus.RAISED,
            raised_by_officer_id=officer_id,
            raised_at=at_time or datetime.now(UTC),
            supersedes_id=supersedes,
        )

    def transition_complaint(
        self,
        complaint: ComplaintRecord,
        new_status: ComplaintStatus,
        officer_id: str,
        new_issue_summary: str | None = None,
        at_time: datetime | None = None,
    ) -> ComplaintRecord:
        """Record a status transition on an existing complaint thread."""
        return complaint.transition(
            new_status=new_status,
            officer_id=officer_id,
            new_issue_summary=new_issue_summary,
            at_time=at_time,
        )
