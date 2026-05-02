"""
User endpoints.

GET    /users/me   — get current user profile
PATCH  /users/me   — update profile fields
DELETE /users/me   — LGPD right-to-erasure (anonymise account)
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import UserResponse, UserUpdate
from app.services import user_service

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current user's profile",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return user_service.get_me(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update profile fields",
)
async def update_me(
    body: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    return await user_service.update_me(db, current_user, body)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account (LGPD right-to-erasure)",
)
async def delete_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> Response:
    await user_service.delete_me(db, current_user, redis)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
