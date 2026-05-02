"""
Mood check-in service — all DB operations for /mood endpoints.

create_checkin      — insert a new MoodCheckin row and generate AI insight inline
list_checkins       — paginated history for a user
get_insights        — aggregated stats for week/month/year (pure DB, no AI)
generate_ai_insight — (re)generate AI insight for an existing check-in (idempotent)

Insight periods:
  week  = last 7 days
  month = last 30 days
  year  = last 365 days

Each period is compared against the equal-length period immediately before it
to produce trend data (intensity_change_pct, checkin_count_change).

Streak calculation:
  Counts consecutive distinct calendar days (user's UTC date) going backwards
  from today that have at least one check-in.

AI insight strategy:
  Generated synchronously at save time — no button required.
  Uses Claude Haiku with extended thinking for deeper pattern analysis.
  If the AI call fails for any reason the check-in is still saved; the
  insight will simply be absent (null) until a retry succeeds.

  Context sent to the model:
    - The current check-in (mood, intensity, note).
    - Up to INSIGHT_HISTORY_DAYS days of recent check-in summaries.
    - Up to 3 recent journal entries (last 7 days, 150-char snippets).
    - Semantically relevant fragments from chat/journal/mood via RAG.
    - User persona context for personalisation.
"""
import logging
import uuid
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.llm_provider import get_insight_provider, _INSIGHT_MAX_TOKENS
from app.database import AsyncSessionLocal
from app.models.journal_entry import JournalEntry
from app.models.mood_checkin import MoodCheckin
from app.models.user import User
from app.services.persona_service import get_persona_context
from app.services.rag_service import embed_and_store, retrieve_context
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
Você é um assistente de bem-estar emocional profundamente empático, especializado em \
Terapia Cognitivo-Comportamental (TCC) e escuta ativa.

O usuário acaba de registrar um check-in de humor. Você receberá:
- O check-in atual (humor, intensidade, nota opcional).
- O histórico de check-ins dos últimos 7 dias.
- Entradas recentes do diário, quando disponíveis.
- Trechos relevantes de conversas anteriores, quando disponíveis.

Ao construir o insight, integre todas as fontes disponíveis:
- Qual é a qualidade e intensidade da emoção relatada agora?
- Existe algum padrão recorrente ou tendência nos últimos dias (melhora, piora, oscilação)?
- O diário ou as conversas recentes revelam um contexto, gatilho ou tema que se conecta \
ao estado emocional atual?
- Qual seria a ação mais gentil e concreta para apoiar esse momento?

Escreva uma resposta curta (2 a 4 frases) em português do Brasil que:
1. Reconheça o estado emocional atual de forma acolhedora e específica (não genérica).
2. Aponte com delicadeza algum padrão, mudança ou conexão observada entre as fontes, \
se houver — sem citar explicitamente "no diário" ou "na conversa".
3. Sugira uma ação pequena, concreta e realista que possa ajudar agora.

