"""
Tests for app/services/mood_service.py

Covers:
  create_checkin  — basic, secondary moods prefix
  list_checkins   — empty, pagination, has_more flag
  get_insights    — empty period, data aggregation, streak
"""
import pytest
from app.core.exceptions import AuthorizationError, NotFoundError
from datetime import UTC, datetime, timedelta

from app.models.mood_checkin import MoodCheckin
from app.schemas.mood import MoodCheckinCreate
from app.services import mood_service


# ── Create ─────────────────────────────────────────────────────────────────────

async def test_create_checkin_basic(db, test_user):
    data = MoodCheckinCreate(mood="alegre", intensity=4, secondary_moods=[])
    resp = await mood_service.create_checkin(db, test_user, data)

    assert resp.mood == "alegre"
    assert resp.intensity == 4
    assert resp.note is None
    assert resp.id is not None


async def test_create_checkin_with_note(db, test_user):
    data = MoodCheckinCreate(mood="ansioso", intensity=3, note="reunião difícil", secondary_moods=[])
    resp = await mood_service.create_checkin(db, test_user, data)

    assert resp.note == "reunião difícil"


async def test_create_checkin_secondary_moods_prefix(db, test_user):
    data = MoodCheckinCreate(
        mood="triste",
        intensity=2,
        note="dia ruim",
        secondary_moods=["cansado", "irritado"],
    )
    resp = await mood_service.create_checkin(db, test_user, data)

    assert resp.note is not None
    assert "Outras emoções: cansado, irritado" in resp.note
    assert "dia ruim" in resp.note


# ── List ───────────────────────────────────────────────────────────────────────

async def test_list_checkins_empty(db, test_user):
    resp = await mood_service.list_checkins(db, test_user)

    assert resp.total == 0
    assert resp.items == []
    assert resp.has_more is False


async def test_list_checkins_pagination(db, test_user):
    # Create 5 checkins
    for i in range(5):
        await mood_service.create_checkin(
            db, test_user,
            MoodCheckinCreate(mood=f"mood{i}", intensity=3, secondary_moods=[]),
        )

    page1 = await mood_service.list_checkins(db, test_user, page=1, page_size=3)
    page2 = await mood_service.list_checkins(db, test_user, page=2, page_size=3)

    assert page1.total == 5
    assert len(page1.items) == 3
    assert page1.has_more is True

    assert len(page2.items) == 2
    assert page2.has_more is False


async def test_list_checkins_only_own(db, test_user, other_user):
    """User only sees their own checkins."""
    await mood_service.create_checkin(
        db, test_user, MoodCheckinCreate(mood="calmo", intensity=3, secondary_moods=[])
    )
    await mood_service.create_checkin(
        db, other_user, MoodCheckinCreate(mood="triste", intensity=2, secondary_moods=[])
    )

    resp = await mood_service.list_checkins(db, test_user)
    assert resp.total == 1
    assert resp.items[0].mood == "calmo"


# ── Insights ───────────────────────────────────────────────────────────────────

async def test_insights_empty_period(db, test_user):
    resp = await mood_service.get_insights(db, test_user, period="week")

    assert resp.total_checkins == 0
    assert resp.average_intensity is None
    assert resp.most_common_mood is None
    assert resp.streak_days == 0
    assert resp.mood_distribution == {}


async def test_insights_with_data(db, test_user):
    moods = [
        ("feliz", 5),
        ("feliz", 4),
        ("ansioso", 2),
    ]
    for mood, intensity in moods:
        await mood_service.create_checkin(
            db, test_user,
            MoodCheckinCreate(mood=mood, intensity=intensity, secondary_moods=[]),
        )

    resp = await mood_service.get_insights(db, test_user, period="week")

    assert resp.total_checkins == 3
    assert resp.average_intensity == pytest.approx(11 / 3, rel=0.01)
    assert resp.most_common_mood == "feliz"
    assert resp.mood_distribution["feliz"] == 2
    assert resp.mood_distribution["ansioso"] == 1


async def test_insights_streak_today(db, test_user):
    """Creating a checkin today gives streak >= 1."""
    await mood_service.create_checkin(
        db, test_user,
        MoodCheckinCreate(mood="bem", intensity=4, secondary_moods=[]),
    )

    resp = await mood_service.get_insights(db, test_user, period="month")
    assert resp.streak_days >= 1


