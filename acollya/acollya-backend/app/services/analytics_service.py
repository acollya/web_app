"""
Analytics service — read-only aggregation queries + scheduled jobs.

User-facing dashboards:
  get_overview     — dashboard metrics: streak, totals, programs, appointments
  get_mood_trend   — daily avg intensity + dominant mood for the last N days
  get_activity     — journal + mood activity per calendar day (heatmap data)

Scheduled background jobs (invoked by handler_jobs.py via EventBridge cron):
  weekly_pattern_report      — Friday 21h UTC: per-user emotional pattern summary
  check_emotional_dependency — Daily 09h UTC:  flag users with excessive chatbot use

Query strategy:
  - User-facing queries are READ-ONLY.
  - Background jobs are READ-ONLY against Postgres; results go to Redis (TTL'd)
    or are simply logged. They never block on a single user's failure.
  - Aggregations run on the DB side (GROUP BY / COUNT / AVG).
  - Python-side work limited to merging two result sets and filling zero-rows.
  - No N+1: each user-facing function issues at most 4 queries total.
"""
import json
import logging
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from sqlalchemy import cast, func, select, type_coerce, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.chat_message import ChatMessage
from app.models.journal_entry import JournalEntry
from app.models.mood_checkin import MoodCheckin
from app.models.program import Chapter
from app.models.program_progress import ProgramProgress
from app.models.user import User
from app.schemas.analytics import (
    ActivityDay,
    ActivityResponse,
    MoodTrendPoint,
    MoodTrendResponse,
    OverviewResponse,
)

logger = logging.getLogger(__name__)


# ── Scheduled job constants ────────────────────────────────────────────────────

# Window used by both jobs to scope "active users".
_ACTIVE_WINDOW_DAYS = 7

# Emotional-dependency thresholds.
# A user who sends > _DEPENDENCY_MSG_THRESHOLD messages within
# _DEPENDENCY_WINDOW_DAYS is flagged as potentially over-relying on the chatbot.
# These numbers are deliberately conservative: false positives only produce log
# warnings (no user-facing action), so it is safer to over-flag than under-flag.
_DEPENDENCY_MSG_THRESHOLD = 20
_DEPENDENCY_SESSION_THRESHOLD = 5
_DEPENDENCY_WINDOW_DAYS = 3

# Redis key prefix + TTL for persisted weekly reports. TTL slightly longer
# than the window between runs so the previous report is still readable while
# the new one is being generated (idempotent re-runs).
_WEEKLY_REPORT_KEY_PREFIX = "weekly_report"
_WEEKLY_REPORT_TTL_SECONDS = 7 * 24 * 3600

# LLM caps for the weekly summary — short, gentle text, never long-form.
_WEEKLY_SUMMARY_MAX_TOKENS = 300

# System prompt for the weekly summary. Kept brief; this is a low-stakes
# personalisation surface, not a clinical intervention.
_WEEKLY_SUMMARY_SYSTEM_PROMPT = (
    "Você é Acollya, assistente virtual de saúde emocional. "
    "Gere um breve resumo semanal (2 a 3 frases) dos padrões emocionais do "
    "usuário com base nos dados fornecidos. Seja gentil, encorajador e "
    "específico, sem nunca emitir diagnóstico clínico, prescrever conduta "
    "ou citar números brutos de forma fria. Responda sempre em português do "
    "Brasil, em tom acolhedor e na segunda pessoa do singular."
)


# ── Scheduled job: Redis singleton (optional — jobs degrade gracefully) ────────

_redis_client = None


def configure_redis(client) -> None:
    """Inject a Redis client for storing weekly reports. Optional."""
    global _redis_client
    _redis_client = client


# ── Helpers ────────────────────────────────────────────────────────────────────

def _compute_streak(checkin_dates: set[date]) -> int:
    """
    Count consecutive days with at least one check-in, ending today or yesterday.
    Mirrors the logic in mood_service to avoid cross-service imports.
    """
    today = datetime.now(UTC).date()
    streak = 0
    current = today
    while current in checkin_dates:
        streak += 1
        current -= timedelta(days=1)
    # If today has no check-in, allow yesterday to start the streak
    if streak == 0 and (today - timedelta(days=1)) in checkin_dates:
        current = today - timedelta(days=1)
        while current in checkin_dates:
            streak += 1
            current -= timedelta(days=1)
    return streak


