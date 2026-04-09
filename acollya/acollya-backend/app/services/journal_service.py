"""
Journal service — all DB operations for /journal endpoints.

create_entry        — insert a new JournalEntry and generate AI reflection inline
list_entries        — paginated history, newest first
get_entry           — single entry (with ownership check)
update_entry        — edit content and/or title; regenerates reflection if content changed
delete_entry        — hard delete (GDPR/LGPD erasure applies at user-level)
generate_reflection — (re)generate AI reflection for an existing entry (idempotent)

Title auto-derivation:
  If no title is provided on create, we extract the first non-empty line of
  content and truncate it to 80 characters. This keeps list views readable
  without requiring users to fill a separate title field.

AI reflection strategy:
  Generated synchronously at save time — no button required.
  Uses Claude Haiku with extended thinking for richer CBT-style reflections.
  If the AI call fails the entry is still saved; ai_reflection will be null.
  On update, if content changed, the reflection is regenerated synchronously.

  The model is instructed to think deeply before responding, producing a
  3–5 sentence reflection in PT-BR that:
    1. Acknowledges the emotion expressed with genuine empathy, calibrated
       by the user's mood check-in from the same day (if available).
    2. Identifies one cognitive pattern present in the text (gently).
    3. Offers one concrete reframing question or actionable suggestion.

  Context sent to the model:
    - Journal entry content (and title when present).
    - Most recent mood check-in from the last 24h (mood, intensity, note).
    - Semantically relevant fragments from chat/journal/mood via RAG.
    - User persona context for personalisation.
"""
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.llm_provider import get_insight_provider, _INSIGHT_MAX_TOKENS
from app.models.journal_entry import JournalEntry
from app.models.mood_checkin import MoodCheckin
from app.models.user import User
from app.services.persona_service import get_persona_context
from app.services.rag_service import embed_and_store, retrieve_context
from app.schemas.journal import (
    JournalEntryCreate,
    JournalEntryResponse,
    JournalEntryUpdate,
    JournalListResponse,
)

logger = logging.getLogger(__name__)

_MAX_AUTO_TITLE = 80

# ── AI reflection constants ────────────────────────────────────────────────────

_REFLECTION_SYSTEM_PROMPT = """\
Você é um terapeuta compassivo e experiente, especializado em \
Terapia Cognitivo-Comportamental (TCC) e escrita terapêutica.

O usuário compartilhou uma entrada de diário. Você receberá a entrada e, \
quando disponível, o estado emocional registrado pelo usuário no mesmo dia \
(check-in de humor). Use essa informação para calibrar o tom e a profundidade \
da reflexão — uma entrada escrita em um momento de alta intensidade emocional \
merece um acolhimento diferente de uma escrita em estado neutro.

Antes de responder, reflita profundamente sobre o que está sendo expresso — \
não apenas as palavras, mas as emoções subjacentes, os padrões de pensamento \
e o que essa pessoa pode estar precisando neste momento.

Ao analisar a entrada, considere:
- Qual emoção predominante está sendo expressa, e há nuances secundárias?
- O estado emocional do dia (se informado) confirma, contrasta ou amplifica \
o que está escrito?
- Existe algum padrão cognitivo identificável (catastrofização, \
generalização, leitura mental, autocrítica excessiva)?
- O que a pessoa parece precisar: validação, perspectiva, encorajamento, \
ou uma ação concreta?
- Qual seria a resposta mais gentil, útil e autêntica para este momento?

Escreva uma reflexão curta (3 a 5 frases) em português do Brasil que:
1. Acolha a emoção expressa com empatia genuína e específica (não genérica), \
considerando o estado emocional do dia quando disponível.
2. Identifique suavemente um padrão cognitivo presente no texto, \
sem rotular ou julgar o usuário.
3. Ofereça uma pergunta de reencadramento ou uma ação concreta e gentil \
que possa ajudar.

Seja caloroso, humano e direto. Não use listas, subtítulos nem markdown. \
Escreva como um terapeuta que realmente se importa, não como um chatbot. \
Nunca mencione explicitamente "seu check-in" ou "seu registro de humor".
"""


