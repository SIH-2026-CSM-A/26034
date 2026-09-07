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
]
