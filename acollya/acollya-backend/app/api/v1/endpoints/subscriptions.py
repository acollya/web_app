"""
Subscription endpoints.

GET /subscriptions/plans   — public plan catalog (no auth required)
GET /subscriptions/status  — current user's subscription state
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.subscription import PlansResponse, SubscriptionStatusResponse
from app.services import subscription_service

router = APIRouter()


@router.get(
    "/plans",
    response_model=PlansResponse,
    summary="List available subscription plans",
)
async def list_plans() -> PlansResponse:
    return subscription_service.get_plans()


@router.get(
    "/status",
    response_model=SubscriptionStatusResponse,
    summary="Get current user's subscription status",
)
async def get_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionStatusResponse:
    return await subscription_service.get_status(db, current_user)
