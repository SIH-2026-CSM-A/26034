"""The complaint lifecycle over HTTP: every transition is a new row, and nothing is edited.

Marked ``postgres``: the fork guard is a database constraint, and only the real schema has it.
"""

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core import ComplaintRow, ComplaintStatus, get_session_factory
from tests.modules.complaints.test_router import escalatable_scan, raise_complaint
from tests.pipeline.conftest import CONTROLLER, INSPECTOR, OTHER_INSPECTOR, auth

pytestmark = pytest.mark.postgres


async def raised(client: AsyncClient) -> dict:
    response = await raise_complaint(client, await escalatable_scan(client))
    assert response.status_code == 201, response.text
    return response.json()


async def move(client: AsyncClient, complaint_id: str, body: dict, principal=INSPECTOR):
    return await client.post(
        f"/complaints/{complaint_id}/transitions", json=body, headers=auth(principal)
    )


async def test_a_transition_is_a_new_superseding_row_and_the_old_row_is_untouched(
    client: AsyncClient,
) -> None:
    first = await raised(client)
    async with get_session_factory()() as session:
        before = (await session.get(ComplaintRow, first["id"])).__dict__.copy()

    response = await move(
        client, first["id"], {"status": "acknowledged", "note": "receipt confirmed by post"}
    )

    assert response.status_code == 201, response.text
    second = response.json()
    assert second["id"] != first["id"]
    assert second["supersedes_id"] == first["id"]
    assert second["status"] == "acknowledged"
    assert second["note"] == "receipt confirmed by post"
    # Restated by value, never reworded.
    for column in ("scan_id", "verdict_id", "manufacturer_name", "issue_summary"):
        assert second[column] == first[column]

    async with get_session_factory()() as session:
        assert await session.scalar(select(func.count()).select_from(ComplaintRow)) == 2
        after = (await session.get(ComplaintRow, first["id"])).__dict__
    for column in [c.name for c in ComplaintRow.__table__.columns]:
        assert after[column] == before[column], column
    assert after["status"] is ComplaintStatus.RAISED


async def test_the_whole_lifecycle_reads_back_as_history(client: AsyncClient) -> None:
    first = await raised(client)
    acknowledged = (await move(client, first["id"], {"status": "acknowledged"})).json()
    resolved = await move(
        client, acknowledged["id"], {"status": "resolved", "note": "batch relabelled"}
    )
    assert resolved.status_code == 201, resolved.text

    thread = await client.get(f"/complaints/{resolved.json()['id']}", headers=auth(INSPECTOR))

    assert [row["status"] for row in thread.json()["history"]] == [
        "raised",
        "acknowledged",
        "resolved",
    ]


async def test_the_transitioning_officer_is_the_principal_never_the_body(
    client: AsyncClient,
) -> None:
    first = await raised(client)

    named = await move(
        client, first["id"], {"status": "acknowledged", "raised_by_officer_id": "someone-else"}
    )
    assert named.status_code == 422, named.text

    response = await move(client, first["id"], {"status": "acknowledged"}, principal=CONTROLLER)
    assert response.status_code == 201, response.text
    assert response.json()["raised_by_officer_id"] == CONTROLLER.subject
    # The thread's first row still names the officer who opened it.
    async with get_session_factory()() as session:
        assert (
            await session.get(ComplaintRow, first["id"])
        ).raised_by_officer_id == INSPECTOR.subject


async def test_a_transition_needs_a_token_and_the_callers_jurisdiction(
    client: AsyncClient,
) -> None:
    first = await raised(client)

    anonymous = await client.post(
        f"/complaints/{first['id']}/transitions", json={"status": "acknowledged"}
    )
    assert anonymous.status_code == 401

    outsider = await move(client, first["id"], {"status": "acknowledged"}, OTHER_INSPECTOR)
    assert outsider.status_code == 404
    async with get_session_factory()() as session:
        assert await session.scalar(select(func.count()).select_from(ComplaintRow)) == 1


@pytest.mark.parametrize("status", ["resolved", "rejected"])
async def test_a_closure_without_a_note_is_refused(client: AsyncClient, status: str) -> None:
    first = await raised(client)
    assert (await move(client, first["id"], {"status": status})).status_code == 422
    assert (await move(client, first["id"], {"status": status, "note": "   "})).status_code == 422


async def test_an_illegal_move_is_a_409_and_writes_nothing(client: AsyncClient) -> None:
    first = await raised(client)
    closed = (await move(client, first["id"], {"status": "rejected", "note": "not theirs"})).json()

    reopened = await move(client, closed["id"], {"status": "acknowledged"})
    back_to_raised = await move(client, closed["id"], {"status": "raised"})

    assert reopened.status_code == 409, reopened.text
    assert back_to_raised.status_code == 409, back_to_raised.text
    async with get_session_factory()() as session:
        assert await session.scalar(select(func.count()).select_from(ComplaintRow)) == 2


async def test_only_the_head_of_a_thread_can_be_transitioned(client: AsyncClient) -> None:
    first = await raised(client)
    assert (await move(client, first["id"], {"status": "acknowledged"})).status_code == 201

    stale = await move(client, first["id"], {"status": "resolved", "note": "stale page"})

    assert stale.status_code == 409, stale.text


async def test_two_simultaneous_transitions_of_one_head_produce_one_row(
    client: AsyncClient,
) -> None:
    first = await raised(client)

    responses = await asyncio.gather(
        move(client, first["id"], {"status": "acknowledged"}),
        move(client, first["id"], {"status": "rejected", "note": "raced"}, CONTROLLER),
    )

    assert sorted(r.status_code for r in responses) == [201, 409]
    async with get_session_factory()() as session:
        successors = await session.scalar(
            select(func.count())
            .select_from(ComplaintRow)
            .where(ComplaintRow.supersedes_id == first["id"])
        )
    assert successors == 1


async def test_the_database_itself_refuses_a_second_successor(client: AsyncClient) -> None:
    """The constraint, without the route's check in front of it."""
    first = await raised(client)
    async with get_session_factory()() as session:
        head = await session.get(ComplaintRow, first["id"])

        def successor() -> ComplaintRow:
            return ComplaintRow(
                scan_id=head.scan_id,
                verdict_id=head.verdict_id,
                manufacturer_name=head.manufacturer_name,
                issue_summary=head.issue_summary,
                status=ComplaintStatus.ACKNOWLEDGED,
                raised_by_officer_id="direct-insert",
                supersedes_id=head.id,
            )

        session.add(successor())
        await session.commit()
        session.add(successor())
        with pytest.raises(IntegrityError, match="uq_complaints_supersedes_id"):
            await session.commit()
