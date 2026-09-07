"""Unit tests for manufacturer complaint repository (CMP-001 Part B)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.complaints import ComplaintRow
from app.core.enums import ComplaintStatus
from app.modules.complaints.domain import ComplaintRecord
from app.modules.complaints.repository import (
    _record_to_row,
    _row_to_record,
    add_complaint,
    get_complaint,
    get_complaints_for_scan,
    get_latest_complaint_for_scan,
)


def _make_domain_record(
    status: ComplaintStatus = ComplaintStatus.RAISED,
    supersedes_id=None,
    scan_id=None,
    verdict_id=None,
) -> ComplaintRecord:
    return ComplaintRecord(
        id=uuid4(),
        scan_id=scan_id or uuid4(),
        verdict_id=verdict_id or uuid4(),
        manufacturer_name="Acme Corp",
        issue_summary="Potential violation under rule R2 for net_quantity",
        status=status,
        raised_by_officer_id="OFFICER-001",
        raised_at=datetime.now(UTC),
        supersedes_id=supersedes_id,
    )


def test_record_to_row_and_row_to_record_roundtrip() -> None:
    """Test bi-directional mapping between domain ComplaintRecord and ORM ComplaintRow."""
    rec = _make_domain_record()
    row = _record_to_row(rec)
    assert row.id == rec.id
    assert row.scan_id == rec.scan_id
    assert row.verdict_id == rec.verdict_id
    assert row.manufacturer_name == rec.manufacturer_name
    assert row.issue_summary == rec.issue_summary
    assert row.status == rec.status
    assert row.raised_by_officer_id == rec.raised_by_officer_id
    assert row.supersedes_id is None

    roundtrip = _row_to_record(row)
    assert roundtrip == rec


@pytest.mark.asyncio
async def test_add_complaint() -> None:
    """Test add_complaint stages row and flushes session."""
    session = AsyncMock()
    session.add = MagicMock()
    rec = _make_domain_record()

    res = await add_complaint(session, rec)
    assert res == rec
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_complaint_found_and_not_found() -> None:
    """Test get_complaint returning mapped record or None when not found."""
    session = AsyncMock()
    rec = _make_domain_record()
    row = _record_to_row(rec)

    session.get.return_value = row
    res = await get_complaint(session, rec.id)
    assert res == rec
    session.get.assert_awaited_once_with(ComplaintRow, rec.id)

    session.get.return_value = None
    res_none = await get_complaint(session, uuid4())
    assert res_none is None


@pytest.mark.asyncio
async def test_get_complaints_for_scan() -> None:
    """Test get_complaints_for_scan query execution and mapping."""
    session = AsyncMock()
    scan_id = uuid4()
    r1 = _make_domain_record(scan_id=scan_id)
    r2 = _make_domain_record(scan_id=scan_id, supersedes_id=r1.id)

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [_record_to_row(r1), _record_to_row(r2)]
    session.scalars.return_value = mock_scalars

    res = await get_complaints_for_scan(session, scan_id)
    assert len(res) == 2
    assert res[0] == r1
    assert res[1] == r2
    session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_latest_complaint_for_scan_empty() -> None:
    """Test get_latest_complaint_for_scan returning None when scan history is empty."""
    session = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    session.scalars.return_value = mock_scalars

    res = await get_latest_complaint_for_scan(session, uuid4())
    assert res is None


@pytest.mark.asyncio
async def test_get_latest_complaint_for_scan_resolves_head() -> None:
    """Test get_latest_complaint_for_scan returns thread head when chain exists."""
    session = AsyncMock()
    scan_id = uuid4()
    verdict_id = uuid4()

    r1 = _make_domain_record(ComplaintStatus.RAISED, scan_id=scan_id, verdict_id=verdict_id)
    r2 = _make_domain_record(
        ComplaintStatus.ACKNOWLEDGED,
        supersedes_id=r1.id,
        scan_id=scan_id,
        verdict_id=verdict_id,
    )
    r3 = _make_domain_record(
        ComplaintStatus.RESOLVED,
        supersedes_id=r2.id,
        scan_id=scan_id,
        verdict_id=verdict_id,
    )

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [
        _record_to_row(r1),
        _record_to_row(r2),
        _record_to_row(r3),
    ]
    session.scalars.return_value = mock_scalars

    res = await get_latest_complaint_for_scan(session, scan_id)
    assert res is not None
    assert res.id == r3.id
    assert res.status == ComplaintStatus.RESOLVED
