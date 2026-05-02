"""
Subscription service — plan catalog, status reads, and RevenueCat webhook sync.

get_plans                 — static plan catalog (no DB)
get_status                — current user subscription state from DB
handle_revenuecat_event   — apply a RevenueCat webhook event to user + subscription

Payments are handled by RevenueCat (iOS/Android IAP).
"""
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.schemas.subscription import (
    PlanConfig,
    PlansResponse,
    SubscriptionStatusResponse,
)

logger = logging.getLogger(__name__)


# ── RevenueCat event constants ───────────────────────────────────────────────

# Events that grant / refresh premium access.
_GRANT_EVENTS = {"INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE", "UNCANCELLATION"}
# Events that schedule cancellation at period end (access stays until expiry).
_CANCEL_EVENTS = {"CANCELLATION"}
# Events that immediately revoke access.
_EXPIRE_EVENTS = {"EXPIRATION"}
# Events that put the subscription into a non-active billing-issue state.
_BILLING_ISSUE_EVENTS = {"BILLING_ISSUES_DETECTED", "BILLING_ISSUE"}


def get_plans() -> PlansResponse:
    plans = [
        PlanConfig(
            id="free",
            name="Gratuito",
            price_brl=0.0,
            billing_period=None,
            features=[
                "Até 20 mensagens por dia com a IA",
                "Diário pessoal",
                "Registro de humor",
                "2 programas gratuitos",
            ],
            is_popular=False,
        ),
        PlanConfig(
            id="monthly",
            name="Premium Mensal",
            price_brl=17.90,
            billing_period="month",
            features=[
                "Mensagens ilimitadas com a IA",
                "Todos os programas",
                "Histórico completo",
                "Agendamento com terapeutas",
                "Desconto nas consultas",
                "Sem anúncios",
            ],
            is_popular=False,
        ),
        PlanConfig(
            id="annual",
            name="Premium Anual",
            price_brl=179.90,
            billing_period="year",
            features=[
                "Tudo do Premium Mensal",
                "Economia de 16% ao ano",
                "Suporte prioritário",
            ],
            is_popular=True,
        ),
    ]
    return PlansResponse(plans=plans)


async def get_status(db: AsyncSession, user: User) -> SubscriptionStatusResponse:
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub: Optional[Subscription] = result.scalars().first()

    now = datetime.now(UTC)

    if sub is None:
        trial_ends = user.trial_ends_at
        if trial_ends is not None and trial_ends.tzinfo is None:
            trial_ends = trial_ends.replace(tzinfo=UTC)
        if trial_ends and trial_ends > now:
            days = max(0, (trial_ends - now).days)
            return SubscriptionStatusResponse(
                status="trialing",
                provider=None,
                current_period_end=trial_ends,
                cancel_at_period_end=False,
                is_active=True,
                days_remaining=days,
            )
        return SubscriptionStatusResponse(
            status="none",
            provider=None,
            current_period_end=None,
            cancel_at_period_end=False,
            is_active=False,
            days_remaining=None,
        )

    is_active = sub.status in (SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value)

    days_remaining: Optional[int] = None
    if sub.current_period_end:
        end = sub.current_period_end
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        days_remaining = max(0, (end - now).days)

    return SubscriptionStatusResponse(
        status=sub.status,
        provider=sub.provider,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        is_active=is_active,
        days_remaining=days_remaining,
    )


# ── RevenueCat webhook handler ───────────────────────────────────────────────

