"""
Analytics endpoints.

GET /analytics/overview              — dashboard card metrics
GET /analytics/mood-trend?days=N     — mood intensity trend (default 30 days)
GET /analytics/activity?days=N       — activity heatmap (default 90 days)
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import ActivityResponse, MoodTrendResponse, OverviewResponse
from app.services import analytics_service

router = APIRouter()


@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="Get user's dashboard overview metrics",
)
async def get_overview(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OverviewResponse:
    return await analytics_service.get_overview(db, current_user)


@router.get(
    "/mood-trend",
    response_model=MoodTrendResponse,
    summary="Get daily mood intensity trend",
)
async def get_mood_trend(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=7, le=365, description="Number of past days to include"),
) -> MoodTrendResponse:
    return await analytics_service.get_mood_trend(db, current_user, days)


@router.get(
    "/activity",
    response_model=ActivityResponse,
    summary="Get daily activity for heatmap",
)
async def get_activity(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(90, ge=7, le=365, description="Number of past days to include"),
) -> ActivityResponse:
    return await analytics_service.get_activity(db, current_user, days)