Seja caloroso, direto e humano. Não use listas, subtítulos nem markdown. \
Escreva como se estivesse conversando com a pessoa, não a avaliando.
"""


# ── Private helpers ───────────────────────────────────────────────────────────

async def _build_insight_message(
    db: AsyncSession, user: User, checkin: MoodCheckin
) -> str:
    """
    Monta o user message para a chamada de insight.

    Inclui:
    - Check-in atual (humor, intensidade, nota)
    - Histórico de check-ins dos últimos 7 dias
    - Entradas de diário dos últimos 7 dias (até 3, snippet de 150 chars)
    """
    cutoff = datetime.now(UTC) - timedelta(days=INSIGHT_HISTORY_DAYS)

    # ── Histórico de humor ────────────────────────────────────────────────────
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

    history_lines: list[str] = []
    for h in reversed(history_rows):
        day = h.created_at.strftime("%d/%m")
        note_snippet = f" — {h.note[:80]}" if h.note else ""
        history_lines.append(
            f"  {day}: {h.mood} (intensidade {h.intensity}/5){note_snippet}"
        )
    history_text = (
        "Histórico de humor (últimos 7 dias):\n" + "\n".join(history_lines)
        if history_lines
        else "Sem check-ins anteriores nos últimos 7 dias."
    )

    # ── Entradas de diário recentes ───────────────────────────────────────────
    journal_result = await db.execute(
        select(JournalEntry)
        .where(
            JournalEntry.user_id == user.id,
            JournalEntry.created_at >= cutoff,
        )
        .order_by(JournalEntry.created_at.desc())
        .limit(3)
    )
    journal_rows: list[JournalEntry] = list(journal_result.scalars().all())

    journal_text = ""
    if journal_rows:
        journal_lines: list[str] = []
        for j in reversed(journal_rows):
            day = j.created_at.strftime("%d/%m")
            snippet = j.content[:150].replace("\n", " ")
            label = j.title or "Diário"
            journal_lines.append(f'  {day} [{label}]: "{snippet}…"')
        journal_text = "\n\nEntradas do diário (últimos 7 dias):\n" + "\n".join(journal_lines)

    # ── Monta mensagem final ──────────────────────────────────────────────────
    note_text = f"\nNota do usuário: {checkin.note}" if checkin.note else ""
    return (
        f"Check-in atual: {checkin.mood} (intensidade {checkin.intensity}/5)"
        f"{note_text}\n\n{history_text}{journal_text}"
    )


async def _run_insight(db: AsyncSession, user: User, checkin: MoodCheckin) -> None:
    """
    Generate and persist the AI insight for a check-in.

    Modifies checkin.ai_insight and commits. Silently logs errors so the
    caller (create_checkin) is never blocked by AI failures.
    """
    try:
        user_message = await _build_insight_message(db, user, checkin)

        # Query RAG composta — foca em fragmentos relacionados ao estado emocional atual
        rag_query = f"{checkin.mood} (intensidade {checkin.intensity}/5)"
        if checkin.note:
            rag_query += f". {checkin.note}"

        persona_context = await get_persona_context(db, user, query_text=rag_query)
        rag_context = await retrieve_context(db, user, rag_query)

        # Blocos nomeados — o modelo atende melhor a seções com cabeçalhos distintos
        sections: list[str] = []
        if persona_context:
            sections.append(f"## Perfil do usuário\n{persona_context}")
        if rag_context:
            sections.append(f"## Histórico relevante de conversas e registros\n{rag_context}")
        system_content = (
            _INSIGHT_SYSTEM_PROMPT + "\n\n" + "\n\n".join(sections)
            if sections else _INSIGHT_SYSTEM_PROMPT
        )

        provider = get_insight_provider()
        insight_text, tokens_used = await provider.complete(
            system=system_content,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=_INSIGHT_MAX_TOKENS,
        )

        checkin.ai_insight = insight_text.strip()
        await db.commit()
        await db.refresh(checkin)

        logger.info(
            "Mood AI insight generated: user=%s checkin=%s tokens=%s",
            user.id,
            checkin.id,
            tokens_used,
        )
    except Exception as exc:
        logger.warning(
            "Mood AI insight failed (non-blocking): user=%s checkin=%s error=%s",
            user.id,
            checkin.id,
            exc,
        )


# ── Background task wrappers ───────────────────────────────────────────────────

async def _bg_embed_checkin(checkin_id: uuid.UUID, embed_text: str) -> None:
    async with AsyncSessionLocal() as db:
        await embed_and_store(db, checkin_id, "mood_checkins", embed_text)


async def _bg_run_insight(checkin_id: uuid.UUID, user_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        try:
            checkin = await db.get(MoodCheckin, checkin_id)
            user = await db.get(User, user_id)
            if checkin and user:
                await _run_insight(db, user, checkin)
        except Exception as exc:
            logger.warning("_bg_run_insight failed: checkin=%s %s", checkin_id, exc)


# ── Create ─────────────────────────────────────────────────────────────────────

async def create_checkin(
    db: AsyncSession, user: User, data: MoodCheckinCreate, background_tasks: BackgroundTasks
) -> MoodCheckinResponse:
    """
    Persist a new mood check-in and generate an AI insight inline.

    Secondary moods are appended to the note as a structured prefix so they
    are searchable and not lost, while keeping the schema simple.

    The AI insight is generated synchronously after the check-in is saved.
    If the AI call fails the check-in is still returned — ai_insight will be null.
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

    embed_text = f"{checkin.mood} (intensidade {checkin.intensity}/5)"
    if checkin.note:
        embed_text += f". {checkin.note}"
    background_tasks.add_task(_bg_embed_checkin, checkin.id, embed_text)
    background_tasks.add_task(_bg_run_insight, checkin.id, user.id)

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


# ── AI insight — idempotent regeneration ──────────────────────────────────────

async def generate_ai_insight(
    db: AsyncSession, user: User, checkin_id: str
) -> MoodCheckinResponse:
    """
    (Re)generate the AI insight for an existing check-in and persist it.

    Idempotent — calling again overwrites the previous insight.
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

    await _run_insight(db, user, checkin)
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