# ── Overview ───────────────────────────────────────────────────────────────────

async def get_overview(db: AsyncSession, user: User) -> OverviewResponse:
    now = datetime.now(UTC)
    today = now.date()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    cutoff_365d = now - timedelta(days=365)

    # 1. Mood totals + streak — bounded to 365 days to cap query cost
    mood_result = await db.execute(
        select(
            type_coerce(func.date(MoodCheckin.created_at), Date).label("day"),
            func.avg(MoodCheckin.intensity).label("avg_int"),
            func.count().label("cnt"),
        )
        .where(
            MoodCheckin.user_id == user.id,
            MoodCheckin.created_at >= cutoff_365d,
        )
        .group_by(type_coerce(func.date(MoodCheckin.created_at), Date))
    )
    mood_rows = mood_result.all()

    total_mood_checkins = sum(r.cnt for r in mood_rows)
    checkin_dates: set[date] = {r.day for r in mood_rows}
    mood_streak_days = _compute_streak(checkin_dates)

    recent_rows = [r for r in mood_rows if r.day >= cutoff_7d.date()]
    avg_intensity_last_7d: Optional[float] = None
    if recent_rows:
        total_w = sum(r.avg_int * r.cnt for r in recent_rows)
        total_c = sum(r.cnt for r in recent_rows)
        avg_intensity_last_7d = round(total_w / total_c, 2) if total_c else None

    # 2. Journal totals — bounded to 365 days
    journal_result = await db.execute(
        select(
            type_coerce(func.date(JournalEntry.created_at), Date).label("day"),
            func.count().label("cnt"),
        )
        .where(
            JournalEntry.user_id == user.id,
            JournalEntry.created_at >= cutoff_365d,
        )
        .group_by(type_coerce(func.date(JournalEntry.created_at), Date))
    )
    journal_rows = journal_result.all()
    total_journal_entries = sum(r.cnt for r in journal_rows)
    journal_entries_last_30d = sum(r.cnt for r in journal_rows if r.day >= cutoff_30d.date())

    # 3. Program progress: started vs completed
    #    a) User's completed chapter counts per program
    progress_result = await db.execute(
        select(
            ProgramProgress.program_id,
            func.count().label("completed_count"),
        )
        .where(
            ProgramProgress.user_id == user.id,
            ProgramProgress.completed == True,  # noqa: E712
        )
        .group_by(ProgramProgress.program_id)
    )
    user_progress: dict[str, int] = {
        r.program_id: r.completed_count for r in progress_result.all()
    }

    #    b) Total chapter counts per program (only for programs the user started)
    if user_progress:
        chapters_result = await db.execute(
            select(
                Chapter.program_id,
                func.count().label("total_count"),
            )
            .where(Chapter.program_id.in_(list(user_progress.keys())))
            .group_by(Chapter.program_id)
        )
        chapter_totals: dict[str, int] = {
            r.program_id: r.total_count for r in chapters_result.all()
        }
        programs_started = len(user_progress)
        programs_completed = sum(
            1 for pid, done in user_progress.items()
            if chapter_totals.get(pid, 0) > 0 and done >= chapter_totals.get(pid, 0)
        )
    else:
        programs_started = 0
        programs_completed = 0

    # 4. Upcoming appointments
    upcoming_result = await db.execute(
        select(func.count())
        .where(
            Appointment.user_id == user.id,
            Appointment.date >= today,
            Appointment.status.notin_(["cancelled", "completed"]),
        )
    )
    upcoming_appointments: int = upcoming_result.scalar_one()

    return OverviewResponse(
        total_mood_checkins=total_mood_checkins,
        mood_streak_days=mood_streak_days,
        avg_intensity_last_7d=avg_intensity_last_7d,
        total_journal_entries=total_journal_entries,
        journal_entries_last_30d=journal_entries_last_30d,
        programs_started=programs_started,
        programs_completed=programs_completed,
        upcoming_appointments=upcoming_appointments,
        member_since=user.created_at,
    )


