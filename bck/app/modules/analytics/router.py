"""FastAPI router for read-only analytics aggregates.

**Officer routes, every one.** An aggregate of potential-violation counts by district is
enforcement intelligence, so each route requires a verified principal and hands it to the
repository, which scopes the scans it counts to that officer's jurisdiction. There is no
jurisdiction parameter here, so there is nothing for a caller to widen.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import Principal, get_current_principal, get_session
from app.modules.analytics import service
from app.modules.analytics.schemas import (
    CategoryAggregateCell,
    DailyAggregateCell,
    JurisdictionAggregateCell,
    RuleAggregateCell,
)

analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])

Session = Annotated[AsyncSession, Depends(get_session)]
Officer = Annotated[Principal, Depends(get_current_principal)]


@analytics_router.get("/by-rule")
async def aggregate_by_rule(session: Session, principal: Officer) -> list[RuleAggregateCell]:
    """Return privacy-eligible distinct-scan cohorts for failing findings by rule."""
    return await service.by_rule(session, principal)


@analytics_router.get("/by-category")
async def aggregate_by_category(
    session: Session, principal: Officer
) -> list[CategoryAggregateCell]:
    """Return privacy-eligible potential-verdict cohorts by confirmed category."""
    return await service.by_category(session, principal)


@analytics_router.get("/over-time")
async def aggregate_over_time(session: Session, principal: Officer) -> list[DailyAggregateCell]:
    """Return privacy-eligible potential-verdict cohorts by UTC evaluation day."""
    return await service.over_time(session, principal)


@analytics_router.get("/jurisdiction")
async def aggregate_by_jurisdiction(
    session: Session, principal: Officer
) -> list[JurisdictionAggregateCell]:
    """Return privacy-eligible potential-verdict cohorts by scan jurisdiction."""
    return await service.by_jurisdiction(session, principal)
