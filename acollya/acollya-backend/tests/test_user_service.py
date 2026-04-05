"""
Tests for app/services/user_service.py

Covers:
  get_me      — returns UserResponse with correct fields
  update_me   — updates only sent fields (exclude_unset), leaves others intact
  delete_me   — LGPD anonymisation: PII overwritten, is_active=False, id preserved
"""
import pytest

from app.schemas.user import UserUpdate
from app.services import user_service


# ── get_me ─────────────────────────────────────────────────────────────────────

def test_get_me_returns_correct_email(test_user):
    resp = user_service.get_me(test_user)
    assert str(resp.email) == test_user.email


def test_get_me_returns_user_id(test_user):
    resp = user_service.get_me(test_user)
    assert resp.id == test_user.id


def test_get_me_includes_trial_flags(test_user):
    resp = user_service.get_me(test_user)
    assert resp.is_trial_active is True   # fixture sets trial 14 days ahead
    assert resp.is_premium is False       # no active paid subscription


# ── update_me ──────────────────────────────────────────────────────────────────

async def test_update_me_changes_name(db, test_user):
    data = UserUpdate(name="Novo Nome")
    resp = await user_service.update_me(db, test_user, data)
    assert resp.name == "Novo Nome"


async def test_update_me_partial_update_preserves_other_fields(db, test_user):
    """Sending only phone must not wipe name or other fields."""
    original_name = test_user.name
    data = UserUpdate(phone="+5511999999999")
    resp = await user_service.update_me(db, test_user, data)

    assert resp.phone == "+5511999999999"
    assert resp.name == original_name


async def test_update_me_empty_body_changes_nothing(db, test_user):
    """Empty update (no fields sent) must leave user unchanged."""
    original_name = test_user.name
    data = UserUpdate()  # all fields unset
    resp = await user_service.update_me(db, test_user, data)
    assert resp.name == original_name


# ── delete_me ──────────────────────────────────────────────────────────────────

async def test_delete_me_deactivates_account(db, test_user):
    await user_service.delete_me(db, test_user)
    assert test_user.is_active is False


async def test_delete_me_anonymises_email(db, test_user):
    original_email = test_user.email
    await user_service.delete_me(db, test_user)

    assert test_user.email != original_email
    assert "@acollya.invalid" in test_user.email
    assert "deleted_" in test_user.email


async def test_delete_me_clears_all_pii_fields(db, test_user):
    test_user.phone = "+5511999999999"
    test_user.google_id = "google_id_123"
    test_user.stripe_customer_id = "cus_test_123"
    test_user.push_token_fcm = "fcm_token_abc"
    await db.commit()

    await user_service.delete_me(db, test_user)

    assert test_user.name == "Conta encerrada"
    assert test_user.phone is None
    assert test_user.birth_date is None
    assert test_user.gender is None
    assert test_user.google_id is None
    assert test_user.password_hash is None
    assert test_user.push_token_fcm is None
    assert test_user.push_token_apns is None
    assert test_user.stripe_customer_id is None
    assert test_user.revenue_cat_id is None


async def test_delete_me_preserves_user_id(db, test_user):
    """ID must never change — needed to maintain referential integrity in analytics."""
    original_id = test_user.id
    await user_service.delete_me(db, test_user)
    assert test_user.id == original_id
