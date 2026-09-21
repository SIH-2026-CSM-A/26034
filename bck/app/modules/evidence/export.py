from collections import Counter
from datetime import UTC, datetime
from io import BytesIO

from app.contracts.enums import DeclarationField, FieldState
from app.contracts.records import FieldFinding, VerdictRecord
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

DECLARATION_CONDITION_KIND = "declaration_required"
"""The condition kind of a rule that requires a declaration to be present.

Read from the finding's own ``rule_snapshot``, which carries the rule by value, so this
cannot drift when the rule set is amended — the snapshot holds the kind the rule had when
the finding was made. It is the one kind under which ``observed_value`` is the declaration
as read off the package; under every other kind it is a measurement *about* the
declaration (a letter height, a set of stroke widths, a bounding box, a contrast ratio),
and printing one of those under "Declared value" would misdescribe the label.

Rules are held to one condition kind each, so this names exactly the declaration rules and
does not have to be widened when a rule is added.
"""


def _is_declaration_rule(finding: FieldFinding) -> bool:
    """Whether this finding came from the rule that requires the declaration itself."""
    conditions = finding.rule_snapshot.parameters.get("conditions")
    if not isinstance(conditions, dict):
        return False
    return conditions.get("kind") == DECLARATION_CONDITION_KIND


def _declared_value(findings: list[FieldFinding]) -> str | None:
    """What the label says for this declaration, or ``None`` where it was not read.

    ``None`` rather than a fallback to any observed value the field happens to carry: a
    field whose declaration could not be read may still have been measured, and reporting
    that measurement as the declared value would put a number on the certificate that the
    package does not bear.
    """
    for finding in findings:
        if _is_declaration_rule(finding) and finding.observed_value is not None:
            return finding.observed_value
    return None


def build_report_model(
    record: VerdictRecord,
    review_row: ReviewRow | None = None,
    image_path: str | None = None,
    evidence_hash: str | None = None,
    evidence_hash_note: str | None = None,
) -> OfficerReportModel:
    """Transforms raw VerdictRecord and ReviewRow into normalized OfficerReportModel.

    ``evidence_hash`` and ``evidence_hash_note`` come from the evidence chain, which this
    module does not read — the digest is a fact about the chain and the chain is the
    service layer's. Exactly one of the two is expected; both absent is reported as such
    on the document rather than silently.
    """
    if review_row is None or review_row.action not in FINALISING_ACTIONS:
        raise UnconfirmedVerdictExportError(
            "Export forbidden: Verdict record has not been finalized by an officer."
        )

    confirmed_at = review_row.created_at.isoformat()
    officer_action = review_row.action.value

    # Grouped in the order the fields first appear in the record, so the document follows
    # the same sequence as the screen rather than an alphabetisation of its own.
    by_field: dict[DeclarationField, list[FieldFinding]] = {}
    for f in record.findings:
        by_field.setdefault(f.field, []).append(f)

    extracted_declarations = [
        ExportDeclaration(
            field_name=field.value,
            declared_value=_declared_value(findings),
            state_counts=_ordered_counts(findings),
            ocr_provider=(
                record.field_providers[field].value
                if record.field_providers and field in record.field_providers
                else "Unspecified"
            ),
            rules_applied=len(findings),
        )
        for field, findings in by_field.items()
    ]

    rule_evaluations = [
        ExportRuleEvaluation(
            rule_id=f.rule_snapshot.rule_id,
            clause_reference=f.rule_snapshot.clause_ref,
            parameter_name=f.field.value,
            required_value=f.expected_value,
            measured_value=f.observed_value,
            state=f.state,
            notes=f.reason,
        )
        for f in record.findings
    ]

    return OfficerReportModel(
        report_id=record.subject_ref,
        generated_at=datetime.now(UTC).isoformat(),
        rule_set_version=record.rule_set_version,
        evidence_hash=evidence_hash,
        evidence_hash_note=evidence_hash_note,
        source_image_path=image_path,
        confirmed_by=review_row.officer_id,
        confirmed_at=confirmed_at,
        officer_action=officer_action,
        officer_notes=review_row.note,
        overall_verdict=record.verdict,
        extracted_declarations=extracted_declarations,
        rule_evaluations=rule_evaluations,
    )


def _ordered_counts(findings: list[FieldFinding]) -> dict[FieldState, int]:
    """How many of this field's rules reached each state, in the enum's own order.

    Enum order rather than descending count, so PASS and FAIL never land adjacent to
    INSUFFICIENT_EVIDENCE by accident of arithmetic, and so two reports of the same field
    list their states in the same sequence.
    """
    counted = Counter(f.state for f in findings)
    return {state: counted[state] for state in FieldState if counted[state]}


def export_compliance_report(
    record: VerdictRecord,
    review_row: ReviewRow | None = None,
    format: str = "pdf",
    image_path: str | None = None,
    evidence_hash: str | None = None,
    evidence_hash_note: str | None = None,
) -> bytes:
    """Entrypoint to export a confirmed verdict record to PDF or DOCX."""
    report_model = build_report_model(
        record,
        review_row=review_row,
        image_path=image_path,
        evidence_hash=evidence_hash,
        evidence_hash_note=evidence_hash_note,
    )

    if format.lower() == "pdf":
        return render_to_pdf(report_model, BytesIO())
    elif format.lower() == "docx":
        return render_to_docx(report_model, BytesIO())
    else:
        raise ValueError(f"Unsupported export format: {format}")
