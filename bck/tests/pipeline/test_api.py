"""The scan endpoints: what they return, who may see it, and what they refuse to do.

Marked ``postgres`` because they run against the real schema. Every one of them was made
to fail before it was claimed.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.contracts import Verdict
from app.core import ReviewAction

from .conftest import CONTROLLER, INSPECTOR, OTHER_INSPECTOR, auth

pytestmark = pytest.mark.postgres

LISTING = {
    "record": {
        "listing_id": "B0TEST",
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


async def submit(client: AsyncClient, principal=INSPECTOR) -> dict:
    response = await client.post("/scans", json=LISTING, headers=auth(principal))
    assert response.status_code == 201, response.text
    return response.json()


async def test_a_scan_requires_a_token(client: AsyncClient) -> None:
    """No principal, no scan. Authorisation is at the route, not in the interface."""
    assert (await client.post("/scans", json=LISTING)).status_code == 401


async def test_a_submitted_scan_carries_its_rule_set_version(client: AsyncClient) -> None:
    """A finding is only meaningful against the rules that produced it.

    A client rendering a verdict without knowing which published set it came from cannot
    tell a re-evaluation from a contradiction.
    """
    scan = await submit(client)
    assert scan["rule_set_version"]
    assert scan["verdict"] in {member.value for member in Verdict}
    assert scan["findings"]


async def test_every_read_route_carries_the_rule_set_version(client: AsyncClient) -> None:
    scan = await submit(client)
    detail = await client.get(f"/scans/{scan['id']}", headers=auth(INSPECTOR))
    listed = await client.get("/scans", headers=auth(INSPECTOR))
    assert detail.json()["rule_set_version"]
    assert all(row["rule_set_version"] for row in listed.json())


async def test_an_out_of_jurisdiction_officer_cannot_tell_the_scan_exists(
    client: AsyncClient,
) -> None:
    """404, byte-identical to the answer for an id that was never issued.

    Not a 403. Telling an officer in Karnataka that a Maharashtra scan exists but is not
    theirs discloses cross-jurisdiction enforcement activity to somebody with no right to
    know of it. The two responses are compared rather than both merely checked for 404, so
    a future edit cannot reintroduce the disclosure through the body.
    """
    scan = await submit(client)
    forbidden = await client.get(f"/scans/{scan['id']}", headers=auth(OTHER_INSPECTOR))
    absent = await client.get(
        "/scans/00000000-0000-0000-0000-000000000000", headers=auth(OTHER_INSPECTOR)
    )
    assert forbidden.status_code == 404
    assert absent.status_code == 404
    assert forbidden.json() == absent.json()


async def test_an_officer_sees_their_own_jurisdiction(client: AsyncClient) -> None:
    """The counterpart: scoping that hid everything would pass the test above."""
    scan = await submit(client)
    assert (await client.get(f"/scans/{scan['id']}", headers=auth(INSPECTOR))).status_code == 200


async def test_a_broader_tier_sees_a_narrower_officers_scan(client: AsyncClient) -> None:
    """A controller's authority contains an inspector's, so their state's scans are theirs."""
    scan = await submit(client)
    assert (await client.get(f"/scans/{scan['id']}", headers=auth(CONTROLLER))).status_code == 200


async def test_the_list_route_never_leaves_the_callers_jurisdiction(
    client: AsyncClient,
) -> None:
    await submit(client)
    mine = await client.get("/scans", headers=auth(INSPECTOR))
    theirs = await client.get("/scans", headers=auth(OTHER_INSPECTOR))
    assert len(mine.json()) == 1
    assert theirs.json() == []


async def test_filters_do_not_widen_the_jurisdiction(client: AsyncClient) -> None:
    """A filter narrows what an officer sees. It can never widen it."""
    await submit(client)
    response = await client.get(
        "/scans",
        params={"product": "Biscuits", "status": "complete", "limit": 200},
        headers=auth(OTHER_INSPECTOR),
    )
    assert response.json() == []


async def test_a_declaration_filter_matches_what_was_actually_read(
    client: AsyncClient,
) -> None:
    """``product`` searches the findings, so it matches the reading rather than a copy."""
    await submit(client)
    hit = await client.get("/scans", params={"product": "Biscuit"}, headers=auth(INSPECTOR))
    miss = await client.get("/scans", params={"product": "Shampoo"}, headers=auth(INSPECTOR))
    assert len(hit.json()) == 1
    assert miss.json() == []


