"""
Tests for app/services/webhook_service.py

Strategy: construct plain dicts that mimic Stripe event payloads
(the service only uses dict-style access, not stripe SDK objects).
No real Stripe API or network calls needed.

Covers:
  handle_stripe_event  — dispatch to correct handler per event type
  checkout.session.completed  — stores customer_id, missing fields, unknown user
  customer.subscription.created/updated — upsert (insert + update), status mapping
  customer.subscription.deleted — marks canceled, syncs user.plan_code
  invoice.payment_failed — marks past_due, syncs user.plan_code
  _resolve_user — metadata fallback → stripe_customer_id fallback
  unknown event type — no crash
"""
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.services import webhook_service


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_event(event_type: str, obj: dict) -> dict:
    return {
        "type": event_type,
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "data": {"object": obj},
    }


def _make_sub_obj(
    user_id: str,
    status: str = "active",
    stripe_sub_id: str = "sub_test_001",
    customer_id: str = "cus_test_001",
    price_id: str = "price_monthly",
    period_end_ts: int = 9999999999,
) -> dict:
    return {
        "id": stripe_sub_id,
        "customer": customer_id,
        "status": status,
        "items": {"data": [{"price": {"id": price_id}}]},
        "current_period_start": 1700000000,
        "current_period_end": period_end_ts,
        "cancel_at_period_end": False,
        "metadata": {"user_id": user_id},
    }


async def _get_user(db, user_id) -> User:
    result = await db.execute(select(User).where(User.id == uuid.UUID(str(user_id))))
    return result.scalar_one()


async def _get_sub(db, stripe_sub_id: str):
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    return result.scalar_one_or_none()


# ── checkout.session.completed ─────────────────────────────────────────────────

async def test_checkout_completed_stores_customer_id(db, test_user):
    assert test_user.stripe_customer_id is None

    event = _make_event("checkout.session.completed", {
        "id": "cs_test_001",
        "client_reference_id": str(test_user.id),
        "customer": "cus_NEW_001",
    })
    await webhook_service.handle_stripe_event(db, event)

    user = await _get_user(db, test_user.id)
    assert user.stripe_customer_id == "cus_NEW_001"


async def test_checkout_completed_already_has_customer_id(db, test_user):
    """If stripe_customer_id already set, no commit needed — should not crash."""
    test_user.stripe_customer_id = "cus_EXISTING"
    await db.commit()

    event = _make_event("checkout.session.completed", {
        "id": "cs_test_002",
        "client_reference_id": str(test_user.id),
        "customer": "cus_EXISTING",  # same value
    })
    await webhook_service.handle_stripe_event(db, event)  # must not raise

    user = await _get_user(db, test_user.id)
    assert user.stripe_customer_id == "cus_EXISTING"


async def test_checkout_completed_missing_fields_no_crash(db):
    """Missing client_reference_id or customer should log warning and return cleanly."""
    event = _make_event("checkout.session.completed", {"id": "cs_bad"})
    await webhook_service.handle_stripe_event(db, event)  # must not raise


async def test_checkout_completed_unknown_user_no_crash(db):
    """Unknown user_id in client_reference_id should log error and return cleanly."""
    event = _make_event("checkout.session.completed", {
        "id": "cs_test_003",
        "client_reference_id": str(uuid.uuid4()),  # user that doesn't exist
        "customer": "cus_TEST_003",
    })
    await webhook_service.handle_stripe_event(db, event)  # must not raise


# ── customer.subscription.created ─────────────────────────────────────────────

async def test_subscription_created_inserts_row_and_activates_user(db, test_user):
    sub_obj = _make_sub_obj(str(test_user.id), status="active")
    event = _make_event("customer.subscription.created", sub_obj)

    await webhook_service.handle_stripe_event(db, event)

    sub = await _get_sub(db, "sub_test_001")
    assert sub is not None
    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.stripe_price_id == "price_monthly"

    user = await _get_user(db, test_user.id)
    assert user.plan_code == 1
    assert user.subscription_status == SubscriptionStatus.ACTIVE


async def test_subscription_created_trialing_activates_user(db, test_user):
    sub_obj = _make_sub_obj(str(test_user.id), status="trialing", stripe_sub_id="sub_trial_001")
    event = _make_event("customer.subscription.created", sub_obj)

    await webhook_service.handle_stripe_event(db, event)

    user = await _get_user(db, test_user.id)
    assert user.plan_code == 1
    assert user.subscription_status == SubscriptionStatus.TRIALING


