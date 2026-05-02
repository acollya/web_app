"""
User service — business logic for /users/me endpoints.

Operations:
  get_me(user)          -> UserResponse (thin wrapper, no DB query needed)
  update_me(db, user, data) -> UserResponse
  delete_me(db, user)   -> None  (LGPD right-to-erasure)

LGPD deletion strategy:
  Rather than a hard DELETE (which would cascade and lose analytics data),
  we anonymise the user record and mark is_active=False.
  Personally identifiable fields are overwritten with placeholder values.
  A background job (future) can hard-delete after a 30-day retention window.
"""
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
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


async def delete_me(db: AsyncSession, user: User) -> None:
    """
    LGPD Art. 18 — right to erasure.

    Anonymises PII fields and deactivates the account.
    The actual row is preserved for 30 days for audit purposes (configurable).
    """
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
    user.stripe_customer_id = None
    user.revenue_cat_id = None
    user.is_active = False
    user.is_anonymized = True
    user.anonymized_at = datetime.now(UTC)

    await db.commit()
    logger.info("User %s anonymised (LGPD deletion request)", user.id)
