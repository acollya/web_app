"""
Persona service — extração, armazenamento e recuperação de fatos sobre o usuário.

Visão geral
-----------
Cada interação do usuário (chat, diário, mood check-in) dispara a extração de
fatos em background. Esses fatos são armazenados na tabela `user_persona_facts`
com embeddings vetoriais para deduplicação por similaridade semântica.

O serviço também fornece `get_persona_context()`, que compila os fatos mais
relevantes em um bloco de texto pronto para ser injetado nos prompts da IA,
tornando cada resposta mais personalizada ao perfil do usuário.

Cache
-----
O resumo da persona é cacheado no Redis por 24h (chave `persona:{user_id}`).
O cache é invalidado toda vez que novos fatos são inseridos ou atualizados.

Deduplicação
------------
Antes de inserir um novo fato, o serviço busca fatos existentes da mesma
categoria com embedding similar (cosine similarity > DEDUP_THRESHOLD = 0.92).
Se encontrar um, o texto e o embedding são atualizados no lugar — evitando
acúmulo de fatos redundantes.

Extração
--------
Um prompt estruturado (JSON mode) pede ao GPT-4o-mini que extraia de 0 a 5 fatos
do texto fornecido. Cada fato possui: categoria, texto, confiança (0.0–1.0).

Public API
----------
extract_and_upsert_facts   — extrai fatos de um texto e persiste com embeddings
get_persona_context        — retorna bloco de texto com a persona para injeção
invalidate_persona_cache   — apaga o cache Redis do usuário
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.user_persona_fact import PersonaCategory, UserPersonaFact

logger = logging.getLogger(__name__)

# ── Constantes ─────────────────────────────────────────────────────────────────

# Cosine similarity acima deste threshold → considera duplicata e atualiza
DEDUP_THRESHOLD = 0.92

# Máximo de fatos retornados por categoria no contexto da persona
MAX_FACTS_PER_CATEGORY = 3

# TTL do cache Redis: 24h em segundos
PERSONA_CACHE_TTL = 60 * 60 * 24

# Dimensão do modelo text-embedding-3-small
EMBEDDING_DIM = 1536

# Rótulos legíveis para o prompt
_CATEGORY_LABELS = {
    PersonaCategory.preferencia:   "Preferência",
    PersonaCategory.aversao:       "Aversão",
    PersonaCategory.rotina:        "Rotina",
    PersonaCategory.gatilho:       "Gatilho emocional",
    PersonaCategory.valor:         "Valor pessoal",
    PersonaCategory.contexto:      "Contexto de vida",
}

# ── Prompt de extração ─────────────────────────────────────────────────────────

_EXTRACTION_SYSTEM_PROMPT = """\
Você é um sistema de extração de fatos sobre o usuário para personalização de saúde mental.

Analise o texto fornecido e extraia até 5 fatos relevantes e duradouros sobre a \
pessoa — preferências, rotinas, gatilhos emocionais, valores ou contexto de vida.

Regras:
- Extraia apenas fatos que realmente aparecem no texto. Se não houver fatos \
  relevantes, retorne uma lista vazia.
- Seja conciso: cada fato deve ter no máximo 1 frase objetiva.
- Não invente fatos nem faça suposições além do que está no texto.
- Evite fatos triviais ou muito temporários (ex: "está com fome hoje").
- Prefira fatos que ajudem a personalizar respostas futuras de saúde mental.

