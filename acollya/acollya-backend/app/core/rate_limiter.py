"""
Redis sliding-window rate limiter.

Algorithm: sorted set per (user_id, action) key.
  - ZADD key score=now member=uuid4   -> add current request
  - ZREMRANGEBYSCORE key 0 window_start -> remove expired entries
  - ZCARD key -> count requests in window
  - EXPIRE key window_seconds -> auto-cleanup

All three commands run in a pipeline for atomicity on the read side.
(True atomic MULTI/EXEC is not needed here — slight over-counting under
race conditions is acceptable and avoids WATCH overhead.)

Usage:
    from app.core.rate_limiter import RateLimiter

    limiter = RateLimiter(redis_client)
    await limiter.check_and_increment(
        user_id=str(user.id),
        action="chat",
        limit=20,
        window_seconds=86400,  # 24 hours
    )
    # Raises RateLimitError if limit exceeded.
"""
import logging
import time
import uuid

from redis.asyncio import Redis

from app.core.exceptions import RateLimitError

logger = logging.getLogger(__name__)

_KEY_PREFIX = "rl"


class RateLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, user_id: str, action: str) -> str:
        return f"{_KEY_PREFIX}:{action}:{user_id}"

    async def check_and_increment(
        self,
        user_id: str,
        action: str,
        limit: int,
        window_seconds: int = 86400,
    ) -> int:
        """
        Record a new request and enforce the rate limit.

        Returns the current request count within the window.
        Raises RateLimitError if limit is already reached before this call.
        """
        key = self._key(user_id, action)
        now = time.time()
        window_start = now - window_seconds
        member = str(uuid.uuid4())

        pipe = self._redis.pipeline()
        # Remove entries outside the sliding window
        pipe.zremrangebyscore(key, 0, window_start)
        # Add the current request
        pipe.zadd(key, {member: now})
        # Count entries in window (after add)
        pipe.zcard(key)
        # Reset TTL
        pipe.expire(key, window_seconds)

        results = await pipe.execute()
        current_count: int = results[2]  # zcard result

        if current_count > limit:
            # Calculate how long until the oldest entry leaves the window
            oldest = await self._redis.zrange(key, 0, 0, withscores=True)
            retry_after: int | None = None
            if oldest:
                _, oldest_score = oldest[0]
                retry_after = max(0, int(oldest_score + window_seconds - now))
            raise RateLimitError(
                f"Limit of {limit} requests per {window_seconds}s exceeded",
                retry_after=retry_after,
            )

        return current_count

    async def get_count(self, user_id: str, action: str, window_seconds: int = 86400) -> int:
        """Return current request count without incrementing."""
        key = self._key(user_id, action)
        window_start = time.time() - window_seconds
        await self._redis.zremrangebyscore(key, 0, window_start)
        return await self._redis.zcard(key)

    async def reset(self, user_id: str, action: str) -> None:
        """Clear rate limit counter (useful for tests or admin resets)."""
        await self._redis.delete(self._key(user_id, action))