# ── customer.subscription.updated ─────────────────────────────────────────────

async def test_subscription_updated_modifies_existing_row(db, test_user):
    # First create
    sub_obj_create = _make_sub_obj(str(test_user.id), status="active", stripe_sub_id="sub_upd_001")
    await webhook_service.handle_stripe_event(db, _make_event("customer.subscription.created", sub_obj_create))

    # Then update to past_due
    sub_obj_update = _make_sub_obj(str(test_user.id), status="past_due", stripe_sub_id="sub_upd_001")
    await webhook_service.handle_stripe_event(db, _make_event("customer.subscription.updated", sub_obj_update))

    sub = await _get_sub(db, "sub_upd_001")
    assert sub.status == SubscriptionStatus.PAST_DUE

    user = await _get_user(db, test_user.id)
    assert user.plan_code == 0
    assert user.subscription_status == SubscriptionStatus.PAST_DUE


# ── customer.subscription.deleted ─────────────────────────────────────────────

async def test_subscription_deleted_marks_canceled(db, test_user):
    # Setup: active subscription
    sub_obj = _make_sub_obj(str(test_user.id), status="active", stripe_sub_id="sub_del_001")
    await webhook_service.handle_stripe_event(db, _make_event("customer.subscription.created", sub_obj))

    # Delete event
    delete_obj = {"id": "sub_del_001", "customer": "cus_test_001"}
    await webhook_service.handle_stripe_event(db, _make_event("customer.subscription.deleted", delete_obj))

    sub = await _get_sub(db, "sub_del_001")
    assert sub.status == SubscriptionStatus.CANCELED
    assert sub.cancel_at_period_end is False

    user = await _get_user(db, test_user.id)
    assert user.plan_code == 0
    assert user.subscription_status == SubscriptionStatus.CANCELED


async def test_subscription_deleted_not_in_db_no_crash(db):
    """Deletion of unknown stripe sub_id should log warning and not raise."""
    delete_obj = {"id": "sub_nonexistent", "customer": "cus_x"}
    event = _make_event("customer.subscription.deleted", delete_obj)
    await webhook_service.handle_stripe_event(db, event)  # must not raise


# ── invoice.payment_failed ─────────────────────────────────────────────────────

async def test_payment_failed_marks_past_due(db, test_user):
    # Setup: active subscription
    sub_obj = _make_sub_obj(str(test_user.id), status="active", stripe_sub_id="sub_fail_001")
    await webhook_service.handle_stripe_event(db, _make_event("customer.subscription.created", sub_obj))

    # Payment failed invoice
    invoice = {"subscription": "sub_fail_001"}
    await webhook_service.handle_stripe_event(db, _make_event("invoice.payment_failed", invoice))

    sub = await _get_sub(db, "sub_fail_001")
    assert sub.status == SubscriptionStatus.PAST_DUE

    user = await _get_user(db, test_user.id)
    assert user.plan_code == 0


async def test_payment_failed_no_subscription_field_no_crash(db):
    """Invoice without subscription field should return early without crashing."""
    invoice = {"id": "in_no_sub"}  # no "subscription" key
    event = _make_event("invoice.payment_failed", invoice)
    await webhook_service.handle_stripe_event(db, event)  # must not raise


# ── _resolve_user fallback ─────────────────────────────────────────────────────

async def test_resolve_user_via_customer_id_fallback(db, test_user):
    """User resolution should fall back to stripe_customer_id when metadata is absent."""
    test_user.stripe_customer_id = "cus_fallback"
    await db.commit()

    sub_obj = {
        "id": "sub_fb_001",
        "customer": "cus_fallback",
        "status": "active",
        "items": {"data": [{"price": {"id": "price_x"}}]},
        "current_period_start": 1700000000,
        "current_period_end": 9999999999,
        "cancel_at_period_end": False,
        "metadata": {},  # no user_id in metadata
    }
    await webhook_service.handle_stripe_event(db, _make_event("customer.subscription.created", sub_obj))

    sub = await _get_sub(db, "sub_fb_001")
    assert sub is not None
    assert sub.user_id == test_user.id


# ── Unknown event type ─────────────────────────────────────────────────────────

async def test_unknown_event_type_no_crash(db):
    event = _make_event("some.unknown.event", {"id": "obj_x"})
    await webhook_service.handle_stripe_event(db, event)  # must not raise
