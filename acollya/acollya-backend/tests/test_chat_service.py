"""
Tests for app/services/chat_service.py

Strategy: seed ChatSession / ChatMessage rows directly in DB. OpenAI calls
are mocked via unittest.mock.patch so no network requests are made.

Covers:
  create_session  — creates session, default/explicit title
  list_sessions   — empty, own-only, pagination
  get_session     — success, not found, wrong owner
  delete_session  — removes session (cascade removes messages)
  list_messages   — empty, pagination, own-session-only
  send_message    — persists user+assistant rows, auto-title, CVV injection
                    for HIGH/CRITICAL crisis, no CVV for NONE, wrong owner
  stream_message  — yields delta+done SSE events, CVV delta on HIGH crisis,
                    error event on OpenAI exception
"""
import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.schemas.chat import ChatSessionCreate
from app.services import chat_service


# ── OpenAI mock helpers ────────────────────────────────────────────────────────

def _make_completion(text: str = "Resposta da IA.", tokens: int = 42) -> MagicMock:
    """Return a mock non-streaming completion matching openai.ChatCompletion shape."""
    choice = MagicMock()
    choice.message.content = text
    comp = MagicMock()
    comp.choices = [choice]
    comp.usage.total_tokens = tokens
    return comp


def _make_stream_chunks(texts: list[str], total_tokens: int = 50):
    """
    Async generator yielding mock stream chunks.
    Last chunk carries usage; all others carry delta text.
    """
    async def _gen():
        for text in texts:
            chunk = MagicMock()
            chunk.usage = None
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = text
            yield chunk
        # Final chunk with usage, no text
        final = MagicMock()
        final.usage = MagicMock()
        final.usage.total_tokens = total_tokens
        final.choices = []
        yield final
    return _gen()


def _patch_openai_send(text: str = "Resposta da IA.", tokens: int = 42):
    """Context manager that patches AsyncOpenAI for the non-streaming path."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_completion(text, tokens)
    )
    return patch(
        "app.services.chat_service.AsyncOpenAI",
        return_value=mock_client,
    )


def _patch_openai_stream(texts: list[str], total_tokens: int = 50):
    """Context manager that patches AsyncOpenAI for the streaming path."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_stream_chunks(texts, total_tokens)
    )
    return patch(
        "app.services.chat_service.AsyncOpenAI",
        return_value=mock_client,
    )


# ── SSE collection helper ──────────────────────────────────────────────────────

async def _collect_sse(gen) -> list[dict]:
    """Drain a stream_message async generator and parse each SSE payload."""
    events = []
    async for line in gen:
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ── DB helpers ─────────────────────────────────────────────────────────────────

