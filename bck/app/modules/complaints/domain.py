"""Domain models and rules for manufacturer complaint escalation (CMP-001)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final
from uuid import UUID, uuid4

from app.contracts import Verdict, VerdictRecord
from app.core.enums import ReviewAction
from app.core.models import ReviewRow


class ComplaintStatus(StrEnum):
    """Where an escalation had got to when the row carrying it was written."""

    RAISED = "raised"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class InvalidStatusTransitionError(ValueError):
    """Raised when an illegal complaint status transition is attempted."""

    pass


class UnconfirmedVerdictError(ValueError):
    """Raised when creating a complaint without a finalising officer confirmation."""

    pass


VALID_TRANSITIONS: Final[dict[ComplaintStatus, set[ComplaintStatus]]] = {
    ComplaintStatus.RAISED: {
        ComplaintStatus.ACKNOWLEDGED,
        ComplaintStatus.RESOLVED,
        ComplaintStatus.REJECTED,
    },
    ComplaintStatus.ACKNOWLEDGED: {
        ComplaintStatus.RESOLVED,
        ComplaintStatus.REJECTED,
    },
    ComplaintStatus.RESOLVED: set(),
    ComplaintStatus.REJECTED: set(),
}

FINALISING_REVIEW_ACTIONS: Final[set[ReviewAction]] = {
    ReviewAction.CONFIRM,
    ReviewAction.REJECT,
    ReviewAction.OVERRIDE,
}

FORBIDDEN_WORDS: Final[tuple[str, ...]] = (
    "violation confirmed",
    "illegal",
    "non-compliant",
)


def validate_status_transition(
    current_status: ComplaintStatus | None, new_status: ComplaintStatus
) -> None:
    """Validate whether transitioning from current_status to new_status is permitted by law."""
    if current_status is None:
        if new_status != ComplaintStatus.RAISED:
            raise InvalidStatusTransitionError(
                f"Initial complaint status must be RAISED, got '{new_status}'."
            )
        return
    if new_status not in VALID_TRANSITIONS.get(current_status, set()):
        raise InvalidStatusTransitionError(
            f"Illegal status transition from '{current_status.value}' to '{new_status.value}'."
        )


def resolve_effective_verdict_domain(record: VerdictRecord, review_row: ReviewRow) -> Verdict:
    """Resolve effective verdict considering officer review action."""
    if review_row.action not in FINALISING_REVIEW_ACTIONS:
        return record.verdict

    if review_row.action == ReviewAction.OVERRIDE:
        if review_row.overridden_verdict is None:
            raise ValueError("OVERRIDE action requires overridden_verdict")
        return review_row.overridden_verdict

    return record.verdict


@dataclass(frozen=True)
class ConfirmedVerdict:
    """Structural wrapper requiring an officer's finalising review yielding POTENTIAL_VIOLATION."""

    record: VerdictRecord
    review_row: ReviewRow

    def __post_init__(self) -> None:
        if self.review_row is None:
            raise UnconfirmedVerdictError(
                "Complaint creation requires a non-null officer ReviewRow."
            )
        if self.review_row.action not in FINALISING_REVIEW_ACTIONS:
            msg = (
                f"Review action '{self.review_row.action}' is non-finalising; "
                "complaint requires CONFIRM, REJECT, or OVERRIDE."
            )
            raise UnconfirmedVerdictError(msg)

        effective = resolve_effective_verdict_domain(self.record, self.review_row)
        if effective != Verdict.POTENTIAL_VIOLATION:
            msg = (
                f"Effective verdict is '{effective.value}'; "
                "complaint creation requires POTENTIAL_VIOLATION."
            )
            raise UnconfirmedVerdictError(msg)

    @property
    def scan_id(self) -> UUID:
        return self.review_row.scan_id

    @property
    def verdict_id(self) -> UUID:
        return self.review_row.verdict_id


def build_issue_summary(
    rule_id: str,
    field: str,
    measured_value: str,
    required_value: str,
) -> str:
    """Construct external-facing complaint text citing potential violation and rule parameters."""
    summary = (
        f"Potential violation identified under rule '{rule_id}' for declaration field '{field}': "
        f"measured value '{measured_value}' does not meet required value '{required_value}'."
    )
    lower_summary = summary.lower()
    for forbidden in FORBIDDEN_WORDS:
        if forbidden in lower_summary:
            raise ValueError(f"Issue summary contains forbidden legal language: '{forbidden}'")
    return summary


@dataclass(frozen=True)
class ComplaintRecord:
    """Pure domain object representing a complaint event in an append-only thread."""

    id: UUID
    scan_id: UUID
    verdict_id: UUID
    manufacturer_name: str
    issue_summary: str
    status: ComplaintStatus
    raised_by_officer_id: str
    raised_at: datetime
    supersedes_id: UUID | None = None

    def transition(
        self,
        new_status: ComplaintStatus,
        officer_id: str,
        new_issue_summary: str | None = None,
        at_time: datetime | None = None,
    ) -> ComplaintRecord:
        """Create a new ComplaintRecord event representing a status transition."""
        validate_status_transition(self.status, new_status)
        return ComplaintRecord(
            id=uuid4(),
            scan_id=self.scan_id,
            verdict_id=self.verdict_id,
            manufacturer_name=self.manufacturer_name,
            issue_summary=(
                new_issue_summary if new_issue_summary is not None else self.issue_summary
            ),
            status=new_status,
            raised_by_officer_id=officer_id,
            raised_at=at_time or datetime.now(UTC),
            supersedes_id=self.id,
        )
