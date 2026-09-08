"""Typed read-only HTTP shapes for the vendor register.

``jurisdiction`` is nested rather than flattened into three sibling columns so that this
response and :class:`~app.modules.vendor.domain.VendorSubmission` describe a territory the
same way. The three names are a contract with
:func:`app.core.rbac.scope_to_jurisdiction`, and a response that spelled them differently
would be a second vocabulary for the same fact.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core import Jurisdiction, VendorRow, VendorType


class VendorSchema(BaseModel):
    """Base schema that rejects fields outside the vendor API contract."""

    model_config = ConfigDict(extra="forbid")


class VendorResponse(VendorSchema):
    """One premises on the register.

    Carries no scan counts and no verdict summary. A vendor-submitted scan is an ordinary
    scan, and :class:`~app.core.market.VendorScanRow` holds nothing the evaluation path
    could branch on; a vendor's compliance history is a question for the scan routes, which
    are scoped in their own right.
    """

    id: UUID
    name: str = Field(min_length=1)
    vendor_type: VendorType
    jurisdiction: Jurisdiction
    created_at: datetime


def vendor_response(row: VendorRow) -> VendorResponse:
    """One stored vendor as the shape the routes return."""
    return VendorResponse(
        id=row.id,
        name=row.name,
        vendor_type=row.vendor_type,
        jurisdiction=Jurisdiction(state=row.state, region=row.region, district=row.district),
        created_at=row.created_at,
    )
