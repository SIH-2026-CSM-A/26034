"""Manufacturer complaint domain and service module for legal escalation tracking."""

from app.modules.complaints.domain import (
    ComplaintRecord,
    ComplaintStatus,
    ConfirmedVerdict,
    InvalidStatusTransitionError,
    UnconfirmedVerdictError,
    build_issue_summary,
    validate_status_transition,
)
from app.modules.complaints.repository import (
    add_complaint,
    get_complaint,
    get_complaints_for_scan,
    get_latest_complaint_for_scan,
)
from app.modules.complaints.service import ComplaintService

__all__ = [
    "ComplaintRecord",
    "ComplaintStatus",
    "ConfirmedVerdict",
    "InvalidStatusTransitionError",
    "UnconfirmedVerdictError",
    "build_issue_summary",
    "validate_status_transition",
    "ComplaintService",
    "add_complaint",
    "get_complaint",
    "get_complaints_for_scan",
    "get_latest_complaint_for_scan",
]
