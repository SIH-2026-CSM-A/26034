import logging
from datetime import datetime, timedelta

from app.contracts.enums import Verdict
from app.contracts.records import VerdictRecord
from app.core.config import get_settings
from app.core.enums import ReviewAction
from app.core.models import ReviewRow

from .chain import append_purge_entry
from .domain import EvidenceEntry, EvidenceAssetType
from .storage import EvidenceStorageClient

logger = logging.getLogger(__name__)


def is_legal_hold(record: VerdictRecord, review_row: ReviewRow | None) -> bool:
    """
    Determines if evidence should be exempt from purge due to a legal hold.

    Requirement: Evidence attached to a confirmed POTENTIAL_VIOLATION
    under active review must not be purged. Confirmation is structural:
    indicated by the existence of a ReviewRow with a final action.
    """
    if record.verdict != Verdict.POTENTIAL_VIOLATION:
        return False

    return review_row is not None and review_row.action in (
        ReviewAction.CONFIRM,
        ReviewAction.REJECT,
        ReviewAction.OVERRIDE,
    )


class RetentionManager:
    """
    Manages the lifecycle of evidence assets, enforcing retention windows
    and executing auditable purges.
    """

    def __init__(self, storage_client: EvidenceStorageClient):
        self.storage_client = storage_client
        self.settings = get_settings()

    def get_retention_days(self, asset_type: EvidenceAssetType) -> int:
        """
        Returns the retention window for a given asset class from configuration.
        """
        if asset_type in (EvidenceAssetType.GEOLOCATION, EvidenceAssetType.PERSONAL_IDENTIFIER):
            return self.settings.evidence_pii_retention_days
        return self.settings.evidence_image_retention_days

    def should_purge(self, entry: EvidenceEntry, current_time: datetime) -> bool:
        """
        Determines if an entry has exceeded its retention window.
        """
        if entry.is_purged:
            return False

        # Parse entry timestamp
        entry_time = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00"))
        retention_days = self.get_retention_days(entry.asset_type)

        expiry_date = entry_time + timedelta(days=retention_days)
        return current_time >= expiry_date

    def purge_evidence(
        self,
        entry: EvidenceEntry,
        prev_entry: EvidenceEntry,
        record: VerdictRecord,
        review_row: ReviewRow | None,
        current_time: datetime,
    ) -> tuple[bool, EvidenceEntry | None]:
        """
        Executes the purge workflow for a single evidence entry.

        Workflow: Legal Hold -> Expiration -> Safety Guard -> Storage Purge -> Audit Entry.
        """
        # 1. Legal Hold check
        if is_legal_hold(record, review_row):
            logger.info(
                f"Skipping purge for entry {entry.sequence}: "
                "Active legal hold (POTENTIAL_VIOLATION)."
            )
            return False, None

        # 2. Expiration check
        if not self.should_purge(entry, current_time):
            return False, None

        # 3. Safety Guard
        if not self.settings.evidence_destructive_purge_enabled:
            logger.info(
                f"Purge simulated for entry {entry.sequence} (destructive_purge_enabled=False)."
            )
            return False, None

        # 4. Storage Purge
        # The storage key is the payload_hash for images, or we assume the storage client
        # knows how to handle the storage_key if the payload was a path.
        # For this system, we use the payload_hash as the key for CAS.
        storage_key = f"evidence/{entry.payload_hash}"
        try:
            self.storage_client.purge_image(storage_key)
        except Exception as e:
            logger.error(f"Failed to purge storage for entry {entry.sequence}: {e}")
            return False, None

        # 5. Audit Entry
        audit_entry = append_purge_entry(
            prev_entry=prev_entry,
            target_sequence=entry.sequence,
            reason="Retention window expired",
            timestamp=current_time.isoformat(),
        )

        # Return True and the audit entry so the caller can append the entry to the chain
        logger.info(f"Successfully purged entry {entry.sequence} and created audit record.")
        return True, audit_entry
