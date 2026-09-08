from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import OfficerReportModel


def _build_title_section(elements: list, report: OfficerReportModel, styles: dict):
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], alignment=TA_CENTER)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9)
    elements.append(Paragraph("Compliance Evidence Report", title_style))
    elements.append(
        Paragraph(
            f"Report ID: {report.report_id}<br/>Generated: {report.generated_at}<br/>"
            f"Rule Set: {report.rule_set_version}<br/>"
            f"Evidence Hash: {report.evidence_hash or 'Not available'}",
            meta_style,
        )
    )
    elements.append(Spacer(1, 12))


def _build_confirmation_section(elements: list, report: OfficerReportModel, styles: dict):
    sec_style = ParagraphStyle("Sec", parent=styles["Heading2"], spaceBefore=12)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9)
    elements.append(Paragraph("Officer Confirmation", sec_style))
    elements.append(
        Paragraph(
            f"Confirmed by: {report.confirmed_by}<br/>Confirmed at: {report.confirmed_at}<br/>"
            f"Action: {report.officer_action}<br/>Notes: {report.officer_notes or 'None'}",
            meta_style,
        )
    )
    elements.append(Spacer(1, 12))


def _build_verdict_section(elements: list, report: OfficerReportModel, styles: dict):
    sec_style = ParagraphStyle("Sec", parent=styles["Heading2"], spaceBefore=12)
    verdict_style = ParagraphStyle(
        "Vrd", parent=styles["Normal"], alignment=TA_CENTER, fontSize=14, textColor=colors.darkblue
    )
    elements.append(Paragraph("Overall Status", sec_style))
    elements.append(Paragraph(f"<b>{report.overall_verdict}</b>", verdict_style))
    elements.append(Spacer(1, 12))


def _build_declarations_section(elements: list, report: OfficerReportModel, styles: dict):
    sec_style = ParagraphStyle("Sec", parent=styles["Heading2"], spaceBefore=12)
    elements.append(Paragraph("Extracted Declarations", sec_style))
    decl_data = [["Field", "Value", "State", "Provider", "Conf"]]
    for d in report.extracted_declarations:
        decl_data.append(
            [
                d.field_name,
                d.declared_value or "N/A",
                d.state,
                d.ocr_provider,
                f"{d.confidence:.2f}" if d.confidence is not None else "N/A",
            ]
        )
    t_decl = Table(decl_data, hAlign="LEFT")
    t_decl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(t_decl)
    elements.append(Spacer(1, 12))


def _build_rules_section(elements: list, report: OfficerReportModel, styles: dict):
    sec_style = ParagraphStyle("Sec", parent=styles["Heading2"], spaceBefore=12)
    elements.append(Paragraph("Rule Evaluation Checklist", sec_style))
    rule_data = [["Rule ID", "Clause", "Parameter", "Required", "Measured", "Status", "Notes"]]
    for r in report.rule_evaluations:
        measured = r.measured_value
        if measured is None and r.state == "INSUFFICIENT_EVIDENCE":
            measured = "Measurement declined"
        elif measured is None:
            measured = "N/A"

        rule_data.append(
            [
                r.rule_id,
                r.clause_reference,
                r.parameter_name,
                r.required_value or "N/A",
                measured,
                r.state,
                r.notes or "",
            ]
        )
    t_rule = Table(rule_data, hAlign="LEFT")
    t_rule.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(t_rule)
    elements.append(Spacer(1, 12))


def render_to_pdf(report: OfficerReportModel, output_stream: BinaryIO | Path) -> bytes:
    """Renders the normalized OfficerReportModel to a professional PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    styles = getSampleStyleSheet()
    elements = []

    _build_title_section(elements, report, styles)
    _build_confirmation_section(elements, report, styles)
    _build_verdict_section(elements, report, styles)
    _build_declarations_section(elements, report, styles)
    _build_rules_section(elements, report, styles)

    sec_style = ParagraphStyle("Sec", parent=styles["Heading2"], spaceBefore=12)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9)
    elements.append(Paragraph("Source Evidence", sec_style))
    elements.append(Paragraph(f"Image Path: {report.source_image_path or 'N/A'}", meta_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    if isinstance(output_stream, Path):
        output_stream.write_bytes(pdf_bytes)
    return pdf_bytes
