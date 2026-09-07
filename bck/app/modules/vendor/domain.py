"""Domain models and value objects for vendor self-scan submissions under VND-001.

These models represent what a vendor supplies at submission time. A vendor submission
does NOT wrap a scan type — it carries vendor identity, trade classification,
territorial jurisdiction, and an image reference. The scan it produces goes through the
identical pipeline as any other scan.

Per ARCHITECTURE.md (precedent set by ExtractionResult), vendor-specific models remain
local to app.modules.vendor and are not exposed through app.contracts.
"""

from uuid import UUID

from pydantic import AliasChoices, Field

from app.contracts import ContractModel
from app.core import Jurisdiction, VendorType


class VendorSubmission(ContractModel):
    """Payload supplied by a vendor at submission time.

    Carries the vendor's identity (id, name, vendor_type), jurisdiction (state required,
    region and district optional, mirroring the Scan jurisdiction shape), plus an image
    reference for the packaged commodity.

    It is not a second verdict path; the scan it produces goes through the identical
    pipeline as any other scan.
    """

    id: UUID = Field(
        description="Unique vendor identifier.",
        validation_alias=AliasChoices("id", "vendor_id"),
    )
    name: str = Field(
        min_length=1,
        description="Registered trade or establishment name of the vendor.",
        validation_alias=AliasChoices("name", "vendor_name"),
    )
    vendor_type: VendorType = Field(
        description="Commercial classification of the establishment.",
    )
    jurisdiction: Jurisdiction = Field(
        description=(
            "Territorial jurisdiction of the establishment mirroring the Scan shape: "
            "state required, region and district optional."
        ),
    )
    image_reference: str = Field(
        min_length=1,
        description="Object storage key or URI referencing the uploaded package label image.",
        validation_alias=AliasChoices("image_reference", "image_ref"),
    )

    @property
    def vendor_id(self) -> UUID:
        """Alias for id."""
        return self.id

    @property
    def vendor_name(self) -> str:
        """Alias for name."""
        return self.name

    @property
    def image_ref(self) -> str:
        """Alias for image_reference."""
        return self.image_reference

    @property
    def state(self) -> str:
        """State jurisdiction level (always present)."""
        return self.jurisdiction.state

    @property
    def region(self) -> str | None:
        """Regional jurisdiction level, or None if broad state-level."""
        return self.jurisdiction.region

    @property
    def district(self) -> str | None:
        """District jurisdiction level, or None if state or regional level."""
        return self.jurisdiction.district


__all__ = [
    "VendorSubmission",
    "VendorType",
]
