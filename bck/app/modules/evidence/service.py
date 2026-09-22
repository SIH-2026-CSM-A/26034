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


def asset_digest(entries: list[EvidenceEntry]) -> tuple[str | None, str | None]:
    """The SHA-256 the chain holds for a captured asset, or the reason it holds none.

    Exactly one of the pair is set. The digest is the ``sha256`` recorded in the payload of
    the first entry whose asset type is not ``AUDIT_LOG`` — the SHA-256 of the exact bytes
    received, which an officer can reproduce from a filed photograph with ``sha256sum``.

    Deliberately **not** that entry's ``payload_hash``. The payload hash covers the whole
    capture record — digest, byte length, storage key, media type — and is what links the
    entry into the chain; it matches no file. An audit-log entry's hash is further still
    from the capture: it covers the *record about* it (the verdict, a purge, an export).
    Printing either in place of the asset digest would put a number on a certificate that
    no photograph can be matched to, which is worse than printing none.
    """
    for entry in entries:
        if entry.asset_type == EvidenceAssetType.AUDIT_LOG:
            continue
        recorded = _document(entry).get("sha256")
        if isinstance(recorded, str) and recorded:
            return recorded, None
        return None, (
            f"The evidence chain holds a {entry.asset_type.value} entry at sequence "
            f"{entry.sequence}, but it records no digest of the asset's bytes, so there is "
            "nothing to certify. This is a defect in whatever wrote that entry."
        )
    count = len(entries)
    if count == 0:
        return None, (
            "No evidence chain is recorded for this scan, so there is no asset digest to certify."
        )
    held = (
        "its single entry is an audit-log entry, which hashes"
        if count == 1
        else f"all {count} of its entries are audit-log entries, which hash"
    )
    return None, (
        f"No captured asset is recorded in this chain: {held} the evaluation record "
        "rather than the photograph. There is no asset digest to certify."
    )


class NoEvidenceError(LookupError):
    """The scan has no evidence chain: it was refused at the gate or never evaluated."""


def verified(entries: list[EvidenceEntry]) -> ChainVerification:
    """Verify a chain as read from storage. A missing chain verifies as ``missing_genesis``."""
    return verify_chain(entries)


def _document(entry: EvidenceEntry) -> dict:
    """An entry's payload as a mapping, whether it was stored as text or as a dict."""
    payload = entry.payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return {}
    return payload if isinstance(payload, dict) else {}


def record_from(entries: list[EvidenceEntry]) -> VerdictRecord:
    """The verdict as it was hashed into the chain.

    Found by its payload, not by position. Since the capture entry was added the genesis
    of an image scan is the photograph's digest and the verdict is the entry after it,
    while a catalogue scan still has the verdict at genesis and chains written before that
    change keep the old shape. Reading ``entries[0]`` would have decided which of those
    this is by luck.
    """
    if not entries:
        raise NoEvidenceError("this scan has no evidence chain")
    for entry in entries:
        document = _document(entry)
        if "verdict" in document:
            return VerdictRecord.model_validate(document["verdict"])
    raise NoEvidenceError(
        f"this scan's evidence chain holds no verdict: {len(entries)} entries and none of "
        "them carries one"
    )


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
    digest, digest_note = asset_digest(entries)
    rendered = export_compliance_report(
        record,
        review_row=review,
        format=fmt,
        image_path=image,
        evidence_hash=digest,
        evidence_hash_note=digest_note,
    )
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
    "asset_digest",
    "bsa_report",
    "export_entry",
    "record_from",
    "report_bytes",
    "verified",
]
