"""Infrastructure every module needs and none should re-implement.

Import from the package, not from its files::

    from app.core import Principal, RoleTier, get_current_principal, get_settings

The split into ``auth.py``, ``config.py`` and ``rbac.py`` is an internal detail. Going
through this surface means rearranging files inside ``core/`` is not a change to six
other people's imports.

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
from app.core.rbac import Jurisdiction, Principal, RoleTier, scope_to_jurisdiction

__all__ = [
    "DEFAULT_ROLE_DESIGNATIONS",
    "Jurisdiction",
    "OfficerCredential",
    "Principal",
    "RoleTier",
    "Settings",
    "Token",
    "auth_router",
    "authenticate_officer",
    "create_access_token",
    "get_current_principal",
    "get_settings",
    "hash_password",
    "principal_from_token",
    "require_tier",
    "scope_to_jurisdiction",
    "verify_password",
]
