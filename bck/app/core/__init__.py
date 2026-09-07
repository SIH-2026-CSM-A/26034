"""Infrastructure every module needs and none should re-implement.

Import from the package, not from its files::

    from app.core import Principal, RoleTier, Scan, get_current_principal, get_session

The split into ``auth.py``, ``complaints.py``, ``config.py``, ``db.py``, ``enums.py``,
``market.py``, ``models.py``, ``rbac.py`` and ``schema.py`` is an internal detail. Going
through this surface means rearranging files inside ``core/`` is not a change to six other
people's imports.

**The model imports below are load-bearing, not tidiness.** ``alembic/env.py`` reaches the
schema through ``from app.core.models import Base``, which executes this file first — so a
table in a module this file does not import is invisible to autogenerate, and produces an
empty migration that passes ``alembic check`` and then fails at the first insert. Every
module that declares a table has to be named here.

``core`` sits above ``contracts`` and below ``modules``: it may import ``app.contracts``
and nothing else from ``app``. ``lint-imports`` enforces that in CI.
"""

from app.core.auth import (
    Token,
    auth_router,
    authenticate_officer,
    create_access_token,
    get_current_principal,
    hash_password,
    principal_from_token,
    require_tier,
    verify_password,
)
from app.core.complaints import ComplaintRow, ProductReviewRow
from app.core.config import (
    DEFAULT_ROLE_DESIGNATIONS,
    OfficerCredential,
    Settings,
    get_settings,
)
from app.core.db import dispose_engine, get_engine, get_session, get_session_factory
from app.core.enums import (
    CalibrationMethod,
    ComplaintStatus,
    ConsumerSafetyClaim,
    ReviewAction,
    ScanSourceType,
    ScanStatus,
    VendorType,
)
from app.core.market import VendorRow, VendorScanRow
from app.core.models import (
    EvidenceEntryRow,
    FieldFindingRow,
    ReviewRow,
    Scan,
    VerdictRow,
)
from app.core.rbac import Jurisdiction, Principal, RoleTier, scope_to_jurisdiction
from app.core.schema import Base

__all__ = [
    "Base",
    "CalibrationMethod",
    "ComplaintRow",
    "ComplaintStatus",
    "ConsumerSafetyClaim",
    "DEFAULT_ROLE_DESIGNATIONS",
    "EvidenceEntryRow",
    "FieldFindingRow",
    "Jurisdiction",
    "OfficerCredential",
    "Principal",
    "ProductReviewRow",
    "ReviewAction",
    "ReviewRow",
    "RoleTier",
    "Scan",
    "ScanSourceType",
    "ScanStatus",
    "Settings",
    "Token",
    "VendorRow",
    "VendorScanRow",
    "VendorType",
    "VerdictRow",
    "auth_router",
    "authenticate_officer",
    "create_access_token",
    "dispose_engine",
    "get_current_principal",
    "get_engine",
    "get_session",
    "get_session_factory",
    "get_settings",
    "hash_password",
    "principal_from_token",
    "require_tier",
    "scope_to_jurisdiction",
    "verify_password",
]
