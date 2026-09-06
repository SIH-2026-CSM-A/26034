"""Token issuance, verification, and the rule that a client never states its own authority.

The criterion behind most of this file is that a protected endpoint acts on the token and
on nothing else. So the tests do not check that a helper returns ``True`` — they hand the
dependency a token that has been tampered with, expired, signed with the wrong key, or
re-labelled with a wider tier, and require that it *raises*. There is no assertion here
that a bad token degrades to reduced access; the only acceptable outcome is refusal.

Every test in this file runs once per designation profile (see ``conftest.py``).
"""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.contracts import EvidenceProvider
from app.core.auth import (
    authenticate_officer,
    create_access_token,
    get_current_principal,
    hash_password,
    issue_access_token,
    principal_from_token,
    require_tier,
    verify_password,
)
from app.core.config import get_settings
from app.core.rbac import Jurisdiction, Principal, RoleTier
from tests.core.conftest import CONTROLLER, INSPECTOR, JWT_SECRET, visible_ids

OFFICER_PASSWORD = "correct horse battery staple"
OFFICER_PASSWORD_HASH = hash_password(OFFICER_PASSWORD)
"""Hashed once at import. bcrypt is deliberately slow; there is no reason to pay for it
in every test."""


def configure_officers(monkeypatch: pytest.MonkeyPatch, *officers: Principal) -> None:
    """Put ``officers`` into the environment the way a deployment would."""
    monkeypatch.setenv(
        "OFFICERS",
        json.dumps(
            [
                {
                    "username": officer.subject,
                    "password_hash": OFFICER_PASSWORD_HASH,
                    "tier": officer.tier.value,
                    "jurisdiction": officer.jurisdiction.model_dump(),
                }
                for officer in officers
            ]
        ),
    )
    get_settings.cache_clear()


OTHER_SECRET = "a-different-signing-key-of-adequate-length"


def signed(claims: dict, key: str = JWT_SECRET, algorithm: str = "HS256") -> str:
    """A token built claim-by-claim, for the cases a legitimate mint cannot produce."""
    return jwt.encode(claims, key, algorithm=algorithm)


