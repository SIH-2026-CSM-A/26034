"""The vendor register endpoints, and the vendor login.

**Two kinds of caller, two dependencies, no overlap.** The register reads and the
registration are officer routes on a :class:`~app.core.Principal`. The token exchange is the
one route here a vendor calls, and what it issues is a token that no officer route accepts.

**Registration is an officer act.** A vendor is put on the register, with a login, by an
officer whose jurisdiction covers the premises; the vendor cannot register themselves, and
the territory the officer states is refused if it is not inside their own. That territory is
what routes the vendor's scans afterwards.

**Authorisation is here, not in the interface.** Both reads go through the repository, which
applies :func:`~app.modules.vendor.service.scope_vendor_query` to every statement. A vendor
outside the caller's jurisdiction is a 404 — the same answer as one that is not on the
register, because a 403 would confirm to an officer in one state that a premises in another
is known to the department.
"""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import (
    Principal,
    RoleTier,
    Token,
    VendorPrincipal,
    create_vendor_token,
    get_current_principal,
    get_session,
    hash_password,
    require_tier,
    verify_password,
)
from app.modules.vendor import repository
from app.modules.vendor.schemas import VendorRegistration, VendorResponse, vendor_response

vendor_router = APIRouter(prefix="/vendors", tags=["vendors"])

Session = Annotated[AsyncSession, Depends(get_session)]
Officer = Annotated[Principal, Depends(get_current_principal)]


@lru_cache(maxsize=1)
def _absent_account_hash() -> str:
    """Checked against when the username is unknown, so an unknown name costs the same
    bcrypt time as a wrong password and the login is not an oracle for the register.
    Computed once, lazily, because bcrypt is deliberately slow."""
    return hash_password("no vendor by that name")


@vendor_router.post("", status_code=status.HTTP_201_CREATED)
async def register_vendor(
    body: VendorRegistration,
    session: Session,
    principal: Annotated[Principal, Depends(require_tier(RoleTier.DISTRICT))],
) -> VendorResponse:
    """Put a premises on the register with a login, inside the officer's own territory."""
    for level in principal.tier.scope_fields:
        if getattr(body.jurisdiction, level) != getattr(principal.jurisdiction, level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"the premises' {level} is outside your jurisdiction",
            )
    if body.jurisdiction.district is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="a registered premises must name its district, or no inspector covers it",
        )
    try:
        password_hash = hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None
    try:
        async with session.begin():
            vendor = await repository.register_vendor(
                session,
                name=body.name,
                vendor_type=body.vendor_type,
                jurisdiction=body.jurisdiction,
                username=body.username,
                password_hash=password_hash,
            )
            # Read back inside the transaction so the response carries the server clock.
            await session.refresh(vendor)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="that username is already registered"
        ) from None
    return vendor_response(vendor)


@vendor_router.post("/auth/token")
async def issue_vendor_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: Session
) -> Token:
    """Exchange a vendor's username and password for a vendor token."""
    account = await repository.account_by_username(session, form_data.username)
    if account is None:
        verify_password(form_data.password, _absent_account_hash())
        raise _bad_login()
    if not verify_password(form_data.password, account.password_hash):
        raise _bad_login()
    vendor = VendorPrincipal(vendor_id=account.vendor_id, subject=account.username)
    return Token(access_token=create_vendor_token(vendor))


def _bad_login() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@vendor_router.get("")
async def list_vendors(session: Session, principal: Officer) -> list[VendorResponse]:
    """Vendors this officer may see, by name.

    The jurisdiction predicate is applied by the repository on every query and is not
    something a caller can widen — there is no jurisdiction parameter on this route.
    """
    return [vendor_response(row) for row in await repository.list_vendors(session, principal)]


@vendor_router.get("/{vendor_id}")
async def get_vendor(vendor_id: UUID, session: Session, principal: Officer) -> VendorResponse:
    """One vendor in full, or a 404 for absent and out-of-jurisdiction alike."""
    row = await repository.get_scoped_vendor(session, vendor_id, principal)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vendor not found")
    return vendor_response(row)