async def _make_session(db, user, *, title: str | None = None) -> ChatSession:
    session = ChatSession(user_id=user.id, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def _make_message(db, user, session_id, *, role: str = "user", content: str = "Oi") -> ChatMessage:
    msg = ChatMessage(
        user_id=user.id,
        session_id=session_id,
        role=role,
        content=content,
        tokens_used=None,
        cached=False,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


# ── create_session ─────────────────────────────────────────────────────────────

async def test_create_session_with_title(db, test_user):
    data = ChatSessionCreate(title="Sessão de ansiedade")
    resp = await chat_service.create_session(db, test_user, data)

    assert resp.title == "Sessão de ansiedade"
    assert resp.id is not None
    assert resp.created_at is not None


async def test_create_session_no_title(db, test_user):
    data = ChatSessionCreate()
    resp = await chat_service.create_session(db, test_user, data)

    assert resp.title is None


# ── list_sessions ──────────────────────────────────────────────────────────────

async def test_list_sessions_empty(db, test_user):
    resp = await chat_service.list_sessions(db, test_user)

    assert resp.total == 0
    assert resp.items == []
    assert resp.has_more is False


async def test_list_sessions_returns_own_only(db, test_user, other_user):
    await _make_session(db, test_user, title="Minha sessão")
    await _make_session(db, other_user, title="Sessão do outro")

    resp = await chat_service.list_sessions(db, test_user)
    assert resp.total == 1
    assert resp.items[0].title == "Minha sessão"


async def test_list_sessions_pagination(db, test_user):
    for i in range(5):
        await _make_session(db, test_user, title=f"Sessão {i}")

    page1 = await chat_service.list_sessions(db, test_user, page=1, page_size=3)
    page2 = await chat_service.list_sessions(db, test_user, page=2, page_size=3)

    assert page1.total == 5
    assert len(page1.items) == 3
    assert page1.has_more is True
    assert len(page2.items) == 2
    assert page2.has_more is False


# ── get_session ────────────────────────────────────────────────────────────────

async def test_get_session_success(db, test_user):
    created = await _make_session(db, test_user, title="Minha sessão")
    resp = await chat_service.get_session(db, test_user, created.id)

    assert resp.id == created.id
    assert resp.title == "Minha sessão"


async def test_get_session_not_found(db, test_user):
    with pytest.raises(NotFoundError):
        await chat_service.get_session(db, test_user, uuid.uuid4())


async def test_get_session_wrong_owner(db, test_user, other_user):
    session = await _make_session(db, other_user)

    with pytest.raises(AuthorizationError):
        await chat_service.get_session(db, test_user, session.id)


# ── delete_session ─────────────────────────────────────────────────────────────

async def test_delete_session_removes_session(db, test_user):
    session = await _make_session(db, test_user)
    await chat_service.delete_session(db, test_user, session.id)

    with pytest.raises(NotFoundError):
        await chat_service.get_session(db, test_user, session.id)


async def test_delete_session_wrong_owner(db, test_user, other_user):
    session = await _make_session(db, other_user)

    with pytest.raises(AuthorizationError):
        await chat_service.delete_session(db, test_user, session.id)


# ── list_messages ──────────────────────────────────────────────────────────────

async def test_list_messages_empty(db, test_user):
    session = await _make_session(db, test_user)
    resp = await chat_service.list_messages(db, test_user, session.id)

    assert resp.total == 0
    assert resp.items == []


async def test_list_messages_pagination(db, test_user):
    session = await _make_session(db, test_user)
    for i in range(5):
        await _make_message(db, test_user, session.id, content=f"msg {i}")

    page1 = await chat_service.list_messages(db, test_user, session.id, page=1, page_size=3)
    page2 = await chat_service.list_messages(db, test_user, session.id, page=2, page_size=3)

    assert page1.total == 5
    assert len(page1.items) == 3
    assert page1.has_more is True
    assert len(page2.items) == 2
    assert page2.has_more is False


async def test_list_messages_wrong_owner(db, test_user, other_user):
    session = await _make_session(db, other_user)

    with pytest.raises(AuthorizationError):
        await chat_service.list_messages(db, test_user, session.id)


# ── send_message ───────────────────────────────────────────────────────────────

async def test_send_message_persists_both_messages(db, test_user):
    session = await _make_session(db, test_user)

    with _patch_openai_send("Tudo bem! Como posso ajudar?"):
        resp = await chat_service.send_message(
            db, test_user, session.id, "Olá, preciso de ajuda."
        )

    assert resp.user_message.role == "user"
    assert resp.user_message.content == "Olá, preciso de ajuda."
    assert resp.assistant_message.role == "assistant"
    assert resp.assistant_message.content == "Tudo bem! Como posso ajudar?"
    assert resp.tokens_used == 42


async def test_send_message_auto_sets_title(db, test_user):
    session = await _make_session(db, test_user, title=None)
    assert session.title is None

    with _patch_openai_send():
        await chat_service.send_message(
            db, test_user, session.id, "Primeira mensagem aqui."
        )

    await db.refresh(session)
    assert session.title == "Primeira mensagem aqui."


async def test_send_message_does_not_overwrite_existing_title(db, test_user):
    session = await _make_session(db, test_user, title="Título original")

    with _patch_openai_send():
        await chat_service.send_message(
            db, test_user, session.id, "Segunda mensagem."
        )

    await db.refresh(session)
    assert session.title == "Título original"


async def test_send_message_crisis_none_no_cvv(db, test_user):
    session = await _make_session(db, test_user)

    with _patch_openai_send("Resposta normal sem crise."):
        resp = await chat_service.send_message(
            db, test_user, session.id, "Hoje foi um dia tranquilo."
        )

    assert resp.crisis_level == "none"
    assert "CVV" not in resp.assistant_message.content
    assert "188" not in resp.assistant_message.content


async def test_send_message_crisis_high_appends_cvv(db, test_user):
    """A HIGH-level crisis phrase must trigger CVV block in the response."""
    session = await _make_session(db, test_user)
    high_crisis_text = "penso em me matar todos os dias"

    with _patch_openai_send("Eu ouço você."):
        resp = await chat_service.send_message(
            db, test_user, session.id, high_crisis_text
        )

    assert resp.crisis_level in ("high", "critical")
    assert "188" in resp.assistant_message.content


async def test_send_message_crisis_critical_appends_cvv(db, test_user):
    """A CRITICAL-level crisis phrase must also trigger CVV block."""
    session = await _make_session(db, test_user)
    critical_text = "vou me matar hoje"

    with _patch_openai_send("Estou aqui com você."):
        resp = await chat_service.send_message(
            db, test_user, session.id, critical_text
        )

    assert resp.crisis_level == "critical"
    assert "188" in resp.assistant_message.content


async def test_send_message_session_not_found(db, test_user):
    with _patch_openai_send():
        with pytest.raises(NotFoundError):
            await chat_service.send_message(
                db, test_user, uuid.uuid4(), "Mensagem qualquer."
            )


async def test_send_message_wrong_owner(db, test_user, other_user):
    session = await _make_session(db, other_user)

    with _patch_openai_send():
        with pytest.raises(AuthorizationError):
            await chat_service.send_message(
                db, test_user, session.id, "Tentativa de acesso."
            )


# ── stream_message ─────────────────────────────────────────────────────────────

async def test_stream_message_yields_delta_and_done(db, test_user):
    """stream_message must yield delta chunks and a final done event."""
    session = await _make_session(db, test_user)

    with _patch_openai_stream(["Olá, ", "como ", "posso ajudar?"], total_tokens=30):
        events = await _collect_sse(
            chat_service.stream_message(db, test_user, session.id, "Oi!")
        )

    delta_events = [e for e in events if e["event"] == "delta"]
    done_events = [e for e in events if e["event"] == "done"]

    assert len(delta_events) == 3
    assert "".join(e["text"] for e in delta_events) == "Olá, como posso ajudar?"
    assert len(done_events) == 1
    assert done_events[0]["tokens_used"] == 30
    assert done_events[0]["crisis_level"] == "none"


async def test_stream_message_persists_messages(db, test_user):
    """After streaming, both messages must be saved in the DB."""
    session = await _make_session(db, test_user)

    with _patch_openai_stream(["Resposta completa."]):
        async for _ in chat_service.stream_message(
            db, test_user, session.id, "Mensagem do usuário."
        ):
            pass

    history = await chat_service.list_messages(db, test_user, session.id)
    assert history.total == 2
    roles = {m.role for m in history.items}
    assert roles == {"user", "assistant"}


async def test_stream_message_crisis_high_emits_cvv_delta(db, test_user):
    """HIGH crisis must emit an extra delta with CVV text before done."""
    session = await _make_session(db, test_user)
    high_text = "penso em me matar todo dia"

    with _patch_openai_stream(["Estou aqui."]):
        events = await _collect_sse(
            chat_service.stream_message(db, test_user, session.id, high_text)
        )

    done = next(e for e in events if e["event"] == "done")
    assert done["crisis_level"] in ("high", "critical")

    all_text = "".join(e.get("text", "") for e in events if e["event"] == "delta")
    assert "188" in all_text


async def test_stream_message_openai_error_yields_error_event(db, test_user):
    """If OpenAI raises, stream_message must yield an error event and stop."""
    session = await _make_session(db, test_user)

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("OpenAI timeout")
    )

    with patch("app.services.chat_service.AsyncOpenAI", return_value=mock_client):
        events = await _collect_sse(
            chat_service.stream_message(db, test_user, session.id, "Olá.")
        )

    assert len(events) == 1
    assert events[0]["event"] == "error"
    assert "OpenAI timeout" in events[0]["error"]


async def test_stream_message_session_not_found(db, test_user):
    """Non-existent session_id must raise NotFoundError before streaming."""
    with _patch_openai_stream(["texto"]):
        with pytest.raises(NotFoundError):
            async for _ in chat_service.stream_message(
                db, test_user, uuid.uuid4(), "Olá."
            ):
                pass
