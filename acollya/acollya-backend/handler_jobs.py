"""
AWS Lambda entry point for scheduled background jobs.

Two handlers, each wired to its own EventBridge cron rule in JobsStack:

  weekly_report_handler(event, context)
      Cron: cron(0 21 ? * FRI *)  — every Friday at 21:00 UTC (18:00 BRT).
      Generates a brief weekly emotional pattern summary for each user who
      had at least one chat message or mood check-in in the last 7 days.
      Results are persisted to Redis with a 7-day TTL when available.

  dependency_check_handler(event, context)
      Cron: cron(0 9 * * ? *)     — every day at 09:00 UTC (06:00 BRT).
      Logs a warning for each user whose chat usage in the last 3 days
      exceeds the dependency threshold. No user-facing action is taken.

Initialisation
--------------
Unlike handler.py (Mangum-wrapped FastAPI), the cron Lambdas DO NOT serve HTTP
traffic and therefore cannot rely on the FastAPI lifespan to set up the DB
engine, secrets and Redis client. We replicate just the parts they need:

  - DB credentials are resolved lazily by app.config.settings.database_url
    via Secrets Manager — no explicit init step required, the first DB call
    will trigger the boto3 fetch and cache the result for the warm container.
  - init_db() is called once per container so we fail fast on connectivity
    issues rather than mid-job.
  - A Redis client is created and injected into analytics_service when env
    vars are present. If Redis is unavailable the weekly report job still
    runs (and logs the summaries) — persistence is best-effort.

Concurrency model
-----------------
Each invocation runs a single asyncio event loop via asyncio.run(). The
function returns when the loop completes, so Lambda's billing window matches
the actual job duration. Both jobs are read-mostly against Postgres and
fan out per-user with swallowed errors, so they are safe to retry.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

# Configure logging before anything else so module-level imports get captured.
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("acollya.jobs")

# Imports below depend on env vars being present (DB_HOST, DB_SECRET_ARN, etc.)
# which CDK injects via the Lambda environment. They MUST come after logging
# is configured so any boto3 / SQLAlchemy startup messages are visible.
from app.config import settings  # noqa: E402
from app.database import AsyncSessionLocal, init_db  # noqa: E402
from app.services import analytics_service  # noqa: E402
from app.services.analytics_service import (  # noqa: E402
    check_emotional_dependency,
    weekly_pattern_report,
)

# ── Container-level state ─────────────────────────────────────────────────────
# Lambda may reuse a warm container across invocations. We initialise the DB
# engine and Redis client once per container and reuse them for subsequent
# calls. _initialised guards against re-running init_db on warm starts.

_initialised: bool = False
_redis_client: Any = None


async def _ensure_initialised() -> None:
    """
    One-time per-container setup: verify DB connectivity, wire Redis if available.

    Called from each handler before doing real work. Safe to call multiple
    times — guarded by the _initialised flag.
    """
    global _initialised, _redis_client
    if _initialised:
        return

    # 1. DB connectivity check. The credentials are fetched from Secrets Manager
    #    lazily on first use of settings.database_url.
    await init_db()

    # 2. Redis client (optional). The weekly report job persists summaries here;
    #    if Redis is unreachable, the job still runs and logs the summaries.
    try:
        from redis.asyncio import Redis  # local import to keep cold-start lean

        if settings.redis_host and settings.redis_host != "localhost":
            redis_url = (
                f"rediss://{settings.redis_host}:{settings.redis_port}"
                if settings.redis_tls
                else f"redis://{settings.redis_host}:{settings.redis_port}"
            )
            _redis_client = Redis.from_url(
                redis_url,
                password=settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            analytics_service.configure_redis(_redis_client)
            logger.info("Jobs Redis client initialised: %s", settings.redis_host)
        else:
            logger.info("Redis host not configured — weekly reports will only be logged.")
    except Exception as exc:
        # Never let a Redis init failure prevent the job from running. The
        # weekly report job tolerates _redis_client being None.
        logger.warning("Failed to initialise Redis for jobs: %s", exc)
        _redis_client = None

    _initialised = True


def _run_async(coro):
    """
    Run an async coroutine to completion in a fresh event loop.

    We deliberately avoid asyncio.run() because in some Lambda runtime versions
    it conflicts with re-entrant calls during warm starts. Creating an explicit
    loop, running, then closing it gives us deterministic cleanup of asyncpg /
    httpx connection pools.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        try:
            # Cancel any leftover tasks (e.g. background _redis_client tasks)
            # so they don't leak into the next warm invocation.
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()


# ── Async job bodies ──────────────────────────────────────────────────────────

async def _weekly_report() -> dict:
    await _ensure_initialised()
    async with AsyncSessionLocal() as db:
        result = await weekly_pattern_report(db)
        logger.info("Weekly report job completed: %s", result)
        return result


async def _dependency_check() -> dict:
    await _ensure_initialised()
    async with AsyncSessionLocal() as db:
        result = await check_emotional_dependency(db)
        logger.info("Dependency check job completed: %s", result)
        return result


# ── Lambda handlers ───────────────────────────────────────────────────────────

def weekly_report_handler(event, context):
    """
    Lambda handler for the Friday weekly pattern report cron.

    Always returns a JSON-serialisable summary so EventBridge / CloudWatch can
    capture it. Internal failures bubble up as 5xx Lambda errors only when the
    setup itself fails (DB unreachable, secrets missing); per-user failures
    are swallowed inside weekly_pattern_report.
    """
    logger.info("weekly_report_handler invoked: event=%s", event)
    try:
        return _run_async(_weekly_report())
    except Exception as exc:
        logger.exception("weekly_report_handler crashed: %s", exc)
        # Re-raise so Lambda marks the invocation as failed and EventBridge
        # can apply its retry policy.
        raise


def dependency_check_handler(event, context):
    """Lambda handler for the daily emotional-dependency scan."""
    logger.info("dependency_check_handler invoked: event=%s", event)
    try:
        return _run_async(_dependency_check())
    except Exception as exc:
        logger.exception("dependency_check_handler crashed: %s", exc)
        raise
