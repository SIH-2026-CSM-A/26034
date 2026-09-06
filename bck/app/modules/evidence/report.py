import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

# BSA §63(4) Part A compliant report schema
# Certifies electronic record authenticity for Legal Metrology evidence.


class UnconfirmedVerdictExportError(Exception):
    """Raised when attempting to generate a report for a verdict that
    hasn't been human-confirmed.
    """

    pass


class FieldDeclaration(BaseModel):
    """Per-field evidence details for a single declaration item."""

    model_config = ConfigDict(frozen=True)

    field_name: str
    declared_value: str | None
    measured_value: str | None
    required_value: str | None
    ocr_provider: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class HumanConfirmation(BaseModel):
    """Officer confirmation details for the report."""

    model_config = ConfigDict(frozen=True)

    confirmed_by: str
    confirmation_timestamp: str  # ISO-8601 UTC
    officer_action: str  # "CONFIRM" or "OVERRIDE"


class EvidenceAuditTrail(BaseModel):
    """Cryptographic audit trail of the evidence chain."""

    model_config = ConfigDict(frozen=True)

    root_entry_hash: str
    latest_entry_hash: str
    total_sequence_count: int


class BSAReport(BaseModel):
    """
    BSA §63(4) Part A compliant Evidence Report.
    Certifies the authenticity and provenance of a packaged commodity scan.
    """

    model_config = ConfigDict(frozen=True)

    # Certificate Metadata
    certificate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    statute_citation: str = "BSA §63(4) Part A"

    # Artifact Details
    source_image_hash: str
    rule_set_version: str

    # Evidence Audit Trail
    audit_trail: EvidenceAuditTrail

    # Field Declarations
    declarations: list[FieldDeclaration]

    # Human Confirmation
    confirmation: HumanConfirmation


def generate_bsa_report(
    source_image_hash: str,
    rule_set_version: str,
    audit_trail: EvidenceAuditTrail,
    declarations: list[FieldDeclaration],
    confirmation: HumanConfirmation | None,
    is_human_confirmed: bool = False,
) -> BSAReport:
    """
    Assembles the final evidence report based on the collected audit trail
    and officer confirmation.

    Enforces the Human Confirmation Gate: reports are NEVER generated for
    unconfirmed verdicts.
    """
    if not is_human_confirmed or confirmation is None:
        raise UnconfirmedVerdictExportError(
            "Evidence report cannot be generated: Verdict has not been human-confirmed."
        )

    return BSAReport(
        source_image_hash=source_image_hash,
        rule_set_version=rule_set_version,
        audit_trail=audit_trail,
        declarations=declarations,
        confirmation=confirmation,
    )
