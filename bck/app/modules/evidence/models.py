from pydantic import BaseModel, ConfigDict

from app.contracts.enums import FieldState, Verdict

# BSA §63(4) Part A compliant report schema
# Certifies electronic record authenticity for Legal Metrology evidence.

NO_EVIDENCE_HASH_SUPPLIED = (
    "Not recorded: this export was produced without an evidence chain, so no asset "
    "digest could be read."
)
"""Printed when neither a digest nor a reason for its absence reached the model. It is a
statement about this export, not about the scan, and it is deliberately not the wording
:func:`app.modules.evidence.service.asset_digest` produces — the two absences have
different causes and a reader must be able to tell them apart."""


class ExportDeclaration(BaseModel):
    """One declaration field, with every state its rules reached.

    One row per declaration, not one per finding. A field is usually governed by several
    rules — the Rule 6 declaration itself, then height, width, placement, free space and
    contrast — and emitting a row each repeated the field name up to nine times with the
    declared value blank on all but one of them.

    ``state_counts`` counts rather than collapses. There is no single state for a field
    whose declaration was read and whose letter height could not be measured, and any
    scalar chosen here would have to merge INSUFFICIENT_EVIDENCE into PASS or into FAIL.
    The per-rule states stay in the Rule Evaluation Checklist, one row per finding.
    """

    model_config = ConfigDict(frozen=True)

    field_name: str
    declared_value: str | None
    """What the declaration says, from the rule that requires the declaration itself —
    never from a rule that measured something about it. A letter height in millimetres and
    a set of stroke widths are observations about the declaration, not the declaration."""
    state_counts: dict[FieldState, int]
    ocr_provider: str
    rules_applied: int

    @property
    def outcomes_line(self) -> str:
        """The states this declaration's rules reached, counted, never merged.

        On the model rather than in a renderer, for the reason this model exists: the PDF
        and the DOCX must not be able to describe the same declaration differently.
        """
        return ", ".join(f"{n} {state.value}" for state, n in self.state_counts.items())


class ExportRuleEvaluation(BaseModel):
    """Normalized rule evaluation for export (PDF/DOCX). One per finding."""

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
    evidence_hash: str | None = None
    """The SHA-256 the evidence chain holds for a captured asset, where it holds one."""
    evidence_hash_note: str | None = None
    """Why there is no digest, where there is none. Set exactly when ``evidence_hash`` is
    ``None`` and the caller knew the reason."""
    source_image_path: str | None
    confirmed_by: str
    confirmed_at: str
    officer_action: str
    officer_notes: str | None = None
    overall_verdict: Verdict
    extracted_declarations: list[ExportDeclaration]
    rule_evaluations: list[ExportRuleEvaluation]

    @property
    def evidence_hash_line(self) -> str:
        """What goes on the certificate beside "Evidence Hash", digest or explanation.

        Both renderers read this one property. Deciding it in each of them is how the PDF
        and the DOCX come to say different things about the same record.
        """
        return self.evidence_hash or self.evidence_hash_note or NO_EVIDENCE_HASH_SUPPLIED
