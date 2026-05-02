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

Hybrid Search (BM25 + vetorial com RRF)
----------------------------------------
Para tabelas com tsvector (chat_messages, journal_entries), combina dois rankings:
  - Vetorial: distância cosseno do embedding (semântica)
  - BM25: ts_rank_cd com plainto_to_tsquery (lexical, keywords exatas)
O Reciprocal Rank Fusion (RRF, k=60) normaliza os dois rankings em um score único.

Time Decay
----------
O score final é multiplicado por exp(-days_old / 60) para priorizar conteúdo
recente. Dados com 60 dias têm peso 0.37×, dados com 180 dias têm peso 0.05×.

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
import math
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

# Limites de distância cosseno por tabela (0 = idêntico, 2 = oposto).
# Mood check-ins são curtos e muito específicos → threshold mais restrito.
# Diários são longos e ricos → threshold mais permissivo.
# Chat está no meio-termo.
_MAX_DISTANCE_CHAT     = 0.32   # similarity > 0.68 — mensagens de chat
_MAX_DISTANCE_JOURNAL  = 0.36   # similarity > 0.64 — entradas de diário
_MAX_DISTANCE_MOOD     = 0.28   # similarity > 0.72 — check-ins de humor
_MAX_DISTANCE_CLINICAL = 0.40   # similarity > 0.60 — base de conhecimento clínico
                                # (mais permissivo: cobertura clínica é ampla
                                #  e o conteúdo não é específico do usuário)
_MAX_DISTANCE_CHAPTERS = 0.38   # similarity > 0.62 — capítulos de programas
                                # (entre chat e journal: conteúdo estruturado,
                                #  mais longo que mood mas mais focado que clínico)

# Score multiplier aplicado aos resultados da base clínica para que ela seja
# tratada como contexto SUPLEMENTAR, sem competir em igualdade com o histórico
# pessoal do usuário (que tem maior valor terapêutico).
_CLINICAL_SCORE_WEIGHT = 0.85

# Score multiplier para capítulos de programas — ligeiramente abaixo da base
# clínica pois os capítulos são mais longos e mais genéricos; o histórico
# pessoal do usuário tem maior relevância terapêutica imediata.
_CHAPTERS_SCORE_WEIGHT = 0.80

_EMBEDDING_DIM = 1536

# RRF constant — k=60 é o valor padrão da literatura; reduz o impacto de outliers
_RRF_K = 60

# Meia-vida do time decay em dias. score *= exp(-days_old / _DECAY_HALFLIFE)
# Com 60 dias → peso 0.37×; com 180 dias → peso 0.05×
_DECAY_HALFLIFE = 60

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


# ── Time decay ─────────────────────────────────────────────────────────────────

