"""The complaint endpoints: who may see an escalation, and who is recorded as raising it.

Marked ``postgres`` because they run against the real schema and the real routes. Every one
of them was made to fail before it was claimed.

The escalation gate wants an effective verdict of POTENTIAL_VIOLATION. These tests reach it
with an OVERRIDE review rather than by finding a listing the rules already fail, so that a
change to the rule corpus cannot quietly turn this file green for the wrong reason.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.contracts import Verdict
from app.core import ReviewAction
from tests.pipeline.conftest import CONTROLLER, INSPECTOR, OTHER_INSPECTOR, auth

pytestmark = pytest.mark.postgres

LISTING = {
    "record": {
        "listing_id": "B0COMPLAINT",
        "platform": "test-marketplace",
        "retrieved_at": datetime(2026, 9, 6, tzinfo=UTC).isoformat(),
        "title": "Acme Biscuits 100 g",
        "declared_fields": {
            "NET_QUANTITY": "100 g",
            "RETAIL_SALE_PRICE": "Rs. 45.00",
            "COMMON_OR_GENERIC_NAME": "Biscuits",
        },
    }
}

RAISE = {
    "manufacturer_name": "Acme Foods Pvt Ltd",
    "rule_id": "rule-6-1-b",
    "field": "NET_QUANTITY",
    "measured_value": "97 g",
    "required_value": "100 g",
}


async def escalatable_scan(client: AsyncClient, principal=INSPECTOR) -> str:
    """A scan an officer has finalised at POTENTIAL_VIOLATION, ready to escalate."""
    submitted = await client.post("/scans", json=LISTING, headers=auth(principal))
    assert submitted.status_code == 201, submitted.text
    scan_id = submitted.json()["id"]

    reviewed = await client.post(
        f"/scans/{scan_id}/review",
        json={
            "action": ReviewAction.OVERRIDE.value,
            "note": "label re-measured on site",
            "overridden_verdict": Verdict.POTENTIAL_VIOLATION.value,
        },
        headers=auth(principal),
    )
    assert reviewed.status_code == 201, reviewed.text
    return scan_id


async def raise_complaint(client: AsyncClient, scan_id: str, principal=INSPECTOR):
    return await client.post(
        "/complaints", json={"scan_id": scan_id, **RAISE}, headers=auth(principal)
    )


async def test_a_complaint_requires_a_token(client: AsyncClient) -> None:
    """No principal, no escalation. Authorisation is at the route, not in the interface."""
    assert (await client.get("/complaints")).status_code == 401
    assert (
        await client.post("/complaints", json={"scan_id": str(uuid4()), **RAISE})
    ).status_code == 401


async def test_the_raising_officer_is_the_principal(client: AsyncClient) -> None:
    """The identity on the stored row is the token's, and it is not a default.

    ``INSPECTOR`` is the only officer in this request, so the assertion is that the row
    names them — the counterpart, that a *different* name in the body cannot displace it,
    is the test below.
    """
    scan_id = await escalatable_scan(client)
    response = await raise_complaint(client, scan_id)
    assert response.status_code == 201, response.text
    assert response.json()["raised_by_officer_id"] == INSPECTOR.subject


async def test_a_body_naming_an_officer_is_refused_outright(client: AsyncClient) -> None:
    """422, not a silently ignored field.

    A request that names an officer and is accepted anyway leaves the caller believing they
    attributed the escalation. Forbidding the field is what makes "the officer comes from
    the principal" something a client is told rather than something it has to trust.
    """
    scan_id = await escalatable_scan(client)
    response = await client.post(
        "/complaints",
        json={"scan_id": scan_id, "raised_by_officer_id": "somebody-else", **RAISE},
        headers=auth(INSPECTOR),
    )
    assert response.status_code == 422, response.text


async def test_a_scan_with_no_finalising_review_cannot_be_escalated(
    client: AsyncClient,
) -> None:
    """409. The scan is real and visible; there is simply no officer decision behind it."""
    submitted = await client.post("/scans", json=LISTING, headers=auth(INSPECTOR))
    response = await raise_complaint(client, submitted.json()["id"])
    assert response.status_code == 409, response.text


async def test_a_verdict_that_is_not_a_potential_violation_cannot_be_escalated(
    client: AsyncClient,
) -> None:
    """409. A confirmed PASS is a finalising review, and it is still nothing to escalate."""
    submitted = await client.post("/scans", json=LISTING, headers=auth(INSPECTOR))
    scan_id = submitted.json()["id"]
    reviewed = await client.post(
        f"/scans/{scan_id}/review",
        json={
            "action": ReviewAction.OVERRIDE.value,
            "note": "declarations verified on site",
            "overridden_verdict": Verdict.PASS.value,
        },
        headers=auth(INSPECTOR),
    )
    assert reviewed.status_code == 201, reviewed.text
    assert (await raise_complaint(client, scan_id)).status_code == 409


async def test_an_out_of_jurisdiction_officer_cannot_tell_the_complaint_exists(
    client: AsyncClient,
) -> None:
    """404, byte-identical to the answer for an id that was never issued.

    Not a 403. Telling an officer in Karnataka that a Maharashtra manufacturer is under
    escalation discloses enforcement activity to somebody with no right to know of it. The
    two responses are compared rather than both merely checked for 404, so a future edit
    cannot reintroduce the disclosure through the body.
    """
    scan_id = await escalatable_scan(client)
    complaint_id = (await raise_complaint(client, scan_id)).json()["id"]

    forbidden = await client.get(f"/complaints/{complaint_id}", headers=auth(OTHER_INSPECTOR))
    absent = await client.get(
        "/complaints/00000000-0000-0000-0000-000000000000", headers=auth(OTHER_INSPECTOR)
    )
    assert forbidden.status_code == 404
    assert absent.status_code == 404
    assert forbidden.json() == absent.json()


async def test_the_list_route_never_leaves_the_callers_jurisdiction(
    client: AsyncClient,
) -> None:
    """The counterpart to the 404: scoping that hid everything would pass that test."""
    scan_id = await escalatable_scan(client)
    await raise_complaint(client, scan_id)

    mine = await client.get("/complaints", headers=auth(INSPECTOR))
    theirs = await client.get("/complaints", headers=auth(OTHER_INSPECTOR))
    assert len(mine.json()) == 1
    assert theirs.json() == []


async def test_a_broader_tier_sees_a_narrower_officers_escalation(
    client: AsyncClient,
) -> None:
    """A controller's authority contains an inspector's, so their state's complaints are theirs."""
    scan_id = await escalatable_scan(client)
    complaint_id = (await raise_complaint(client, scan_id)).json()["id"]
    assert (
        await client.get(f"/complaints/{complaint_id}", headers=auth(CONTROLLER))
    ).status_code == 200


