"""
Subscription service — plan catalog and status reads.

get_plans   — static plan catalog (no DB)
get_status  — current user subscription state from DB

Payments are handled by RevenueCat (iOS/Android IAP).
"""
import logging
from datetime import UTC, datetime
from typing import Optional

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
    )