def _time_decay_factor(dt: datetime) -> float:
    """Retorna fator de decaimento exponencial baseado na idade do registro."""
    now = datetime.now(timezone.utc)
    aware = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    days_old = max(0, (now - aware).days)
    return math.exp(-days_old / _DECAY_HALFLIFE)


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

        # fragments: (rrf_score, formatted_line) — score MAIOR = mais relevante
        fragments: list[tuple[float, str]] = []

        # ── chat_messages: usuário + assistente com RRF + time decay ─────────────
        # Mensagens do assistente são incluídas com threshold mais restrito
        # (-0.05) e penalidade de 0.05 no ranking vetorial — fornece contexto
        # bidirecional mas sem competir em igualdade com mensagens do usuário.
        rows = await db.execute(
            text(
                """
                WITH vec_ranked AS (
                    SELECT id, role, content, created_at,
                           row_number() OVER (
                               ORDER BY (embedding <=> CAST(:vec AS vector))
                                        + CASE WHEN role = 'assistant' THEN 0.05 ELSE 0 END
                           ) AS vec_rank
                    FROM chat_messages
                    WHERE user_id = :uid
                      AND embedding IS NOT NULL
                      AND (
                          (role = 'user'      AND embedding <=> CAST(:vec AS vector) < :max_dist)
                          OR
                          (role = 'assistant' AND embedding <=> CAST(:vec AS vector) < :max_dist_asst)
                      )
                    LIMIT :k_inner
                ),
                bm25_ranked AS (
                    SELECT id, role, content, created_at,
                           row_number() OVER (ORDER BY ts_rank_cd(ts_content, plainto_tsquery('portuguese', :query)) DESC) AS bm25_rank
                    FROM chat_messages
                    WHERE user_id = :uid
                      AND ts_content @@ plainto_tsquery('portuguese', :query)
                    LIMIT :k_inner
                )
                SELECT COALESCE(v.id, b.id) AS id,
                       COALESCE(v.role, b.role) AS role,
                       COALESCE(v.content, b.content) AS content,
                       COALESCE(v.created_at, b.created_at) AS created_at,
                       COALESCE(1.0 / (:rrf_k + v.vec_rank), 0) +
                       COALESCE(1.0 / (:rrf_k + b.bm25_rank), 0) AS rrf_score
                FROM vec_ranked v
                FULL OUTER JOIN bm25_ranked b ON v.id = b.id
                ORDER BY rrf_score DESC
                LIMIT :k
                """
            ),
            {
                "vec": vec, "uid": user_id, "query": query_text[:500],
                "max_dist": _MAX_DISTANCE_CHAT,
                "max_dist_asst": _MAX_DISTANCE_CHAT - 0.05,
                "rrf_k": _RRF_K,
                "k_inner": _TOP_K_PER_TABLE * 3, "k": _TOP_K_PER_TABLE,
            },
        )
        for row in rows.fetchall():
            snippet = row.content[:200].replace("\n", " ")
            role_label = "Acollya" if row.role == "assistant" else "Chat"
            line = f'[{role_label} - {_relative_time(row.created_at)}] "{snippet}"'
            score = row.rrf_score * _time_decay_factor(row.created_at)
            fragments.append((score, line))

        # ── journal_entries: hybrid BM25 + vetorial com RRF + time decay ───────
        rows = await db.execute(
            text(
                """
                WITH vec_ranked AS (
                    SELECT id, title, content, created_at,
                           row_number() OVER (ORDER BY embedding <=> CAST(:vec AS vector)) AS vec_rank
                    FROM journal_entries
                    WHERE user_id = :uid
                      AND embedding IS NOT NULL
                      AND embedding <=> CAST(:vec AS vector) < :max_dist
                    LIMIT :k_inner
                ),
                bm25_ranked AS (
                    SELECT id, title, content, created_at,
                           row_number() OVER (ORDER BY ts_rank_cd(ts_content, plainto_tsquery('portuguese', :query)) DESC) AS bm25_rank
                    FROM journal_entries
                    WHERE user_id = :uid
                      AND ts_content @@ plainto_tsquery('portuguese', :query)
                    LIMIT :k_inner
                )
                SELECT COALESCE(v.id, b.id) AS id,
                       COALESCE(v.title, b.title) AS title,
                       COALESCE(v.content, b.content) AS content,
                       COALESCE(v.created_at, b.created_at) AS created_at,
                       COALESCE(1.0 / (:rrf_k + v.vec_rank), 0) +
                       COALESCE(1.0 / (:rrf_k + b.bm25_rank), 0) AS rrf_score
                FROM vec_ranked v
                FULL OUTER JOIN bm25_ranked b ON v.id = b.id
                ORDER BY rrf_score DESC
                LIMIT :k
                """
            ),
            {
                "vec": vec, "uid": user_id, "query": query_text[:500],
                "max_dist": _MAX_DISTANCE_JOURNAL, "rrf_k": _RRF_K,
                "k_inner": _TOP_K_PER_TABLE * 3, "k": _TOP_K_PER_TABLE,
            },
        )
        for row in rows.fetchall():
            snippet = row.content[:200].replace("\n", " ")
            label = row.title or "Diário"
            line = f'[{label} - {_relative_time(row.created_at)}] "{snippet}"'
            score = row.rrf_score * _time_decay_factor(row.created_at)
            fragments.append((score, line))

        # ── mood_checkins: apenas vetorial + time decay (sem texto rico) ────────
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
            {"vec": vec, "uid": user_id, "max_dist": _MAX_DISTANCE_MOOD, "k": _TOP_K_PER_TABLE},
        )
        for row in rows.fetchall():
            mood_str = f"{row.mood} (intensidade {row.intensity})"
            if row.note:
                mood_str += f' — "{row.note[:120]}"'
            line = f"[Humor - {_relative_time(row.created_at)}] {mood_str}"
            # mood usa score vetorial invertido (distância → similaridade) com decay
            vec_score = (1.0 / (_RRF_K + 1)) * (1 - row.distance)
            score = vec_score * _time_decay_factor(row.created_at)
            fragments.append((score, line))

        # ── chapters: hybrid BM25 + vetorial com RRF (sem time decay) ────────────
        # Capítulos de programas terapêuticos — catálogo GLOBAL (sem user_id).
        # Apenas capítulos de texto (content_type='text') têm embedding útil.
        # Score final multiplicado por _CHAPTERS_SCORE_WEIGHT para tratar como
        # contexto suplementar ao histórico pessoal do usuário.
        rows = await db.execute(
            text(
                """
                WITH vec_ranked AS (
                    SELECT c.id, c.title AS chapter_title, c.content,
                           p.title AS program_title,
                           row_number() OVER (ORDER BY c.embedding <=> CAST(:vec AS vector)) AS vec_rank
                    FROM chapters c
                    JOIN programs p ON c.program_id = p.id
                    WHERE c.embedding IS NOT NULL
                      AND c.content_type = 'text'
                      AND c.embedding <=> CAST(:vec AS vector) < :max_dist
                    LIMIT :k_inner
                ),
                bm25_ranked AS (
                    SELECT c.id, c.title AS chapter_title, c.content,
                           p.title AS program_title,
                           row_number() OVER (ORDER BY ts_rank_cd(c.ts_content, plainto_tsquery('portuguese', :query)) DESC) AS bm25_rank
                    FROM chapters c
                    JOIN programs p ON c.program_id = p.id
                    WHERE c.ts_content @@ plainto_tsquery('portuguese', :query)
                      AND c.content_type = 'text'
                    LIMIT :k_inner
                )
                SELECT COALESCE(v.id, b.id) AS id,
                       COALESCE(v.chapter_title, b.chapter_title) AS chapter_title,
                       COALESCE(v.content, b.content) AS content,
                       COALESCE(v.program_title, b.program_title) AS program_title,
                       COALESCE(1.0 / (:rrf_k + v.vec_rank), 0) +
                       COALESCE(1.0 / (:rrf_k + b.bm25_rank), 0) AS rrf_score
                FROM vec_ranked v
                FULL OUTER JOIN bm25_ranked b ON v.id = b.id
                ORDER BY rrf_score DESC
                LIMIT :k
                """
            ),
            {
                "vec": vec, "query": query_text[:500],
                "max_dist": _MAX_DISTANCE_CHAPTERS, "rrf_k": _RRF_K,
                "k_inner": _TOP_K_PER_TABLE * 3, "k": _TOP_K_PER_TABLE,
            },
        )
        for row in rows.fetchall():
            snippet = row.content[:200].replace("\n", " ")
            line = f'[Programa: {row.program_title} — {row.chapter_title}] "{snippet}"'
            score = row.rrf_score * _CHAPTERS_SCORE_WEIGHT
            fragments.append((score, line))

        # ── clinical_knowledge: hybrid BM25 + vetorial com RRF (sem time decay) ─
        # Conteúdo TCC/TRS estático e GLOBAL (não depende de user_id).
        # Score final é multiplicado por _CLINICAL_SCORE_WEIGHT para tratar a
        # base como contexto suplementar ao histórico pessoal do usuário.
        rows = await db.execute(
            text(
                """
                WITH vec_ranked AS (
                    SELECT id, category, title, chunk_text,
                           row_number() OVER (ORDER BY embedding <=> CAST(:vec AS vector)) AS vec_rank
                    FROM clinical_knowledge
                    WHERE embedding IS NOT NULL
                      AND embedding <=> CAST(:vec AS vector) < :max_dist
                    LIMIT :k_inner
                ),
                bm25_ranked AS (
                    SELECT id, category, title, chunk_text,
                           row_number() OVER (ORDER BY ts_rank_cd(ts_content, plainto_tsquery('portuguese', :query)) DESC) AS bm25_rank
                    FROM clinical_knowledge
                    WHERE ts_content @@ plainto_tsquery('portuguese', :query)
                    LIMIT :k_inner
                )
                SELECT COALESCE(v.id, b.id) AS id,
                       COALESCE(v.category, b.category) AS category,
                       COALESCE(v.title, b.title) AS title,
                       COALESCE(v.chunk_text, b.chunk_text) AS chunk_text,
                       COALESCE(1.0 / (:rrf_k + v.vec_rank), 0) +
                       COALESCE(1.0 / (:rrf_k + b.bm25_rank), 0) AS rrf_score
                FROM vec_ranked v
                FULL OUTER JOIN bm25_ranked b ON v.id = b.id
                ORDER BY rrf_score DESC
                LIMIT :k
                """
            ),
            {
                "vec": vec, "query": query_text[:500],
                "max_dist": _MAX_DISTANCE_CLINICAL, "rrf_k": _RRF_K,
                "k_inner": _TOP_K_PER_TABLE * 3, "k": _TOP_K_PER_TABLE,
            },
        )
        for row in rows.fetchall():
            snippet = row.chunk_text[:240].replace("\n", " ")
            line = f'[Conhecimento clínico - {row.category}] "{snippet}"'
            score = row.rrf_score * _CLINICAL_SCORE_WEIGHT
            fragments.append((score, line))

        if not fragments:
            return ""

        # Ordena por score RRF + decay (maior primeiro) e limita ao top_k global
        fragments.sort(key=lambda t: t[0], reverse=True)
        top_lines = [line for _, line in fragments[:top_k]]

        return "Histórico relevante do usuário (use como contexto adicional):\n" + "\n".join(top_lines)

    except Exception as exc:
        logger.warning("retrieve_context failed silently: user=%s %s", user.id, exc)
        return ""
