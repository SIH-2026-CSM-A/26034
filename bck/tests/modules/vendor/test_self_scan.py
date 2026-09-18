"""Vendor self-scan: a vendor logs in, scans their own stock, and the covering officer sees it.

Marked ``postgres``: registration, login and attribution are rows, and the vendor's
visibility is a WHERE clause over them.
"""

from uuid import uuid4

import cv2
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core import Principal, Scan, VendorAccountRow, VendorPrincipal, get_session_factory
from app.core.auth import create_vendor_token, principal_from_token, vendor_from_token
from app.pipeline.router import VENDOR_SUBJECT_PREFIX
from tests.pipeline.conftest import CONTROLLER, INSPECTOR, OTHER_INSPECTOR, auth
from tests.pipeline.test_orchestrator import blurred_image

pytestmark = pytest.mark.postgres

SATARA = {"state": "Maharashtra", "region": "Pune", "district": "Satara"}
KOLHAPUR = {"state": "Maharashtra", "region": "Pune", "district": "Kolhapur"}

REGISTRATION = {
    "name": "Patil Kirana Stores",
    "vendor_type": "kirana",
    "jurisdiction": SATARA,
    "username": "patil-kirana",
    "password": "shelf-stock-2026",
}


async def register(client: AsyncClient, principal=INSPECTOR, **overrides) -> dict:
    response = await client.post("/vendors", json=REGISTRATION | overrides, headers=auth(principal))
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, username="patil-kirana", password="shelf-stock-2026"):
    return await client.post(
        "/vendors/auth/token", data={"username": username, "password": password}
    )


async def vendor_auth(client: AsyncClient, **credentials) -> dict[str, str]:
    response = await login(client, **credentials)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _files() -> dict:
    ok, encoded = cv2.imencode(".jpg", blurred_image())
    assert ok
    return {"image": ("shelf.jpg", encoded.tobytes(), "image/jpeg")}


