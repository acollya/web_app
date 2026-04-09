"""
RAG service — memória semântica do usuário.

Responsabilidades
-----------------
embed_and_store()    — gera e persiste o embedding de um registro novo/atualizado.
retrieve_context()   — recupera registros semanticamente similares ao texto atual
                       e os formata como bloco de contexto para injeção no prompt.

Fluxo típico
------------
1. Usuário envia mensagem / salva diário / faz check-in.
2. O service cria o registro no banco e, via BackgroundTask, chama:
       embed_and_store(db, record_id, "chat_messages", text)
3. Na próxima interação, antes da chamada de IA, o service chama:
       context = await retrieve_context(db, user, query_text)
   e injeta `context` no system prompt.

Embedding
---------
Usa OpenAI text-embedding-3-small (1536 dims) — mesmo modelo do persona_service,
garantindo espaço vetorial comum entre tabelas.

Design de resiliência
---------------------
Ambas as funções silenciam exceções internamente. Um erro de RAG nunca deve
bloquear a resposta principal ao usuário.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Constantes ─────────────────────────────────────────────────────────────────

# Máximo de resultados trazidos por tabela (antes do merge final)
_TOP_K_PER_TABLE = 2

# Máximo de fragmentos de contexto injetados no prompt
_TOP_K_FINAL = 5

# Limite de distância cosseno (0 = idêntico, 2 = oposto).
# distance < 0.45  →  similarity > 0.55  →  relevância razoável.
_MAX_DISTANCE = 0.45

_EMBEDDING_DIM = 1536

TableName = Literal["chat_messages", "journal_entries", "mood_checkins"]


# ── Cliente OpenAI ──────────────────────────────────────────────────────────────

def _openai() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_config["api_key"])


def _embedding_model() -> str:
    return settings.openai_config.get("embedding_model", "text-embedding-3-small")


# ── Geração de embedding ────────────────────────────────────────────────────────

async def _generate_embedding(text_input: str) -> list[float] | None:
    """Gera embedding via OpenAI. Retorna None em caso de erro."""
    if not text_input or not text_input.strip():
        return None
    try:
        resp = await _openai().embeddings.create(
            model=_embedding_model(),
            input=text_input[:8000],   # limite seguro de tokens
            dimensions=_EMBEDDING_DIM,
        )
        return resp.data[0].embedding
    except Exception as exc:
        logger.warning("RAG embedding generation failed: %s", exc)
        return None


def _vec_literal(embedding: list[float]) -> str:
    """Serializa embedding para o formato literal aceito pelo pgvector."""
    return f"[{','.join(str(x) for x in embedding)}]"


# ── Tempo relativo ──────────────────────────────────────────────────────────────

def _relative_time(dt: datetime) -> str:
    """Retorna descrição relativa em português (ex: 'ontem', '3 dias atrás')."""
    now = datetime.now(timezone.utc)
    aware = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    days = (now - aware).days
    if days == 0:
        return "hoje"
    if days == 1:
        return "ontem"
    if days < 7:
        return f"{days} dias atrás"
    weeks = days // 7
    if weeks == 1:
        return "1 semana atrás"
    if weeks < 5:
        return f"{weeks} semanas atrás"
    months = days // 30
    if months == 1:
        return "1 mês atrás"
    return f"{months} meses atrás"


# ── API Pública ─────────────────────────────────────────────────────────────────

async def embed_and_store(
    db: AsyncSession,
    record_id: uuid.UUID,
    table: TableName,
    text_to_embed: str,
) -> None:
    """
    Gera o embedding de `text_to_embed` e persiste na coluna `embedding` da
    linha identificada por `record_id` em `table`.

    Projetado para ser chamado via FastAPI BackgroundTasks — silencia exceções.

    Parâmetros
    ----------
    db            : sessão async
    record_id     : UUID da linha a atualizar
    table         : nome da tabela (chat_messages | journal_entries | mood_checkins)
    text_to_embed : texto cujo embedding será gerado e armazenado
    """
    try:
        embedding = await _generate_embedding(text_to_embed)
        if embedding is None:
            return

        await db.execute(
            text(
                f"UPDATE {table} "           # tabela validada pelo tipo Literal
                "SET embedding = CAST(:vec AS vector) "
                "WHERE id = :id"
            ),
            {"vec": _vec_literal(embedding), "id": str(record_id)},
        )
        await db.commit()
        logger.debug("RAG embedding stored: table=%s id=%s", table, record_id)

    except Exception as exc:
        logger.warning("embed_and_store failed silently: table=%s id=%s %s", table, record_id, exc)


async def retrieve_context(
    db: AsyncSession,
    user: User,
    query_text: str,
    top_k: int = _TOP_K_FINAL,
) -> str:
    """
    Recupera registros semanticamente similares a `query_text` nas três tabelas
    do usuário e os formata como bloco de texto para injeção no system prompt.

    Retorna string vazia se não houver resultados relevantes ou em caso de erro.

    Formato do retorno (exemplo):
        Histórico relevante do usuário:
        [Diário - 2 dias atrás] "Sinto que estou carregando muita coisa sozinho..."
        [Chat - ontem] "Tenho dormido mal por causa da ansiedade no trabalho."
        [Humor - hoje] ansioso (intensidade 4) — "Reunião pesada com o chefe"
    """
    try:
        query_embedding = await _generate_embedding(query_text)
        if query_embedding is None:
            return ""

        vec = _vec_literal(query_embedding)
        user_id = str(user.id)
        fragments: list[tuple[float, str]] = []   # (distance, formatted_line)

        # ── chat_messages: apenas mensagens do usuário ─────────────────────────
        rows = await db.execute(
            text(
                """
                SELECT content, created_at,
                       embedding <=> CAST(:vec AS vector) AS distance
                FROM chat_messages
                WHERE user_id = :uid
                  AND role = 'user'
                  AND embedding IS NOT NULL
                  AND embedding <=> CAST(:vec AS vector) < :max_dist
                ORDER BY distance
                LIMIT :k
                """
            ),
            {"vec": vec, "uid": user_id, "max_dist": _MAX_DISTANCE, "k": _TOP_K_PER_TABLE},
        )
        for row in rows.fetchall():
            snippet = row.content[:200].replace("\n", " ")
            line = f'[Chat - {_relative_time(row.created_at)}] "{snippet}"'
            fragments.append((row.distance, line))

        # ── journal_entries ────────────────────────────────────────────────────
        rows = await db.execute(
            text(
                """
                SELECT title, content, created_at,
                       embedding <=> CAST(:vec AS vector) AS distance
                FROM journal_entries
                WHERE user_id = :uid
                  AND embedding IS NOT NULL
                  AND embedding <=> CAST(:vec AS vector) < :max_dist
                ORDER BY distance
                LIMIT :k
                """
            ),
            {"vec": vec, "uid": user_id, "max_dist": _MAX_DISTANCE, "k": _TOP_K_PER_TABLE},
        )
        for row in rows.fetchall():
            snippet = row.content[:200].replace("\n", " ")
            label = row.title or "Diário"
            line = f'[{label} - {_relative_time(row.created_at)}] "{snippet}"'
            fragments.append((row.distance, line))

        # ── mood_checkins ──────────────────────────────────────────────────────
        rows = await db.execute(
            text(
                """
                SELECT mood, intensity, note, created_at,
                       embedding <=> CAST(:vec AS vector) AS distance
                FROM mood_checkins
                WHERE user_id = :uid
                  AND embedding IS NOT NULL
                  AND embedding <=> CAST(:vec AS vector) < :max_dist
                ORDER BY distance
                LIMIT :k
                """
            ),
            {"vec": vec, "uid": user_id, "max_dist": _MAX_DISTANCE, "k": _TOP_K_PER_TABLE},
        )
        for row in rows.fetchall():
            mood_str = f"{row.mood} (intensidade {row.intensity})"
            if row.note:
                mood_str += f' — "{row.note[:120]}"'
            line = f"[Humor - {_relative_time(row.created_at)}] {mood_str}"
            fragments.append((row.distance, line))

        if not fragments:
            return ""

        # Ordena por distância (mais similar primeiro) e limita ao top_k global
        fragments.sort(key=lambda t: t[0])
        top_lines = [line for _, line in fragments[:top_k]]

        return "Histórico relevante do usuário (use como contexto adicional):\n" + "\n".join(top_lines)

    except Exception as exc:
        logger.warning("retrieve_context failed silently: user=%s %s", user.id, exc)
        return ""
