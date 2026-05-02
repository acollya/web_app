"""
User endpoints.

GET    /users/me                       — get current user profile
PATCH  /users/me                       — update profile fields
DELETE /users/me                       — LGPD right-to-erasure (anonymise account)
PATCH  /users/me/password              — change password (revokes all sessions)
GET    /users/me/sessions              — list active refresh-token sessions
DELETE /users/me/sessions/{jti}        — revoke a specific session
DELETE /users/me/sessions              — revoke every active session
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_redis
from app.core.rate_limiter import RateLimiter
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import (
    PasswordChangeRequest,
    SessionListResponse,
    SessionResponse,
    UserResponse,
    UserUpdate,
)
from app.services import auth_service, user_service

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


@router.patch(
    "/me/password",
    response_model=UserResponse,
    summary="Change the authenticated user's password",
    description=(
        "Verifies the current password, updates the bcrypt hash and revokes "
        "every active refresh-token session. The caller will need to log in "
        "again on every device after this call succeeds."
    ),
)
async def change_password(
    body: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> UserResponse:
    await RateLimiter(redis).check_and_increment(
        user_id=str(current_user.id),
        action="password_change",
        limit=5,
        window_seconds=900,
    )
    return await user_service.change_password(db, redis, current_user, body)


@router.get(
    "/me/sessions",
    response_model=SessionListResponse,
    summary="List active refresh-token sessions",
)
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> SessionListResponse:
    raw = await auth_service.list_sessions(redis, str(current_user.id))
    sessions = [SessionResponse(**s) for s in raw]
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.delete(
    "/me/sessions/{jti}",
    response_model=MessageResponse,
    summary="Revoke a specific refresh-token session",
    description=(
        "Idempotent: returns 200 even when the jti does not exist or no longer "
        "belongs to the user. Ownership is verified via the user's session set "
        "— a user can never revoke another user's session."
    ),
)
async def revoke_session(
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
    jti: str = Path(min_length=1, max_length=128),
) -> MessageResponse:
    revoked = await auth_service.revoke_session(redis, str(current_user.id), jti)
    if revoked:
        return MessageResponse(message="Sessão revogada com sucesso")
    return MessageResponse(message="Sessão não encontrada ou já expirada")


@router.delete(
    "/me/sessions",
    response_model=MessageResponse,
    summary="Revoke every active session (log out everywhere)",
)
async def revoke_all_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> MessageResponse:
    count = await auth_service.revoke_all_sessions(redis, str(current_user.id))
    return MessageResponse(message=f"{count} sessão(ões) revogada(s)")