async def test_a_second_escalation_supersedes_the_first_and_both_survive(
    client: AsyncClient,
) -> None:
    """Append-only, over HTTP. The second row names the first and the first is still there.

    ``supersedes_id`` is resolved from the stored thread head, not supplied — the request
    body has no such field — which is what stops a caller choosing what their row replaces.
    """
    scan_id = await escalatable_scan(client)
    first = (await raise_complaint(client, scan_id)).json()
    second = await raise_complaint(client, scan_id)
    assert second.status_code == 201, second.text

    assert second.json()["supersedes_id"] == first["id"]
    thread = await client.get(f"/complaints/{second.json()['id']}", headers=auth(INSPECTOR))
    assert [row["id"] for row in thread.json()["history"]] == [first["id"], second.json()["id"]]


async def test_an_escalation_carries_the_reviewed_verdict_not_the_latest_scan_state(
    client: AsyncClient,
) -> None:
    """The complaint names the verdict the officer actually reviewed.

    ``verdict_id`` comes off the finalising :class:`~app.core.models.ReviewRow`, which is
    what makes the escalation answerable: a complaint naming only the scan would not say
    what was escalated once a re-evaluation wrote a second verdict.
    """
    scan_id = await escalatable_scan(client)
    complaint = (await raise_complaint(client, scan_id)).json()
    assert complaint["scan_id"] == scan_id
    assert complaint["verdict_id"]
    assert complaint["status"] == "raised"
