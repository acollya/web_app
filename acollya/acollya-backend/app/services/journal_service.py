"""
Journal service — all DB operations for /journal endpoints.

create_entry        — insert a new JournalEntry
list_entries        — paginated history, newest first
get_entry           — single entry (with ownership check)
update_entry        — edit content and/or title
delete_entry        — hard delete (GDPR/LGPD erasure applies at user-level)
generate_reflection — call OpenAI to write a CBT-style reflection and persist
                      it in JournalEntry.ai_reflection (Phase 2)

Title auto-derivation:
  If no title is provided on create, we extract the first non-empty line of
  content and truncate it to 80 characters. This keeps list views readable
  without requiring users to fill a separate title field.

AI reflection prompt strategy:
  A concise system instruction asks the model to act as a compassionate CBT
  therapist and produce a short (3–5 sentence) reflection in PT-BR that:
    1. Acknowledges the emotion expressed.
    2. Identifies one cognitive pattern (gently, without labelling).
    3. Offers one concrete reframing question or action.
  The model does NOT see prior conversation history — only the entry content.
"""
import logging
import uuid
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.journal_entry import JournalEntry
from app.models.user import User
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
Você é um terapeuta compassivo especializado em Terapia Cognitivo-Comportamental (TCC).
O usuário compartilhou uma entrada de diário. Escreva uma reflexão curta (3 a 5 frases)
em português do Brasil que:
1. Acolha a emoção expressa de forma empática.
2. Identifique suavemente um padrão cognitivo presente no texto (sem rotular o usuário).
3. Ofereça uma pergunta de reencadramento ou uma ação concreta e gentil.
Seja breve, caloroso e direto. Não use listas, subtítulos nem markdown.
"""


def _derive_title(content: str) -> Optional[str]:
    """Extract the first non-empty line of content as a fallback title."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:_MAX_AUTO_TITLE]
    return None


# ── Create ─────────────────────────────────────────────────────────────────────

async def create_entry(
    db: AsyncSession, user: User, data: JournalEntryCreate
) -> JournalEntryResponse:
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
    result = await db.execute(
        select(JournalEntry).where(JournalEntry.id == uuid.UUID(entry_id))
    )
    entry: JournalEntry | None = result.scalar_one_or_none()

    if entry is None:
        raise NotFoundError("Journal entry not found")
    if str(entry.user_id) != str(user.id):
        raise AuthorizationError("This entry does not belong to you")

    update_fields = data.model_dump(exclude_unset=True)

    # If content changed and title was not explicitly sent, re-derive title
    if "content" in update_fields and "title" not in update_fields:
        update_fields["title"] = _derive_title(update_fields["content"])

    for field, value in update_fields.items():
        setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)
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


# ── AI reflection (Phase 2) ────────────────────────────────────────────────────

async def generate_reflection(
    db: AsyncSession, user: User, entry_id: str
) -> JournalEntryResponse:
    """
    Generate a CBT-style reflection for the journal entry via OpenAI and
    persist it in JournalEntry.ai_reflection.

    Idempotent: calling again overwrites the previous reflection.
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

    client = AsyncOpenAI(api_key=settings.openai_config["api_key"])
    model = settings.openai_config.get("chat_model", "gpt-4o-mini")

    completion = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _REFLECTION_SYSTEM_PROMPT},
            {"role": "user", "content": entry.content},
        ],
        stream=False,
    )

    reflection: str = completion.choices[0].message.content or ""
    entry.ai_reflection = reflection.strip()

    await db.commit()
    await db.refresh(entry)

    logger.info(
        "Journal reflection generated: user=%s entry=%s tokens=%s",
        user.id,
        entry_id,
        completion.usage.total_tokens if completion.usage else None,
    )
    return JournalEntryResponse.model_validate(entry)
