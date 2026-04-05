"""
Analytics service — read-only aggregation queries.

get_overview     — dashboard metrics: streak, totals, programs, appointments
get_mood_trend   — daily avg intensity + dominant mood for the last N days
get_activity     — journal + mood activity per calendar day (heatmap data)

Query strategy:
  - All queries are READ-ONLY (no writes).
  - Aggregations run on the DB side (GROUP BY / COUNT / AVG).
  - Python-side work limited to merging two result sets and filling zero-rows.
  - No N+1: each function issues at most 4 queries total.
"""
import logging
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from sqlalchemy import cast, func, select, type_coerce, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
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

    # 1. Mood totals + streak
    mood_result = await db.execute(
        select(
            type_coerce(func.date(MoodCheckin.created_at), Date).label("day"),
            func.avg(MoodCheckin.intensity).label("avg_int"),
            func.count().label("cnt"),
        )
        .where(MoodCheckin.user_id == user.id)
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

    # 2. Journal totals
    journal_result = await db.execute(
        select(
            type_coerce(func.date(JournalEntry.created_at), Date).label("day"),
            func.count().label("cnt"),
        )
        .where(JournalEntry.user_id == user.id)
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
    cutoff = datetime.now(UTC) - timedelta(days=days)

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
    cutoff = datetime.now(UTC) - timedelta(days=days)

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
