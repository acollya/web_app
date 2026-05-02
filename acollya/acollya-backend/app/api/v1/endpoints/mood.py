"""
Mood check-in endpoints.

POST /mood              — record a check-in (requires trial/premium)
GET  /mood              — paginated history
GET  /mood/insights     — aggregated stats for a period
POST /mood/{id}/insight — generate AI insight for a check-in (Phase 2)
"""
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_premium
from app.models.user import User
from app.schemas.mood import (
    MoodCheckinCreate,
    MoodCheckinResponse,
    MoodHistoryResponse,
    MoodInsightsResponse,
)
from app.services import mood_service
from app.services.persona_service import bg_extract_and_upsert_facts

router = APIRouter()


@router.post(
    "",
    response_model=MoodCheckinResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a mood check-in",
)
async def create_checkin(
    body: MoodCheckinCreate,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MoodCheckinResponse:
    checkin = await mood_service.create_checkin(db, current_user, body, background_tasks)
    if body.note:
        mood_text = f"Humor: {body.mood}, intensidade {body.intensity}/5. Nota: {body.note}"
        background_tasks.add_task(
            bg_extract_and_upsert_facts,
            user_id=current_user.id,
            text_input=mood_text,
            source="mood_checkin",
            source_id=uuid.UUID(checkin.id) if isinstance(checkin.id, str) else checkin.id,
        )
    return checkin


@router.get(
    "",
    response_model=MoodHistoryResponse,
    summary="List mood check-in history (paginated)",
)
async def list_checkins(
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> MoodHistoryResponse:
    return await mood_service.list_checkins(db, current_user, page, page_size)


@router.get(
    "/insights",
    response_model=MoodInsightsResponse,
    summary="Get aggregated mood insights for a period",
)
async def get_insights(
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: Literal["week", "month", "year"] = Query(
        "week", description="Aggregation period"
    ),
) -> MoodInsightsResponse:
    return await mood_service.get_insights(db, current_user, period)


@router.post(
    "/{checkin_id}/insight",
    response_model=MoodCheckinResponse,
    summary="Generate an AI insight for a mood check-in (Phase 2)",
)
async def generate_insight(
    checkin_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MoodCheckinResponse:
    """
    Calls OpenAI with the check-in and recent history to produce a personalised
    insight. Persists the result in MoodCheckin.ai_insight and returns the
    updated check-in. Idempotent — calling again overwrites the previous insight.
    """
    return await mood_service.generate_ai_insight(db, current_user, str(checkin_id))
