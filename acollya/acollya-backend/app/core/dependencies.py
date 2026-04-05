"""
FastAPI dependency injection functions.

Depends chain:
  get_redis          -> Redis client from app.state (set during lifespan)
  get_db             -> AsyncSession (one per request, auto-closed)
  get_current_user   -> User ORM object (requires valid access token)
  get_optional_user  -> User | None (allows anonymous access)
  require_premium    -> User (raises 402 if not subscribed)

Typical endpoint usage:

    @router.get("/chat")
    async def chat(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
    ):
        ...
"""
import logging
import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_access_token
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    TrialExpiredError,
    PremiumRequiredError,
)
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)

# OAuth2 scheme — extracts Bearer token from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ── Redis ──────────────────────────────────────────────────────────────────────

async def get_redis(request: Request) -> Redis:
    """
    Return the Redis client stored on app.state.

    app.state.redis is set in main.py lifespan on cold start.
    """
    redis: Redis | None = getattr(request.app.state, "redis", None)
    if redis is None:
        raise RuntimeError("Redis client not initialised (check lifespan startup)")
    return redis


# ── Database ───────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:  # type: ignore[override]
    """Yield one AsyncSession per request, always closed on exit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ── Auth ───────────────────────────────────────────────────────────────────────

async def _resolve_user(
    token: str | None,
    db: AsyncSession,
    required: bool,
) -> User | None:
    """Shared logic for get_current_user and get_optional_user."""
    if token is None:
        if required:
            raise AuthenticationError("Authorization header missing")
        return None

    payload = decode_access_token(token)  # raises TokenExpiredError / InvalidTokenError
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token has no subject")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthorizationError("Account is deactivated")

    return user


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Require a valid access token. Raises 401 on failure."""
    user = await _resolve_user(token, db, required=True)
    assert user is not None  # guaranteed by required=True
    return user


async def get_optional_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Return User if token is present and valid, None otherwise."""
    return await _resolve_user(token, db, required=False)


# ── Subscription guards ────────────────────────────────────────────────────────

async def require_premium(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Require the user to have an active subscription.

    Trial period counts as active (checked via trial_ends_at on User).
    Raises TrialExpiredError or PremiumRequiredError (both 402).
    """
    from datetime import UTC, datetime

    # Check active subscription in DB
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    )
    subscription: Subscription | None = result.scalar_one_or_none()

    if subscription is not None:
        return user

    # Check trial window
    if user.trial_ends_at and user.trial_ends_at > datetime.now(UTC):
        return user

    # No active subscription and trial has ended
    if user.trial_ends_at:
        raise TrialExpiredError()
    raise PremiumRequiredError()
