"""
Tests for app/services/journal_service.py

Covers:
  create_entry — auto-title derivation, explicit title
  list_entries — empty, pagination, only own entries
  get_entry    — own entry, other user's entry (403), not found (404)
  update_entry — content change re-derives title, explicit title preserved,
                 other user blocked (403)
  delete_entry — success, other user blocked (403)
"""
import pytest

from app.core.exceptions import AuthorizationError, NotFoundError
from app.schemas.journal import JournalEntryCreate, JournalEntryUpdate
from app.services import journal_service


# ── Create ─────────────────────────────────────────────────────────────────────

async def test_create_auto_title(db, test_user):
    data = JournalEntryCreate(content="Hoje foi um dia incrível\n\nMuita coisa aconteceu.")
    resp = await journal_service.create_entry(db, test_user, data)

    assert resp.title == "Hoje foi um dia incrível"
    assert resp.content == data.content
    assert resp.id is not None


async def test_create_auto_title_truncated(db, test_user):
    long_first_line = "A" * 100
    data = JournalEntryCreate(content=long_first_line)
    resp = await journal_service.create_entry(db, test_user, data)

    assert resp.title is not None
    assert len(resp.title) <= 80


async def test_create_explicit_title(db, test_user):
    data = JournalEntryCreate(content="Conteúdo qualquer.", title="Meu título especial")
    resp = await journal_service.create_entry(db, test_user, data)

    assert resp.title == "Meu título especial"


async def test_create_no_title_blank_first_line(db, test_user):
    """Content starting with blank lines should still find a title."""
    data = JournalEntryCreate(content="\n\nPrimeira linha com conteúdo.")
    resp = await journal_service.create_entry(db, test_user, data)

    assert resp.title == "Primeira linha com conteúdo."


# ── List ───────────────────────────────────────────────────────────────────────

async def test_list_entries_empty(db, test_user):
    resp = await journal_service.list_entries(db, test_user)

    assert resp.total == 0
    assert resp.items == []
    assert resp.has_more is False


async def test_list_entries_pagination(db, test_user):
    for i in range(5):
        await journal_service.create_entry(
            db, test_user, JournalEntryCreate(content=f"Entrada {i}")
        )

    page1 = await journal_service.list_entries(db, test_user, page=1, page_size=3)
    page2 = await journal_service.list_entries(db, test_user, page=2, page_size=3)

    assert page1.total == 5
    assert len(page1.items) == 3
    assert page1.has_more is True
    assert len(page2.items) == 2
    assert page2.has_more is False


async def test_list_entries_only_own(db, test_user, other_user):
    await journal_service.create_entry(db, test_user, JournalEntryCreate(content="Minha entrada"))
    await journal_service.create_entry(db, other_user, JournalEntryCreate(content="Entrada do outro"))

    resp = await journal_service.list_entries(db, test_user)
    assert resp.total == 1
    assert "Minha" in resp.items[0].content


# ── Get ────────────────────────────────────────────────────────────────────────

async def test_get_entry_success(db, test_user):
    created = await journal_service.create_entry(
        db, test_user, JournalEntryCreate(content="Conteúdo do diário.")
    )
    fetched = await journal_service.get_entry(db, test_user, str(created.id))

    assert fetched.id == created.id
    assert fetched.content == "Conteúdo do diário."


async def test_get_entry_not_found(db, test_user):
    with pytest.raises(NotFoundError):
        await journal_service.get_entry(db, test_user, "00000000-0000-0000-0000-000000000000")


async def test_get_entry_wrong_owner(db, test_user, other_user):
    created = await journal_service.create_entry(
        db, other_user, JournalEntryCreate(content="Entrada privada do outro.")
    )
    with pytest.raises(AuthorizationError):
        await journal_service.get_entry(db, test_user, str(created.id))


# ── Update ─────────────────────────────────────────────────────────────────────

