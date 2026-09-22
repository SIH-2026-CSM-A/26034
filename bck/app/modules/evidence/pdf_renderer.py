"""The officer's compliance report, rendered for filing.

**Why the page is landscape, and why every cell is a Paragraph.** The checklist is seven
columns wide and one of them is the reason a finding reached its state, which runs to
several hundred characters. Cells used to be raw strings, which reportlab measures at
their full unwrapped width: on one live scan the table grew to twelve times the width of
A4 and every column past ``Required`` — including ``Status`` and ``Notes`` — was drawn
outside the media box. The text was in the file and absent from the paper, so
``extract_text`` found it and a reader never could.

The ``Paragraph`` is what fixes that, measured rather than assumed: a table of Paragraphs
sizes its columns from the longest unbreakable word, so it stays on the page even with no
``colWidths`` at all. ``colWidths`` is here for the proportions — left to itself reportlab
gives ``Notes`` whatever its longest word asks for and starves ``Clause`` — and the frame
check in :func:`_grid` is what stops a later edit declaring widths that do not fit.
Landscape is what makes seven readable columns and a wrapped reason fit at all.
"""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import OfficerReportModel

PAGE_SIZE = landscape(A4)
MARGIN = 30
FRAME_WIDTH = PAGE_SIZE[0] - 2 * MARGIN
"""Every table's column widths must sum to this. A table wider than its frame is not
clipped by reportlab; it is drawn off the page and silently lost."""

DECLARATION_COLUMNS = (115, 300, 215, 55, 95)
RULE_COLUMNS = (95, 110, 105, 85, 85, 96, 205)


def _cell_style(font_size: float) -> ParagraphStyle:
    return ParagraphStyle(
        "Cell",
        fontName="Helvetica",
        fontSize=font_size,
        leading=font_size + 1.5,
        # A single unbroken token longer than its column would otherwise overflow it.
        splitLongWords=1,
    )


def _grid(data: list[list], col_widths: tuple[int, ...]) -> Table:
    """A table that fits the frame, repeats its header, and may split across pages."""
    if sum(col_widths) > FRAME_WIDTH:
        # Not cosmetic. reportlab does not clip a table to its frame; it draws the
        # overflowing columns outside the media box, where the text is in the file and
        # absent from the paper. Refusing to render is the only way that stays visible.
        raise ValueError(
            f"columns sum to {sum(col_widths)}pt, wider than the {FRAME_WIDTH}pt frame"
        )
    table = Table(data, colWidths=list(col_widths), hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _row(values: list[str], style: ParagraphStyle) -> list[Paragraph]:
    return [Paragraph(escape(v), style) for v in values]


def _build_title_section(elements: list, report: OfficerReportModel, styles: dict):
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], alignment=TA_CENTER)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9)
    elements.append(Paragraph("Compliance Evidence Report", title_style))
    elements.append(
        Paragraph(
            f"Report ID: {escape(report.report_id)}<br/>"
            f"Generated: {escape(report.generated_at)}<br/>"
            f"Rule Set: {escape(report.rule_set_version)}<br/>"
            f"Evidence Hash: {escape(report.evidence_hash_line)}",
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
            f"Confirmed by: {escape(report.confirmed_by)}<br/>"
            f"Confirmed at: {escape(report.confirmed_at)}<br/>"
            f"Action: {escape(report.officer_action)}<br/>"
            f"Notes: {escape(report.officer_notes or 'None')}",
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
    elements.append(Paragraph(f"<b>{escape(report.overall_verdict)}</b>", verdict_style))
    elements.append(Spacer(1, 12))


def _build_declarations_section(elements: list, report: OfficerReportModel, styles: dict):
    sec_style = ParagraphStyle("Sec", parent=styles["Heading2"], spaceBefore=12)
    elements.append(Paragraph("Extracted Declarations", sec_style))
    cell = _cell_style(8)
    decl_data = [_row(["Field", "Declared value", "Outcomes", "Rules", "Provider"], cell)]
    for d in report.extracted_declarations:
        decl_data.append(
            _row(
                [
                    d.field_name,
                    d.declared_display or "Not read",
                    d.outcomes_line,
                    str(d.rules_applied),
                    d.ocr_provider,
                ],
                cell,
            )
        )
    elements.append(_grid(decl_data, DECLARATION_COLUMNS))
    elements.append(Spacer(1, 12))


def _build_rules_section(elements: list, report: OfficerReportModel, styles: dict):
    sec_style = ParagraphStyle("Sec", parent=styles["Heading2"], spaceBefore=12)
    elements.append(Paragraph("Rule Evaluation Checklist", sec_style))
    cell = _cell_style(7)
    rule_data = [
        _row(
            ["Rule ID", "Clause", "Parameter", "Required", "Measured", "Status", "Notes"],
            cell,
        )
    ]
    for r in report.rule_evaluations:
        measured = r.measured_display
        if measured is None and r.state == "INSUFFICIENT_EVIDENCE":
            measured = "Measurement declined"
        elif measured is None:
            measured = "N/A"

        rule_data.append(
            _row(
                [
                    r.rule_id,
                    r.clause_reference,
                    r.parameter_name,
                    r.required_display or "N/A",
                    measured,
                    r.state,
                    r.notes or "",
                ],
                cell,
            )
        )
    elements.append(_grid(rule_data, RULE_COLUMNS))
    elements.append(Spacer(1, 12))


def render_to_pdf(report: OfficerReportModel, output_stream: BinaryIO | Path) -> bytes:
    """Renders the normalized OfficerReportModel to a professional PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
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
    elements.append(
        Paragraph(f"Image Path: {escape(report.source_image_path or 'N/A')}", meta_style)
    )

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    if isinstance(output_stream, Path):
        output_stream.write_bytes(pdf_bytes)
    return pdf_bytes
