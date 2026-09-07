"""What the verdict derivation promises, one branch at a time.

The assertion this file exists for is the one in
:func:`test_insufficient_evidence_without_a_fail_is_review`: evidence we could not obtain
must never be reported as a package that falls short. Every other test here is guarding
the boundaries around it.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.contracts import (
    DeclarationField,
    EvidenceProvider,
    FieldFinding,
    FieldState,
    RuleParameterSnapshot,
    RuleSeverity,
    RuleStatus,
    Verdict,
)
from app.pipeline.verdict import assemble_verdict, derive_verdict

EVALUATED_AT = datetime(2026, 9, 6, 11, 15, tzinfo=UTC)
RULE_SET_VERSION = "2026.09.1"

SNAPSHOT = RuleParameterSnapshot(
    rule_id="R6-1-C",
    clause_ref="Rule 6(1)(c)",
    gazette_ref="LMPC-2011__amended-to-2021-10-31__maharashtra-compilation.pdf",
    source_text="The net quantity, in terms of the standard unit of weight or measure.",
    status=RuleStatus.VERIFIED,
    severity=RuleSeverity.MANDATORY,
    rule_set_version=RULE_SET_VERSION,
    parameters={},
    rounding_increment=None,
    tolerance=None,
    tolerance_basis=None,
)


def finding(
    state: FieldState, field: DeclarationField = DeclarationField.NET_QUANTITY
) -> FieldFinding:
    """A finding in ``state``. Only the state and field matter to the derivation."""
    return FieldFinding(
        field=field,
        state=state,
        rule_snapshot=SNAPSHOT,
        reason=f"synthetic finding in state {state.value}",
    )


# --- the three verdict branches -------------------------------------------------------


def test_any_fail_is_a_potential_violation() -> None:
    findings = (finding(FieldState.PASS), finding(FieldState.FAIL, DeclarationField.DIMENSIONS))
    assert derive_verdict(findings) is Verdict.POTENTIAL_VIOLATION


def test_review_required_without_a_fail_is_review() -> None:
    findings = (
        finding(FieldState.PASS),
        finding(FieldState.REVIEW_REQUIRED, DeclarationField.DIMENSIONS),
    )
    assert derive_verdict(findings) is Verdict.REVIEW


def test_all_pass_is_pass() -> None:
    findings = (finding(FieldState.PASS), finding(FieldState.PASS, DeclarationField.DIMENSIONS))
    assert derive_verdict(findings) is Verdict.PASS


# --- the distinction the five-state vocabulary exists for ------------------------------


def test_insufficient_evidence_without_a_fail_is_review() -> None:
    """ "We could not read it" is not "it is not there".

    A glared panel routes to an officer. It does not become a POTENTIAL_VIOLATION against
    a manufacturer on the strength of a photograph nobody could read.
    """
    findings = (
        finding(FieldState.PASS),
        finding(FieldState.INSUFFICIENT_EVIDENCE, DeclarationField.RETAIL_SALE_PRICE),
    )
    assert derive_verdict(findings) is Verdict.REVIEW
    assert derive_verdict(findings) is not Verdict.POTENTIAL_VIOLATION


def test_insufficient_evidence_alone_is_review() -> None:
    """With nothing else in the set, an unreadable field is still only a review."""
    assert derive_verdict((finding(FieldState.INSUFFICIENT_EVIDENCE),)) is Verdict.REVIEW


def test_a_fail_alongside_insufficient_evidence_still_reports_the_fail() -> None:
    """Precedence, not merging.

    The two states are never grouped, and keeping them apart must not cost the FAIL: a
    legible shortfall on one field is not softened by a second field being unreadable.
    """
    findings = (
        finding(FieldState.FAIL),
        finding(FieldState.INSUFFICIENT_EVIDENCE, DeclarationField.RETAIL_SALE_PRICE),
    )
    assert derive_verdict(findings) is Verdict.POTENTIAL_VIOLATION


# --- carve-outs and the empty case ------------------------------------------------------


def test_not_applicable_alongside_pass_is_pass() -> None:
    """A statutory carve-out removes the obligation. That is not a defect to review."""
    findings = (
        finding(FieldState.PASS),
        finding(FieldState.NOT_APPLICABLE, DeclarationField.MANUFACTURE_DATE),
    )
    assert derive_verdict(findings) is Verdict.PASS


def test_every_finding_not_applicable_is_review_and_never_pass() -> None:
    """Nothing was evaluated, so nothing may be asserted — the empty case in another form.

    Renamed and inverted by RUL-005. It previously asserted PASS, which was correct while
    the only source of NOT_APPLICABLE was a sector override: those carve out some
    obligations and leave the rest, so an all-NOT_APPLICABLE set was unreachable. Rule 3
    reaches it — a package outside Chapter II owes nothing in the store — and PASS on a
    package this system did not evaluate is the same error
    :func:`test_no_findings_is_review_and_never_pass` already guards against.

    Still not a merge: NOT_APPLICABLE keeps falling through when anything else is present,
    which :func:`test_not_applicable_alongside_pass_is_pass` pins.
    """
    assert derive_verdict((finding(FieldState.NOT_APPLICABLE),)) is Verdict.REVIEW
    assert derive_verdict((finding(FieldState.NOT_APPLICABLE),)) is not Verdict.PASS

    every_field = tuple(
        finding(FieldState.NOT_APPLICABLE, field)
        for field in (
            DeclarationField.NET_QUANTITY,
            DeclarationField.RETAIL_SALE_PRICE,
            DeclarationField.MANUFACTURE_DATE,
        )
    )
    assert derive_verdict(every_field) is Verdict.REVIEW


def test_no_findings_is_review_and_never_pass() -> None:
    """Nothing was examined, so nothing can be asserted about the package."""
    assert derive_verdict(()) is Verdict.REVIEW
    assert derive_verdict(()) is not Verdict.PASS


# --- assembly ---------------------------------------------------------------------------


def test_assembly_records_the_derived_verdict_and_its_evidence() -> None:
    record = assemble_verdict(
        subject_ref="scan-0001",
        findings=(finding(FieldState.FAIL),),
        rule_set_version=RULE_SET_VERSION,
        evaluated_at=EVALUATED_AT,
        field_providers={DeclarationField.NET_QUANTITY: EvidenceProvider.PADDLEOCR},
    )
    assert record.verdict is Verdict.POTENTIAL_VIOLATION
    assert record.subject_ref == "scan-0001"
    assert record.rule_set_version == RULE_SET_VERSION
    assert record.evaluated_at == EVALUATED_AT
    assert record.field_providers[DeclarationField.NET_QUANTITY] is EvidenceProvider.PADDLEOCR
    assert record.findings[0].rule_snapshot.gazette_ref == SNAPSHOT.gazette_ref


def test_assembly_reads_no_clock() -> None:
    """Two assemblies of the same findings are identical, so a replay is reproducible."""
    kwargs = {
        "subject_ref": "scan-0002",
        "findings": (finding(FieldState.PASS),),
        "rule_set_version": RULE_SET_VERSION,
        "evaluated_at": EVALUATED_AT,
    }
    assert assemble_verdict(**kwargs) == assemble_verdict(**kwargs)


def test_assembling_a_record_with_no_findings_is_refused() -> None:
    """The derivation answers REVIEW for an empty set; the record still declines to hold one.

    Both are right. A caller with no findings has an evaluation failure to report, not a
    verdict to store.
    """
    with pytest.raises(ValidationError):
        assemble_verdict(
            subject_ref="scan-0003",
            findings=(),
            rule_set_version=RULE_SET_VERSION,
            evaluated_at=EVALUATED_AT,
        )


def test_a_record_with_no_providers_still_assembles() -> None:
    """A field evaluated with no readable value has no provider entry, which is not an error."""
    record = assemble_verdict(
        subject_ref="scan-0004",
        findings=(finding(FieldState.INSUFFICIENT_EVIDENCE),),
        rule_set_version=RULE_SET_VERSION,
        evaluated_at=EVALUATED_AT,
    )
    assert record.field_providers == {}
    assert record.verdict is Verdict.REVIEW
