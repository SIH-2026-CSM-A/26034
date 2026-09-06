"""OAuth2 password flow and JWT verification.

The shape is FastAPI's own: a ``POST /auth/token`` that exchanges a username and password
for a signed access token, and a dependency that turns the ``Authorization: Bearer``
header back into a :class:`~app.core.rbac.Principal`. No refresh token — the pattern this
follows has none, and a second credential lifetime is a second thing to get wrong.

The rule the rest of the system depends on: **a principal comes from a verified token and
from nowhere else.** :func:`principal_from_token` is the only way to build one from a
request. A tier or a jurisdiction that arrived in a request body is a claim by the client
about itself; an endpoint that trusted one would be scoping its queries with data the
person being scoped chose. Every failure here raises — there is no path that returns a
partly-trusted principal, and none that falls back to a wider scope.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import Field

from app.contracts import ContractModel
from app.core.config import get_settings
from app.core.rbac import Jurisdiction, Principal, RoleTier

BCRYPT_MAX_PASSWORD_BYTES = 72
"""bcrypt truncates silently past this length. We refuse instead — a password whose tail
is ignored is weaker than the one its owner believes they set."""

REQUIRED_CLAIMS = ("sub", "tier", "jur", "exp", "iat")
"""Claims a token must carry. ``exp`` is in the list because a token without one never
expires, and PyJWT will not check an expiry that is not there."""

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class Token(ContractModel):
    """The token response, in the shape the OAuth2 password flow specifies."""

    access_token: str = Field(min_length=1)
    """The signed JWT."""

    token_type: str = "bearer"
    """Always ``bearer``. Named by the spec, and clients read it."""


def hash_password(password: str) -> str:
    """Hash a password for storage in ``OFFICERS``.

    How an administrator produces a ``password_hash``. Raises on a password bcrypt would
    truncate.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"password is {len(encoded)} bytes; bcrypt silently ignores anything past "
            f"{BCRYPT_MAX_PASSWORD_BYTES}"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Whether ``password`` matches ``password_hash``. False on any malformed input."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False


@lru_cache(maxsize=1)
def _absent_officer_hash() -> str:
    """A hash to check an unknown username against.

    Without it, an unknown username returns before doing any bcrypt work and a known one
    does not, which is a timing oracle for enumerating officers. Computed once, lazily,
    because bcrypt is deliberately slow and this should not cost anything at import.
    """
    return hash_password("no officer by that name")


def create_access_token(principal: Principal, expires_in: timedelta | None = None) -> str:
    """Sign an access token carrying ``principal``'s tier and jurisdiction.

    The tier and jurisdiction travel *inside* the signature, which is what makes them
    trustworthy on the way back. ``expires_in`` overrides the configured lifetime; it
    exists so an expiry can be exercised without waiting an hour for one.
    """
    settings = get_settings()
    issued_at = datetime.now(UTC)
    lifetime = (
        expires_in
        if expires_in is not None
        else timedelta(minutes=settings.access_token_ttl_minutes)
    )
    claims = {
        "sub": principal.subject,
        "tier": principal.tier.value,
        "jur": principal.jurisdiction.model_dump(),
        "iat": issued_at,
        "exp": issued_at + lifetime,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _unauthorised(detail: str) -> HTTPException:
    """A 401 carrying the challenge header the bearer scheme requires."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def principal_from_token(token: str) -> Principal:
    """Verify a token and rebuild the principal it carries.

    Verification is server-side and total: signature against the configured secret, the
    algorithm against an explicit allowlist (so a token presenting ``alg: none`` is
    rejected rather than accepted unsigned), expiry, and the presence of every claim in
    :data:`REQUIRED_CLAIMS`. The claims are then fed back through
    :class:`~app.core.rbac.Principal`, so a tampered jurisdiction that no longer matches
    its tier fails the same validation an honestly-built principal passes.
    """
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": list(REQUIRED_CLAIMS)},
        )
    except jwt.PyJWTError as exc:
        raise _unauthorised("could not validate credentials") from exc

    try:
        return Principal(
            subject=claims["sub"],
            tier=RoleTier(claims["tier"]),
            jurisdiction=Jurisdiction(**claims["jur"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _unauthorised("token claims do not describe a usable principal") from exc


async def get_current_principal(token: Annotated[str, Depends(oauth2_scheme)]) -> Principal:
    """FastAPI dependency: the authenticated officer, or a 401.

    Put this on every protected endpoint. What it returns is the only description of the
    caller's authority an endpoint may act on.
    """
    return principal_from_token(token)


def require_tier(minimum: RoleTier) -> Callable[[Principal], Principal]:
    """Build a dependency that additionally requires a tier at least as broad as ``minimum``.

    Comparison, not identity: a controller passes a check that requires an inspector,
    because their authority contains it. The 403 names the required designation using the
    deployment's own nomenclature.
    """

    def dependency(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if not principal.tier.covers(minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(f"this action requires at least a {get_settings().designation(minimum)}"),
            )
        return principal

    return dependency


def authenticate_officer(username: str, password: str) -> Principal | None:
    """Check a username and password against the configured officers.

    Returns the principal on success and ``None`` on any failure — a wrong password and
    an unknown username are indistinguishable to the caller and cost roughly the same
    time.
    """
    for officer in get_settings().officers:
        if officer.username == username:
            if verify_password(password, officer.password_hash):
                return Principal(
                    subject=officer.username,
                    tier=officer.tier,
                    jurisdiction=officer.jurisdiction,
                )
            return None
    verify_password(password, _absent_officer_hash())
    return None


@auth_router.post("/token")
async def issue_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Exchange officer credentials for an access token."""
    principal = authenticate_officer(form_data.username, form_data.password)
    if principal is None:
        raise _unauthorised("incorrect username or password")
    return Token(access_token=create_access_token(principal))
