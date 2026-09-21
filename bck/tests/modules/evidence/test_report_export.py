import uuid
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import patch

import pdfplumber
import pytest
from docx import Document

from app.contracts.enums import (
    DeclarationField,
    EvidenceAssetType,
    EvidenceProvider,
    FieldState,
    RuleSeverity,
    RuleStatus,
    Verdict,
)
from app.contracts.records import FieldFinding, RuleParameterSnapshot, VerdictRecord
from app.core.enums import ReviewAction
from app.core.models import ReviewRow
from app.modules.evidence.export import (
    UnconfirmedVerdictExportError,
    build_report_model,
    export_compliance_report,
)
from app.modules.evidence.service import asset_digest


def extract_pdf_text(pdf_bytes):
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return "".join((page.extract_text() or "") + "\n" for page in pdf.pages)


def extract_docx_text(docx_bytes):
    doc = Document(BytesIO(docx_bytes))
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text.append(cell.text)
    return "\n".join(text)


def make_finding(
    field: DeclarationField = DeclarationField.NET_QUANTITY,
    state: FieldState = FieldState.PASS,
    clause_ref: str = "Clause 4(1)",
    rule_id: str = "R1",
    observed_value: str | None = "500g",
    expected_value: str | None = ">=500g",
    reason: str = "Weight matches specification",
) -> FieldFinding:
    snapshot = RuleParameterSnapshot(
        rule_id=rule_id,
        clause_ref=clause_ref,
        gazette_ref="G.S.R. 123(E)",
        source_text="Rule source text",
        status=RuleStatus.VERIFIED,
        severity=RuleSeverity.MANDATORY,
        rule_set_version="v1.0",
        parameters={},
        rounding_increment=None,
        tolerance=None,
        tolerance_basis=None,
    )
    return FieldFinding(
        field=field,
        state=state,
        rule_snapshot=snapshot,
        observed_value=observed_value,
        expected_value=expected_value,
        reason=reason,
        evidence_span_ids=["span-1"],
    )


def make_review_row(
    action: ReviewAction = ReviewAction.CONFIRM,
    officer_id: str = "Officer Smith",
    note: str | None = "Looks good",
) -> ReviewRow:
    return ReviewRow(
        id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        verdict_id=uuid.uuid4(),
        action=action,
        officer_id=officer_id,
        note=note,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def confirmed_record():
    finding_1 = make_finding(
        field=DeclarationField.NET_QUANTITY,
        state=FieldState.PASS,
        clause_ref="Clause 4(1)",
        rule_id="R1",
        observed_value="505g",
        expected_value=">=500g",
        reason="Quantity meets requirement",
    )
    finding_2 = make_finding(
        field=DeclarationField.RETAIL_SALE_PRICE,
        state=FieldState.PASS,
        clause_ref="Clause 5(2)",
        rule_id="R2",
        observed_value="2.1mm",
        expected_value=">=2mm",
        reason="Height requirement satisfied",
    )
    return VerdictRecord(
        subject_ref="REP-123",
        verdict=Verdict.PASS,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding_1, finding_2),
        field_providers={
            DeclarationField.NET_QUANTITY: EvidenceProvider.PADDLEOCR,
            DeclarationField.RETAIL_SALE_PRICE: EvidenceProvider.PADDLEOCR,
        },
    )


@pytest.fixture
def review_row():
    return make_review_row()


def test_divergence_pdf_docx(confirmed_record, review_row):
    """AC1: Assert PDF and DOCX content match for the same record."""
    pdf_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="pdf")
    docx_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="docx")

    pdf_text = extract_pdf_text(pdf_bytes).lower()
    docx_text = extract_docx_text(docx_bytes).lower()

    critical_fields = [
        confirmed_record.subject_ref.lower(),
        confirmed_record.rule_set_version.lower(),
        review_row.officer_id.lower(),
        review_row.action.value.lower(),
        confirmed_record.verdict.value.lower(),
        "net_quantity",
        "505g",
        FieldState.PASS.value.lower(),
        "paddleocr",
        "n/a",
        "not recorded",
        "r1",
        "clause 4(1)",
        "r2",
        "clause 5(2)",
        "2.1mm",
    ]

    for field in critical_fields:
        assert field in pdf_text, f"Field '{field}' missing from PDF"
        assert field in docx_text, f"Field '{field}' missing from DOCX"


