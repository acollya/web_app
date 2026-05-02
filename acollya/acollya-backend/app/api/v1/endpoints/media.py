"""
Media endpoints.

POST /media/transcribe — transcreve um arquivo de áudio via OpenAI Whisper-1
                         e retorna o texto em português.

POST /media/tts        — converte texto em fala via OpenAI TTS-1 e retorna
                         URL pré-assinada S3 (TTL 60 s) com o arquivo mp3.

Design
------
- Autenticado: requer Bearer token.
- Rate limit: 20 requisições por hora por usuário em ambos os endpoints.
- Transcribe: formatos aceitos m4a, mp3, wav, webm, ogg; máximo 25 MB.
- TTS: texto de até 1500 caracteres; vozes OpenAI (nova padrão para PT-BR).
- O áudio TTS é gerado em memória, enviado ao S3 e exposto via URL
  pré-assinada de 60 segundos — não persiste objeto público.
"""
import io
import logging
import uuid
from typing import Annotated

import boto3
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, field_validator
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

# Rate limit compartilhado: 20 requisições por hora (transcribe e tts)
_RATE_LIMIT = 20
_RATE_WINDOW = 3600  # 1 hora

# URL pré-assinada S3: TTL 60 segundos
_TTS_PRESIGNED_TTL = 60


# ── Schemas ────────────────────────────────────────────────────────────────────

class TranscriptionResponse(BaseModel):
    text: str


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1500)
    voice: str = Field(default="nova")

    @field_validator("voice")
    @classmethod
    def validate_voice(cls, v: str) -> str:
        allowed = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
        if v not in allowed:
            raise ValueError(f"voice deve ser um de: {', '.join(sorted(allowed))}")
        return v


class TTSResponse(BaseModel):
    audio_url: str
    expires_in: int = _TTS_PRESIGNED_TTL


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


# ── TTS Endpoint ──────────────────────────────────────────────────────────────

@router.post(
    "/tts",
    response_model=TTSResponse,
    status_code=status.HTTP_200_OK,
    summary="Converte texto em fala (OpenAI TTS-1) e retorna URL pré-assinada S3",
    responses={
        422: {"description": "Texto inválido ou voz não permitida"},
        429: {"description": "Rate limit excedido (20 requisições/hora)"},
        502: {"description": "Falha na geração de áudio ou upload S3"},
    },
)
async def text_to_speech(
    body: TTSRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TTSResponse:
    """
    Gera um arquivo mp3 a partir do texto informado usando OpenAI TTS-1.

    O áudio é enviado ao S3 e retornado como URL pré-assinada com TTL de 60
    segundos. A URL expira após esse período — o cliente deve reproduzir o
    áudio imediatamente.

    Vozes disponíveis: alloy, echo, fable, nova (padrão), onyx, shimmer.
    """
    # ── Rate limit ────────────────────────────────────────────────────────────
    limiter = RateLimiter(redis)
    try:
        await limiter.check_and_increment(
            user_id=str(current_user.id),
            action="tts",
            limit=_RATE_LIMIT,
            window_seconds=_RATE_WINDOW,
        )
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite de {_RATE_LIMIT} requisições TTS por hora atingido.",
            headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else {},
        )

    # ── Geração de áudio via OpenAI TTS-1 ────────────────────────────────────
    try:
        cfg = settings.openai_config
        client = AsyncOpenAI(api_key=cfg["api_key"])
        tts_response = await client.audio.speech.create(
            model="tts-1",
            voice=body.voice,
            input=body.text,
            response_format="mp3",
        )
        audio_bytes: bytes = tts_response.content

        logger.info(
            "TTS generated: user=%s voice=%s chars=%d bytes=%d",
            current_user.id,
            body.voice,
            len(body.text),
            len(audio_bytes),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "TTS generation failed: user=%s error=%s",
            current_user.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao gerar o áudio. Tente novamente.",
        )

    # ── Upload S3 e URL pré-assinada ──────────────────────────────────────────
    try:
        s3 = boto3.client("s3", region_name=settings.aws_region)
        key = f"tts/{current_user.id}/{uuid.uuid4()}.mp3"
        s3.put_object(
            Bucket=settings.media_bucket,
            Key=key,
            Body=audio_bytes,
            ContentType="audio/mpeg",
        )
        audio_url: str = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.media_bucket, "Key": key},
            ExpiresIn=_TTS_PRESIGNED_TTL,
        )
    except Exception as exc:
        logger.error(
            "TTS S3 upload failed: user=%s key=%s error=%s",
            current_user.id,
            key if "key" in dir() else "unknown",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao armazenar o áudio gerado. Tente novamente.",
        )

    return TTSResponse(audio_url=audio_url, expires_in=_TTS_PRESIGNED_TTL)
