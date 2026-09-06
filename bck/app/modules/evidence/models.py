from typing import Literal

from pydantic import BaseModel, ConfigDict

VerdictState = Literal["PASS", "REVIEW", "POTENTIAL VIOLATION"]
"""Strict possible states for the overall verdict."""


class ExportDeclaration(BaseModel):
    """Normalized declaration for export (PDF/DOCX)."""

    model_config = ConfigDict(frozen=True)

    field_name: str
    declared_value: str | None
    state: str  # e.g. "MATCH", "MISMATCH", "INSUFFICIENT_EVIDENCE"
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
    status: str  # "COMPLIANT", "NON_COMPLIANT", "INSUFFICIENT_EVIDENCE"
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
    overall_verdict: VerdictState
    extracted_declarations: list[ExportDeclaration]
    rule_evaluations: list[ExportRuleEvaluation]
