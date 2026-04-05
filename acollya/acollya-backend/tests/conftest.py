"""
Shared pytest fixtures for the Acollya backend test suite.

Setup strategy:
  - SQLite async (aiosqlite) in-memory DB — one fresh DB per test function.
  - RSA key pair generated once at module import and patched into settings.jwt_config
    so create_access_token / create_refresh_token work without real keys.
  - Redis is mocked with AsyncMock — no real Redis needed.
  - All fixtures are function-scoped for full test isolation.
"""
import pytest
import pytest_asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Patch JWT config BEFORE any service code accesses settings.jwt_config ─────
from app.config import settings
import app.models  # noqa: F401  — registers all ORM models with Base.metadata
from app.database import Base
from app.core.auth import hash_password
from app.models.user import User


def _generate_rsa_keys() -> tuple[str, str]:
    """Return (private_pem, public_pem) for a 2048-bit RSA key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


_PRIVATE_KEY, _PUBLIC_KEY = _generate_rsa_keys()

# Override the @cached_property so tests always get test keys
settings.__dict__["jwt_config"] = {
    "private_key": _PRIVATE_KEY,
    "public_key": _PUBLIC_KEY,
    "algorithm": "RS256",
    "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 30,
    "google_client_ids": [],
}


# ── DB engine — fresh in-memory SQLite per test ────────────────────────────────

@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    """Yield one AsyncSession per test. Rolls back uncommitted state on exit."""
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as session:
        yield session
        await session.rollback()


# ── User fixtures ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    """Primary test user with a known password."""
    user = User(
        email="user@test.acollya.com",
        name="Test User",
        password_hash=hash_password("Senha1234"),
        trial_ends_at=datetime.now(UTC) + timedelta(days=14),
        subscription_status="trialing",
        terms_accepted=True,
        terms_accepted_date=datetime.now(UTC),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_user(db: AsyncSession) -> User:
    """Second user for ownership / authorization tests."""
    user = User(
        email="other@test.acollya.com",
        name="Other User",
        password_hash=hash_password("Senha1234"),
        trial_ends_at=datetime.now(UTC) + timedelta(days=14),
        subscription_status="trialing",
        terms_accepted=True,
        terms_accepted_date=datetime.now(UTC),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ── Redis mock ─────────────────────────────────────────────────────────────────

# ── HTTP client (for existing unit/integration tests) ─────────────────────────

@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """
    Minimal ASGI test client for smoke/health tests.
    No DB or Redis override — suitable only for endpoints that need neither.
    """
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Redis mock ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis() -> AsyncMock:
    """
    AsyncMock simulating a Redis client.

    Default: get() returns None (JTI not found / already revoked).
    Tests that need a valid JTI should set mock_redis.get.return_value explicitly.
    """
    redis = AsyncMock()
    redis.get.return_value = None
    redis.setex.return_value = True
    redis.delete.return_value = 1
    return redis
