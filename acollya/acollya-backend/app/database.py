"""
Async SQLAlchemy database engine and session factory.

Lambda connection pooling:
  Lambda creates a new Python process on cold start and may reuse the container
  for warm invocations. Without RDS Proxy, each cold start creates a new DB
  connection. Pool settings are tuned for Lambda (small pool, aggressive recycling).

  For 1-10k users: Direct connection is fine (pool_size=2, max_overflow=3).
  For 100k+ users: Enable RDS Proxy in DatabaseStack and increase pool_size.
"""
import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────
# NullPool in Lambda: don't maintain persistent connections between invocations.
# This avoids "connection already closed" errors during container reuse pauses.
engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=settings.log_level == "DEBUG",
    connect_args={
        "ssl": "require" if settings.stage != "dev" else "prefer",
        "server_settings": {
            "application_name": f"acollya-lambda-{settings.stage}",
        },
    },
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Base Model ────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass




# ── Init ──────────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """Called on Lambda cold start (lifespan). Verifies DB connectivity."""
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("Database connection established.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise
