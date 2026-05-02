"""
Auth service — business logic for all authentication flows.

Flows:
  register(db, redis, req)    -> TokenResponse
  login(db, redis, req)       -> TokenResponse
  refresh_tokens(db, redis, refresh_token) -> TokenResponse
  logout(redis, refresh_token)
  google_auth(db, redis, req) -> TokenResponse

Redis key convention for refresh token JTIs:
  Key:  refresh_jti:{jti}            -> value: user_id (str), TTL: 30 days
  Key:  user_sessions:{user_id}      -> SET of jti, TTL synced to longest jti

Secondary index rationale:
  The `user_sessions:{user_id}` SET is a reverse lookup so we can list / revoke
  every active refresh token for a user in O(1) without SCAN. Membership in
  this set is also the ownership check used by DELETE /users/me/sessions/{jti}
  — a user can only revoke a jti present in *their* set.

Rotation strategy:
  On refresh:  delete old jti (and SREM from set), issue new access + refresh
               pair, store new jti (and SADD to set).
  On logout:   delete jti and SREM from set — token is immediately revoked.
  Consequence: stolen refresh tokens are mitigated because the legitimate user's
               next refresh will rotate, invalidating the stolen token.
"""
import logging
import uuid
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_apple_identity_token,
    verify_google_id_token,
    verify_password,
)
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    InvalidTokenError,
)
from app.models.user import User
from app.schemas.auth import AppleAuthRequest, GoogleAuthRequest, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

_JTI_PREFIX = "refresh_jti"
_USER_SESSIONS_PREFIX = "user_sessions"


def _jti_key(jti: str) -> str:
    return f"{_JTI_PREFIX}:{jti}"


def _user_sessions_key(user_id: str) -> str:
    return f"{_USER_SESSIONS_PREFIX}:{user_id}"


def _token_ttl() -> int:
    return settings.jwt_config.get("refresh_token_expire_days", 30) * 86400


def _access_ttl() -> int:
    return settings.jwt_config.get("access_token_expire_minutes", 15) * 60


async def _store_jti(redis: Redis, jti: str, user_id: str) -> None:
    """
    Persist the jti -> user_id mapping AND register the jti in the user's
    session set so we can list/revoke without SCAN.

    Both keys share the same TTL. EXPIREAT on the set is bumped to the latest
    jti's expiration so the set lives at least as long as its newest member.
    """
    user_id = str(user_id)
    ttl = _token_ttl()
    sessions_key = _user_sessions_key(user_id)

    pipe = redis.pipeline()
    pipe.setex(_jti_key(jti), ttl, user_id)
    pipe.sadd(sessions_key, jti)
    pipe.expire(sessions_key, ttl)
    await pipe.execute()


async def _validate_jti(redis: Redis, jti: str) -> str:
    """Return user_id stored under jti, or raise InvalidTokenError."""
    user_id = await redis.get(_jti_key(jti))
    if not user_id:
        raise InvalidTokenError("Refresh token has been revoked or expired")
    return user_id


async def _revoke_jti(redis: Redis, jti: str, user_id: str | None = None) -> None:
    """
    Delete the jti key and remove it from the user's session set.

    user_id is optional — if not provided we read it from the jti key first
    (so the secondary index stays consistent even when the caller doesn't
    know the owner).
    """
    if user_id is None:
        user_id = await redis.get(_jti_key(jti))

    pipe = redis.pipeline()
    pipe.delete(_jti_key(jti))
    if user_id:
        pipe.srem(_user_sessions_key(str(user_id)), jti)
    await pipe.execute()


# ── Session management (used by /users/me/sessions endpoints) ─────────────────