async def self_scan(client: AsyncClient, headers: dict[str, str]) -> dict:
    response = await client.post("/vendor/scans/image", files=_files(), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["scan"]


# --- registration and login ------------------------------------------------------------------


async def test_an_officer_registers_a_premises_with_a_login_and_the_vendor_can_log_in(
    client: AsyncClient,
) -> None:
    vendor = await register(client)
    assert vendor["jurisdiction"] == SATARA
    assert "password" not in vendor and "password_hash" not in vendor

    token = await login(client)
    assert token.status_code == 200, token.text
    principal = vendor_from_token(token.json()["access_token"])
    assert principal == VendorPrincipal(vendor_id=vendor["id"], subject="patil-kirana")

    async with get_session_factory()() as session:
        account = (await session.scalars(select(VendorAccountRow))).one()
    assert account.password_hash != "shelf-stock-2026"
    assert account.password_hash.startswith("$2")


async def test_registration_is_an_officer_act_inside_their_own_territory(
    client: AsyncClient,
) -> None:
    anonymous = await client.post("/vendors", json=REGISTRATION)
    assert anonymous.status_code == 401

    outside = await client.post("/vendors", json=REGISTRATION, headers=auth(OTHER_INSPECTOR))
    assert outside.status_code == 403, outside.text

    # A controller may register a district premises; a district officer may not register
    # one in the next district over.
    assert (await register(client, CONTROLLER, username="controller-registered")) is not None
    next_district = await client.post(
        "/vendors",
        json=REGISTRATION | {"jurisdiction": KOLHAPUR, "username": "kolhapur-kirana"},
        headers=auth(INSPECTOR),
    )
    assert next_district.status_code == 403, next_district.text

    no_district = await client.post(
        "/vendors",
        json=REGISTRATION | {"jurisdiction": {"state": "Maharashtra"}, "username": "statewide"},
        headers=auth(CONTROLLER),
    )
    assert no_district.status_code == 422, no_district.text


async def test_a_vendor_cannot_register_a_vendor(client: AsyncClient) -> None:
    await register(client)
    headers = await vendor_auth(client)
    response = await client.post(
        "/vendors", json=REGISTRATION | {"username": "second-shop"}, headers=headers
    )
    assert response.status_code == 401, response.text


async def test_a_username_is_taken_once_and_a_bad_login_is_refused(client: AsyncClient) -> None:
    await register(client)
    duplicate = await client.post(
        "/vendors", json=REGISTRATION | {"name": "Another"}, headers=auth(INSPECTOR)
    )
    assert duplicate.status_code == 409, duplicate.text

    assert (await login(client, password="wrong")).status_code == 401
    assert (await login(client, username="nobody")).status_code == 401


# --- the two principals cannot be exchanged --------------------------------------------------


async def test_a_vendor_token_opens_no_officer_route_and_vice_versa(client: AsyncClient) -> None:
    vendor = await register(client)
    headers = await vendor_auth(client)
    token = headers["Authorization"].removeprefix("Bearer ")

    with pytest.raises(Exception, match="401"):
        principal_from_token(token)
    with pytest.raises(Exception, match="401"):
        vendor_from_token(auth(INSPECTOR)["Authorization"].removeprefix("Bearer "))

    for url in ("/scans", "/vendors", f"/vendors/{vendor['id']}", "/analytics/by-rule"):
        response = await client.get(url, headers=headers)
        assert response.status_code == 401, (url, response.text)
    assert (await client.get("/vendor/scans", headers=auth(INSPECTOR))).status_code == 401
    assert not issubclass(VendorPrincipal, Principal)


async def test_a_vendor_can_never_confirm_reject_or_override_a_verdict(
    client: AsyncClient,
) -> None:
    """The officer act, attempted by the vendor who filed the scan. Refused, unwritten."""
    await register(client)
    headers = await vendor_auth(client)
    scan = await self_scan(client, headers)

    for body in (
        {"action": "confirm"},
        {"action": "reject", "note": "we relabelled it"},
        {"action": "override", "note": "surely fine", "overridden_verdict": "PASS"},
    ):
        response = await client.post(f"/scans/{scan['id']}/review", json=body, headers=headers)
        assert response.status_code == 401, (body, response.text)
    category = await client.post(
        f"/scans/{scan['id']}/category", json={"product_category": "food"}, headers=headers
    )
    assert category.status_code == 401, category.text

    as_vendor = await client.get(f"/vendor/scans/{scan['id']}", headers=headers)
    assert as_vendor.json()["scan"]["finalised"] is False


# --- routing and visibility ------------------------------------------------------------------


async def test_a_vendor_scan_is_filed_in_the_premises_territory_and_reaches_its_inspector(
    client: AsyncClient,
) -> None:
    """The routing rule: the scan carries the register's jurisdiction, not a request's."""
    await register(client)
    headers = await vendor_auth(client)
    scan = await self_scan(client, headers)

    async with get_session_factory()() as session:
        row = await session.get(Scan, scan["id"])
    assert (row.state, row.region, row.district) == ("Maharashtra", "Pune", "Satara")
    assert row.officer_id == f"{VENDOR_SUBJECT_PREFIX}patil-kirana"
    assert row.product_category is None

    covering = await client.get(f"/scans/{scan['id']}", headers=auth(INSPECTOR))
    assert covering.status_code == 200, covering.text
    assert scan["id"] in {
        s["id"] for s in (await client.get("/scans", headers=auth(INSPECTOR))).json()
    }
    assert (await client.get(f"/scans/{scan['id']}", headers=auth(CONTROLLER))).status_code == 200
    elsewhere = await client.get(f"/scans/{scan['id']}", headers=auth(OTHER_INSPECTOR))
    assert elsewhere.status_code == 404


async def test_a_vendor_sees_only_their_own_submissions(client: AsyncClient) -> None:
    """As a WHERE clause: the list and the detail both join on the vendor in the token."""
    await register(client)
    await register(client, username="second-shop", name="Second Shop")
    first = await vendor_auth(client)
    second = await vendor_auth(client, username="second-shop")

    mine = await self_scan(client, first)
    theirs = await self_scan(client, second)
    officer_scan = (
        await client.post(
            "/scans/image",
            files=_files(),
            data={"calibration_method": "none"},
            headers=auth(INSPECTOR),
        )
    ).json()

    listed = {s["id"] for s in (await client.get("/vendor/scans", headers=first)).json()}
    assert listed == {mine["id"]}
    assert (await client.get(f"/vendor/scans/{mine['id']}", headers=first)).status_code == 200
    assert (await client.get(f"/vendor/scans/{theirs['id']}", headers=first)).status_code == 404
    assert (
        await client.get(f"/vendor/scans/{officer_scan['id']}", headers=first)
    ).status_code == 404
    assert (await client.get(f"/vendor/scans/{uuid4()}", headers=first)).status_code == 404


async def test_the_own_scans_query_is_a_where_clause_on_the_attribution(
    client: AsyncClient,
) -> None:
    from app.modules.vendor.repository import own_scans

    statement = str(own_scans(VendorPrincipal(vendor_id=uuid4(), subject="x")))
    assert "JOIN vendor_scans" in statement
    assert "vendor_scans.vendor_id = " in statement


async def test_a_vendor_scan_carries_its_routing_once_it_has_a_verdict(client: AsyncClient) -> None:
    await register(client)
    headers = await vendor_auth(client)
    scan = await self_scan(client, headers)  # blurred: refused at the gate, no verdict

    view = (await client.get(f"/vendor/scans/{scan['id']}", headers=headers)).json()
    assert view["scan"]["verdict"] is None
    assert view["routing"] is None


async def test_a_deleted_vendor_token_is_refused_at_submission(client: AsyncClient) -> None:
    """A signed token for a vendor id that is not on the register files nothing."""
    ghost = create_vendor_token(VendorPrincipal(vendor_id=uuid4(), subject="ghost"))
    response = await client.post(
        "/vendor/scans/image", files=_files(), headers={"Authorization": f"Bearer {ghost}"}
    )
    assert response.status_code == 401
