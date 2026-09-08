from datetime import UTC, datetime
from io import BytesIO

from app.contracts.records import VerdictRecord
from app.core.enums import ReviewAction
from app.core.models import ReviewRow

from .docx_renderer import render_to_docx
from .models import (
    ExportDeclaration,
    ExportRuleEvaluation,
    OfficerReportModel,
)
from .pdf_renderer import render_to_pdf
from .report import UnconfirmedVerdictExportError

FINALISING_ACTIONS = frozenset(
    {
        ReviewAction.CONFIRM,
        ReviewAction.REJECT,
        ReviewAction.OVERRIDE,
    }
)


def build_report_model(
    record: VerdictRecord,
    review_row: ReviewRow | None = None,
    image_path: str | None = None,
) -> OfficerReportModel:
    """Transforms raw VerdictRecord and ReviewRow into normalized OfficerReportModel."""
    if review_row is None or review_row.action not in FINALISING_ACTIONS:
        raise UnconfirmedVerdictExportError(
            "Export forbidden: Verdict record has not been finalized by an officer."
        )

    confirmed_at = (
        review_row.created_at.isoformat()
        if hasattr(review_row.created_at, "isoformat")
        else str(review_row.created_at)
    )
    officer_action = (
        review_row.action.value if hasattr(review_row.action, "value") else str(review_row.action)
    )

    extracted_declarations = []
    rule_evaluations = []

    for f in record.findings:
        field_str = f.field.value if hasattr(f.field, "value") else str(f.field)
        provider_obj = record.field_providers.get(f.field) if record.field_providers else None
        provider_name = (
            provider_obj.name
            if hasattr(provider_obj, "name")
            else (str(provider_obj) if provider_obj else "PaddleOCR")
        )

        extracted_declarations.append(
            ExportDeclaration(
                field_name=field_str,
                declared_value=f.observed_value,
                state=f.state,
                ocr_provider=provider_name,
                confidence=1.0,
            )
        )

        rule_evaluations.append(
            ExportRuleEvaluation(
                rule_id=f.rule_snapshot.rule_id,
                clause_reference=f.rule_snapshot.clause_ref,
                parameter_name=field_str,
                required_value=f.expected_value,
                measured_value=f.observed_value,
                state=f.state,
                notes=f.reason,
            )
        )

    return OfficerReportModel(
        report_id=record.subject_ref,
        generated_at=datetime.now(UTC).isoformat(),
        rule_set_version=record.rule_set_version,
        evidence_hash=record.subject_ref,
        source_image_path=image_path,
        confirmed_by=review_row.officer_id,
        confirmed_at=confirmed_at,
        officer_action=officer_action,
        officer_notes=review_row.note,
        overall_verdict=record.verdict,
        extracted_declarations=extracted_declarations,
        rule_evaluations=rule_evaluations,
    )


def export_compliance_report(
    record: VerdictRecord,
    review_row: ReviewRow | None = None,
    format: str = "pdf",
    image_path: str | None = None,
) -> bytes:
    """Entrypoint to export a confirmed verdict record to PDF or DOCX."""
    report_model = build_report_model(record, review_row=review_row, image_path=image_path)

    if format.lower() == "pdf":
        return render_to_pdf(report_model, BytesIO())
    elif format.lower() == "docx":
        return render_to_docx(report_model, BytesIO())
    else:
        raise ValueError(f"Unsupported export format: {format}")
