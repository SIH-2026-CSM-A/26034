from datetime import UTC, datetime
from io import BytesIO

from .docx_renderer import render_to_docx
from .models import (
    ExportDeclaration,
    ExportRuleEvaluation,
    OfficerReportModel,
)
from .pdf_renderer import render_to_pdf
from .report import UnconfirmedVerdictExportError


def build_report_model(verdict_record) -> OfficerReportModel:
    """Transforms raw verdict record into normalized OfficerReportModel."""
    if not getattr(verdict_record, "is_human_confirmed", False):
        raise UnconfirmedVerdictExportError(
            "Export forbidden: Verdict record has not been human-confirmed."
        )

    return OfficerReportModel(
        report_id=getattr(verdict_record, "report_id", "unknown"),
        generated_at=datetime.now(UTC).isoformat(),
        rule_set_version=getattr(verdict_record, "rule_set_version", "unknown"),
        evidence_hash=getattr(verdict_record, "source_image_hash", "unknown"),
        source_image_path=getattr(verdict_record, "image_path", None),
        confirmed_by=verdict_record.confirmation.confirmed_by,
        confirmed_at=verdict_record.confirmation.confirmation_timestamp,
        officer_action=verdict_record.confirmation.officer_action,
        officer_notes=getattr(verdict_record, "officer_notes", None),
        overall_verdict=verdict_record.overall_verdict,
        extracted_declarations=[
            ExportDeclaration(
                field_name=d.field_name,
                declared_value=d.declared_value,
                state=d.state,
                ocr_provider=d.ocr_provider,
                confidence=d.confidence,
            )
            for d in verdict_record.declarations
        ],
        rule_evaluations=[
            ExportRuleEvaluation(
                rule_id=r.rule_id,
                clause_reference=r.clause,
                parameter_name=r.parameter,
                required_value=r.required,
                measured_value=r.measured,
                status=r.status,
                notes=r.notes,
            )
            for r in verdict_record.rule_evaluations
        ],
    )


def export_compliance_report(verdict_record, format: str = "pdf") -> bytes:
    """Entrypoint to export a confirmed verdict record to PDF or DOCX."""
    report_model = build_report_model(verdict_record)

    if format.lower() == "pdf":
        return render_to_pdf(report_model, BytesIO())
    elif format.lower() == "docx":
        return render_to_docx(report_model, BytesIO())
    else:
        raise ValueError(f"Unsupported export format: {format}")