def test_pass_report_completeness(confirmed_record, review_row):
    """AC2: Assert PASS reports render all rule checks in full detail."""
    pdf_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="pdf")
    pdf_text = extract_pdf_text(pdf_bytes)

    for f in confirmed_record.findings:
        assert f.rule_snapshot.rule_id in pdf_text
        assert f.rule_snapshot.clause_ref in pdf_text
        assert f.field.value in pdf_text
        assert f.state.value in pdf_text


def test_forbidden_vocabulary(review_row):
    """AC3: Assert POTENTIAL_VIOLATION reports avoid banned terms."""
    finding = make_finding(
        field=DeclarationField.NET_QUANTITY,
        state=FieldState.FAIL,
        clause_ref="Clause 4(1)",
        rule_id="R1",
        observed_value="400g",
        expected_value="500g",
        reason="Quantity deficient",
    )
    record = VerdictRecord(
        subject_ref="REP-VIOLATION",
        verdict=Verdict.POTENTIAL_VIOLATION,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding,),
        field_providers={DeclarationField.NET_QUANTITY: EvidenceProvider.PADDLEOCR},
    )

    banned_terms = [
        "violation confirmed",
        "non-compliant",
        "non_compliant",
        "noncompliant",
        "illegal",
        "guilty",
    ]

    for fmt in ["pdf", "docx"]:
        out_bytes = export_compliance_report(record, review_row=review_row, format=fmt)
        if fmt == "pdf":
            text = extract_pdf_text(out_bytes).lower()
        else:
            text = extract_docx_text(out_bytes).lower()
        for term in banned_terms:
            assert term not in text, f"Banned term '{term}' found in {fmt} report"


def test_human_confirmation_gate(confirmed_record):
    """AC4: Assert unconfirmed records raise UnconfirmedVerdictExportError."""
    # 1. No review row at all
    for fmt in ["pdf", "docx"]:
        with pytest.raises(UnconfirmedVerdictExportError):
            export_compliance_report(confirmed_record, review_row=None, format=fmt)

    # 2. Review row with non-finalising action
    unconfirmed_row = ReviewRow(
        id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        verdict_id=uuid.uuid4(),
        action=ReviewAction.ANNOTATE,
        officer_id="Officer Smith",
        created_at=datetime.now(UTC),
    )
    for fmt in ["pdf", "docx"]:
        with pytest.raises(UnconfirmedVerdictExportError):
            export_compliance_report(confirmed_record, review_row=unconfirmed_row, format=fmt)


def test_clause_citation_assertion(confirmed_record, review_row):
    """AC5: Assert 100% of rule check rows contain a non-empty clause_reference."""
    pdf_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="pdf")
    pdf_text = extract_pdf_text(pdf_bytes)

    for f in confirmed_record.findings:
        assert f.rule_snapshot.clause_ref in pdf_text
        assert f.rule_snapshot.clause_ref != "", "Clause reference must not be empty"


def test_measurement_refusal_rendering(review_row):
    """AC: Assert measurement refusal renders as 'Measurement declined' instead of 'N/A'
    and prints no number.
    """
    finding = make_finding(
        field=DeclarationField.RETAIL_SALE_PRICE,
        state=FieldState.INSUFFICIENT_EVIDENCE,
        clause_ref="Clause 5(2)",
        rule_id="R1",
        observed_value=None,
        expected_value=">=2mm",
        reason="Refused measurement due to glare",
    )
    record = VerdictRecord(
        subject_ref="REP-REFUSED",
        verdict=Verdict.REVIEW,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding,),
        field_providers={DeclarationField.RETAIL_SALE_PRICE: EvidenceProvider.PADDLEOCR},
    )

    for fmt in ["pdf", "docx"]:
        out_bytes = export_compliance_report(record, review_row=review_row, format=fmt)
        text = extract_pdf_text(out_bytes) if fmt == "pdf" else extract_docx_text(out_bytes)
        assert "Measurement declined" in text, f"Refusal text missing from {fmt} report"
        status_split = text.split("Status")[0]
        assert "N/A" not in status_split, f"'N/A' found in measured value for {fmt} report"