# ── Mood trend ─────────────────────────────────────────────────────────────────

async def get_mood_trend(
    db: AsyncSession, user: User, days: int
) -> MoodTrendResponse:
    cutoff = datetime.now(UTC) - timedelta(days=min(days, 365))

    # Fetch all rows in range — aggregate in Python to compute dominant mood
    result = await db.execute(
        select(
            type_coerce(func.date(MoodCheckin.created_at), Date).label("day"),
            MoodCheckin.mood,
            MoodCheckin.intensity,
        )
        .where(
            MoodCheckin.user_id == user.id,
            MoodCheckin.created_at >= cutoff,
        )
        .order_by(type_coerce(func.date(MoodCheckin.created_at), Date))
    )
    rows = result.all()

    # Group by day in Python
    day_moods: dict[date, list[str]] = defaultdict(list)
    day_intensities: dict[date, list[int]] = defaultdict(list)
    for row in rows:
        day_moods[row.day].append(row.mood)
        day_intensities[row.day].append(row.intensity)

    points: list[MoodTrendPoint] = []
    for day in sorted(day_intensities.keys()):
        intensities = day_intensities[day]
        moods = day_moods[day]
        dominant = Counter(moods).most_common(1)[0][0] if moods else None
        points.append(MoodTrendPoint(
            date=day,
            avg_intensity=round(sum(intensities) / len(intensities), 2),
            checkin_count=len(intensities),
            dominant_mood=dominant,
        ))

    return MoodTrendResponse(period_days=days, points=points)


# ── Activity heatmap ───────────────────────────────────────────────────────────

async def get_activity(
    db: AsyncSession, user: User, days: int
) -> ActivityResponse:
    cutoff = datetime.now(UTC) - timedelta(days=min(days, 365))

    # Mood checkins per day
    mood_result = await db.execute(
        select(
            type_coerce(func.date(MoodCheckin.created_at), Date).label("day"),
            func.count().label("cnt"),
        )
        .where(
            MoodCheckin.user_id == user.id,
            MoodCheckin.created_at >= cutoff,
        )
        .group_by(type_coerce(func.date(MoodCheckin.created_at), Date))
    )
    mood_by_day: dict[date, int] = {r.day: r.cnt for r in mood_result.all()}

    # Journal entries per day
    journal_result = await db.execute(
        select(
            type_coerce(func.date(JournalEntry.created_at), Date).label("day"),
            func.count().label("cnt"),
        )
        .where(
            JournalEntry.user_id == user.id,
            JournalEntry.created_at >= cutoff,
        )
        .group_by(type_coerce(func.date(JournalEntry.created_at), Date))
    )
    journal_by_day: dict[date, int] = {r.day: r.cnt for r in journal_result.all()}

    # Merge: union of all active days
    all_days = set(mood_by_day.keys()) | set(journal_by_day.keys())

    activity_days: list[ActivityDay] = []
    for d in sorted(all_days):
        j = journal_by_day.get(d, 0)
        m = mood_by_day.get(d, 0)
        activity_days.append(ActivityDay(
            date=d,
            journal_count=j,
            mood_count=m,
            total=j + m,
        ))

    max_activity = max((a.total for a in activity_days), default=0)

    return ActivityResponse(
        period_days=days,
        days=activity_days,
        max_activity=max_activity,
    )


# ── Scheduled jobs ─────────────────────────────────────────────────────────────
#
# Both functions below are designed to be invoked from a Lambda cron entry point
# (handler_jobs.py). They share three guarantees:
#
#   1. Per-user errors are SWALLOWED (logged, then continue). One failure must
#      never prevent the rest of the user base from being processed.
#   2. Returned dicts are always JSON-serialisable so the Lambda runtime can
#      surface them to CloudWatch / EventBridge as the invocation result.
#   3. They issue a single aggregate query first, then iterate per user in
#      Python — no N+1 scan of the users table.


