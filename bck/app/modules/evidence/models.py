from pydantic import BaseModel, ConfigDict

from app.contracts.enums import FieldState, Verdict

# BSA §63(4) Part A compliant report schema
# Certifies electronic record authenticity for Legal Metrology evidence.


class ExportDeclaration(BaseModel):
    """Normalized declaration for export (PDF/DOCX)."""

    model_config = ConfigDict(frozen=True)

    field_name: str
    declared_value: str | None
    state: FieldState
    ocr_provider: str
    confidence: float


class ExportRuleEvaluation(BaseModel):
    """Normalized rule evaluation for export (PDF/DOCX)."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    clause_reference: str
    parameter_name: str
    required_value: str | None
    measured_value: str | None
    state: FieldState
    notes: str | None = None


class OfficerReportModel(BaseModel):
    """
    Shared intermediate model that normalizes report data for all export formats.
    Ensures PDF and DOCX outputs never diverge in content.
    """

    model_config = ConfigDict(frozen=True)

    report_id: str
    generated_at: str
    rule_set_version: str
    evidence_hash: str
    source_image_path: str | None
    confirmed_by: str
    confirmed_at: str
    officer_action: str
    officer_notes: str | None = None
    overall_verdict: Verdict
    extracted_declarations: list[ExportDeclaration]
    rule_evaluations: list[ExportRuleEvaluation]
