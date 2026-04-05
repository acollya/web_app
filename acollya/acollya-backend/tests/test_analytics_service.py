"""
Tests for app/services/analytics_service.py

Strategy: seed MoodCheckin, JournalEntry, Program/Chapter/ProgramProgress,
and Appointment rows directly in DB. All queries are read-only aggregations.

Covers:
  get_overview   — empty user, mood streak, journal counts, programs, appointments
  get_mood_trend — empty range, single day aggregation, multi-day grouping
  get_activity   — empty range, mood-only days, journal-only days, merged days
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.appointment import Appointment
from app.models.journal_entry import JournalEntry
from app.models.mood_checkin import MoodCheckin
from app.models.program import Chapter, Program
from app.models.program_progress import ProgramProgress
from app.models.therapist import Therapist
from app.services import analytics_service


# ── Helpers ─────────────────────────────────────────────────────────────────────

async def _add_mood(db, user, *, mood: str = "feliz", intensity: int = 4, days_ago: int = 0):
    created_at = datetime.now(UTC) - timedelta(days=days_ago)
    m = MoodCheckin(
        user_id=user.id,
        mood=mood,
        intensity=intensity,
        note=None,
        created_at=created_at,
    )
    db.add(m)
    await db.commit()


async def _add_journal(db, user, *, days_ago: int = 0):
    created_at = datetime.now(UTC) - timedelta(days=days_ago)
    j = JournalEntry(
        user_id=user.id,
        title="Título",
        content="Conteúdo",
        created_at=created_at,
    )
    db.add(j)
    await db.commit()


async def _make_program_with_chapters(db, *, program_id: str = "prog-001", num_chapters: int = 2):
    prog = Program(
        id=program_id, title="Programa", description="Desc",
        category="saude", duration_days=7, difficulty="beginner",
        is_premium=False, is_active=True, sort_order=0,
    )
    db.add(prog)
    await db.commit()
    for i in range(1, num_chapters + 1):
        ch = Chapter(
            id=f"{program_id}-ch-{i}", program_id=program_id, order=i,
            title=f"Cap {i}", content=".", content_type="text", duration_minutes=5,
        )
        db.add(ch)
    await db.commit()


async def _complete_chapter(db, user, program_id: str, chapter_id: str):
    pp = ProgramProgress(
        user_id=user.id, program_id=program_id,
        chapter_id=chapter_id, completed=True, completed_at=datetime.now(UTC),
    )
    db.add(pp)
    await db.commit()


async def _add_appointment(db, user, *, days_ahead: int = 3, status: str = "pending"):
    t = Therapist(
        id="t-analytics", name="Dr. Analytics", photo_key=None, bio="",
        specialties='[]', credentials='[]', crp="00/00000",
        rating=Decimal("5.0"), review_count=0,
        hourly_rate=Decimal("100.00"), premium_discount_pct=0,
        working_days_mask=31, slot_start="09:00", slot_end="17:00",
        is_active=True, sort_order=0,
    )
    db.add(t)
    await db.commit()
    appt = Appointment(
        user_id=user.id, therapist_id="t-analytics",
        date=datetime.now(UTC).date() + timedelta(days=days_ahead),
        time="10:00", status=status, payment_status="pending",
        amount=Decimal("100.00"),
    )
    db.add(appt)
    await db.commit()


# ── get_overview ─────────────────────────────────────────────────────────────────

async def test_overview_all_zeros_for_new_user(db, test_user):
    resp = await analytics_service.get_overview(db, test_user)

    assert resp.total_mood_checkins == 0
    assert resp.mood_streak_days == 0
    assert resp.avg_intensity_last_7d is None
    assert resp.total_journal_entries == 0
    assert resp.journal_entries_last_30d == 0
    assert resp.programs_started == 0
    assert resp.programs_completed == 0
    assert resp.upcoming_appointments == 0


async def test_overview_counts_mood_checkins(db, test_user):
    await _add_mood(db, test_user, days_ago=0)
    await _add_mood(db, test_user, days_ago=1)

    resp = await analytics_service.get_overview(db, test_user)
    assert resp.total_mood_checkins == 2


async def test_overview_streak_consecutive_days(db, test_user):
    await _add_mood(db, test_user, days_ago=0)
    await _add_mood(db, test_user, days_ago=1)
    await _add_mood(db, test_user, days_ago=2)

    resp = await analytics_service.get_overview(db, test_user)
    assert resp.mood_streak_days == 3


async def test_overview_avg_intensity_last_7d(db, test_user):
    await _add_mood(db, test_user, intensity=4, days_ago=1)
    await _add_mood(db, test_user, intensity=2, days_ago=2)

    resp = await analytics_service.get_overview(db, test_user)
    assert resp.avg_intensity_last_7d == 3.0


async def test_overview_counts_journal_entries(db, test_user):
    await _add_journal(db, test_user, days_ago=0)
    await _add_journal(db, test_user, days_ago=5)

    resp = await analytics_service.get_overview(db, test_user)
    assert resp.total_journal_entries == 2
    assert resp.journal_entries_last_30d == 2


async def test_overview_programs_started_and_completed(db, test_user):
    await _make_program_with_chapters(db, program_id="prog-001", num_chapters=1)

    await _complete_chapter(db, test_user, "prog-001", "prog-001-ch-1")

    resp = await analytics_service.get_overview(db, test_user)
    assert resp.programs_started == 1
    assert resp.programs_completed == 1


async def test_overview_upcoming_appointments(db, test_user):
    await _add_appointment(db, test_user, days_ahead=3)

    resp = await analytics_service.get_overview(db, test_user)
    assert resp.upcoming_appointments == 1


async def test_overview_cancelled_appointment_not_counted(db, test_user):
    await _add_appointment(db, test_user, days_ahead=3, status="cancelled")

    resp = await analytics_service.get_overview(db, test_user)
    assert resp.upcoming_appointments == 0


# ── get_mood_trend ────────────────────────────────────────────────────────────

async def test_mood_trend_empty_range(db, test_user):
    resp = await analytics_service.get_mood_trend(db, test_user, days=30)

    assert resp.period_days == 30
    assert resp.points == []


async def test_mood_trend_single_day(db, test_user):
    await _add_mood(db, test_user, mood="ansioso", intensity=3, days_ago=1)

    resp = await analytics_service.get_mood_trend(db, test_user, days=7)

    assert len(resp.points) == 1
    assert resp.points[0].avg_intensity == 3.0
    assert resp.points[0].dominant_mood == "ansioso"
    assert resp.points[0].checkin_count == 1


async def test_mood_trend_multiple_days_grouped(db, test_user):
    await _add_mood(db, test_user, mood="feliz", intensity=5, days_ago=1)
    await _add_mood(db, test_user, mood="feliz", intensity=3, days_ago=1)  # same day
    await _add_mood(db, test_user, mood="triste", intensity=2, days_ago=2)

    resp = await analytics_service.get_mood_trend(db, test_user, days=7)

    assert len(resp.points) == 2
    # Day 1 back: 2 checkins, avg = 4.0
    day1 = next(p for p in resp.points if p.checkin_count == 2)
    assert day1.avg_intensity == 4.0
    assert day1.dominant_mood == "feliz"


async def test_mood_trend_dominant_mood_most_common(db, test_user):
    """Three 'triste' vs one 'feliz' on same day → dominant = 'triste'."""
    for _ in range(3):
        await _add_mood(db, test_user, mood="triste", intensity=2, days_ago=0)
    await _add_mood(db, test_user, mood="feliz", intensity=5, days_ago=0)

    resp = await analytics_service.get_mood_trend(db, test_user, days=1)

    assert resp.points[0].dominant_mood == "triste"


# ── get_activity ──────────────────────────────────────────────────────────────

async def test_activity_empty_range(db, test_user):
    resp = await analytics_service.get_activity(db, test_user, days=30)

    assert resp.period_days == 30
    assert resp.days == []
    assert resp.max_activity == 0


async def test_activity_mood_only_day(db, test_user):
    await _add_mood(db, test_user, days_ago=1)
    await _add_mood(db, test_user, days_ago=1)

    resp = await analytics_service.get_activity(db, test_user, days=7)

    assert len(resp.days) == 1
    assert resp.days[0].mood_count == 2
    assert resp.days[0].journal_count == 0
    assert resp.days[0].total == 2
    assert resp.max_activity == 2


async def test_activity_journal_only_day(db, test_user):
    await _add_journal(db, test_user, days_ago=2)

    resp = await analytics_service.get_activity(db, test_user, days=7)

    assert len(resp.days) == 1
    assert resp.days[0].journal_count == 1
    assert resp.days[0].mood_count == 0


async def test_activity_merged_same_day(db, test_user):
    await _add_mood(db, test_user, days_ago=1)
    await _add_journal(db, test_user, days_ago=1)

    resp = await analytics_service.get_activity(db, test_user, days=7)

    assert len(resp.days) == 1
    assert resp.days[0].total == 2
    assert resp.days[0].mood_count == 1
    assert resp.days[0].journal_count == 1


async def test_activity_max_activity_correct(db, test_user):
    # day 1: 3 items; day 2: 1 item
    for _ in range(3):
        await _add_mood(db, test_user, days_ago=1)
    await _add_journal(db, test_user, days_ago=2)

    resp = await analytics_service.get_activity(db, test_user, days=7)

    assert resp.max_activity == 3
