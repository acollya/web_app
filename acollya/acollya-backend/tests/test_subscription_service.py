"""
Tests for app/services/subscription_service.py

Stripe SDK calls are patched via unittest.mock.patch — no real API calls made.

Covers:
  get_plans        — 3 plans, structure, free plan has no price_id, annual is popular
  get_status       — trial active, trial expired, active sub row, past_due sub row
  create_checkout  — creates new Stripe customer + session; reuses existing customer
  create_portal    — success; raises ValidationError when no stripe_customer_id
"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import ValidationError
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.subscription import CheckoutRequest, PortalRequest
from app.services import subscription_service


# ── get_plans ──────────────────────────────────────────────────────────────────

def test_get_plans_returns_three_plans():
    resp = subscription_service.get_plans()
    assert len(resp.plans) == 3


def test_get_plans_free_has_no_stripe_price_id():
    resp = subscription_service.get_plans()
    free = next(p for p in resp.plans if p.id == "free")
    assert free.stripe_price_id is None
    assert free.price_brl == 0.0


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
        provider="stripe",
        stripe_subscription_id="sub_active_001",
        stripe_price_id="price_monthly",
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
    assert resp.provider == "stripe"


async def test_get_status_past_due_is_not_active(db, test_user):
    """past_due Subscription → is_active=False."""
    sub = Subscription(
        user_id=test_user.id,
        provider="stripe",
        stripe_subscription_id="sub_pd_001",
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
        provider="stripe",
        stripe_subscription_id="sub_can_001",
        status=SubscriptionStatus.CANCELED,
        cancel_at_period_end=False,
    )
    db.add(sub)
    await db.commit()

    resp = await subscription_service.get_status(db, test_user)
    assert resp.is_active is False


# ── create_checkout ────────────────────────────────────────────────────────────

async def test_create_checkout_creates_new_customer(db, test_user):
    """User without stripe_customer_id → creates customer then session."""
    assert test_user.stripe_customer_id is None

    mock_customer = MagicMock()
    mock_customer.id = "cus_NEW_TEST"

    mock_session = MagicMock()
    mock_session.id = "cs_test_001"
    mock_session.url = "https://checkout.stripe.com/cs_test_001"

    mock_client = MagicMock()
    mock_client.customers.create.return_value = mock_customer
    mock_client.checkout.sessions.create.return_value = mock_session

    with patch("app.services.subscription_service._stripe_client", return_value=mock_client):
        resp = await subscription_service.create_checkout(
            db, test_user,
            CheckoutRequest(
                price_id="price_monthly",
                success_url="https://app.acollya.com.br/success",
                cancel_url="https://app.acollya.com.br/cancel",
            ),
        )

    assert resp.session_id == "cs_test_001"
    assert resp.url == "https://checkout.stripe.com/cs_test_001"
    mock_client.customers.create.assert_called_once()

    # Customer ID persisted on user
    await db.refresh(test_user)
    assert test_user.stripe_customer_id == "cus_NEW_TEST"


async def test_create_checkout_reuses_existing_customer(db, test_user):
    """User with existing stripe_customer_id → skips customer.create."""
    test_user.stripe_customer_id = "cus_EXISTING"
    await db.commit()

    mock_session = MagicMock()
    mock_session.id = "cs_test_002"
    mock_session.url = "https://checkout.stripe.com/cs_test_002"

    mock_client = MagicMock()
    mock_client.checkout.sessions.create.return_value = mock_session

    with patch("app.services.subscription_service._stripe_client", return_value=mock_client):
        resp = await subscription_service.create_checkout(
            db, test_user,
            CheckoutRequest(
                price_id="price_annual",
                success_url="https://app.acollya.com.br/success",
                cancel_url="https://app.acollya.com.br/cancel",
            ),
        )

    assert resp.session_id == "cs_test_002"
    mock_client.customers.create.assert_not_called()


# ── create_portal ──────────────────────────────────────────────────────────────

async def test_create_portal_raises_when_no_customer(db, test_user):
    """User with no stripe_customer_id → ValidationError."""
    assert test_user.stripe_customer_id is None

    with pytest.raises(ValidationError):
        await subscription_service.create_portal(
            db, test_user, PortalRequest(return_url="https://app.acollya.com.br")
        )


async def test_create_portal_returns_url(db, test_user):
    test_user.stripe_customer_id = "cus_PORTAL_TEST"
    await db.commit()

    mock_session = MagicMock()
    mock_session.url = "https://billing.stripe.com/session/test"

    mock_client = MagicMock()
    mock_client.billing_portal.sessions.create.return_value = mock_session

    with patch("app.services.subscription_service._stripe_client", return_value=mock_client):
        resp = await subscription_service.create_portal(
            db, test_user, PortalRequest(return_url="https://app.acollya.com.br")
        )

    assert resp.url == "https://billing.stripe.com/session/test"
    mock_client.billing_portal.sessions.create.assert_called_once()
