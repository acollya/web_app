"""
Mood check-in service — all DB operations for /mood endpoints.

create_checkin      — insert a new MoodCheckin row
list_checkins       — paginated history for a user
get_insights        — aggregated stats for week/month/year (pure DB, no AI)
generate_ai_insight — call OpenAI with recent history to produce a
                      personalised insight; persists in MoodCheckin.ai_insight
                      (Phase 2)

Insight periods:
  week  = last 7 days
  month = last 30 days
  year  = last 365 days

Each period is compared against the equal-length period immediately before it
to produce trend data (intensity_change_pct, checkin_count_change).

Streak calculation:
  Counts consecutive distinct calendar days (user's UTC date) going backwards
  from today that have at least one check-in.

AI insight prompt strategy:
  The model receives the current check-in (mood + intensity + note) plus up to
  INSIGHT_HISTORY_DAYS days of recent check-in summaries as context, so the
  insight can acknowledge patterns rather than treating each entry in isolation.
"""
import logging
import uuid
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.mood_checkin import MoodCheckin
from app.models.user import User
from app.services.persona_service import get_persona_context
from app.schemas.mood import (
    MoodCheckinCreate,
    MoodCheckinResponse,
    MoodHistoryResponse,
    MoodInsightsResponse,
)

logger = logging.getLogger(__name__)

Period = Literal["week", "month", "year"]

_PERIOD_DAYS: dict[str, int] = {
    "week": 7,
    "month": 30,
    "year": 365,
}

# ── AI insight constants ───────────────────────────────────────────────────────

# How many days of history to include as context for the AI insight.
INSIGHT_HISTORY_DAYS = 7

_INSIGHT_SYSTEM_PROMPT = """\
Você é um assistente de bem-estar emocional empático e especializado em \
Terapia Cognitivo-Comportamental (TCC).
O usuário registrou um check-in de humor. Com base nesse check-in e no \
histórico recente fornecido, escreva um insight curto (2 a 4 frases) em \
português do Brasil que:
1. Reconheça o estado emocional atual de forma acolhedora.
2. Aponte (com gentileza) algum padrão ou tendência observada no histórico, \
se houver.
3. Sugira uma ação pequena e concreta que possa ajudar.
Seja breve, caloroso e direto. Não use listas, subtítulos nem markdown.
"""


# ── Create ─────────────────────────────────────────────────────────────────────

async def create_checkin(
    db: AsyncSession, user: User, data: MoodCheckinCreate
) -> MoodCheckinResponse:
    """
    Persist a new mood check-in.

    Secondary moods are appended to the note as a structured prefix so they
    are searchable and not lost, while keeping the schema simple.
    """
    note = data.note or ""
    if data.secondary_moods:
        prefix = "Outras emoções: " + ", ".join(data.secondary_moods)
        note = f"{prefix}\n\n{note}".strip() if note else prefix

    checkin = MoodCheckin(
        user_id=user.id,
        mood=data.mood,
        intensity=data.intensity,
        note=note or None,
    )
    db.add(checkin)
    await db.commit()
    await db.refresh(checkin)

    logger.info("Mood check-in created: user=%s mood=%s", user.id, data.mood)
    return MoodCheckinResponse.model_validate(checkin)


# ── List ───────────────────────────────────────────────────────────────────────