async def test_insights_streak_multi_day(db, test_user):
    """Inserting checkins with past dates should produce a multi-day streak."""
    today = datetime.now(UTC).date()

    for days_ago in range(3):
        checkin_dt = datetime(today.year, today.month, today.day) - timedelta(days=days_ago)
        checkin = MoodCheckin(
            user_id=test_user.id,
            mood="calmo",
            intensity=3,
            created_at=checkin_dt,
        )
        db.add(checkin)
    await db.commit()

    resp = await mood_service.get_insights(db, test_user, period="month")
    assert resp.streak_days >= 3


# ── generate_ai_insight (Phase 2) ─────────────────────────────────────────────

def _patch_openai_insight(text: str = "Insight gerado pela IA."):
    from unittest.mock import AsyncMock, MagicMock, patch
    choice = MagicMock()
    choice.message.content = text
    completion = MagicMock()
    completion.choices = [choice]
    completion.usage.total_tokens = 25
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=completion)
    return patch("app.services.mood_service.AsyncOpenAI", return_value=mock_client)


async def test_generate_ai_insight_persists_insight(db, test_user):
    checkin = await mood_service.create_checkin(
        db, test_user,
        MoodCheckinCreate(mood="ansioso", intensity=3, note="reunião difícil", secondary_moods=[]),
    )
    assert checkin.ai_insight is None

    with _patch_openai_insight("Ansiedade antes de reuniões é comum e manejável."):
        updated = await mood_service.generate_ai_insight(db, test_user, str(checkin.id))

    assert updated.id == checkin.id
    assert updated.ai_insight == "Ansiedade antes de reuniões é comum e manejável."


async def test_generate_ai_insight_idempotent(db, test_user):
    """Calling generate_ai_insight twice overwrites the previous value."""
    checkin = await mood_service.create_checkin(
        db, test_user,
        MoodCheckinCreate(mood="triste", intensity=2, secondary_moods=[]),
    )

    with _patch_openai_insight("Primeiro insight."):
        await mood_service.generate_ai_insight(db, test_user, str(checkin.id))

    with _patch_openai_insight("Segundo insight, mais detalhado."):
        updated = await mood_service.generate_ai_insight(db, test_user, str(checkin.id))

    assert updated.ai_insight == "Segundo insight, mais detalhado."


async def test_generate_ai_insight_with_history(db, test_user):
    """When prior check-ins exist, OpenAI must be called (history context included)."""
    from unittest.mock import AsyncMock, MagicMock, patch

    # Seed 3 prior check-ins
    for mood, intensity in [("feliz", 5), ("ansioso", 2), ("calmo", 4)]:
        await mood_service.create_checkin(
            db, test_user,
            MoodCheckinCreate(mood=mood, intensity=intensity, secondary_moods=[]),
        )

    target = await mood_service.create_checkin(
        db, test_user,
        MoodCheckinCreate(mood="triste", intensity=1, secondary_moods=[]),
    )

    choice = MagicMock()
    choice.message.content = "Você tem alternado bastante entre emoções."
    completion = MagicMock()
    completion.choices = [choice]
    completion.usage.total_tokens = 30
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=completion)

    with patch("app.services.mood_service.AsyncOpenAI", return_value=mock_client):
        updated = await mood_service.generate_ai_insight(db, test_user, str(target.id))

    # Verify the model was actually called
    mock_client.chat.completions.create.assert_called_once()
    call_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    # The user message should contain recent history
    user_msg = next(m for m in call_messages if m["role"] == "user")
    assert "feliz" in user_msg["content"] or "Histórico" in user_msg["content"]
    assert updated.ai_insight == "Você tem alternado bastante entre emoções."


async def test_generate_ai_insight_no_history(db, test_user):
    """With no prior check-ins, the function still generates an insight."""
    checkin = await mood_service.create_checkin(
        db, test_user,
        MoodCheckinCreate(mood="neutro", intensity=3, secondary_moods=[]),
    )

    with _patch_openai_insight("Sem histórico ainda, mas você fez bem em registrar."):
        updated = await mood_service.generate_ai_insight(db, test_user, str(checkin.id))

    assert updated.ai_insight is not None


async def test_generate_ai_insight_not_found(db, test_user):
    with _patch_openai_insight():
        with pytest.raises(NotFoundError):
            await mood_service.generate_ai_insight(
                db, test_user, "00000000-0000-0000-0000-000000000000"
            )


async def test_generate_ai_insight_wrong_owner(db, test_user, other_user):
    checkin = await mood_service.create_checkin(
        db, other_user,
        MoodCheckinCreate(mood="feliz", intensity=5, secondary_moods=[]),
    )

    with _patch_openai_insight():
        with pytest.raises(AuthorizationError):
            await mood_service.generate_ai_insight(db, test_user, str(checkin.id))
