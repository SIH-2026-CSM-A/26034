"""Typed HTTP shapes for manufacturer complaint escalation.

``extra="forbid"`` is the load-bearing part of :class:`ComplaintRaiseRequest`. The officer
who raised a complaint is read from the authenticated principal and never from the body, and
forbidding unknown fields is what turns a request carrying ``raised_by_officer_id`` into a
422 rather than into a field that is silently ignored — the difference between a caller
being told they cannot name the officer and a caller believing they did.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


CLOSING_STATUSES = frozenset({ComplaintStatus.RESOLVED, ComplaintStatus.REJECTED})
"""The transitions that end a thread, and therefore the ones that must say why."""


class ComplaintTransitionRequest(ComplaintSchema):
    """What an officer supplies to move an escalation on: the new state, and their words.

    Carries no officer identity — that is the principal's — and no ``supersedes_id``: the
    row being transitioned is named by the URL, and the new row supersedes exactly that one.
    RAISED is not refused here; the domain's transition table refuses it, with every other
    illegal move, so there is one definition of which moves exist.
    """

    status: ComplaintStatus
    note: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _a_closure_states_its_reason(self) -> "ComplaintTransitionRequest":
        if self.status in CLOSING_STATUSES and (self.note is None or not self.note.strip()):
            raise ValueError(f"a transition to '{self.status.value}' requires a note")
        return self


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
    note: str | None = None


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
        note=record.note,
    )