async def list_sessions(redis: Redis, user_id: str) -> list[dict]:
    """
    Return every active refresh-token session for user_id.

    For each jti we read its TTL to derive an approximate created_at /
    expires_at (the actual JWT iat/exp aren't stored separately to keep the
    key compact; the TTL gives us a usable approximation for UX).

    Stale entries (jti present in the set but key already expired) are pruned
    from the set on the fly so the index self-heals.
    """
    sessions_key = _user_sessions_key(str(user_id))
    members = await redis.smembers(sessions_key)
    if not members:
        return []

    ttl_max = _token_ttl()
    now = datetime.now(UTC)
    stale: list[str] = []
    sessions: list[dict] = []

    for raw in members:
        jti = raw.decode() if isinstance(raw, bytes) else raw
        ttl = await redis.ttl(_jti_key(jti))
        if ttl is None or ttl < 0:
            stale.append(jti)
            continue

        expires_at = now + timedelta(seconds=ttl)
        created_at = expires_at - timedelta(seconds=ttl_max)
        sessions.append({"jti": jti, "created_at": created_at, "expires_at": expires_at})

    if stale:
        await redis.srem(sessions_key, *stale)

    sessions.sort(key=lambda s: s["created_at"], reverse=True)
    return sessions


async def revoke_session(redis: Redis, user_id: str, jti: str) -> bool:
    """
    Revoke a single session — only if it belongs to user_id.

    Ownership is verified via SET membership (`user_sessions:{user_id}`):
    a user can never revoke another user's jti. Returns True if the jti was
    found and revoked, False otherwise (idempotent — caller treats both as 200).
    """
    sessions_key = _user_sessions_key(str(user_id))
    is_member = await redis.sismember(sessions_key, jti)
    if not is_member:
        return False

    pipe = redis.pipeline()
    pipe.delete(_jti_key(jti))
    pipe.srem(sessions_key, jti)
    await pipe.execute()
    return True


async def revoke_all_sessions(redis: Redis, user_id: str) -> int:
    """
    Revoke every active refresh-token session for user_id.

    Used on password change and on LGPD account deletion. Returns the number
    of sessions invalidated.
    """
    sessions_key = _user_sessions_key(str(user_id))
    members = await redis.smembers(sessions_key)
    if not members:
        return 0

    jtis = [m.decode() if isinstance(m, bytes) else m for m in members]

    pipe = redis.pipeline()
    for jti in jtis:
        pipe.delete(_jti_key(jti))
    pipe.delete(sessions_key)
    await pipe.execute()

    logger.info("Revoked %d session(s) for user %s", len(jtis), user_id)
    return len(jtis)


def _build_token_response(
    user: User,
    access_token: str,
    refresh_token: str,
    is_new_user: bool = False,
) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=_access_ttl(),
        user_id=str(user.id),
        is_new_user=is_new_user,
        user=UserResponse.model_validate(user),
    )


# ── Register ───────────────────────────────────────────────────────────────────

async def register(db: AsyncSession, redis: Redis, req: RegisterRequest) -> TokenResponse:
    # Duplicate email check
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise ConflictError("An account with this email already exists")

    now = datetime.now(UTC)
    user = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        trial_ends_at=now + timedelta(days=settings.trial_days),
        subscription_status="trialing",
        terms_accepted=req.terms_accepted,
        terms_accepted_date=now if req.terms_accepted else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id))
    refresh_token, jti = create_refresh_token(str(user.id))
    await _store_jti(redis, jti, str(user.id))

    logger.info("New user registered: %s", user.id)
    return _build_token_response(user, access_token, refresh_token, is_new_user=True)


# ── Login ──────────────────────────────────────────────────────────────────────

async def login(db: AsyncSession, redis: Redis, req: LoginRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == req.email))
    user: User | None = result.scalar_one_or_none()

    # Constant-time path: always call verify_password to prevent timing attacks
    dummy_hash = "$2b$12$" + "a" * 53
    stored = user.password_hash if (user and user.password_hash) else dummy_hash
    valid = verify_password(req.password, stored)

    if not user or not valid:
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    access_token = create_access_token(str(user.id))
    refresh_token, jti = create_refresh_token(str(user.id))
    await _store_jti(redis, jti, str(user.id))

    return _build_token_response(user, access_token, refresh_token)