async def test_a_scan_is_not_finalised_until_an_officer_reviews_it(
    client: AsyncClient,
) -> None:
    """Submission produces a verdict. It does not produce agreement with one."""
    scan = await submit(client)
    assert scan["finalised"] is False
    detail = await client.get(f"/scans/{scan['id']}", headers=auth(INSPECTOR))
    assert detail.json()["finalised"] is False
    assert detail.json()["status"] == "complete"


async def test_confirming_finalises_the_scan(client: AsyncClient) -> None:
    """The one path to a finalised scan, and it is a person taking it."""
    scan = await submit(client)
    review = await client.post(
        f"/scans/{scan['id']}/review",
        json={"action": ReviewAction.CONFIRM.value},
        headers=auth(INSPECTOR),
    )
    assert review.status_code == 201, review.text
    assert review.json()["finalised"] is True
    detail = await client.get(f"/scans/{scan['id']}", headers=auth(INSPECTOR))
    assert detail.json()["finalised"] is True


async def test_an_annotation_records_without_finalising(client: AsyncClient) -> None:
    """A note is not a decision, and asking for a better photograph is not one either."""
    scan = await submit(client)
    for action in (ReviewAction.ANNOTATE, ReviewAction.REQUEST_RECAPTURE):
        response = await client.post(
            f"/scans/{scan['id']}/review",
            json={"action": action.value, "note": "the panel is partly obscured"},
            headers=auth(INSPECTOR),
        )
        assert response.status_code == 201, response.text
        assert response.json()["finalised"] is False


async def test_an_override_must_state_the_verdict_it_substitutes(
    client: AsyncClient,
) -> None:
    """An override that names no verdict has not said what the officer decided."""
    scan = await submit(client)
    response = await client.post(
        f"/scans/{scan['id']}/review",
        json={"action": ReviewAction.OVERRIDE.value, "note": "checked by hand"},
        headers=auth(INSPECTOR),
    )
    assert response.status_code == 422


async def test_a_rejection_must_say_why(client: AsyncClient) -> None:
    """A rejection nobody explained is not reviewable by the next person to read it."""
    scan = await submit(client)
    response = await client.post(
        f"/scans/{scan['id']}/review",
        json={"action": ReviewAction.REJECT.value},
        headers=auth(INSPECTOR),
    )
    assert response.status_code == 422


async def test_an_out_of_jurisdiction_officer_cannot_review(client: AsyncClient) -> None:
    """The review route is scoped the same way the reads are."""
    scan = await submit(client)
    response = await client.post(
        f"/scans/{scan['id']}/review",
        json={"action": ReviewAction.CONFIRM.value},
        headers=auth(OTHER_INSPECTOR),
    )
    assert response.status_code == 404


async def test_a_correction_supersedes_rather_than_edits(client: AsyncClient) -> None:
    """Reviews are events. A correction is a new row naming the one it replaces."""
    scan = await submit(client)
    first = await client.post(
        f"/scans/{scan['id']}/review",
        json={"action": ReviewAction.CONFIRM.value},
        headers=auth(INSPECTOR),
    )
    second = await client.post(
        f"/scans/{scan['id']}/review",
        json={
            "action": ReviewAction.OVERRIDE.value,
            "note": "re-examined the panel",
            "overridden_verdict": Verdict.REVIEW.value,
            "supersedes_id": first.json()["id"],
        },
        headers=auth(INSPECTOR),
    )
    assert second.status_code == 201, second.text
    assert second.json()["supersedes_id"] == first.json()["id"]
    assert second.json()["id"] != first.json()["id"]


async def test_an_unknown_product_category_is_refused_rather_than_stored(
    client: AsyncClient,
) -> None:
    """A category the sector dispatch does not know would silently route nothing."""
    body = LISTING | {"product_category": "confectionery"}
    response = await client.post("/scans", json=body, headers=auth(INSPECTOR))
    assert response.status_code == 422


async def test_cors_answers_the_vite_origin_and_nobody_else(client: AsyncClient) -> None:
    """The officer surface is the only thing that should be calling this API."""
    allowed = await client.options(
        "/scans",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    denied = await client.options(
        "/scans",
        headers={
            "Origin": "https://not-the-officer-surface.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers
