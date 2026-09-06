"""Infrastructure every module needs and none should re-implement.

Import from the package, not from its files::

    from app.core import Principal, RoleTier, Scan, get_current_principal, get_session

The split into ``auth.py``, ``config.py``, ``db.py``, ``enums.py``, ``models.py``,
``rbac.py`` and ``schema.py`` is an internal detail. Going through this surface means
rearranging files inside ``core/`` is not a change to six other people's imports.

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
from app.core.config import (
    DEFAULT_ROLE_DESIGNATIONS,
    OfficerCredential,
    Settings,
    get_settings,
)
from app.core.db import dispose_engine, get_engine, get_session, get_session_factory
from app.core.enums import CalibrationMethod, ReviewAction, ScanSourceType, ScanStatus
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
    "DEFAULT_ROLE_DESIGNATIONS",
    "Base",
    "CalibrationMethod",
    "EvidenceEntryRow",
    "FieldFindingRow",
    "Jurisdiction",
    "OfficerCredential",
    "Principal",
    "ReviewAction",
    "ReviewRow",
    "RoleTier",
    "Scan",
    "ScanSourceType",
    "ScanStatus",
    "Settings",
    "Token",
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