# ── Refresh ────────────────────────────────────────────────────────────────────

async def refresh_tokens(
    db: AsyncSession, redis: Redis, refresh_token: str
) -> TokenResponse:
    payload = decode_refresh_token(refresh_token)
    jti: str = payload.get("jti", "")
    user_id: str = payload.get("sub", "")

    await _validate_jti(redis, jti)  # raises InvalidTokenError if revoked

    # Ensure user still exists and is active
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user: User | None = result.scalar_one_or_none()
    if not user or not user.is_active:
        await _revoke_jti(redis, jti, user_id)
        raise AuthenticationError("User not found or deactivated")

    # Rotate: revoke old jti, issue new pair
    await _revoke_jti(redis, jti, str(user.id))
    new_access = create_access_token(str(user.id))
    new_refresh, new_jti = create_refresh_token(str(user.id))
    await _store_jti(redis, new_jti, str(user.id))

    return _build_token_response(user, new_access, new_refresh)


# ── Logout ─────────────────────────────────────────────────────────────────────

async def logout(redis: Redis, refresh_token: str) -> None:
    try:
        payload = decode_refresh_token(refresh_token)
        jti: str = payload.get("jti", "")
        if jti:
            await _revoke_jti(redis, jti)
    except Exception:
        # Logout is always successful from the client's perspective
        pass


# ── Google OAuth ───────────────────────────────────────────────────────────────

async def google_auth(
    db: AsyncSession, redis: Redis, req: GoogleAuthRequest
) -> TokenResponse:
    google_data = await verify_google_id_token(req.id_token)
    google_id: str = google_data["sub"]
    email: str = google_data["email"]
    name: str = google_data.get("name", email.split("@")[0])

    is_new_user = False

    # Try by google_id first, then by email (link existing account)
    result = await db.execute(select(User).where(User.google_id == google_id))
    user: User | None = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user:
        # Link google_id if not already linked
        if not user.google_id:
            user.google_id = google_id
            await db.commit()
    else:
        # New user via Google
        is_new_user = True
        now = datetime.now(UTC)
        user = User(
            email=email,
            name=name,
            google_id=google_id,
            trial_ends_at=now + timedelta(days=settings.trial_days),
            subscription_status="trialing",
            terms_accepted=req.terms_accepted,
            terms_accepted_date=now if req.terms_accepted else None,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    access_token = create_access_token(str(user.id))
    refresh_token, jti = create_refresh_token(str(user.id))
    await _store_jti(redis, jti, str(user.id))

    return _build_token_response(user, access_token, refresh_token, is_new_user=is_new_user)


async def apple_auth(
    db: AsyncSession, redis: Redis, req: AppleAuthRequest
) -> TokenResponse:
    apple_data = await verify_apple_identity_token(req.identity_token)
    apple_id: str = apple_data["sub"]
    # Apple only provides email on first sign-in
    email: str | None = apple_data.get("email")

    is_new_user = False

    # Try by apple_id first
    result = await db.execute(select(User).where(User.apple_id == apple_id))
    user: User | None = result.scalar_one_or_none()

    if not user and email:
        # Try by email (link existing account)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user:
        if not user.apple_id:
            user.apple_id = apple_id
            await db.commit()
    else:
        if not email:
            raise AuthenticationError("Apple did not provide email — cannot create account")
        is_new_user = True
        name = req.full_name or email.split("@")[0]
        now = datetime.now(UTC)
        user = User(
            email=email,
            name=name,
            apple_id=apple_id,
            trial_ends_at=now + timedelta(days=settings.trial_days),
            subscription_status="trialing",
            terms_accepted=req.terms_accepted,
            terms_accepted_date=now if req.terms_accepted else None,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    access_token = create_access_token(str(user.id))
    refresh_token, jti = create_refresh_token(str(user.id))
    await _store_jti(redis, jti, str(user.id))

    return _build_token_response(user, access_token, refresh_token, is_new_user=is_new_user)