def test_insufficient_evidence_rendering(review_row):
    """
    AC: Assert INSUFFICIENT_EVIDENCE:
    1. Visibly distinct from FAIL (not containing 'FAIL' in status).
    2. Actual reason/notes appear in both PDF and DOCX.
    3. Reason is not replaced by generic placeholder.
    """
    reason_text = "Image too blurry to determine font size"
    finding = make_finding(
        field=DeclarationField.RETAIL_SALE_PRICE,
        state=FieldState.INSUFFICIENT_EVIDENCE,
        clause_ref="Clause 5(2)",
        rule_id="R1",
        observed_value=None,
        expected_value=">=2mm",
        reason=reason_text,
    )
    record = VerdictRecord(
        subject_ref="REP-INSUFF",
        verdict=Verdict.REVIEW,
        rule_set_version="v1.0",
        evaluated_at=datetime.now(UTC),
        findings=(finding,),
        field_providers={DeclarationField.RETAIL_SALE_PRICE: EvidenceProvider.PADDLEOCR},
    )

    for fmt in ["pdf", "docx"]:
        out_bytes = export_compliance_report(record, review_row=review_row, format=fmt)
        text = extract_pdf_text(out_bytes) if fmt == "pdf" else extract_docx_text(out_bytes)

        # 1. Distinct from FAIL
        assert FieldState.INSUFFICIENT_EVIDENCE.value in text
        assert FieldState.FAIL.value not in text

        # 2. Actual reason appears
        assert reason_text in text, f"Reason '{reason_text}' missing from {fmt} report"


def test_offline_and_zero_stub(confirmed_record, review_row):
    """AC6: Assert clean execution offline and no placeholder text."""
    with patch("socket.socket", side_effect=OSError("Offline")):
        pdf_bytes = export_compliance_report(confirmed_record, review_row=review_row, format="pdf")
        pdf_text = extract_pdf_text(pdf_bytes)
        docx_bytes = export_compliance_report(
            confirmed_record, review_row=review_row, format="docx"
        )
        docx_text = extract_docx_text(docx_bytes)

    placeholders = ["sample text", "placeholder", "lorem ipsum", "[INSERT]", "TBD"]
    for text in [pdf_text, docx_text]:
        text_lower = text.lower()
        for ph in placeholders:
            assert ph.lower() not in text_lower, f"Placeholder '{ph}' found in report"


# ── The document has to fit on the paper ────────────────────────────────────────────
#
# Until this section existed the report rendered every column it was asked for and drew
# most of them outside the media box: on one live scan 2,606 words sat past the right
# edge of A4, among them every Status and every Notes cell. `extract_text` reads those
# words, so a test that only searched the extracted text passed over the defect. These
# tests read the word geometry instead, and the fixture below carries the cell widths a
# real scan produces — an OCR dump under a declaration, a reason running to 380
# characters — because the defect is width-dependent and a two-finding record cannot
# reach it.

MDH_OCR_DUMP = (
    "MDH | Kitchen King | ... 3 | , ,, 3 | Serving per package : 20 | Serving size : | "
    "Per Serve | % RDA* | Energy | 401 | 20.1 | 1.0 | Protein | 12.1 | 0.6 | Carbohydrate "
    "| 55.8 | 2.8 | Total Sugars | 5.2 | 0.3 | Added Sugars | 0 | 0 | 0.0 | Total Fat | "
    "14.3 | 0.7 | 1.0 | Sodium | 62 | 3.1 | 0.2 | Manufactured & Packed by: | Net "
    "Quantity: | MRP | 75.00 | 0.75 | KK2407 | New Delhi - 110 015 | 81906216000418"
)
TABLE_I_REASON = (
    "the measured principal display panel area of 102.3 +/- 10.2 cm2 lies across a Table-I "
    "band edge: 1.5 mm is required below it and 2.5 mm above; the measured character "
    "height of 2.61 +/- 0.13 mm lies across the 2.5 mm requirement: which side of the "
    "requirement this package falls on is not established at the measurement's own "
    "precision."
)
DECLARATION_CONDITIONS = {"conditions": {"kind": "declaration_required", "declarations": []}}
MEASUREMENT_CONDITIONS = {"conditions": {"kind": "table_height"}}


