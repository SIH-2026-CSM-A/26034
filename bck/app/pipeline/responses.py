"""Stored rows and pipeline records into the shapes the scan routes return.

Assembly only. Nothing here queries, decides or validates — it turns what the repository
and the orchestrator produced into a DTO, so the routes stay about HTTP and transactions
and this stays about presentation.

The round-trip through :meth:`~pydantic.BaseModel.model_validate` in
:func:`finding_from_row` is the load-bearing part. Findings are written with
``model_dump(mode="json")`` and must come back the same way: a ``Decimal`` tolerance that
returned as a float would corrupt the comparison that decided the finding, and it would do
it silently, long after the officer acted on the result.
"""

from collections.abc import Sequence

from app.contracts import (
    CategoryProposal,
    FieldFinding,
    RuleParameterSnapshot,
    VerdictRecord,
)
from app.core import FieldFindingRow, Scan, VerdictRow
from app.pipeline.capture import QualityRejection
from app.pipeline.schemas import ScanDetail, ScanSummary


def finding_from_row(row: FieldFindingRow) -> FieldFinding:
    """One stored finding back into the contract type, rule snapshot and all."""
    return FieldFinding(
        field=row.field,
        state=row.state,
        rule_snapshot=RuleParameterSnapshot.model_validate(row.rule_snapshot),
        observed_value=row.observed_value,
        expected_value=row.expected_value,
        reason=row.reason,
        evidence_span_ids=tuple(row.evidence_span_ids),
    )


def scan_detail(
    scan: Scan,
    record: VerdictRecord | None,
    *,
    finalised: bool,
    quality: QualityRejection | None = None,
    category_proposal: CategoryProposal | None = None,
) -> ScanDetail:
    """The response for a freshly submitted scan, verdict or capture instruction.

    ``category_proposal`` is passed through untouched and is not consulted for anything
    else on the way — in particular it never becomes ``product_category``, which is read
    off the stored scan row and is the officer's own answer.
    """
    return ScanDetail(
        id=scan.id,
        source_type=scan.source_type,
        status=scan.status,
        verdict=None if record is None else record.verdict,
        product_category=scan.product_category,
        officer_id=scan.officer_id,
        created_at=scan.created_at,
        rule_set_version=scan.rule_set_version,
        finalised=finalised,
        subject_ref=None if record is None else record.subject_ref,
        evaluated_at=None if record is None else record.evaluated_at,
        findings=() if record is None else record.findings,
        quality=quality,
        category_proposal=category_proposal,
    )


def scan_summary(scan: Scan, *, verdict: VerdictRow | None, finalised: bool) -> ScanSummary:
    """One scan as a list row. No findings — those belong on the detail route."""
    return ScanSummary(
        id=scan.id,
        source_type=scan.source_type,
        status=scan.status,
        verdict=None if verdict is None else verdict.verdict,
        product_category=scan.product_category,
        officer_id=scan.officer_id,
        created_at=scan.created_at,
        rule_set_version=scan.rule_set_version,
        finalised=finalised,
    )


def stored_detail(
    scan: Scan,
    *,
    verdict: VerdictRow | None,
    findings: Sequence[FieldFindingRow],
    finalised: bool,
) -> ScanDetail:
    """A scan read back from storage, with the findings behind its latest verdict.

    A scan with no verdict row is not an error and not an empty verdict: the quality gate
    refused the capture, or evaluation has not finished. ``verdict`` is ``None`` and there
    are no findings, which says exactly that and nothing about the package.
    """
    return ScanDetail(
        **scan_summary(scan, verdict=verdict, finalised=finalised).model_dump(),
        subject_ref=None if verdict is None else verdict.subject_ref,
        evaluated_at=None if verdict is None else verdict.evaluated_at,
        findings=tuple(finding_from_row(row) for row in findings),
    )
