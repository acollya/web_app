"""
Analytics schemas.

OverviewResponse    — dashboard card metrics (streak, totals, programs, appointments)
MoodTrendPoint      — single day in a mood trend series
MoodTrendResponse   — time-series wrapper for mood trend chart
ActivityDay         — single day in the activity heatmap
ActivityResponse    — heatmap wrapper with max_activity for scaling
"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# ── Overview ───────────────────────────────────────────────────────────────────

class OverviewResponse(BaseModel):
    # Mood
    total_mood_checkins: int
    mood_streak_days: int           # consecutive days with at least one check-in (up to today)
    avg_intensity_last_7d: Optional[float]  # None if no check-ins in last 7 days

    # Journal
    total_journal_entries: int
    journal_entries_last_30d: int

    # Programs
    programs_started: int           # at least one chapter completed
    programs_completed: int         # all chapters completed

    # Appointments
    upcoming_appointments: int      # pending/confirmed with date >= today

    # Account
    member_since: datetime


# ── Mood trend (line chart) ────────────────────────────────────────────────────

class MoodTrendPoint(BaseModel):
    date: date
    avg_intensity: float
    checkin_count: int
    dominant_mood: Optional[str]    # most frequent mood on this day


class MoodTrendResponse(BaseModel):
    period_days: int
    points: list[MoodTrendPoint]    # one entry per day that had at least one check-in


# ── Activity heatmap ───────────────────────────────────────────────────────────

class ActivityDay(BaseModel):
    date: date
    journal_count: int
    mood_count: int
    total: int                      # journal_count + mood_count


class ActivityResponse(BaseModel):
    period_days: int
    days: list[ActivityDay]         # only days with total > 0
    max_activity: int               # highest 'total' value in the period (for heatmap scaling)