def _ms_to_datetime(value: Optional[int]) -> Optional[datetime]:
    """Convert a RevenueCat millisecond epoch to an aware UTC datetime."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    except (OverflowError, OSError, TypeError, ValueError):
        return None


def _extract_entitlement(event: dict[str, Any]) -> Optional[str]:
    """Best-effort extraction of the entitlement identifier from an event."""
    entitlement = event.get("entitlement_id")
    if entitlement:
        return entitlement
    ids = event.get("entitlement_ids") or []
    if isinstance(ids, list) and ids:
        return ids[0]
    return None


def _candidate_user_keys(event: dict[str, Any]) -> list[str]:
    """Collect non-empty identifiers RevenueCat may use to refer to a user."""
    keys: list[str] = []
    for raw in (
        event.get("app_user_id"),
        event.get("original_app_user_id"),
        *(event.get("aliases") or []),
    ):
        if isinstance(raw, str) and raw and raw not in keys:
            keys.append(raw)
    return keys


async def _find_user_by_event(
    db: AsyncSession, event: dict[str, Any]
) -> Optional[User]:
    """Resolve the User referenced by a RevenueCat event.

    Lookup order:
      1. Match against User.revenue_cat_id using all known identifiers (safe — read-only).
      2. UUID fallback — only for the primary app_user_id, never for aliases/original_app_user_id.
         This prevents an attacker-controlled alias from being matched to another user's UUID.
    """
    candidates = _candidate_user_keys(event)
    if candidates:
        result = await db.execute(
            select(User).where(User.revenue_cat_id.in_(candidates))
        )
        user = result.scalars().first()
        if user is not None:
            return user

    # UUID fallback restricted to primary app_user_id only to prevent alias-based IDOR
    aid = event.get("app_user_id")
    if isinstance(aid, str) and aid:
        try:
            result = await db.execute(select(User).where(User.id == uuid.UUID(aid)))
            return result.scalar_one_or_none()
        except (ValueError, AttributeError):
            pass

    return None


async def _get_or_create_subscription(
    db: AsyncSession, user: User, entitlement: Optional[str]
) -> Subscription:
    """Fetch the Subscription row for (user, entitlement) or create a new one.

    Idempotent: repeated webhook deliveries for the same entitlement reuse the
    existing row instead of inserting duplicates.
    """
    stmt = select(Subscription).where(Subscription.user_id == user.id)
    if entitlement is not None:
        stmt = stmt.where(Subscription.revenue_cat_entitlement == entitlement)
    stmt = stmt.order_by(Subscription.created_at.desc()).limit(1)

    result = await db.execute(stmt)
    sub = result.scalars().first()

    if sub is not None:
        return sub

    sub = Subscription(
        user_id=user.id,
        provider="revenue_cat",
        revenue_cat_entitlement=entitlement,
        status=SubscriptionStatus.ACTIVE.value,
        cancel_at_period_end=False,
    )
    db.add(sub)
    return sub


async def handle_revenuecat_event(db: AsyncSession, event: dict[str, Any]) -> None:
    """Process a RevenueCat webhook event and sync subscription state.

    Always commits or rolls back its own transaction. Unknown event types are
    silently ignored so RevenueCat's retry pipeline is not exercised by
    forward-compatible additions.
    """
    event_type = (event.get("type") or "").upper()
    if not event_type:
        logger.warning("revenuecat_event_missing_type")
        return

    user = await _find_user_by_event(db, event)
    if user is None:
        # Likely a race: webhook arrived before the user record exists locally.
        # Returning cleanly tells RevenueCat we accepted the event; subsequent
        # RENEWAL events (or a fetcher) will reconcile state when the user appears.
        logger.info(
            "revenuecat_event_user_not_found",
            extra={"event_type": event_type, "candidates": _candidate_user_keys(event)},
        )
        return

    entitlement = _extract_entitlement(event)
    period_start = _ms_to_datetime(event.get("purchased_at_ms"))
    period_end = _ms_to_datetime(event.get("expiration_at_ms"))

    try:
        if event_type in _GRANT_EVENTS:
            sub = await _get_or_create_subscription(db, user, entitlement)
            sub.provider = "revenue_cat"
            sub.revenue_cat_entitlement = entitlement
            sub.status = SubscriptionStatus.ACTIVE.value
            sub.cancel_at_period_end = False
            if period_start is not None:
                sub.current_period_start = period_start
            # Only advance period_end — never regress it (guards against out-of-order delivery)
            if period_end is not None and (
                sub.current_period_end is None or period_end >= sub.current_period_end
            ):
                sub.current_period_end = period_end

            user.subscription_status = "active"
            user.plan_code = 1
            # Backfill revenue_cat_id only from the primary app_user_id (never aliases)
            if user.revenue_cat_id is None:
                aid = event.get("app_user_id")
                if isinstance(aid, str) and aid:
                    user.revenue_cat_id = aid

        elif event_type in _CANCEL_EVENTS:
            sub = await _get_or_create_subscription(db, user, entitlement)
            sub.cancel_at_period_end = True
            # Access remains until current_period_end; status stays ACTIVE.
            sub.status = SubscriptionStatus.ACTIVE.value
            if period_end is not None:
                sub.current_period_end = period_end
            user.subscription_status = "active"

        elif event_type in _EXPIRE_EVENTS:
            sub = await _get_or_create_subscription(db, user, entitlement)
            sub.status = SubscriptionStatus.CANCELED.value
            sub.cancel_at_period_end = False
            if period_end is not None:
                sub.current_period_end = period_end
            user.subscription_status = "canceled"
            user.plan_code = 0

        elif event_type in _BILLING_ISSUE_EVENTS:
            sub = await _get_or_create_subscription(db, user, entitlement)
            sub.status = SubscriptionStatus.PAST_DUE.value
            user.subscription_status = "past_due"

        else:
            # Unknown / unhandled event type — acknowledge silently.
            logger.info(
                "revenuecat_event_ignored",
                extra={"event_type": event_type, "user_id": str(user.id)},
            )
            return

        await db.commit()
        logger.info(
            "revenuecat_event_processed",
            extra={"event_type": event_type, "user_id": str(user.id)},
        )
    except Exception:
        await db.rollback()
        raise