def base_claims(**overrides: object) -> dict:
    now = datetime.now(UTC)
    claims = {
        "sub": INSPECTOR.subject,
        "tier": INSPECTOR.tier.value,
        "jur": INSPECTOR.jurisdiction.model_dump(),
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return claims


# --- what a good token carries -------------------------------------------------------


def test_a_token_carries_the_tier_and_jurisdiction_as_claims() -> None:
    claims = jwt.decode(create_access_token(INSPECTOR), JWT_SECRET, algorithms=["HS256"])
    assert claims["sub"] == "inspector"
    assert claims["tier"] == RoleTier.DISTRICT.value
    assert claims["jur"] == {"state": "Maharashtra", "region": "Pune", "district": "Satara"}


def test_a_minted_token_round_trips_to_an_equal_principal() -> None:
    assert principal_from_token(create_access_token(INSPECTOR)) == INSPECTOR


async def test_the_dependency_returns_the_principal_the_token_names() -> None:
    assert await get_current_principal(create_access_token(CONTROLLER)) == CONTROLLER


# --- what a bad token gets -----------------------------------------------------------


def test_a_tampered_token_is_rejected() -> None:
    """Flip one character of the signature. Nothing about the payload changed."""
    header, payload, signature = create_access_token(INSPECTOR).split(".")
    forged = f"{header}.{payload}.{'A' if signature[0] != 'A' else 'B'}{signature[1:]}"
    with pytest.raises(HTTPException) as raised:
        principal_from_token(forged)
    assert raised.value.status_code == 401


def test_a_token_signed_with_another_key_is_rejected() -> None:
    with pytest.raises(HTTPException) as raised:
        principal_from_token(signed(base_claims(), key=OTHER_SECRET))
    assert raised.value.status_code == 401


def test_an_unsigned_token_is_rejected() -> None:
    """``alg: none`` — the classic way in. The decode allowlist is what refuses it."""
    with pytest.raises(HTTPException) as raised:
        principal_from_token(signed(base_claims(), key="", algorithm="none"))
    assert raised.value.status_code == 401


def test_an_expired_token_is_rejected() -> None:
    expired = create_access_token(INSPECTOR, expires_in=timedelta(minutes=-5))
    with pytest.raises(HTTPException) as raised:
        principal_from_token(expired)
    assert raised.value.status_code == 401


def test_a_token_with_no_expiry_is_rejected() -> None:
    """A token that never expires is worse than one that expired."""
    claims = base_claims()
    del claims["exp"]
    with pytest.raises(HTTPException) as raised:
        principal_from_token(signed(claims))
    assert raised.value.status_code == 401


def test_claims_that_do_not_describe_a_valid_principal_are_rejected() -> None:
    """Correctly signed, and still refused.

    A DISTRICT tier whose jurisdiction names no district would filter one level short.
    The claims are re-validated on the way in rather than trusted because the signature
    checked out.
    """
    widened = base_claims(jur={"state": "Maharashtra", "region": "Pune", "district": None})
    with pytest.raises(HTTPException) as raised:
        principal_from_token(signed(widened))
    assert raised.value.status_code == 401


def test_an_unknown_tier_is_rejected() -> None:
    with pytest.raises(HTTPException) as raised:
        principal_from_token(signed(base_claims(tier="chief-commissioner")))
    assert raised.value.status_code == 401


async def test_a_garbage_bearer_value_is_rejected() -> None:
    with pytest.raises(HTTPException):
        await get_current_principal("not-a-token")


# --- the endpoint never takes the client's word ---------------------------------------


async def protected_listing(session: Session, token: str, request_body: dict) -> set[str]:
    """Shaped like a protected endpoint: authority from the dependency, filters from the
    body. The body's jurisdiction fields are not a parameter of the scoping call and
    cannot become one."""
    principal = await get_current_principal(token)
    assert request_body  # the endpoint reads the body for its own filters, not for scope
    return visible_ids(session, principal)


async def test_a_client_supplied_jurisdiction_does_not_widen_what_it_sees(
    session: Session,
) -> None:
    """An inspector asks for the whole state in the request body and still gets one
    district, because the scope came out of the signed token."""
    visible = await protected_listing(
        session,
        create_access_token(INSPECTOR),
        {"tier": "state", "jurisdiction": {"state": "Maharashtra"}, "page": 1},
    )
    assert visible == {"mh-pune-satara"}


async def test_relabelling_the_tier_claim_does_not_widen_what_it_sees(
    session: Session,
) -> None:
    """The other way to try it: edit the tier inside the token. Without the key, the
    signature no longer matches and the request never reaches a query at all."""
    header, _, signature = create_access_token(INSPECTOR).split(".")
    forged_payload = jwt.encode(base_claims(tier="state"), OTHER_SECRET, algorithm="HS256")
    forged = f"{header}.{forged_payload.split('.')[1]}.{signature}"
    with pytest.raises(HTTPException):
        await protected_listing(session, forged, {})


# --- tier requirements ----------------------------------------------------------------


def test_a_broader_tier_satisfies_a_narrower_requirement() -> None:
    assert require_tier(RoleTier.DISTRICT)(CONTROLLER) == CONTROLLER


def test_a_narrower_tier_does_not_satisfy_a_broader_requirement() -> None:
    with pytest.raises(HTTPException) as raised:
        require_tier(RoleTier.STATE)(INSPECTOR)
    assert raised.value.status_code == 403


def test_the_refusal_names_the_deployments_own_designation() -> None:
    """The 403 speaks the state's nomenclature, not a hardcoded title."""
    with pytest.raises(HTTPException) as raised:
        require_tier(RoleTier.STATE)(INSPECTOR)
    assert get_settings().designation(RoleTier.STATE) in raised.value.detail


# --- passwords and login --------------------------------------------------------------


def test_a_password_verifies_against_its_own_hash() -> None:
    assert verify_password(OFFICER_PASSWORD, OFFICER_PASSWORD_HASH)
    assert not verify_password("something else", OFFICER_PASSWORD_HASH)


def test_a_password_bcrypt_would_truncate_is_refused() -> None:
    with pytest.raises(ValueError, match="72"):
        hash_password("x" * 73)


def test_a_malformed_hash_verifies_as_false_rather_than_raising() -> None:
    assert not verify_password(OFFICER_PASSWORD, "not-a-bcrypt-hash")


def test_a_configured_officer_authenticates_to_their_own_jurisdiction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_officers(monkeypatch, INSPECTOR)
    assert authenticate_officer(INSPECTOR.subject, OFFICER_PASSWORD) == INSPECTOR


def test_a_wrong_password_authenticates_nobody(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_officers(monkeypatch, INSPECTOR)
    assert authenticate_officer(INSPECTOR.subject, "wrong") is None


def test_an_unknown_username_authenticates_nobody(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_officers(monkeypatch, INSPECTOR)
    assert authenticate_officer("nobody", OFFICER_PASSWORD) is None


def test_a_deployment_with_no_officers_has_no_accounts() -> None:
    assert get_settings().officers == ()
    assert authenticate_officer("inspector", OFFICER_PASSWORD) is None


async def test_login_issues_a_token_that_verifies_back_to_the_officer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_officers(monkeypatch, INSPECTOR)
    token = await issue_access_token(
        OAuth2PasswordRequestForm(username=INSPECTOR.subject, password=OFFICER_PASSWORD)
    )
    assert token.token_type == "bearer"
    assert principal_from_token(token.access_token) == INSPECTOR


async def test_login_with_bad_credentials_issues_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_officers(monkeypatch, INSPECTOR)
    with pytest.raises(HTTPException) as raised:
        await issue_access_token(
            OAuth2PasswordRequestForm(username=INSPECTOR.subject, password="wrong")
        )
    assert raised.value.status_code == 401


# --- cost ceilings ---------------------------------------------------------------------


def test_cloud_ocr_is_off_by_default() -> None:
    """Zero is the shipped ceiling. Turning cloud OCR on is a deliberate act."""
    assert get_settings().cost_ceiling(EvidenceProvider.CLOUD_OCR.value) == Decimal("0")


def test_a_provider_with_no_budget_raises_rather_than_defaulting() -> None:
    with pytest.raises(LookupError, match="no cost ceiling"):
        get_settings().cost_ceiling("some-paid-api")


def test_a_deployment_can_raise_a_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COST_CEILINGS", json.dumps({"CLOUD_OCR": "1250.00"}))
    get_settings.cache_clear()
    assert get_settings().cost_ceiling("CLOUD_OCR") == Decimal("1250.00")


def test_an_officer_credential_stores_a_hash_and_not_a_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_officers(monkeypatch, INSPECTOR)
    stored = get_settings().officers[0]
    assert OFFICER_PASSWORD not in stored.password_hash
    assert stored.jurisdiction == Jurisdiction(
        state="Maharashtra", region="Pune", district="Satara"
    )