async def test_update_content_rederives_title(db, test_user):
    created = await journal_service.create_entry(
        db, test_user, JournalEntryCreate(content="Título original")
    )
    updated = await journal_service.update_entry(
        db, test_user, str(created.id),
        JournalEntryUpdate(content="Novo conteúdo aqui\nSegunda linha"),
    )

    assert updated.content == "Novo conteúdo aqui\nSegunda linha"
    assert updated.title == "Novo conteúdo aqui"


async def test_update_explicit_title_preserved(db, test_user):
    created = await journal_service.create_entry(
        db, test_user, JournalEntryCreate(content="Texto qualquer")
    )
    updated = await journal_service.update_entry(
        db, test_user, str(created.id),
        JournalEntryUpdate(content="Conteúdo novo", title="Título fixo"),
    )

    assert updated.title == "Título fixo"


async def test_update_wrong_owner(db, test_user, other_user):
    created = await journal_service.create_entry(
        db, other_user, JournalEntryCreate(content="Entrada do outro")
    )
    with pytest.raises(AuthorizationError):
        await journal_service.update_entry(
            db, test_user, str(created.id),
            JournalEntryUpdate(content="Tentativa de edição"),
        )


# ── Delete ─────────────────────────────────────────────────────────────────────

async def test_delete_entry_success(db, test_user):
    created = await journal_service.create_entry(
        db, test_user, JournalEntryCreate(content="Para deletar")
    )
    await journal_service.delete_entry(db, test_user, str(created.id))

    with pytest.raises(NotFoundError):
        await journal_service.get_entry(db, test_user, str(created.id))


async def test_delete_entry_wrong_owner(db, test_user, other_user):
    created = await journal_service.create_entry(
        db, other_user, JournalEntryCreate(content="Não pode deletar")
    )
    with pytest.raises(AuthorizationError):
        await journal_service.delete_entry(db, test_user, str(created.id))


# ── generate_reflection (Phase 2) ─────────────────────────────────────────────

def _patch_openai_reflection(text: str = "Reflexão gerada pela IA."):
    from unittest.mock import AsyncMock, MagicMock, patch
    choice = MagicMock()
    choice.message.content = text
    completion = MagicMock()
    completion.choices = [choice]
    completion.usage.total_tokens = 20
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=completion)
    return patch("app.services.journal_service.AsyncOpenAI", return_value=mock_client)


async def test_generate_reflection_persists_ai_reflection(db, test_user):
    created = await journal_service.create_entry(
        db, test_user, JournalEntryCreate(content="Hoje me senti muito ansioso no trabalho.")
    )
    assert created.ai_reflection is None

    with _patch_openai_reflection("É natural sentir ansiedade em momentos de pressão."):
        updated = await journal_service.generate_reflection(db, test_user, str(created.id))

    assert updated.id == created.id
    assert updated.ai_reflection == "É natural sentir ansiedade em momentos de pressão."


async def test_generate_reflection_idempotent(db, test_user):
    """Calling generate_reflection twice overwrites the previous value."""
    created = await journal_service.create_entry(
        db, test_user, JournalEntryCreate(content="Reflexão sobre o dia.")
    )

    with _patch_openai_reflection("Primeira reflexão."):
        await journal_service.generate_reflection(db, test_user, str(created.id))

    with _patch_openai_reflection("Segunda reflexão, mais precisa."):
        updated = await journal_service.generate_reflection(db, test_user, str(created.id))

    assert updated.ai_reflection == "Segunda reflexão, mais precisa."


async def test_generate_reflection_not_found(db, test_user):
    with _patch_openai_reflection():
        with pytest.raises(NotFoundError):
            await journal_service.generate_reflection(
                db, test_user, "00000000-0000-0000-0000-000000000000"
            )


async def test_generate_reflection_wrong_owner(db, test_user, other_user):
    created = await journal_service.create_entry(
        db, other_user, JournalEntryCreate(content="Entrada privada.")
    )

    with _patch_openai_reflection():
        with pytest.raises(AuthorizationError):
            await journal_service.generate_reflection(db, test_user, str(created.id))
