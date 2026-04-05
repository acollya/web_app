"""
Tests for app/services/auth_service.py

Covers:
  register   — success, duplicate email
  login      — success, wrong password, nonexistent user, inactive account
  refresh    — success (token rotation), revoked JTI
  logout     — always succeeds (even with invalid token)
"""
import pytest
from unittest.mock import AsyncMock

from app.core.exceptions import AuthenticationError, ConflictError, InvalidTokenError
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import auth_service


# ── Register ───────────────────────────────────────────────────────────────────

async def test_register_success(db, mock_redis):
    req = RegisterRequest(
        email="novo@test.acollya.com",
        name="Novo Usuario",
        password="Senha1234",
        terms_accepted=True,
    )
    resp = await auth_service.register(db, mock_redis, req)

    assert resp.access_token
    assert resp.refresh_token
    assert resp.is_new_user is True
    assert resp.user_id
    # JTI was stored in Redis
    mock_redis.setex.assert_called_once()


async def test_register_duplicate_email(db, mock_redis, test_user):
    req = RegisterRequest(
        email=test_user.email,  # already exists
        name="Outro",
        password="Senha1234",
        terms_accepted=True,
    )
    with pytest.raises(ConflictError):
        await auth_service.register(db, mock_redis, req)


# ── Login ──────────────────────────────────────────────────────────────────────

async def test_login_success(db, mock_redis, test_user):
    req = LoginRequest(email=test_user.email, password="Senha1234")
    resp = await auth_service.login(db, mock_redis, req)

    assert resp.access_token
    assert resp.refresh_token
    assert resp.is_new_user is False
    assert resp.user_id == str(test_user.id)


async def test_login_wrong_password(db, mock_redis, test_user):
    req = LoginRequest(email=test_user.email, password="SenhaErrada1")
    with pytest.raises(AuthenticationError):
        await auth_service.login(db, mock_redis, req)


async def test_login_nonexistent_user(db, mock_redis):
    req = LoginRequest(email="fantasma@test.acollya.com", password="Senha1234")
    with pytest.raises(AuthenticationError):
        await auth_service.login(db, mock_redis, req)


async def test_login_inactive_user(db, mock_redis, test_user):
    test_user.is_active = False
    await db.commit()

    req = LoginRequest(email=test_user.email, password="Senha1234")
    with pytest.raises(AuthenticationError):
        await auth_service.login(db, mock_redis, req)


# ── Refresh ────────────────────────────────────────────────────────────────────

async def test_refresh_success(db, mock_redis, test_user):
    # First login to get a refresh token
    login_resp = await auth_service.login(
        db, mock_redis, LoginRequest(email=test_user.email, password="Senha1234")
    )
    # Configure mock so JTI lookup returns the user id (simulates Redis having it)
    mock_redis.get.return_value = str(test_user.id).encode()

    new_resp = await auth_service.refresh_tokens(db, mock_redis, login_resp.refresh_token)

    assert new_resp.access_token
    assert new_resp.refresh_token
    # Old JTI was revoked
    mock_redis.delete.assert_called()
    # New JTI was stored
    assert mock_redis.setex.call_count >= 2  # login + refresh each store a JTI


async def test_refresh_revoked_jti(db, mock_redis, test_user):
    login_resp = await auth_service.login(
        db, mock_redis, LoginRequest(email=test_user.email, password="Senha1234")
    )
    # mock_redis.get returns None by default → JTI not in Redis → revoked
    mock_redis.get.return_value = None

    with pytest.raises(InvalidTokenError):
        await auth_service.refresh_tokens(db, mock_redis, login_resp.refresh_token)


# ── Logout ─────────────────────────────────────────────────────────────────────

async def test_logout_succeeds_with_valid_token(db, mock_redis, test_user):
    login_resp = await auth_service.login(
        db, mock_redis, LoginRequest(email=test_user.email, password="Senha1234")
    )
    # Should not raise
    await auth_service.logout(mock_redis, login_resp.refresh_token)
    mock_redis.delete.assert_called()


async def test_logout_succeeds_with_garbage_token(mock_redis):
    """Logout is always successful — even with a malformed token."""
    await auth_service.logout(mock_redis, "not.a.valid.jwt")
    # delete should NOT have been called (invalid token, nothing to revoke)
    mock_redis.delete.assert_not_called()
