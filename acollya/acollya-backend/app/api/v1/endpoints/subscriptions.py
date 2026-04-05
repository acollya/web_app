"""
Subscription endpoints.

GET  /subscriptions/plans      — public plan catalog (no auth required)
GET  /subscriptions/status     — current user's subscription state
POST /subscriptions/checkout   — create Stripe Checkout Session
POST /subscriptions/portal     — create Stripe Customer Portal session
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.subscription import (
    CheckoutRequest,
    CheckoutResponse,
    PlansResponse,
    PortalRequest,
    PortalResponse,
    SubscriptionStatusResponse,
)
from app.services import subscription_service

router = APIRouter()


@router.get(
    "/plans",
    response_model=PlansResponse,
    summary="List available subscription plans",
)
async def list_plans() -> PlansResponse:
    # NOTE: /plans must be registered before /{id} style routes if any are added
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


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create a Stripe Checkout Session",
)
async def create_checkout(
    body: CheckoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CheckoutResponse:
    return await subscription_service.create_checkout(db, current_user, body)


@router.post(
    "/portal",
    response_model=PortalResponse,
    summary="Create a Stripe Customer Portal session",
)
async def create_portal(
    body: PortalRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PortalResponse:
    return await subscription_service.create_portal(db, current_user, body)