def _format_mood_summary(mood_rows: list[tuple[str, int, float]]) -> str:
    """
    Render a compact PT-BR description of a user's weekly mood distribution.

    Input rows are (mood, count, avg_intensity). We keep the prompt context
    short and human-readable so the LLM doesn't anchor on raw numbers.
    """
    if not mood_rows:
        return "nenhum registro de humor"
    parts = []
    for mood, cnt, avg_int in mood_rows:
        parts.append(f"{mood} ({cnt}x, intensidade média {avg_int:.1f})")
    return ", ".join(parts)


async def _store_weekly_report_in_redis(
    user_id: str, week_iso: str, payload: dict
) -> bool:
    """
    Persist a weekly report to Redis with TTL.

    Returns True if stored successfully, False if Redis is unavailable or
    the write fails. Failure is non-fatal — the report still ends up in
    CloudWatch logs via the calling job.
    """
    if _redis_client is None:
        return False
    key = f"{_WEEKLY_REPORT_KEY_PREFIX}:{user_id}:{week_iso}"
    try:
        await _redis_client.setex(
            key, _WEEKLY_REPORT_TTL_SECONDS, json.dumps(payload)
        )
        return True
    except Exception as exc:
        # Don't let a Redis hiccup poison the whole job.
        logger.warning("Failed to store weekly report for %s in Redis: %s", user_id, exc)
        return False