def make_snapshot_finding(
    field: DeclarationField,
    state: FieldState,
    rule_id: str,
    clause_ref: str,
    parameters: dict,
    observed_value: str | None,
    expected_value: str | None,
    reason: str,
) -> FieldFinding:
    return FieldFinding(
        field=field,
        state=state,
        rule_snapshot=RuleParameterSnapshot(
            rule_id=rule_id,
            clause_ref=clause_ref,
            gazette_ref="LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
            source_text="Rule source text",
            status=RuleStatus.VERIFIED,
            severity=RuleSeverity.MANDATORY,
            rule_set_version="2026.09.2",
            parameters=parameters,
            rounding_increment=None,
            tolerance=None,
            tolerance_basis=None,
        ),
        observed_value=observed_value,
        expected_value=expected_value,
        reason=reason,
        evidence_span_ids=(),
    )


@pytest.fixture
def wide_record():
    """A record shaped like a real image scan: many rules per field, long cells.

    Every one of the five field states appears exactly once somewhere in it, so a test can
    ask whether each reached the page.
    """
    findings = [
        make_snapshot_finding(
            DeclarationField.NET_QUANTITY,
            FieldState.REVIEW_REQUIRED,
            "R7-2-TABLE-I",
            "Rule 7(2), Table-I",
            MEASUREMENT_CONDITIONS,
            "2.61 mm",
            "1.5 mm to 2.5 mm",
            TABLE_I_REASON,
        ),
        make_snapshot_finding(
            DeclarationField.NET_QUANTITY,
            FieldState.REVIEW_REQUIRED,
            "R6-1-C",
            "Rule 6(1)(c)",
            DECLARATION_CONDITIONS,
            "100 g",
            None,
            "the declaration is present and was read from the package. An officer should "
            "examine this declaration: a second OCR pass over the same print read '1g' "
            "where the first read '100g', and the figures in them do not agree.",
        ),
        make_snapshot_finding(
            DeclarationField.NET_QUANTITY,
            FieldState.PASS,
            "R7-3-WIDTH-RATIO",
            "Rule 7(3)",
            MEASUREMENT_CONDITIONS,
            "1=0.44, 0=0.72, 0=0.72, g=0.61",
            "width at least 0.33 of height, except 1, i, I, l",
            "every character in the declaration meets the width ratio.",
        ),
        make_snapshot_finding(
            DeclarationField.NET_QUANTITY,
            FieldState.NOT_APPLICABLE,
            "R6-10A-GSR-128E",
            "Rule 6(10A)",
            {"conditions": {"kind": "ecommerce_country_of_origin_filter"}},
            None,
            None,
            "this obligation is owed by an e-commerce entity about a product listing. A "
            "physical package scan is not a listing, so the duty does not arise.",
        ),
        make_snapshot_finding(
            DeclarationField.COMMON_OR_GENERIC_NAME,
            FieldState.PASS,
            "R6-1-B",
            "Rule 6(1)(b)",
            DECLARATION_CONDITIONS,
            MDH_OCR_DUMP,
            None,
            "the declaration is present and was read from the package.",
        ),
        make_snapshot_finding(
            DeclarationField.MANUFACTURE_DATE,
            FieldState.INSUFFICIENT_EVIDENCE,
            "R6-1-D",
            "Rule 6(1)(d)",
            DECLARATION_CONDITIONS,
            None,
            None,
            "text on the panel was bound to this declaration 2 times and the values do not "
            "agree: 2024-07-15 | 2026-07-14. A package bears one such date, so all but one "
            "of these is something else and the reading cannot say which.",
        ),
        make_snapshot_finding(
            DeclarationField.RETAIL_SALE_PRICE,
            FieldState.FAIL,
            "R6-1-E",
            "Rule 6(1)(e)",
            DECLARATION_CONDITIONS,
            None,
            "declaration present",
            "the retail sale price is not declared on this listing.",
        ),
    ]
    return VerdictRecord(
        subject_ref="91893092-1809-48a1-9df6-c4647f0fd6cd",
        verdict=Verdict.POTENTIAL_VIOLATION,
        rule_set_version="2026.09.2",
        evaluated_at=datetime.now(UTC),
        findings=tuple(findings),
        field_providers={
            DeclarationField.NET_QUANTITY: EvidenceProvider.PADDLEOCR,
            DeclarationField.COMMON_OR_GENERIC_NAME: EvidenceProvider.PADDLEOCR,
        },
    )


