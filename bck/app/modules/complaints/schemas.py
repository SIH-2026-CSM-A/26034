"""Typed HTTP shapes for manufacturer complaint escalation.

``extra="forbid"`` is the load-bearing part of :class:`ComplaintRaiseRequest`. The officer
who raised a complaint is read from the authenticated principal and never from the body, and
forbidding unknown fields is what turns a request carrying ``raised_by_officer_id`` into a
422 rather than into a field that is silently ignored — the difference between a caller
being told they cannot name the officer and a caller believing they did.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts import DeclarationField
from app.modules.complaints.domain import ComplaintRecord, ComplaintStatus


class ComplaintSchema(BaseModel):
    """Base schema that rejects fields outside the complaint API contract."""

    model_config = ConfigDict(extra="forbid")


class ComplaintRaiseRequest(ComplaintSchema):
    """What an officer supplies to open an escalation against a manufacturer.

    Carries no officer identity and no status: the first is the principal's, and the second
    is RAISED by construction — ``ComplaintService.raise_complaint`` is the only way a first
    row is written, and it names the status itself.
    """

    scan_id: UUID
    manufacturer_name: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    field: DeclarationField
    measured_value: str = Field(min_length=1)
    required_value: str = Field(min_length=1)


class ComplaintResponse(ComplaintSchema):
    """One complaint row, which is one event in an append-only thread.

    ``status`` is the state *this row* asserts, not a field that moved, and
    ``supersedes_id`` names the row it replaced where it replaced one. Both rows stay.
    """

    id: UUID
    scan_id: UUID
    verdict_id: UUID
    manufacturer_name: str
    issue_summary: str
    status: ComplaintStatus
    raised_by_officer_id: str
    raised_at: datetime
    supersedes_id: UUID | None = None


class ComplaintThread(ComplaintSchema):
    """One complaint and the escalation history recorded against its scan, oldest first."""

    complaint: ComplaintResponse
    history: list[ComplaintResponse]


def complaint_response(record: ComplaintRecord) -> ComplaintResponse:
    """One domain record as the shape the routes return."""
    return ComplaintResponse(
        id=record.id,
        scan_id=record.scan_id,
        verdict_id=record.verdict_id,
        manufacturer_name=record.manufacturer_name,
        issue_summary=record.issue_summary,
        status=record.status,
        raised_by_officer_id=record.raised_by_officer_id,
        raised_at=record.raised_at,
        supersedes_id=record.supersedes_id,
    )