async def weekly_pattern_report(db: AsyncSession) -> dict:
    """
    Generate weekly emotional pattern summaries for active users.

    For each user with at least one chat message OR mood check-in in the last
    7 days, this job:
      1. Counts chat messages sent (user-role only).
      2. Aggregates the mood distribution from mood_checkins.
      3. Calls the insight LLM provider for a 2-3 sentence gentle summary.
      4. Persists the resulting payload to Redis at
         weekly_report:{user_id}:{week_iso} with a 7-day TTL.

    Per-user errors are logged and swallowed so a single failure never aborts
    the run. Returns {"processed": N, "errors": M, "skipped": K}, where
    "skipped" counts users whose Redis write failed (LLM ran successfully).

    Notes:
      - We import get_insight_provider() lazily inside the function so that
        the analytics_service module can be imported in test/dev environments
        that don't have Anthropic credentials configured.
      - The LLM call uses _WEEKLY_SUMMARY_MAX_TOKENS (300) as a hard cap; for
        the thinking provider, that argument is ignored and the budget is
        controlled by thinking_budget at provider construction.
    """
    from app.core.llm_provider import get_chat_provider  # lazy import — non-thinking for cron speed

    now = datetime.now(UTC)
    window_cutoff = now - timedelta(days=_ACTIVE_WINDOW_DAYS)
    week_start = (now - timedelta(days=_ACTIVE_WINDOW_DAYS)).date()
    week_end = now.date()
    # ISO year-week — stable key across timezones.
    iso_year, iso_week, _ = now.isocalendar()
    week_iso = f"{iso_year}-W{iso_week:02d}"

    # Step 1: Find users active in the last 7 days. A user is "active" if they
    # have at least one chat message OR mood check-in in the window.
    active_user_ids: set = set()

    chat_active = await db.execute(
        select(ChatMessage.user_id)
        .where(ChatMessage.created_at >= window_cutoff)
        .distinct()
    )
    active_user_ids.update(r[0] for r in chat_active.all())

    mood_active = await db.execute(
        select(MoodCheckin.user_id)
        .where(MoodCheckin.created_at >= window_cutoff)
        .distinct()
    )
    active_user_ids.update(r[0] for r in mood_active.all())

    if not active_user_ids:
        logger.info("Weekly report job: no active users in the last %d days.", _ACTIVE_WINDOW_DAYS)
        return {"processed": 0, "errors": 0, "skipped": 0, "active_users": 0}

    # Step 2: Aggregate per-user counts in two batched queries. Iterating one
    # SELECT per user would be O(N) round-trips; this stays O(1) regardless
    # of user-base size.
    user_ids = list(active_user_ids)

    msg_count_rows = (await db.execute(
        select(ChatMessage.user_id, func.count().label("cnt"))
        .where(
            ChatMessage.user_id.in_(user_ids),
            ChatMessage.created_at >= window_cutoff,
            ChatMessage.role == "user",
        )
        .group_by(ChatMessage.user_id)
    )).all()
    msg_counts: dict = {r.user_id: r.cnt for r in msg_count_rows}

    mood_dist_rows = (await db.execute(
        select(
            MoodCheckin.user_id,
            MoodCheckin.mood,
            func.count().label("cnt"),
            func.avg(MoodCheckin.intensity).label("avg_int"),
        )
        .where(
            MoodCheckin.user_id.in_(user_ids),
            MoodCheckin.created_at >= window_cutoff,
        )
        .group_by(MoodCheckin.user_id, MoodCheckin.mood)
    )).all()

    mood_by_user: dict = defaultdict(list)
    for r in mood_dist_rows:
        mood_by_user[r.user_id].append((r.mood, r.cnt, float(r.avg_int or 0)))

    # Step 3: Generate summaries per user. Errors are swallowed individually.
    provider = get_chat_provider()
    processed = 0
    errors = 0
    skipped = 0

    for user_id in user_ids:
        try:
            msg_count = int(msg_counts.get(user_id, 0))
            mood_rows = mood_by_user.get(user_id, [])
            mood_summary = _format_mood_summary(mood_rows)

            user_message = (
                f"Semana de {week_start.isoformat()} a {week_end.isoformat()}. "
                f"Mensagens enviadas pelo usuário: {msg_count}. "
                f"Humores registrados: {mood_summary}."
            )

            content, tokens = await provider.complete(
                _WEEKLY_SUMMARY_SYSTEM_PROMPT,
                [{"role": "user", "content": user_message}],
                max_tokens=_WEEKLY_SUMMARY_MAX_TOKENS,
            )
            summary_text = (content or "").strip()
            if not summary_text:
                # LLM returned empty — log and treat as a soft failure.
                logger.warning("Weekly report: empty LLM response for user %s", user_id)
                errors += 1
                continue

            payload = {
                "user_id": str(user_id),
                "week_iso": week_iso,
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "message_count": msg_count,
                "mood_distribution": [
                    {"mood": m, "count": c, "avg_intensity": round(a, 2)}
                    for m, c, a in mood_rows
                ],
                "summary": summary_text,
                "tokens_used": tokens,
                "generated_at": now.isoformat(),
            }

            stored = await _store_weekly_report_in_redis(str(user_id), week_iso, payload)
            if not stored:
                skipped += 1
                logger.info(
                    "Weekly report generated for %s but not persisted (Redis unavailable).",
                    user_id,
                )
            else:
                logger.info("Weekly report stored for user %s (week %s).", user_id, week_iso)

            processed += 1
        except Exception as exc:
            # Per-user failure: log with user_id for triage, then continue.
            logger.exception("Weekly report failed for user %s: %s", user_id, exc)
            errors += 1

    result = {
        "processed": processed,
        "errors": errors,
        "skipped": skipped,
        "active_users": len(user_ids),
        "week_iso": week_iso,
    }
    logger.info("Weekly report job summary: %s", result)
    return result


