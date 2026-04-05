"""
Stripe webhook service — event processing.

handle_stripe_event  — dispatch incoming verified Stripe event to the right handler

Handled events:
  checkout.session.completed          → upsert subscription from checkout metadata
  customer.subscription.created       → upsert subscription
  customer.subscription.updated       → upsert subscription (handles renewals, upgrades)
  customer.subscription.deleted       → mark subscription canceled
  invoice.payment_failed              → update subscription status to past_due

Stripe → DB status mapping:
  active          → SubscriptionStatus.ACTIVE      + user.plan_code=1
  trialing        → SubscriptionStatus.TRIALING     + user.plan_code=1
  past_due/unpaid → SubscriptionStatus.PAST_DUE     + user.plan_code=0
  canceled        → SubscriptionStatus.CANCELED     + user.plan_code=0
  *anything else  → plan_code=0
"""
import logging
import uuid
from datetime import UTC, datetime, timezone
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Stripe status → internal status ───────────────────────────────────────────

_STATUS_MAP: dict[str, str] = {
    "active":    SubscriptionStatus.ACTIVE,
    "trialing":  SubscriptionStatus.TRIALING,
    "past_due":  SubscriptionStatus.PAST_DUE,
    "canceled":  SubscriptionStatus.CANCELED,
    "unpaid":    SubscriptionStatus.UNPAID,
}

_ACTIVE_STATUSES = {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}


def _plan_code_for_status(status: str) -> int:
    return 1 if status in _ACTIVE_STATUSES else 0


def _ts_to_dt(ts: Optional[int]) -> Optional[datetime]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)


# ── Main dispatcher ────────────────────────────────────────────────────────────

async def handle_stripe_event(db: AsyncSession, event: stripe.Event) -> None:
    event_type: str = event["type"]
    logger.info("Processing Stripe event: %s id=%s", event_type, event["id"])

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, event["data"]["object"])

    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        await _upsert_from_subscription(db, event["data"]["object"])

    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, event["data"]["object"])

    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, event["data"]["object"])

    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)


# ── Handlers ───────────────────────────────────────────────────────────────────

async def _handle_checkout_completed(db: AsyncSession, session: dict) -> None:
    """
    checkout.session.completed fires when payment succeeds.

    We resolve the user via client_reference_id (user.id UUID) and
    ensure stripe_customer_id is stored on the user record.
    The subscription object is not yet guaranteed to be in the event at this
    point, so we just sync the customer ID; the customer.subscription.created
    event carries the full subscription payload.
    """
    user_id: Optional[str] = session.get("client_reference_id")
    customer_id: Optional[str] = session.get("customer")

    if not user_id or not customer_id:
        logger.warning(
            "checkout.session.completed missing client_reference_id or customer: %s",
            session.get("id"),
        )
        return

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        logger.error("checkout.session.completed: invalid user_id format: %s", user_id)
        return
    result = await db.execute(select(User).where(User.id == uid))
    user: Optional[User] = result.scalar_one_or_none()
    if not user:
        logger.error("checkout.session.completed: user %s not found", user_id)
        return

    if user.stripe_customer_id != customer_id:
        user.stripe_customer_id = customer_id
        await db.commit()
        logger.info("Stored stripe_customer_id %s on user %s", customer_id, user_id)


async def _upsert_from_subscription(db: AsyncSession, sub_obj: dict) -> None:
    """
    Upsert a Subscription row from a Stripe subscription object.

    Uses stripe_subscription_id as the idempotency key.
    Resolves user via sub_obj.metadata.user_id (set at checkout) or
    via customer → user.stripe_customer_id.
    """
    stripe_sub_id: str = sub_obj["id"]
    customer_id: str = sub_obj["customer"]
    stripe_status: str = sub_obj.get("status", "")
    internal_status = _STATUS_MAP.get(stripe_status, SubscriptionStatus.CANCELED)

    price_id: Optional[str] = None
    items = sub_obj.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")

    period_start = _ts_to_dt(sub_obj.get("current_period_start"))
    period_end = _ts_to_dt(sub_obj.get("current_period_end"))
    cancel_at_period_end: bool = sub_obj.get("cancel_at_period_end", False)

    # Resolve user
    user = await _resolve_user(db, sub_obj, customer_id)
    if not user:
        return

    # Upsert subscription row
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    sub: Optional[Subscription] = result.scalar_one_or_none()

    if sub is None:
        sub = Subscription(
            user_id=user.id,
            provider="stripe",
            stripe_subscription_id=stripe_sub_id,
            stripe_price_id=price_id,
            status=internal_status,
            current_period_start=period_start,
            current_period_end=period_end,
            cancel_at_period_end=cancel_at_period_end,
        )
        db.add(sub)
    else:
        sub.status = internal_status
        sub.stripe_price_id = price_id
        sub.current_period_start = period_start
        sub.current_period_end = period_end
        sub.cancel_at_period_end = cancel_at_period_end

    # Sync denormalised fields on User
    user.subscription_status = internal_status
    user.plan_code = _plan_code_for_status(internal_status)

    await db.commit()
    logger.info(
        "Subscription upserted: user=%s stripe_sub=%s status=%s",
        user.id, stripe_sub_id, internal_status,
    )


async def _handle_subscription_deleted(db: AsyncSession, sub_obj: dict) -> None:
    stripe_sub_id: str = sub_obj["id"]
    customer_id: str = sub_obj["customer"]

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    sub: Optional[Subscription] = result.scalar_one_or_none()
    if not sub:
        logger.warning("customer.subscription.deleted: sub %s not in DB", stripe_sub_id)
        return

    sub.status = SubscriptionStatus.CANCELED
    sub.cancel_at_period_end = False

    # Sync user
    result2 = await db.execute(select(User).where(User.id == sub.user_id))
    user: Optional[User] = result2.scalar_one_or_none()
    if user:
        user.subscription_status = SubscriptionStatus.CANCELED
        user.plan_code = 0

    await db.commit()
    logger.info("Subscription canceled: stripe_sub=%s", stripe_sub_id)


async def _handle_payment_failed(db: AsyncSession, invoice: dict) -> None:
    stripe_sub_id: Optional[str] = invoice.get("subscription")
    if not stripe_sub_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    sub: Optional[Subscription] = result.scalar_one_or_none()
    if not sub:
        logger.warning("invoice.payment_failed: sub %s not in DB", stripe_sub_id)
        return

    sub.status = SubscriptionStatus.PAST_DUE

    result2 = await db.execute(select(User).where(User.id == sub.user_id))
    user: Optional[User] = result2.scalar_one_or_none()
    if user:
        user.subscription_status = SubscriptionStatus.PAST_DUE
        user.plan_code = 0

    await db.commit()
    logger.info("Payment failed, subscription marked past_due: stripe_sub=%s", stripe_sub_id)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _resolve_user(
    db: AsyncSession, sub_obj: dict, customer_id: str
) -> Optional[User]:
    """
    Resolve user from subscription metadata.user_id (preferred) or
    via user.stripe_customer_id (fallback).
    """
    user_id: Optional[str] = (sub_obj.get("metadata") or {}).get("user_id")

    if user_id:
        try:
            uid = uuid.UUID(user_id)
            result = await db.execute(select(User).where(User.id == uid))
            user = result.scalar_one_or_none()
            if user:
                return user
        except ValueError:
            pass
        logger.warning("_resolve_user: metadata.user_id=%s not found, falling back to customer", user_id)

    # Fallback: match by stripe_customer_id
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.error(
            "_resolve_user: cannot resolve user for customer=%s sub=%s",
            customer_id, sub_obj.get("id"),
        )
    return user