def _derive_title(content: str) -> Optional[str]:
    """Extract the first non-empty line of content as a fallback title."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:_MAX_AUTO_TITLE]
    return None


# ── Private helper ─────────────────────────────────────────────────────────────

async def _run_reflection(db: AsyncSession, user: User, entry: JournalEntry) -> None:
    """
    Generate and persist the AI reflection for a journal entry.

    Modifies entry.ai_reflection and commits. Silently logs errors so the
    caller (create_entry / update_entry) is never blocked by AI failures.
    """
    try:
        # ── D1: busca o check-in mais recente das últimas 24h ─────────────────
        since = datetime.now(UTC) - timedelta(hours=24)
        mood_result = await db.execute(
            select(MoodCheckin)
            .where(
                MoodCheckin.user_id == user.id,
                MoodCheckin.created_at >= since,
            )
            .order_by(MoodCheckin.created_at.desc())
            .limit(1)
        )
        recent_checkin: MoodCheckin | None = mood_result.scalar_one_or_none()

        # ── D2: monta user_message com estado emocional do dia ────────────────
        if recent_checkin:
            mood_line = (
                f"Estado emocional do dia: {recent_checkin.mood} "
                f"(intensidade {recent_checkin.intensity}/5)"
            )
            if recent_checkin.note:
                mood_line += f" — {recent_checkin.note[:100]}"
            user_message = f"{mood_line}\n\nEntrada do diário:\n{entry.content}"
        else:
            user_message = entry.content

        # ── Contexto: persona + RAG (query = conteúdo da entrada) ────────────
        persona_context = await get_persona_context(db, user)
        rag_context = await retrieve_context(db, user, entry.content)

        sections: list[str] = []
        if persona_context:
            sections.append(f"## Perfil do usuário\n{persona_context}")
        if rag_context:
            sections.append(f"## Histórico relevante\n{rag_context}")
        system_content = (
            _REFLECTION_SYSTEM_PROMPT + "\n\n" + "\n\n".join(sections)
            if sections else _REFLECTION_SYSTEM_PROMPT
        )

        provider = get_insight_provider()
        reflection_text, tokens_used = await provider.complete(
            system=system_content,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=_INSIGHT_MAX_TOKENS,
        )

        entry.ai_reflection = reflection_text.strip()
        await db.commit()
        await db.refresh(entry)

        logger.info(
            "Journal reflection generated: user=%s entry=%s tokens=%s",
            user.id,
            entry.id,
            tokens_used,
        )
    except Exception as exc:
        logger.warning(
            "Journal reflection failed (non-blocking): user=%s entry=%s error=%s",
            user.id,
            entry.id,
            exc,
        )


# ── Create ─────────────────────────────────────────────────────────────────────

async def create_entry(
    db: AsyncSession, user: User, data: JournalEntryCreate
) -> JournalEntryResponse:
    """
    Persist a new journal entry and generate an AI reflection inline.

    If the AI call fails the entry is still returned — ai_reflection will be null.
    """
    title = data.title or _derive_title(data.content)

    entry = JournalEntry(
        user_id=user.id,
        title=title,
        content=data.content,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    logger.info("Journal entry created: user=%s entry=%s", user.id, entry.id)

    # Embedding para RAG — título + conteúdo
    embed_text = f"{entry.title}\n{entry.content}" if entry.title else entry.content
    await embed_and_store(db, entry.id, "journal_entries", embed_text)

    await _run_reflection(db, user, entry)

    return JournalEntryResponse.model_validate(entry)


# ── List ───────────────────────────────────────────────────────────────────────

async def list_entries(
    db: AsyncSession,
    user: User,
    page: int = 1,
    page_size: int = 20,
) -> JournalListResponse:
    offset = (page - 1) * page_size

    count_result = await db.execute(
        select(func.count()).where(JournalEntry.user_id == user.id)
    )
    total: int = count_result.scalar_one()

    result = await db.execute(
        select(JournalEntry)
        .where(JournalEntry.user_id == user.id)
        .order_by(JournalEntry.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.scalars().all()

    return JournalListResponse(
        items=[JournalEntryResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(rows)) < total,
    )


# ── Get single ─────────────────────────────────────────────────────────────────

async def get_entry(
    db: AsyncSession, user: User, entry_id: str
) -> JournalEntryResponse:
    result = await db.execute(
        select(JournalEntry).where(JournalEntry.id == uuid.UUID(entry_id))
    )
    entry: JournalEntry | None = result.scalar_one_or_none()

    if entry is None:
        raise NotFoundError("Journal entry not found")
    if str(entry.user_id) != str(user.id):
        raise AuthorizationError("This entry does not belong to you")

    return JournalEntryResponse.model_validate(entry)


# ── Update ─────────────────────────────────────────────────────────────────────

async def update_entry(
    db: AsyncSession, user: User, entry_id: str, data: JournalEntryUpdate
) -> JournalEntryResponse:
    """
    Edit content and/or title of a journal entry.

    If content changed, regenerates the AI reflection synchronously so the
    updated entry always returns a reflection consistent with the new text.
    """
    result = await db.execute(
        select(JournalEntry).where(JournalEntry.id == uuid.UUID(entry_id))
    )
    entry: JournalEntry | None = result.scalar_one_or_none()

    if entry is None:
        raise NotFoundError("Journal entry not found")
    if str(entry.user_id) != str(user.id):
        raise AuthorizationError("This entry does not belong to you")

    update_fields = data.model_dump(exclude_unset=True)
    content_changed = "content" in update_fields

    # If content changed and title was not explicitly sent, re-derive title
    if content_changed and "title" not in update_fields:
        update_fields["title"] = _derive_title(update_fields["content"])

    # Clear stale reflection before saving so it's never inconsistent
    if content_changed:
        update_fields["ai_reflection"] = None

    for field, value in update_fields.items():
        setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)

    if content_changed:
        # Regenera embedding com o novo conteúdo
        embed_text = f"{entry.title}\n{entry.content}" if entry.title else entry.content
        await embed_and_store(db, entry.id, "journal_entries", embed_text)

        await _run_reflection(db, user, entry)

    return JournalEntryResponse.model_validate(entry)


# ── Delete ─────────────────────────────────────────────────────────────────────

async def delete_entry(
    db: AsyncSession, user: User, entry_id: str
) -> None:
    result = await db.execute(
        select(JournalEntry).where(JournalEntry.id == uuid.UUID(entry_id))
    )
    entry: JournalEntry | None = result.scalar_one_or_none()

    if entry is None:
        raise NotFoundError("Journal entry not found")
    if str(entry.user_id) != str(user.id):
        raise AuthorizationError("This entry does not belong to you")

    await db.delete(entry)
    await db.commit()
    logger.info("Journal entry deleted: user=%s entry=%s", user.id, entry_id)


# ── AI reflection — idempotent regeneration ───────────────────────────────────

async def generate_reflection(
    db: AsyncSession, user: User, entry_id: str
) -> JournalEntryResponse:
    """
    (Re)generate the AI reflection for an existing journal entry and persist it.

    Idempotent — calling again overwrites the previous reflection.
    Raises NotFoundError if the entry does not exist or belongs to another user.
    """
    result = await db.execute(
        select(JournalEntry).where(JournalEntry.id == uuid.UUID(entry_id))
    )
    entry: JournalEntry | None = result.scalar_one_or_none()

    if entry is None:
        raise NotFoundError("Journal entry not found")
    if str(entry.user_id) != str(user.id):
        raise AuthorizationError("This entry does not belong to you")

    await _run_reflection(db, user, entry)
    return JournalEntryResponse.model_validate(entry)
