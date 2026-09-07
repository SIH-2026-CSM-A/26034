"""FastAPI router for read-only analytics aggregates."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_session
from app.modules.analytics import service
from app.modules.analytics.schemas import (
    CategoryAggregateCell,
    DailyAggregateCell,
    JurisdictionAggregateCell,
    RuleAggregateCell,
)

analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])

Session = Annotated[AsyncSession, Depends(get_session)]


@analytics_router.get("/by-rule")
async def aggregate_by_rule(session: Session) -> list[RuleAggregateCell]:
    """Return privacy-eligible distinct-scan cohorts for failing findings by rule."""
    return await service.by_rule(session)


@analytics_router.get("/by-category")
async def aggregate_by_category(session: Session) -> list[CategoryAggregateCell]:
    """Return privacy-eligible potential-verdict cohorts by confirmed category."""
    return await service.by_category(session)


@analytics_router.get("/over-time")
async def aggregate_over_time(session: Session) -> list[DailyAggregateCell]:
    """Return privacy-eligible potential-verdict cohorts by UTC evaluation day."""
    return await service.over_time(session)


@analytics_router.get("/jurisdiction")
async def aggregate_by_jurisdiction(session: Session) -> list[JurisdictionAggregateCell]:
    """Return privacy-eligible potential-verdict cohorts by scan jurisdiction."""
    return await service.by_jurisdiction(session)
