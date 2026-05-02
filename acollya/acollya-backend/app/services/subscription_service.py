"""
Subscription service — Stripe Checkout + Customer Portal + status reads.

get_plans          — static plan catalog (no DB)
get_status         — current user subscription state from DB
create_checkout    — create Stripe Checkout Session, return {url, session_id}
create_portal      — create Stripe Customer Portal session, return {url}

Stripe secret key comes from settings.stripe_config["secret_key"].
Price IDs come from settings.stripe_config["monthly_price_id"] /
"annual_price_id" (set via env vars or Secrets Manager).
"""
import logging
from datetime import UTC, datetime, timezone
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.schemas.subscription import (
    CheckoutRequest,
    CheckoutResponse,
    PlanConfig,
    PlansResponse,
    PortalRequest,
    PortalResponse,
    SubscriptionStatusResponse,
)

logger = logging.getLogger(__name__)


def _stripe_client() -> stripe.StripeClient:
    """Return a configured Stripe client (lazy, one per invocation)."""
    cfg = settings.stripe_config
    return stripe.StripeClient(cfg["secret_key"])


# ── Static plan catalog ────────────────────────────────────────────────────────

def get_plans() -> PlansResponse:
    cfg = settings.stripe_config
    plans = [
        PlanConfig(
            id="free",
            name="Gratuito",
            price_brl=0.0,
            stripe_price_id=None,
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
            stripe_price_id=cfg.get("monthly_price_id"),
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
            stripe_price_id=cfg.get("annual_price_id"),
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


# ── Status ─────────────────────────────────────────────────────────────────────

async def get_status(db: AsyncSession, user: User) -> SubscriptionStatusResponse:
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub: Optional[Subscription] = result.scalars().first()

    now = datetime.now(UTC)

    # No subscription row at all
    if sub is None:
        # Check trial (normalize naive datetimes from SQLite)
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
                stripe_customer_id=user.stripe_customer_id,
            )
        return SubscriptionStatusResponse(
            status="none",
            provider=None,
            current_period_end=None,
            cancel_at_period_end=False,
            is_active=False,
            days_remaining=None,
            stripe_customer_id=user.stripe_customer_id,
        )

    is_active = sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)

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
        stripe_customer_id=user.stripe_customer_id,
    )


# ── Checkout ───────────────────────────────────────────────────────────────────

async def create_checkout(
    db: AsyncSession, user: User, data: CheckoutRequest
) -> CheckoutResponse:
    client = _stripe_client()

    # Ensure Stripe customer exists; store it on the user
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = client.customers.create(
            params={
                "email": user.email,
                "name": user.name,
                "metadata": {"user_id": str(user.id)},
            }
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        await db.commit()
        logger.info("Created Stripe customer %s for user %s", customer_id, user.id)

    session = client.checkout.sessions.create(
        params={
            "customer": customer_id,
            "client_reference_id": str(user.id),
            "line_items": [{"price": data.price_id, "quantity": 1}],
            "mode": "subscription",
            "success_url": data.success_url,
            "cancel_url": data.cancel_url,
            "metadata": {"user_id": str(user.id)},
            "subscription_data": {
                "metadata": {"user_id": str(user.id)},
            },
        }
    )

    logger.info(
        "Checkout session created: user=%s session=%s price=%s",
        user.id, session.id, data.price_id,
    )
    return CheckoutResponse(session_id=session.id, url=session.url)


# ── Customer Portal ────────────────────────────────────────────────────────────

async def create_portal(
    db: AsyncSession, user: User, data: PortalRequest
) -> PortalResponse:
    if not user.stripe_customer_id:
        raise ValidationError(
            "No payment method on file. Please subscribe first."
        )

    client = _stripe_client()
    session = client.billing_portal.sessions.create(
        params={
            "customer": user.stripe_customer_id,
            "return_url": data.return_url,
        }
    )

    logger.info("Portal session created: user=%s customer=%s", user.id, user.stripe_customer_id)
    return PortalResponse(url=session.url)