def words_outside_the_page(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Every word reportlab drew past the right or bottom edge of its page."""
    stray = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            for word in page.extract_words():
                if word["x1"] > page.width + 1 or word["bottom"] > page.height + 1:
                    stray.append((number, word["text"]))
    return stray


def on_page_text(pdf_bytes: bytes) -> str:
    """Only the words that landed inside the media box — what a reader can actually see."""
    lines = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            lines.extend(w["text"] for w in page.extract_words() if w["x1"] <= page.width + 1)
    return " ".join(lines)


def test_no_word_is_drawn_outside_the_page(wide_record, review_row):
    """Every cell the report renders lands on the paper.

    reportlab does not clip a table to its frame. Sized to its content, a seven-column
    checklist carrying a 380-character reason grew to twelve times the width of A4 and the
    columns past 'Required' were drawn off the media box.
    """
    pdf_bytes = export_compliance_report(wide_record, review_row=review_row, format="pdf")
    stray = words_outside_the_page(pdf_bytes)
    assert stray == [], f"{len(stray)} words drawn off the page, first: {stray[:6]}"


CHECKLIST_HEADER = ["Rule ID", "Clause", "Parameter", "Required", "Measured", "Status", "Notes"]


def checklist_rows(pdf_bytes: bytes) -> list[dict[str, str]]:
    """Every data row of the Rule Evaluation Checklist, read out of the ruled table.

    Read structurally, by column, rather than by searching the page text: a state that
    appears somewhere on the paper is not the same as a state in the Status cell of its
    own rule's row, and only the second is what an officer reads off the checklist.
    """
    rows: list[dict[str, str]] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                flat = [(c or "").replace("\n", "") for c in table[0]]
                if flat != CHECKLIST_HEADER:
                    continue
                for row in table[1:]:
                    cells = [(c or "").replace("\n", "") for c in row]
                    rows.append(dict(zip(CHECKLIST_HEADER, cells, strict=False)))
    return rows


def test_the_checklist_carries_a_status_for_every_finding(wide_record, review_row):
    """One checklist row per finding, in order, each with its clause and its own state."""
    pdf_bytes = export_compliance_report(wide_record, review_row=review_row, format="pdf")
    rows = checklist_rows(pdf_bytes)
    assert len(rows) == len(wide_record.findings)
    for row, finding in zip(rows, wide_record.findings, strict=True):
        assert row["Rule ID"] == finding.rule_snapshot.rule_id
        assert row["Clause"] == finding.rule_snapshot.clause_ref
        assert row["Status"] == finding.state.value


def test_every_field_state_appears_in_the_checklist_status_column(wide_record, review_row):
    """All five states are readable in the Status column, including on the second page.

    INSUFFICIENT_EVIDENCE and FAIL are both in this set on purpose: the checklist is where
    the two stay apart, and a document that prints one and not the other collapses them.
    """
    pdf_bytes = export_compliance_report(wide_record, review_row=review_row, format="pdf")
    statuses = {row["Status"] for row in checklist_rows(pdf_bytes)}
    assert statuses == {state.value for state in FieldState}


def test_one_declaration_row_per_field(wide_record, review_row):
    """The declarations table names each field once, however many rules governed it."""
    model = build_report_model(wide_record, review_row=review_row)
    names = [d.field_name for d in model.extracted_declarations]
    assert names == sorted(set(names), key=names.index), f"a field repeats: {names}"
    assert len(names) == len({f.field for f in wide_record.findings})
    net_quantity = next(d for d in model.extracted_declarations if d.field_name == "NET_QUANTITY")
    assert net_quantity.rules_applied == 4


def test_a_field_s_states_are_counted_not_collapsed(wide_record, review_row):
    """A field governed by rules that disagreed keeps every state it reached."""
    model = build_report_model(wide_record, review_row=review_row)
    net_quantity = next(d for d in model.extracted_declarations if d.field_name == "NET_QUANTITY")
    assert net_quantity.state_counts == {
        FieldState.PASS: 1,
        FieldState.REVIEW_REQUIRED: 2,
        FieldState.NOT_APPLICABLE: 1,
    }
    assert net_quantity.outcomes_line == "1 PASS, 2 REVIEW_REQUIRED, 1 NOT_APPLICABLE"


def test_declared_value_is_the_declaration_never_a_measurement(wide_record, review_row):
    """The declared value comes from the rule requiring the declaration.

    NET_QUANTITY here is governed by Rule 6(1)(c), which read '100 g' off the package, and
    by Rule 7(2) Table-I, which measured a character height of 2.61 mm. Only the first is
    something the package declares.
    """
    model = build_report_model(wide_record, review_row=review_row)
    net_quantity = next(d for d in model.extracted_declarations if d.field_name == "NET_QUANTITY")
    assert net_quantity.declared_value == "100 g"


def test_a_field_read_from_no_declaration_rule_says_so(wide_record, review_row):
    """A declaration that was never read reports nothing rather than a nearby number."""
    model = build_report_model(wide_record, review_row=review_row)
    date = next(d for d in model.extracted_declarations if d.field_name == "MANUFACTURE_DATE")
    assert date.declared_value is None
    pdf_bytes = export_compliance_report(wide_record, review_row=review_row, format="pdf")
    assert "Not read" in on_page_text(pdf_bytes)


# ── The evidence hash, and why it is sometimes absent ───────────────────────────────


def make_entry(asset_type: EvidenceAssetType, payload: str, sequence: int = 0):
    from app.modules.evidence.chain import append_entry, create_genesis_entry

    timestamp = datetime.now(UTC).isoformat()
    genesis = create_genesis_entry(payload, timestamp, EvidenceAssetType.AUDIT_LOG)
    if sequence == 0:
        return create_genesis_entry(payload, timestamp, asset_type)
    return append_entry(genesis, payload, timestamp, asset_type)


def test_asset_digest_is_the_hash_of_the_asset_entry():
    """Where the chain holds a captured asset, the certificate prints its digest."""
    entry = make_entry(EvidenceAssetType.PRODUCT_IMAGE, "the captured photograph")
    digest, note = asset_digest([entry])
    assert digest == entry.payload_hash
    assert note is None


def test_asset_digest_never_reports_an_audit_log_hash_as_an_asset():
    """An audit-log entry hashes the record about a capture, not the capture.

    Reported as an evidence hash it would be a digest no photograph could be matched to.
    """
    audit_only = [make_entry(EvidenceAssetType.AUDIT_LOG, '{"verdict": {}}')]
    digest, note = asset_digest(audit_only)
    assert digest is None
    assert note is not None
    assert "audit-log" in note
    assert audit_only[0].payload_hash not in (note or "")


def test_the_report_prints_the_reason_there_is_no_digest(wide_record, review_row):
    """The absence is stated in words on the page, not left as a blank label."""
    _, note = asset_digest([make_entry(EvidenceAssetType.AUDIT_LOG, '{"verdict": {}}')])
    pdf_bytes = export_compliance_report(
        wide_record, review_row=review_row, format="pdf", evidence_hash_note=note
    )
    visible = on_page_text(pdf_bytes)
    assert "No captured asset is recorded in this chain" in visible


def test_the_report_prints_the_digest_when_there_is_one(wide_record, review_row):
    digest, _ = asset_digest([make_entry(EvidenceAssetType.PRODUCT_IMAGE, "photograph bytes")])
    pdf_bytes = export_compliance_report(
        wide_record, review_row=review_row, format="pdf", evidence_hash=digest
    )
    assert digest in on_page_text(pdf_bytes)


def test_a_table_wider_than_the_frame_is_refused():
    """Declaring columns that do not fit fails loudly instead of printing off the page."""
    from app.modules.evidence.pdf_renderer import FRAME_WIDTH, _cell_style, _grid

    cell = _cell_style(8)
    too_wide = (int(FRAME_WIDTH), int(FRAME_WIDTH))
    with pytest.raises(ValueError, match="wider than"):
        _grid([_row_of(["a", "b"], cell)], too_wide)


def _row_of(values, style):
    from reportlab.platypus import Paragraph

    return [Paragraph(v, style) for v in values]
