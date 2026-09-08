"""The vendor register endpoints: who is on it, and who may see them.

Marked ``postgres`` because they run against the real schema and the real routes. Every one
of them was made to fail before it was claimed.

Vendors are inserted directly rather than through a route, because there is no create route
and deliberately so — a vendor row is written while attributing a scan. What is under test
is the scoping on the way back out.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core import VendorRow, VendorType
from app.core.db import get_session_factory
from tests.pipeline.conftest import CONTROLLER, INSPECTOR, OTHER_INSPECTOR, auth

pytestmark = pytest.mark.postgres

SATARA = {"state": "Maharashtra", "region": "Pune", "district": "Satara"}
MYSURU = {"state": "Karnataka", "region": "Mysuru", "district": "Mysuru"}
STATEWIDE = {"state": "Maharashtra", "region": None, "district": None}


async def register(**vendors: dict) -> dict[str, str]:
    """Put named vendors on the register and return their ids."""
    ids = {}
    async with get_session_factory()() as session, session.begin():
        for name, territory in vendors.items():
            row = VendorRow(id=uuid4(), name=name, vendor_type=VendorType.KIRANA, **territory)
            session.add(row)
            ids[name] = str(row.id)
    return ids


async def test_the_register_requires_a_token(client: AsyncClient) -> None:
    """No principal, no register. Authorisation is at the route, not in the interface."""
    assert (await client.get("/vendors")).status_code == 401
    assert (await client.get(f"/vendors/{uuid4()}")).status_code == 401


async def test_an_officer_sees_the_vendors_in_their_own_district(client: AsyncClient) -> None:
    ids = await register(Kirana=SATARA)
    response = await client.get(f"/vendors/{ids['Kirana']}", headers=auth(INSPECTOR))
    assert response.status_code == 200, response.text
    assert response.json()["jurisdiction"] == SATARA


async def test_an_out_of_jurisdiction_officer_cannot_tell_the_vendor_exists(
    client: AsyncClient,
) -> None:
    """404, byte-identical to the answer for an id that was never issued.

    Not a 403. Telling an officer in Karnataka that a Maharashtra premises is on the register
    discloses which establishments another state's department knows about. The two responses
    are compared rather than both merely checked for 404, so a future edit cannot
    reintroduce the disclosure through the body.
    """
    ids = await register(Kirana=SATARA)
    forbidden = await client.get(f"/vendors/{ids['Kirana']}", headers=auth(OTHER_INSPECTOR))
    absent = await client.get(
        "/vendors/00000000-0000-0000-0000-000000000000", headers=auth(OTHER_INSPECTOR)
    )
    assert forbidden.status_code == 404
    assert absent.status_code == 404
    assert forbidden.json() == absent.json()


async def test_the_list_route_never_leaves_the_callers_jurisdiction(
    client: AsyncClient,
) -> None:
    """Each officer sees their own district and nothing of the other's."""
    await register(Kirana=SATARA, Nandini=MYSURU)

    mine = await client.get("/vendors", headers=auth(INSPECTOR))
    theirs = await client.get("/vendors", headers=auth(OTHER_INSPECTOR))
    assert [row["name"] for row in mine.json()] == ["Kirana"]
    assert [row["name"] for row in theirs.json()] == ["Nandini"]


async def test_a_broader_tier_sees_every_vendor_in_its_state(client: AsyncClient) -> None:
    """A controller's authority contains an inspector's, and one level it does not pin.

    The statewide row is the point: it has no district, so it is invisible to the district
    officer above and visible here. That is ``NULL = 'Satara'`` never being true, not a bug —
    a NULL says the level was never recorded, not that it matches everything.
    """
    await register(Kirana=SATARA, Depot=STATEWIDE, Nandini=MYSURU)

    controller = await client.get("/vendors", headers=auth(CONTROLLER))
    inspector = await client.get("/vendors", headers=auth(INSPECTOR))
    assert [row["name"] for row in controller.json()] == ["Depot", "Kirana"]
    assert [row["name"] for row in inspector.json()] == ["Kirana"]


async def test_the_register_carries_no_compliance_summary(client: AsyncClient) -> None:
    """A vendor-submitted scan is an ordinary scan, and this route says nothing about one.

    A verdict count or a trust score here would be the first column an evaluation could
    branch on, which is exactly what the vendor tables are shaped to prevent.
    """
    ids = await register(Kirana=SATARA)
    row = (await client.get(f"/vendors/{ids['Kirana']}", headers=auth(INSPECTOR))).json()
    assert set(row) == {"id", "name", "vendor_type", "jurisdiction", "created_at"}
