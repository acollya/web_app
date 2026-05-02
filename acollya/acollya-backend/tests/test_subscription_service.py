"""
Tests for app/services/subscription_service.py

Covers:
  get_plans   — 3 plans, structure, free plan is free, annual is popular
  get_status  — trial active, trial expired, active sub row, past_due sub row
"""
from datetime import UTC, datetime, timedelta

from app.models.subscription import Subscription, SubscriptionStatus
from app.services import subscription_service


# ── get_plans ──────────────────────────────────────────────────────────────────

def test_get_plans_returns_three_plans():
    resp = subscription_service.get_plans()
    assert len(resp.plans) == 3


def test_get_plans_free_is_zero_price():
    resp = subscription_service.get_plans()
    free = next(p for p in resp.plans if p.id == "free")
    assert free.price_brl == 0.0
    assert free.billing_period is None


def test_get_plans_annual_is_popular():
    resp = subscription_service.get_plans()
    annual = next(p for p in resp.plans if p.id == "annual")
    assert annual.is_popular is True


def test_get_plans_monthly_is_not_popular():
    resp = subscription_service.get_plans()
    monthly = next(p for p in resp.plans if p.id == "monthly")
    assert monthly.is_popular is False


# ── get_status ─────────────────────────────────────────────────────────────────

async def test_get_status_trial_active_no_sub_row(db, test_user):
    """User in trial with no Subscription row → status=trialing, is_active=True."""
    resp = await subscription_service.get_status(db, test_user)

    assert resp.status == "trialing"
    assert resp.is_active is True
    assert resp.days_remaining is not None
    assert resp.days_remaining > 0
    assert resp.provider is None


async def test_get_status_trial_expired_no_sub_row(db, test_user):
    """Expired trial with no Subscription row → status=none, is_active=False."""
    test_user.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
    await db.commit()

    resp = await subscription_service.get_status(db, test_user)

    assert resp.status == "none"
    assert resp.is_active is False
    assert resp.days_remaining is None


async def test_get_status_with_active_subscription(db, test_user):
    """Active Subscription row → is_active=True, days_remaining > 0."""
    future = datetime.now(UTC) + timedelta(days=30)
    sub = Subscription(
        user_id=test_user.id,
        provider="revenue_cat",
        status=SubscriptionStatus.ACTIVE,
        current_period_end=future,
        cancel_at_period_end=False,
    )
    db.add(sub)
    await db.commit()

    resp = await subscription_service.get_status(db, test_user)

    assert resp.status == SubscriptionStatus.ACTIVE
    assert resp.is_active is True
    assert resp.days_remaining is not None
    assert resp.days_remaining > 0
    assert resp.provider == "revenue_cat"


async def test_get_status_past_due_is_not_active(db, test_user):
    """past_due Subscription → is_active=False."""
    sub = Subscription(
        user_id=test_user.id,
        provider="revenue_cat",
        status=SubscriptionStatus.PAST_DUE,
        cancel_at_period_end=False,
    )
    db.add(sub)
    await db.commit()

    resp = await subscription_service.get_status(db, test_user)

    assert resp.status == SubscriptionStatus.PAST_DUE
    assert resp.is_active is False


async def test_get_status_canceled_is_not_active(db, test_user):
    sub = Subscription(
        user_id=test_user.id,
        provider="revenue_cat",
        status=SubscriptionStatus.CANCELED,
        cancel_at_period_end=False,
    )
    db.add(sub)
    await db.commit()

    resp = await subscription_service.get_status(db, test_user)
    assert resp.is_active is False