async def scan_deteriorating_users(db: AsyncSession) -> dict:
    """
    Scan all users who have mood check-ins in the last 14 days and identify
    those showing an emotional deterioration pattern.

    For each active user, calls check_deterioration() from
    sentiment_trajectory_service and logs the user_id + confidence level when
    deterioration is detected.

    Design mirrors the other scheduled jobs in this module:
      - One aggregate query to identify active users (no N+1 scan of users table).
      - Per-user errors are swallowed so a single failure never aborts the run.
      - Returns a JSON-serialisable dict so the Lambda runtime can surface it to
        CloudWatch / EventBridge as the invocation result.

    Returns {"deteriorating": count, "processed": total}.

    This function is wired to a future scheduled job (EventBridge cron). No
    endpoint or background task calls it yet — it is ready for wiring.
    """
    from app.services.sentiment_trajectory_service import (  # lazy import
        analyze_trajectory,
        check_deterioration,
    )
    from app.models.user import User as UserModel  # avoid shadowing outer import

    now = datetime.now(UTC)
    window_cutoff = now - timedelta(days=14)

    # Step 1: collect distinct user_ids with at least one check-in in the last
    # 14 days. A single aggregate query keeps this O(1) round-trips.
    active_uid_rows = (await db.execute(
        select(MoodCheckin.user_id)
        .where(MoodCheckin.created_at >= window_cutoff)
        .distinct()
    )).all()

    user_ids = [r[0] for r in active_uid_rows]

    if not user_ids:
        logger.info(
            "Deterioration scan: no users with mood check-ins in the last 14 days."
        )
        return {"deteriorating": 0, "processed": 0}

    # Step 2: load user objects in a single IN query.
    user_rows = (await db.execute(
        select(UserModel).where(UserModel.id.in_(user_ids))
    )).scalars().all()

    processed = 0
    deteriorating = 0

    for user_obj in user_rows:
        try:
            trajectory = await analyze_trajectory(db, user_obj)
            if trajectory.is_deteriorating and trajectory.confidence in ("high", "medium"):
                deteriorating += 1
                logger.warning(
                    "Deterioration detected: user_id=%s confidence=%s "
                    "slope=%.4f avg_recent=%.2f avg_prior=%.2f checkins=%d",
                    user_obj.id,
                    trajectory.confidence,
                    trajectory.slope,
                    trajectory.avg_recent,
                    trajectory.avg_prior,
                    trajectory.checkin_count,
                )
            processed += 1
        except Exception as exc:
            # Per-user failure: log and continue — never abort the whole scan.
            logger.exception(
                "Deterioration scan failed for user_id=%s: %s", user_obj.id, exc
            )

    result = {"deteriorating": deteriorating, "processed": processed}
    logger.info("Deterioration scan job summary: %s", result)
    return result


async def check_emotional_dependency(db: AsyncSession) -> dict:
    """
    Detect users who may be over-relying on the chatbot.

    A user is flagged when they sent more than _DEPENDENCY_MSG_THRESHOLD (20)
    messages in the last _DEPENDENCY_WINDOW_DAYS (3) days. Flagged users only
    receive a log warning — no push notification or DB write. The intent is
    to surface a signal for product/clinical review, not to silently nudge
    the user (which would require additional consent and UX work).

    Returns {"flagged": N, "processed": M, "window_days": D, "threshold": T}.
    """
    now = datetime.now(UTC)
    window_cutoff = now - timedelta(days=_DEPENDENCY_WINDOW_DAYS)

    # Single aggregate query. Filter to user-role messages only — assistant
    # replies don't reflect user effort and would inflate the count.
    rows = (await db.execute(
        select(
            ChatMessage.user_id,
            func.count().label("msg_count"),
            func.count(func.distinct(ChatMessage.session_id)).label("session_count"),
        )
        .where(
            ChatMessage.created_at >= window_cutoff,
            ChatMessage.role == "user",
        )
        .group_by(ChatMessage.user_id)
    )).all()

    processed = len(rows)
    flagged = 0

    for r in rows:
        try:
            if (
                r.msg_count > _DEPENDENCY_MSG_THRESHOLD
                or r.session_count > _DEPENDENCY_SESSION_THRESHOLD
            ):
                flagged += 1
                logger.warning(
                    "Emotional dependency signal: user_id=%s messages=%d sessions=%d "
                    "window=%dd thresholds(msg=%d, sess=%d)",
                    r.user_id,
                    r.msg_count,
                    r.session_count,
                    _DEPENDENCY_WINDOW_DAYS,
                    _DEPENDENCY_MSG_THRESHOLD,
                    _DEPENDENCY_SESSION_THRESHOLD,
                )
        except Exception as exc:
            # Defensive: per-row processing should never throw, but if it does
            # we don't want to fail the whole batch.
            logger.exception("Dependency check failed for row %s: %s", r, exc)

    result = {
        "flagged": flagged,
        "processed": processed,
        "window_days": _DEPENDENCY_WINDOW_DAYS,
        "msg_threshold": _DEPENDENCY_MSG_THRESHOLD,
        "session_threshold": _DEPENDENCY_SESSION_THRESHOLD,
    }
    logger.info("Dependency check job summary: %s", result)
    return result
