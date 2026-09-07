"""The tables that say where a scanned package came from.

:mod:`app.core.models` holds the tables the scan path writes. These two hold the vendor a
package was found at and the attribution linking the two, which is written at capture and
read by nothing in the evaluation path.

The one guarantee to read before editing anything here: **a vendor-submitted scan is an
ordinary scan.** It reaches the same quality gate, the same rules, the same verdict and the
same officer. What makes that structural rather than promised is that
:class:`VendorScanRow` holds nothing the evaluation path could branch on — no submission
channel, no trust level, no status — and that there is no vendor column on
:class:`app.core.models.Scan` at all. A column here that could change how a scan is
evaluated would make vendor submissions a second verdict path, which is the thing this
shape exists to prevent.

The vocabularies live in :mod:`app.core.enums` and the column plumbing in
:mod:`app.core.schema`, the same division ``models.py`` follows.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import VendorType
from app.core.schema import JURISDICTION_LEVEL_LENGTH, Base, enum_column


class VendorRow(Base):
    """A retail or storage premises a scanned package came from."""

    __tablename__ = "vendors"
    __table_args__ = (Index("ix_vendors_state_region_district", "state", "region", "district"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    """The trading name, as written on the premises.

    ``Text`` rather than a capped ``String`` because there is no source for a cap. The
    widths in this schema are either structural (:data:`~app.core.schema.SHA256_HEX_LENGTH`)
    or bounded by a vocabulary, and a shop name is neither; a length limit is a
    request-boundary concern, the way :attr:`app.core.models.Scan.product_category`'s
    vocabulary is.
    """

    vendor_type: Mapped[VendorType] = mapped_column(
        enum_column(VendorType, "vendor_type"), nullable=False
    )
    """What kind of premises this is. Read by nothing in the verdict path."""

    state: Mapped[str] = mapped_column(String(JURISDICTION_LEVEL_LENGTH), nullable=False)
    region: Mapped[str | None] = mapped_column(String(JURISDICTION_LEVEL_LENGTH))
    district: Mapped[str | None] = mapped_column(String(JURISDICTION_LEVEL_LENGTH))
    """The territory this vendor sits in, mirroring :class:`app.core.rbac.Jurisdiction` and
    :class:`app.core.models.Scan` exactly — the same three names, the same width, the same
    nullability, in the same order.

    The names are a contract with :func:`app.core.rbac.scope_to_jurisdiction`, which reaches
    all three by ``getattr`` using the :class:`~app.core.rbac.RoleTier` member *values*.
    Renaming one, or folding the three into a JSON document, makes every scoped query over
    this table raise. Matching ``Scan`` rather than being stricter than it is what keeps the
    two tables agreeing about what a jurisdiction is; a disagreement there surfaces as a
    query matching nothing, never as an error.

    The consequence of the nullability, which is counter-intuitive and therefore written
    down: ``NULL = 'Satara'`` is NULL and never true, so a vendor with no ``district``
    is absent from a district officer's scoped query while remaining visible to the state
    officer above them. A NULL says the level was never recorded, not that it matches
    everything. Whether onboarding can always collect a district belongs to the ticket that
    builds onboarding.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VendorScanRow(Base):
    """One scan's vendor attribution. Three columns, and that is the whole table.

    **A vendor-submitted scan is an ordinary scan carrying an attribution**, not a second
    scan type and not a second verdict path. This table is the only place the attribution
    lives, and it holds nothing an evaluation could branch on: no channel, no trust level,
    no status, no flag. The verdict path does not join to this table, and there would be
    nothing here for it to read if it did.

    :attr:`scan_id` is the primary key rather than a surrogate ``id`` with a unique
    constraint beside it, so "at most one vendor attribution per scan" is the primary key
    itself. That is also why there is no surrogate: nothing foreign-keys to this row — a
    scan's vendor is reached from the scan — unlike :class:`app.core.models.ReviewRow`,
    which needs an ``id`` for ``supersedes_id``, and
    :class:`app.core.models.FieldFindingRow`, which needs one alongside its three-column
    uniqueness constraint.
    """

    __tablename__ = "vendor_scans"

    scan_id: Mapped[UUID] = mapped_column(ForeignKey("scans.id"), primary_key=True)
    """The scan, and the primary key."""

    vendor_id: Mapped[UUID] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    """The vendor it is attributed to. Indexed because "every scan from this vendor" is the
    query this table exists to answer."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
