"""
Persona endpoints — perfil de hiperpersonalização do usuário.

GET  /persona         — retorna todos os fatos da persona + preview do contexto
POST /persona/extract — extrai fatos manualmente a partir de um texto (debug/seed)
DELETE /persona       — apaga todos os fatos e invalida o cache Redis

Estes endpoints são úteis para:
  - Debug em desenvolvimento (verificar o que a IA sabe sobre o usuário)
  - Seed inicial de personas para novos usuários
  - Painel de transparência (LGPD: usuário vê e pode apagar seus dados de persona)
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_redis
from app.core.exceptions import RateLimitError
from app.core.rate_limiter import RateLimiter
from app.models.user import User
from app.models.user_persona_fact import PersonaCategory, UserPersonaFact
from app.schemas.persona import (
    PersonaExtractRequest,
    PersonaFactResponse,
    PersonaProfileResponse,
)
from app.services.persona_service import (
    extract_and_upsert_facts,
    get_persona_context,
    invalidate_persona_cache,
)

router = APIRouter()


# ── GET /persona ───────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PersonaProfileResponse,
    summary="Get the user's persona profile",
    description=(
        "Returns all persona facts grouped by category, plus a preview of the "
        "context block injected into AI prompts. Useful for debugging and for "
        "LGPD transparency (users can see what the AI knows about them)."
    ),
)
async def get_persona(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PersonaProfileResponse:
    # Busca todos os fatos do usuário ordenados por confiança decrescente
    result = await db.execute(
        select(UserPersonaFact)
        .where(UserPersonaFact.user_id == current_user.id)
        .order_by(
            UserPersonaFact.confidence.desc(),
            UserPersonaFact.updated_at.desc(),
        )
    )
    facts: list[UserPersonaFact] = list(result.scalars().all())

    # Agrupa por categoria
    facts_by_category: dict[str, list[PersonaFactResponse]] = {}
    for cat in PersonaCategory:
        cat_facts = [f for f in facts if f.category == cat]
        if cat_facts:
            facts_by_category[cat.value] = [
                PersonaFactResponse.model_validate(f) for f in cat_facts
            ]

    # Gera o preview do contexto (usa cache se disponível)
    context_preview = await get_persona_context(db, current_user)

    return PersonaProfileResponse(
        total_facts=len(facts),
        facts_by_category=facts_by_category,
        context_preview=context_preview,
    )


# ── POST /persona/extract ──────────────────────────────────────────────────────

@router.post(
    "/extract",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually extract persona facts from a text (debug / seed)",
    description=(
        "Sends `text` through the persona extraction pipeline synchronously. "
        "Extracted facts are persisted with deduplication. "
        "Returns 202 Accepted — the number of facts may not be known immediately "
        "since deduplication can merge entries."
    ),
    response_model=dict,
)
async def extract_facts(
    body: PersonaExtractRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict:
    # 10 manual extractions per hour — this endpoint calls OpenAI GPT-4 per request
    try:
        await RateLimiter(redis).check_and_increment(
            user_id=str(current_user.id),
            action="persona_extract",
            limit=10,
            window_seconds=3600,
        )
    except RateLimitError as exc:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else {}
        return JSONResponse(
            status_code=429,
            content={"detail": "Limite de extrações atingido. Tente novamente mais tarde."},
            headers=headers,
        )

    await extract_and_upsert_facts(
        db=db,
        user=current_user,
        text_input=body.text,
        source=body.source,
        source_id=None,
    )
    return {"status": "accepted", "message": "Extração de fatos iniciada com sucesso."}


# ── DELETE /persona ────────────────────────────────────────────────────────────

@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete all persona facts (LGPD erasure / reset)",
    description=(
        "Hard-deletes all persona facts for the current user and clears the "
        "Redis cache. The AI will stop using personalization for this user until "
        "new interactions rebuild the profile."
    ),
)
async def delete_persona(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await db.execute(
        delete(UserPersonaFact).where(UserPersonaFact.user_id == current_user.id)
    )
    await db.commit()
    await invalidate_persona_cache(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
