"""
User service — business logic for /users/me endpoints.

Operations:
  get_me(user)                    -> UserResponse (thin wrapper, no DB query needed)
  update_me(db, user, data)       -> UserResponse
  delete_me(db, user, redis)      -> None  (LGPD right-to-erasure)

LGPD deletion strategy:
  Rather than a hard DELETE (which would cascade and lose analytics data),
  we anonymise the user record and mark is_active=False.
  Personally identifiable fields are overwritten with placeholder values.
  Identity-linked tables (persona_facts, user_sessions) are hard-deleted.
  All active refresh tokens are invalidated in Redis.
  A background job (future) can hard-delete the user row after a 30-day retention window.

What is DELETED on erasure request:
  - users fields: all PII overwritten (email, name, phone, birth_date, gender,
    google_id, apple_id, password_hash, push tokens, revenue_cat_id)
  - user_persona_facts: extracted identity facts ("lives in X", "has anxiety")
  - user_sessions: device fingerprints (user_agent, device_type, IP)
  - Redis refresh_jti:{jti} keys: all active refresh tokens revoked

What is PRESERVED intentionally for future ML fine-tuning:
  - chat_messages, journal_entries, mood_checkins, program_progress,
    appointments, RAG embeddings (chat/journal/mood vectors)
  Legal basis: LGPD Art. 12 — these rows reference only the anonymised UUID.
  After erasure the UUID cannot re-identify the data subject because all PII
  columns in `users` have been zeroed; the UUID is a pseudonymous key with no
  remaining linkage to a natural person.
"""
import logging
import uuid
from datetime import UTC, datetime
from typing import Optional

from redis.asyncio import Redis
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_persona_fact import UserPersonaFact
from app.models.user_session import UserSession
from app.schemas.user import UserResponse, UserUpdate

logger = logging.getLogger(__name__)


def get_me(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


async def update_me(db: AsyncSession, user: User, data: UserUpdate) -> UserResponse:
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


async def delete_me(
    db: AsyncSession,
    user: User,
    redis: Optional[Redis] = None,
) -> None:
    """
    LGPD Art. 18 — right to erasure.

    Execution order:
      1. Hard-delete persona_facts — extracted identity data (PII category).
      2. Hard-delete user_sessions — device fingerprints (PII category).
      3. Anonymise all PII fields on the users row and mark is_active=False.
      4. Commit the DB transaction (points 1-3 are atomic).
      5. Revoke all active refresh tokens in Redis (best-effort, non-fatal).

    What is DELETED:
      - user_persona_facts rows for this user
      - user_sessions rows for this user
      - users PII columns (email, name, phone, birth_date, gender,
        google_id, apple_id, password_hash, push tokens, revenue_cat_id)
      - Redis keys matching refresh_jti:* whose value equals this user_id

    What is PRESERVED (LGPD Art. 12 — pseudonymous data):
      - chat_messages, journal_entries, mood_checkins, program_progress,
        appointments, and all RAG embedding vectors.
      These rows reference only the anonymised UUID. After erasure the UUID
      cannot re-identify the data subject because all PII in `users` is zeroed.
    """
    user_id_str = str(user.id)

    # 1. Delete identity-linked facts
    await db.execute(sql_delete(UserPersonaFact).where(UserPersonaFact.user_id == user.id))

    # 2. Delete device-fingerprint sessions
    await db.execute(sql_delete(UserSession).where(UserSession.user_id == user.id))

    # 3. Anonymise PII columns on the user row
    anon_id = str(uuid.uuid4())[:8]
    user.email = f"deleted_{anon_id}@acollya.invalid"
    user.name = "Conta encerrada"
    user.phone = None
    user.birth_date = None
    user.gender = None
    user.google_id = None
    user.apple_id = None
    user.password_hash = None
    user.push_token_fcm = None
    user.push_token_apns = None
    user.revenue_cat_id = None
    user.is_active = False
    user.is_anonymized = True
    user.anonymized_at = datetime.now(UTC)

    # 4. Commit steps 1-3 atomically
    await db.commit()
    logger.info(
        "User %s anonymised (LGPD deletion request): persona_facts and user_sessions deleted",
        user.id,
    )

    # 5. Revoke all active refresh tokens in Redis (best-effort — must not raise)
    if redis is not None:
        await _revoke_user_refresh_tokens(redis, user_id_str)


async def _revoke_user_refresh_tokens(redis: Redis, user_id: str) -> None:
    """
    Scan Redis for all refresh_jti:* keys belonging to user_id and delete them.

    Uses SCAN (non-blocking, cursor-based) to avoid KEYS blocking the server.
    Errors are caught and logged — token revocation must never fail the deletion
    request because the DB transaction has already committed.

    Key format: refresh_jti:{jti}  →  value: user_id (str)
    """
    try:
        keys_to_delete: list[str] = []
        cursor: int = 0

        while True:
            cursor, keys = await redis.scan(cursor, match="refresh_jti:*", count=100)
            for key in keys:
                value = await redis.get(key)
                if value == user_id:
                    keys_to_delete.append(key)
            if cursor == 0:
                break

        if keys_to_delete:
            await redis.delete(*keys_to_delete)
            logger.info(
                "Revoked %d refresh token(s) for deleted user %s",
                len(keys_to_delete),
                user_id,
            )
        else:
            logger.debug("No active refresh tokens found in Redis for user %s", user_id)

    except Exception as exc:  # noqa: BLE001
        # Non-fatal: tokens will naturally expire within 30 days.
        # The user row is already deactivated so _validate_jti in auth_service
        # will reject any attempt to use them before they expire.
        logger.error(
            "Failed to revoke Redis refresh tokens for user %s: %s",
            user_id,
            exc,
            exc_info=True,
        )