async def list_checkins(
    db: AsyncSession,
    user: User,
    page: int = 1,
    page_size: int = 20,
) -> MoodHistoryResponse:
    offset = (page - 1) * page_size

    # Total count
    count_result = await db.execute(
        select(func.count()).where(MoodCheckin.user_id == user.id)
    )
    total: int = count_result.scalar_one()

    # Paginated rows
    result = await db.execute(
        select(MoodCheckin)
        .where(MoodCheckin.user_id == user.id)
        .order_by(MoodCheckin.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.scalars().all()

    return MoodHistoryResponse(
        items=[MoodCheckinResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(rows)) < total,
    )


# ── Insights ───────────────────────────────────────────────────────────────────

async def get_insights(
    db: AsyncSession, user: User, period: Period
) -> MoodInsightsResponse:
    days = _PERIOD_DAYS[period]
    now = datetime.now(UTC)
    period_start = now - timedelta(days=days)
    prev_period_start = period_start - timedelta(days=days)

    # ── Current period rows ────────────────────────────────────────────────────
    current_result = await db.execute(
        select(MoodCheckin)
        .where(
            MoodCheckin.user_id == user.id,
            MoodCheckin.created_at >= period_start,
        )
        .order_by(MoodCheckin.created_at.asc())
    )
    current_rows: list[MoodCheckin] = list(current_result.scalars().all())

    # ── Previous period rows (for trend) ──────────────────────────────────────
    prev_result = await db.execute(
        select(MoodCheckin)
        .where(
            MoodCheckin.user_id == user.id,
            MoodCheckin.created_at >= prev_period_start,
            MoodCheckin.created_at < period_start,
        )
    )
    prev_rows: list[MoodCheckin] = list(prev_result.scalars().all())

    # ── Aggregations ───────────────────────────────────────────────────────────
    total_current = len(current_rows)
    total_prev = len(prev_rows)

    avg_intensity: float | None = None
    if current_rows:
        avg_intensity = round(
            sum(r.intensity for r in current_rows) / total_current, 2
        )

    mood_distribution: dict[str, int] = dict(
        Counter(r.mood for r in current_rows)
    )
    most_common_mood: str | None = (
        max(mood_distribution, key=mood_distribution.__getitem__)
        if mood_distribution
        else None
    )

    # Trend: intensity change %
    intensity_change_pct: float | None = None
    if prev_rows and current_rows:
        prev_avg = sum(r.intensity for r in prev_rows) / total_prev
        curr_avg = sum(r.intensity for r in current_rows) / total_current
        if prev_avg > 0:
            intensity_change_pct = round((curr_avg - prev_avg) / prev_avg * 100, 1)

    checkin_count_change: int | None = None
    if total_prev > 0 or total_current > 0:
        checkin_count_change = total_current - total_prev

    # ── Streak ─────────────────────────────────────────────────────────────────
    streak_days = _compute_streak(current_rows + prev_rows, now.date())

    return MoodInsightsResponse(
        period=period,
        total_checkins=total_current,
        average_intensity=avg_intensity,
        mood_distribution=mood_distribution,
        most_common_mood=most_common_mood,
        intensity_change_pct=intensity_change_pct,
        checkin_count_change=checkin_count_change,
        streak_days=streak_days,
    )


# ── AI insight (Phase 2) ───────────────────────────────────────────────────────

async def generate_ai_insight(
    db: AsyncSession, user: User, checkin_id: str
) -> MoodCheckinResponse:
    """
    Generate a personalised AI insight for a mood check-in and persist it in
    MoodCheckin.ai_insight.

    Context sent to the model:
      - The target check-in (mood, intensity, note).
      - Up to INSIGHT_HISTORY_DAYS days of recent check-ins (summarised as
        plain text) to allow the model to reference patterns.

    Idempotent: calling again overwrites the previous insight.
    Raises NotFoundError / AuthorizationError when appropriate.
    """
    result = await db.execute(
        select(MoodCheckin).where(MoodCheckin.id == uuid.UUID(checkin_id))
    )
    checkin: MoodCheckin | None = result.scalar_one_or_none()

    if checkin is None:
        raise NotFoundError("Mood check-in not found")
    if str(checkin.user_id) != str(user.id):
        raise AuthorizationError("This check-in does not belong to you")

    # Load recent history for context (excluding the target check-in itself)
    cutoff = datetime.now(UTC) - timedelta(days=INSIGHT_HISTORY_DAYS)
    history_result = await db.execute(
        select(MoodCheckin)
        .where(
            MoodCheckin.user_id == user.id,
            MoodCheckin.created_at >= cutoff,
            MoodCheckin.id != checkin.id,
        )
        .order_by(MoodCheckin.created_at.desc())
        .limit(20)
    )
    history_rows: list[MoodCheckin] = list(history_result.scalars().all())

    # Build a concise plain-text summary of recent check-ins
    history_lines: list[str] = []
    for h in reversed(history_rows):
        day = h.created_at.strftime("%d/%m")
        note_snippet = f" — {h.note[:80]}" if h.note else ""
        history_lines.append(
            f"  {day}: {h.mood} (intensidade {h.intensity}/5){note_snippet}"
        )
    history_text = (
        "Histórico recente (últimos 7 dias):\n" + "\n".join(history_lines)
        if history_lines
        else "Sem check-ins anteriores nos últimos 7 dias."
    )

    note_text = f"\nNota do usuário: {checkin.note}" if checkin.note else ""
    user_message = (
        f"Check-in atual: {checkin.mood} (intensidade {checkin.intensity}/5){note_text}\n\n"
        f"{history_text}"
    )

    # Busca persona para personalizar o insight
    persona_context = await get_persona_context(db, user)
    system_content = _INSIGHT_SYSTEM_PROMPT
    if persona_context:
        system_content = f"{_INSIGHT_SYSTEM_PROMPT}\n\n{persona_context}"

    client = AsyncOpenAI(api_key=settings.openai_config["api_key"])
    model = settings.openai_config.get("chat_model", "gpt-4o-mini")

    completion = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_message},
        ],
        stream=False,
    )

    insight: str = completion.choices[0].message.content or ""
    checkin.ai_insight = insight.strip()

    await db.commit()
    await db.refresh(checkin)

    logger.info(
        "Mood AI insight generated: user=%s checkin=%s tokens=%s",
        user.id,
        checkin_id,
        completion.usage.total_tokens if completion.usage else None,
    )
    return MoodCheckinResponse.model_validate(checkin)


def _compute_streak(rows: list[MoodCheckin], today: date) -> int:
    """Count consecutive days (backwards from today) that have a check-in."""
    if not rows:
        return 0

    days_with_checkin: set[date] = {
        r.created_at.date() if r.created_at.tzinfo else r.created_at.date()
        for r in rows
    }

    streak = 0
    current_day = today
    while current_day in days_with_checkin:
        streak += 1
        current_day -= timedelta(days=1)
    return streak
