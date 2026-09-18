"""What an officer may take away from an evidence chain: its verification, and a report.

Two things are decided here and nowhere else. A report is produced from the **chain**, not
from the verdict tables: the record it certifies is the one whose bytes were hashed at
evaluation time, read back out of the payload of the genesis entry, so the report cannot
describe a verdict that has drifted from its evidence. And a report is produced only past
a finalising review — CONFIRM, REJECT or OVERRIDE — because the BSA s.63(4) Part A
certificate is a statement a person makes about a record, and no automated path may make
it on their behalf.
"""

import json
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version

from app.contracts import EvidenceAssetType, VerdictRecord
from app.core import get_settings
from app.core.models import ReviewRow, Scan

from .chain import append_entry, compute_sha256, verify_chain
from .domain import ChainVerification, EvidenceEntry
from .export import export_compliance_report
from .report import (
    BSAReport,
    EvidenceAuditTrail,
    FieldDeclaration,
    HumanConfirmation,
    UnconfirmedVerdictExportError,
    generate_bsa_report,
)

REPORT_FORMATS = ("json", "pdf", "docx")
"""``json`` is the BSA s.63(4) Part A certificate itself; the other two are the officer's
compliance report rendered for filing."""


class NoEvidenceError(LookupError):
    """The scan has no evidence chain: it was refused at the gate or never evaluated."""


def verified(entries: list[EvidenceEntry]) -> ChainVerification:
    """Verify a chain as read from storage. A missing chain verifies as ``missing_genesis``."""
    return verify_chain(entries)


def record_from(entries: list[EvidenceEntry]) -> VerdictRecord:
    """The verdict as it was hashed into the genesis entry."""
    if not entries:
        raise NoEvidenceError("this scan has no evidence chain")
    payload = entries[0].payload
    document = json.loads(payload) if isinstance(payload, str) else payload
    return VerdictRecord.model_validate(document["verdict"])


def _model_versions() -> dict[str, str]:
    """What actually read the package. Measured off the environment, never a default."""
    settings = get_settings()

    def installed(package: str) -> str:
        try:
            return f"{package} {version(package)}"
        except PackageNotFoundError:
            return f"{package} (not installed)"

    weights = settings.pdp_weights_path
    return {
        "ocr_engine": installed("paddleocr"),
        "ocr_second_reading": installed("pytesseract"),
        "pdp_detector": (
            f"ultralytics {version('ultralytics')} weights {weights.name}"
            if weights is not None and weights.exists()
            else "morphological text-region heuristic (no trained detector configured)"
        ),
        "tamper_detector": "edge-discontinuity and conflicting-price heuristics (uncalibrated)",
    }


def bsa_report(scan: Scan, entries: list[EvidenceEntry], review: ReviewRow | None) -> BSAReport:
    """The BSA s.63(4) Part A certificate for a finalised scan, from its chain.

    Raises :class:`UnconfirmedVerdictExportError` without a finalising review, which is
    :func:`~app.modules.evidence.report.generate_bsa_report`'s own gate and the only
    reason this function exists outside it: the gate needs the review row to decide.
    """
    record = record_from(entries)
    verification = verify_chain(entries)
    if not verification.is_valid:
        raise UnconfirmedVerdictExportError(
            f"the evidence chain does not verify ({verification.reason} at entry "
            f"{verification.broken_link_index}); no certificate can be issued over it"
        )
    source = scan.image_refs[0]["storage_key"].rpartition("/")[2] if scan.image_refs else ""
    return generate_bsa_report(
        source_image_hash=source,
        rule_set_version=record.rule_set_version,
        audit_trail=EvidenceAuditTrail(
            root_entry_hash=entries[0].entry_hash,
            latest_entry_hash=entries[-1].entry_hash,
            total_sequence_count=len(entries),
        ),
        declarations=[
            FieldDeclaration(
                field_name=finding.field.value,
                declared_value=finding.observed_value,
                measured_value=finding.observed_value,
                required_value=finding.expected_value,
                ocr_provider=(
                    record.field_providers[finding.field].value
                    if finding.field in record.field_providers
                    else "none"
                ),
                confidence=0.0,
            )
            for finding in record.findings
        ],
        confirmation=(
            HumanConfirmation(
                confirmed_by=review.officer_id,
                confirmation_timestamp=review.created_at.isoformat(),
                officer_action=review.action.value.upper(),
            )
            if review is not None
            else None
        ),
        is_human_confirmed=review is not None,
        model_versions=_model_versions(),
    )


def report_bytes(
    scan: Scan, entries: list[EvidenceEntry], review: ReviewRow | None, fmt: str
) -> tuple[bytes, str]:
    """The report in ``fmt``, and its media type. Every format passes the same gate."""
    if fmt == "json":
        return bsa_report(scan, entries, review).model_dump_json(indent=2).encode(), (
            "application/json"
        )
    record = record_from(entries)
    image = scan.image_refs[0]["storage_key"] if scan.image_refs else None
    rendered = export_compliance_report(record, review_row=review, format=fmt, image_path=image)
    media = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }[fmt]
    return rendered, media


def export_entry(
    entries: list[EvidenceEntry], *, fmt: str, rendered: bytes, officer_id: str
) -> EvidenceEntry:
    """Append the fact of an export to the chain: who took what away, and its hash.

    The report is not stored, its digest is. An officer holding a filed PDF can show it is
    the one the chain records, and nobody can later claim a different report was issued.
    """
    payload = json.dumps(
        {
            "type": "report_export",
            "format": fmt,
            "report_sha256": compute_sha256(rendered),
            "exported_by": officer_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return append_entry(
        entries[-1], payload, datetime.now(UTC).isoformat(), EvidenceAssetType.AUDIT_LOG
    )


__all__ = [
    "NoEvidenceError",
    "REPORT_FORMATS",
    "bsa_report",
    "export_entry",
    "record_from",
    "report_bytes",
    "verified",
]