Responda SOMENTE com JSON neste formato (sem texto adicional):
{
  "facts": [
    {
      "category": "<preferencia|aversao|rotina|gatilho|valor|contexto>",
      "fact_text": "<fato em português, 1 frase, máx 120 caracteres>",
      "confidence": <0.0 a 1.0>
    }
  ]
}
"""


# ── Clientes OpenAI ────────────────────────────────────────────────────────────

def _get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_config["api_key"])


def _get_chat_model() -> str:
    return settings.openai_config.get("chat_model", "gpt-4o-mini")


def _get_embedding_model() -> str:
    return settings.openai_config.get("embedding_model", "text-embedding-3-small")


# ── Redis helpers ──────────────────────────────────────────────────────────────

def _persona_cache_key(user_id: uuid.UUID) -> str:
    return f"persona:{user_id}"


async def _get_redis():
    """Retorna cliente Redis assíncrono. Importação lazy para não quebrar se Redis
    não estiver configurado em ambiente de testes."""
    try:
        import redis.asyncio as aioredis
        client = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            ssl=settings.redis_tls,
            decode_responses=True,
        )
        return client
    except Exception:
        return None


async def invalidate_persona_cache(user_id: uuid.UUID) -> None:
    """Apaga o cache Redis da persona do usuário."""
    try:
        redis = await _get_redis()
        if redis:
            await redis.delete(_persona_cache_key(user_id))
            await redis.aclose()
    except Exception as exc:
        logger.warning("Failed to invalidate persona cache user=%s: %s", user_id, exc)


# ── Geração de embeddings ──────────────────────────────────────────────────────

async def _generate_embedding(text_input: str) -> list[float] | None:
    """Gera embedding via OpenAI text-embedding-3-small. Retorna None em erro."""
    try:
        client = _get_openai_client()
        response = await client.embeddings.create(
            model=_get_embedding_model(),
            input=text_input,
            dimensions=EMBEDDING_DIM,
        )
        return response.data[0].embedding
    except Exception as exc:
        logger.warning("Embedding generation failed: %s", exc)
        return None


# ── Extração de fatos ─────────────────────────────────────────────────────────

async def _extract_facts_from_text(
    text_input: str,
) -> list[dict]:
    """
    Chama GPT-4o-mini em JSON mode para extrair fatos do texto.
    Retorna lista de dicts com: category, fact_text, confidence.
    Retorna lista vazia em caso de erro ou texto sem fatos relevantes.
    """
    if not text_input or len(text_input.strip()) < 20:
        return []

    try:
        client = _get_openai_client()
        completion = await client.chat.completions.create(
            model=_get_chat_model(),
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": text_input[:4000]},  # limita tokens
            ],
            response_format={"type": "json_object"},
            temperature=0.2,  # menos criativo, mais factual
            max_tokens=800,
        )
        raw = completion.choices[0].message.content or "{}"
        data = json.loads(raw)
        return data.get("facts", [])
    except Exception as exc:
        logger.warning("Fact extraction failed: %s", exc)
        return []


# ── Deduplicação e upsert ─────────────────────────────────────────────────────

async def _find_similar_fact(
    db: AsyncSession,
    user_id: uuid.UUID,
    category: PersonaCategory,
    embedding: list[float],
) -> UserPersonaFact | None:
    """
    Busca um fato existente do mesmo usuário e categoria com embedding similar
    (cosine similarity > DEDUP_THRESHOLD). Retorna o primeiro match ou None.

    Usa a função de distância cosseno do pgvector (<=>).
    """
    try:
        # pgvector: <=> é distância cosseno (0 = idêntico, 2 = oposto)
        # similarity = 1 - distance → threshold de distância = 1 - DEDUP_THRESHOLD
        distance_threshold = 1 - DEDUP_THRESHOLD

        stmt = text(
            """
            SELECT id
            FROM user_persona_facts
            WHERE user_id = :user_id
              AND category = :category
              AND embedding IS NOT NULL
              AND embedding <=> CAST(:embedding AS vector) < :threshold
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT 1
            """
        )
        result = await db.execute(stmt, {
            "user_id": str(user_id),
            "category": category.value,
            "embedding": f"[{','.join(str(x) for x in embedding)}]",
            "threshold": distance_threshold,
        })
        row = result.fetchone()
        if row is None:
            return None

        fact_result = await db.execute(
            select(UserPersonaFact).where(UserPersonaFact.id == row[0])
        )
        return fact_result.scalar_one_or_none()
    except Exception as exc:
        logger.warning("Similarity search failed: %s", exc)
        return None


async def _upsert_fact(
    db: AsyncSession,
    user_id: uuid.UUID,
    category: PersonaCategory,
    fact_text: str,
    confidence: float,
    source: str,
    source_id: uuid.UUID | None,
    embedding: list[float] | None,
) -> None:
    """
    Insere um novo fato ou atualiza um existente semanticamente similar.
    """
    existing: UserPersonaFact | None = None

    if embedding is not None:
        existing = await _find_similar_fact(db, user_id, category, embedding)

    if existing is not None:
        # Atualiza o fato existente com o texto mais recente
        existing.fact_text = fact_text
        existing.confidence = max(existing.confidence, confidence)  # mantém a maior confiança
        existing.embedding = embedding
        existing.source = source
        existing.source_id = source_id
        existing.updated_at = datetime.utcnow()
        logger.debug("Persona fact updated: user=%s category=%s", user_id, category.value)
    else:
        new_fact = UserPersonaFact(
            user_id=user_id,
            category=category,
            fact_text=fact_text,
            confidence=confidence,
            source=source,
            source_id=source_id,
            embedding=embedding,
        )
        db.add(new_fact)
        logger.debug("Persona fact inserted: user=%s category=%s", user_id, category.value)


# ── API Pública ────────────────────────────────────────────────────────────────

async def extract_and_upsert_facts(
    db: AsyncSession,
    user: User,
    text_input: str,
    source: str,
    source_id: Optional[uuid.UUID] = None,
) -> None:
    """
    Extrai fatos de `text_input`, gera embeddings e persiste em `user_persona_facts`.

    Projetado para ser chamado via FastAPI BackgroundTasks — não levanta exceções
    para não quebrar o fluxo principal. Todos os erros são logados silenciosamente.

    Parâmetros
    ----------
    db          : sessão async do banco
    user        : usuário dono dos fatos
    text_input  : texto livre da interação (mensagem de chat, entrada do diário, nota de humor)
    source      : origem ("chat" | "journal" | "mood_checkin")
    source_id   : UUID do registro de origem (opcional)
    """
    try:
        raw_facts = await _extract_facts_from_text(text_input)
        if not raw_facts:
            return

        inserted = 0
        for raw in raw_facts:
            try:
                category_str = raw.get("category", "")
                try:
                    category = PersonaCategory(category_str)
                except ValueError:
                    logger.debug("Unknown persona category '%s' — skipping", category_str)
                    continue

                fact_text = (raw.get("fact_text") or "").strip()
                if not fact_text:
                    continue

                confidence = float(raw.get("confidence", 0.8))
                confidence = max(0.0, min(1.0, confidence))

                embedding = await _generate_embedding(fact_text)

                await _upsert_fact(
                    db=db,
                    user_id=user.id,
                    category=category,
                    fact_text=fact_text,
                    confidence=confidence,
                    source=source,
                    source_id=source_id,
                    embedding=embedding,
                )
                inserted += 1

            except Exception as fact_exc:
                logger.warning("Failed to process individual fact: %s", fact_exc)
                continue

        if inserted > 0:
            await db.commit()
            await invalidate_persona_cache(user.id)
            logger.info(
                "Persona facts extracted: user=%s source=%s new_facts=%d",
                user.id, source, inserted,
            )

    except Exception as exc:
        logger.error(
            "extract_and_upsert_facts failed silently: user=%s source=%s error=%s",
            user.id, source, exc,
        )


async def get_persona_context(
    db: AsyncSession,
    user: User,
    max_facts: int = MAX_FACTS_PER_CATEGORY,
) -> str:
    """
    Retorna um bloco de texto formatado com os fatos mais relevantes da persona
    do usuário, pronto para ser injetado no system prompt da IA.

    O resultado é cacheado no Redis por 24h. Se não houver fatos cadastrados,
    retorna string vazia (sem impacto nos prompts).

    Formato do retorno:
        Perfil do usuário (personalização):
        - [Preferência] Prefere meditações curtas pela manhã
        - [Rotina] Trabalha em home office com dois filhos pequenos
        - [Gatilho emocional] Sente ansiedade antes de reuniões importantes
    """
    cache_key = _persona_cache_key(user.id)

    # ── Tenta cache Redis ─────────────────────────────────────────────────────
    try:
        redis = await _get_redis()
        if redis:
            cached = await redis.get(cache_key)
            if cached is not None:
                await redis.aclose()
                return cached
            await redis.aclose()
    except Exception as exc:
        logger.warning("Redis read failed for persona cache: %s", exc)

    # ── Consulta banco ────────────────────────────────────────────────────────
    try:
        result = await db.execute(
            select(UserPersonaFact)
            .where(UserPersonaFact.user_id == user.id)
            .order_by(
                UserPersonaFact.confidence.desc(),
                UserPersonaFact.updated_at.desc(),
            )
        )
        all_facts: list[UserPersonaFact] = list(result.scalars().all())

        if not all_facts:
            return ""

        # Agrupa por categoria e limita a max_facts por categoria
        by_category: dict[PersonaCategory, list[UserPersonaFact]] = {}
        for fact in all_facts:
            cat = fact.category
            if cat not in by_category:
                by_category[cat] = []
            if len(by_category[cat]) < max_facts:
                by_category[cat].append(fact)

        # Monta bloco de texto
        lines: list[str] = ["Perfil do usuário (use para personalizar sua resposta):"]
        category_order = [
            PersonaCategory.contexto,
            PersonaCategory.rotina,
            PersonaCategory.preferencia,
            PersonaCategory.aversao,
            PersonaCategory.valor,
            PersonaCategory.gatilho,
        ]
        for cat in category_order:
            for fact in by_category.get(cat, []):
                label = _CATEGORY_LABELS.get(cat, cat.value.capitalize())
                lines.append(f"- [{label}] {fact.fact_text}")

        context = "\n".join(lines) if len(lines) > 1 else ""

    except Exception as exc:
        logger.error("get_persona_context DB query failed: user=%s %s", user.id, exc)
        return ""

    # ── Armazena no Redis ─────────────────────────────────────────────────────
    if context:
        try:
            redis = await _get_redis()
            if redis:
                await redis.set(cache_key, context, ex=PERSONA_CACHE_TTL)
                await redis.aclose()
        except Exception as exc:
            logger.warning("Redis write failed for persona cache: %s", exc)

    return context
