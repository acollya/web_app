"""
Media endpoints.

POST /media/transcribe — transcreve um arquivo de áudio via OpenAI Whisper-1
                         e retorna o texto em português.

Design
------
- Autenticado: requer Bearer token.
- Rate limit: 20 transcrições por hora por usuário (evita abuso de API).
- Formatos aceitos: m4a, mp3, wav, webm, ogg (suportados pelo Whisper).
- Tamanho máximo: 25 MB (limite do Whisper API).
- O arquivo é lido em memória — não persiste em disco.
- Após transcrever, extrai fatos de persona e gera embedding do texto em
  background via extract_and_upsert_facts (source="transcription").
  Isso alimenta o sistema de hiperpersonalização sem bloquear a resposta.
"""
import io
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_redis
from app.core.exceptions import RateLimitError
from app.core.rate_limiter import RateLimiter
from app.config import settings
from app.models.user import User
from app.services.persona_service import extract_and_upsert_facts
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Constants ─────────────────────────────────────────────────────────────────

_ALLOWED_MIME_TYPES = {
    "audio/m4a",
    "audio/x-m4a",
    "audio/mpeg",       # mp3
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "application/octet-stream",  # fallback para uploads mobile sem MIME correto
}

_ALLOWED_EXTENSIONS = {".m4a", ".mp3", ".wav", ".webm", ".ogg"}

# Limite do Whisper API: 25 MB
_MAX_FILE_SIZE = 25 * 1024 * 1024

# Rate limit: 20 transcrições por hora
_RATE_LIMIT = 20
_RATE_WINDOW = 3600  # 1 hora


# ── Schema ─────────────────────────────────────────────────────────────────────

class TranscriptionResponse(BaseModel):
    text: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _file_extension(filename: str | None) -> str:
    if not filename:
        return ""
    parts = filename.rsplit(".", 1)
    return f".{parts[-1].lower()}" if len(parts) == 2 else ""


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcreve um arquivo de áudio para texto (Whisper-1, PT-BR)",
    responses={
        400: {"description": "Formato de arquivo inválido ou tamanho excedido"},
        429: {"description": "Rate limit excedido (20 transcrições/hora)"},
    },
)
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    file: UploadFile = File(..., description="Arquivo de áudio (m4a, mp3, wav, webm, ogg)"),
) -> TranscriptionResponse:
    """
    Transcreve um arquivo de áudio para texto usando OpenAI Whisper-1.

    O idioma é fixado em português (pt) para melhor precisão.
    O arquivo é processado em memória — não é armazenado no servidor.
    """
    # ── Rate limit ────────────────────────────────────────────────────────────
    limiter = RateLimiter(redis)
    try:
        await limiter.check_and_increment(
            user_id=str(current_user.id),
            action="transcribe",
            limit=_RATE_LIMIT,
            window_seconds=_RATE_WINDOW,
        )
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite de {_RATE_LIMIT} transcrições por hora atingido.",
            headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else {},
        )

    # ── Validação de extensão ─────────────────────────────────────────────────
    ext = _file_extension(file.filename)
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato não suportado: '{ext or 'desconhecido'}'. "
                   f"Use: {', '.join(sorted(_ALLOWED_EXTENSIONS))}.",
        )

    # ── Leitura e validação de tamanho ────────────────────────────────────────
    audio_bytes = await file.read()
    if len(audio_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arquivo excede o limite de {_MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo de áudio vazio.",
        )

    # ── Transcrição via Whisper ───────────────────────────────────────────────
    try:
        client = AsyncOpenAI(api_key=settings.openai_config["api_key"])
        audio_file = (file.filename or f"audio{ext}", io.BytesIO(audio_bytes), "audio/mpeg")

        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="pt",
            response_format="text",
        )

        # response_format="text" retorna str diretamente
        transcribed_text: str = response.strip() if isinstance(response, str) else str(response).strip()

        logger.info(
            "Audio transcribed: user=%s size=%d chars=%d",
            current_user.id,
            len(audio_bytes),
            len(transcribed_text),
        )

        # Extrai fatos de persona e gera embedding do texto transcrito em
        # background — alimenta hiperpersonalização e RAG sem bloquear resposta.
        if transcribed_text:
            background_tasks.add_task(
                extract_and_upsert_facts,
                db=db,
                user=current_user,
                text_input=transcribed_text,
                source="transcription",
            )

        return TranscriptionResponse(text=transcribed_text)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Transcription failed: user=%s error=%s",
            current_user.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao transcrever o áudio. Tente novamente.",
        )
