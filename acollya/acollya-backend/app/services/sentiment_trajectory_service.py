"""
sentiment_trajectory_service — detects emotional deterioration over a 14-day window.

Public API
----------
analyze_trajectory(db, user)  — computes a sentiment score trend over the last
                                14 days using mood_checkins. Returns a
                                SentimentTrajectory dataclass.
check_deterioration(db, user) — returns True if deterioration is detected with
                                medium or high confidence. Swallows all exceptions.
get_therapist_suggestion()    — returns a fixed PT-BR string suggesting human
                                therapy when deterioration is detected.

Algorithm
---------
1. Fetch mood_checkins for the last 14 days, ordered chronologically.
2. Map mood text to a 1-5 numeric score; fall back to the stored intensity when
   the text is not in the canonical map.
3. Split into two 7-day windows: recent (0-7 days) and prior (7-14 days).
4. Require at least 3 check-ins total; otherwise return has_data=False.
5. Compute a least-squares linear regression slope over all (x, score) pairs
   where x is fractional days from the window start. Pure Python — no numpy.
6. Declare deterioration when ALL three conditions hold:
     • slope < -0.05          (downward trend)
     • avg_recent < avg_prior (recent window worse than prior)
     • avg_recent <= 2.5      (recent average is genuinely low)
7. Confidence: "high" (>= 7 check-ins), "medium" (>= 4), "low" otherwise.

Design constraints
------------------
- No numpy — only stdlib math.
- No new DB tables — queries only mood_checkins.
- check_deterioration() and the in-stream call must NEVER raise.
- The therapist suggestion must be emitted as a "delta" SSE chunk, never as a
  new event type.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mood_checkin import MoodCheckin
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

# Rolling window for the analysis.
_TRAJECTORY_WINDOW_DAYS = 14
_RECENT_WINDOW_DAYS = 7  # 0-7 days ago
_PRIOR_WINDOW_DAYS = 14  # 7-14 days ago

# Minimum check-ins required to consider the data valid.
_MIN_CHECKINS = 3

# Deterioration thresholds.
_SLOPE_THRESHOLD = -0.05   # must be this negative to count as worsening
_RECENCY_THRESHOLD = 2.5   # avg_recent must be <= this to confirm low mood
_CONFIDENCE_HIGH = 7       # check-in count >= this → "high"
_CONFIDENCE_MEDIUM = 4     # check-in count >= this → "medium"

# Canonical PT-BR mood text → numeric score mapping.
# If the stored mood text is not in this map we fall back to the raw intensity.
_MOOD_SCORE_MAP: dict[str, float] = {
    "muito bem": 5.0,
    "bem": 4.0,
    "neutro": 3.0,
    "mal": 2.0,
    "muito mal": 1.0,
}

# Fixed PT-BR therapist suggestion string, formatted as a markdown block so the
# client can render it distinctly from the main LLM reply.
_THERAPIST_SUGGESTION = (
    "\n\n---\n"
    "\U0001f499 *Percebi que você tem enfrentado momentos difíceis com mais frequência. "
    "Às vezes, conversar com um profissional de saúde mental pode fazer uma grande diferença. "
    "Considere buscar um psicólogo ou terapeuta — o cuidado humano especializado é insubstituível.*"
)


# ── Dataclass ──────────────────────────────────────────────────────────────────

@dataclass
class SentimentTrajectory:
    """Result of a single trajectory analysis run for one user."""

    user_id: uuid.UUID
    has_data: bool          # False when fewer than _MIN_CHECKINS exist in window
    slope: float            # Least-squares slope over the 14-day window.
                            #   negative → worsening; positive → improving
    avg_recent: float       # Mean score for the 0-7-day sub-window
    avg_prior: float        # Mean score for the 7-14-day sub-window
    checkin_count: int      # Total check-ins used in the analysis
    is_deteriorating: bool  # True when all three deterioration conditions hold
    confidence: str         # "high" | "medium" | "low"


# ── Pure-Python least-squares slope ───────────────────────────────────────────

def _least_squares_slope(xs: list[float], ys: list[float]) -> float:
    """
    Compute the slope of the OLS regression line through the given points.

    Uses the closed-form formula:
        b = (n * Σxy  − Σx * Σy) / (n * Σx²  − (Σx)²)

    Returns 0.0 when the denominator is zero (all x values are identical,
    i.e. fewer than two distinct time points) to avoid ZeroDivisionError.
    """
    n = len(xs)
    if n < 2:
        return 0.0

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denom = n * sum_x2 - sum_x ** 2
    if denom == 0.0:
        return 0.0

    return (n * sum_xy - sum_x * sum_y) / denom


def _mean(values: list[float]) -> float:
    """Return the arithmetic mean of a non-empty list; caller ensures non-empty."""
    return sum(values) / len(values)


# ── Core analysis ──────────────────────────────────────────────────────────────

async def analyze_trajectory(
    db: AsyncSession, user: User
) -> SentimentTrajectory:
    """
    Fetch the last 14 days of mood check-ins for *user* and compute a sentiment
    trajectory.

    The function is intentionally simple and cheap: one SELECT, then pure-Python
    aggregation. It is called inline after all LLM delta chunks have been yielded
    (see chat_service.stream_message), so it only adds latency to the final
    "done" event, not to the first token.

    Returns a SentimentTrajectory with has_data=False when there is insufficient
    data to make a meaningful assessment.
    """
    now = datetime.now(UTC)
    window_start = now - timedelta(days=_TRAJECTORY_WINDOW_DAYS)
    recent_cutoff = now - timedelta(days=_RECENT_WINDOW_DAYS)

    # Single query: fetch all check-ins in the 14-day window, chronologically.
    result = await db.execute(
        select(MoodCheckin.mood, MoodCheckin.intensity, MoodCheckin.created_at)
        .where(
            MoodCheckin.user_id == user.id,
            MoodCheckin.created_at >= window_start,
        )
        .order_by(MoodCheckin.created_at.asc())
    )
    rows = result.all()

    checkin_count = len(rows)

    # Not enough data — return a safe, non-deteriorating placeholder.
    if checkin_count < _MIN_CHECKINS:
        return SentimentTrajectory(
            user_id=user.id,
            has_data=False,
            slope=0.0,
            avg_recent=3.0,
            avg_prior=3.0,
            checkin_count=checkin_count,
            is_deteriorating=False,
            confidence="low",
        )

    # Map each row to a numeric score and an elapsed-time x-value (in fractional
    # days from window_start). Using elapsed days (not raw timestamps) keeps the
    # slope in interpretable units: "score change per day".
    recent_scores: list[float] = []
    prior_scores: list[float] = []
    xs: list[float] = []
    ys: list[float] = []

    for row in rows:
        # Resolve score: canonical map first, raw intensity as fallback.
        score = _MOOD_SCORE_MAP.get(row.mood.strip().lower(), float(row.intensity))

        # created_at may or may not be timezone-aware depending on DB driver.
        ts = row.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        elapsed_days = (ts - window_start).total_seconds() / 86400.0
        xs.append(elapsed_days)
        ys.append(score)

        if ts >= recent_cutoff:
            recent_scores.append(score)
        else:
            prior_scores.append(score)

    # Compute window averages. Use 3.0 (neutral) as default when a window has no
    # check-ins — this avoids spurious deterioration signals from one-sided data.
    avg_recent = _mean(recent_scores) if recent_scores else 3.0
    avg_prior = _mean(prior_scores) if prior_scores else 3.0

    # Least-squares slope over all points in the window.
    slope = _least_squares_slope(xs, ys)

    # Confidence tiers.
    if checkin_count >= _CONFIDENCE_HIGH:
        confidence = "high"
    elif checkin_count >= _CONFIDENCE_MEDIUM:
        confidence = "medium"
    else:
        confidence = "low"

    # Deterioration requires ALL three conditions to hold simultaneously.
    # This triple-guard minimises false positives: a single bad day does not
    # trigger the alert; there must be a statistically visible downward trend,
    # a measurable drop between windows, AND genuinely low recent scores.
    is_deteriorating = (
        slope < _SLOPE_THRESHOLD
        and avg_recent < avg_prior
        and avg_recent <= _RECENCY_THRESHOLD
    )

    return SentimentTrajectory(
        user_id=user.id,
        has_data=True,
        slope=round(slope, 4),
        avg_recent=round(avg_recent, 2),
        avg_prior=round(avg_prior, 2),
        checkin_count=checkin_count,
        is_deteriorating=is_deteriorating,
        confidence=confidence,
    )


# ── Public helpers ─────────────────────────────────────────────────────────────

async def check_deterioration(db: AsyncSession, user: User) -> bool:
    """
    Return True if the user is showing a deteriorating mood trajectory with at
    least medium confidence.

    This function is designed to be called inline in the chat hot-path. It:
    - Never raises (all exceptions are swallowed and logged at WARNING level).
    - Only returns True when confidence is "high" or "medium" to prevent noisy
      false-positive suggestions for users with sparse check-in history.

    Returns False on any error so the response is never blocked.
    """
    try:
        trajectory = await analyze_trajectory(db, user)
        return trajectory.is_deteriorating and trajectory.confidence in ("high", "medium")
    except Exception as exc:
        logger.warning(
            "check_deterioration failed for user_id=%s: %s", user.id, exc
        )
        return False


def get_therapist_suggestion() -> str:
    """
    Return the fixed PT-BR string that suggests the user seek a human therapist.

    This string is emitted as a "delta" SSE event — not a separate event type —
    so the client renders it as a continuation of the assistant's reply. The
    markdown horizontal rule visually separates it from the LLM-generated text.
    """
    return _THERAPIST_SUGGESTION
