"""
Chat endpoints.

POST   /chat/sessions                        — create session
GET    /chat/sessions                        — list sessions (paginated)
GET    /chat/sessions/{session_id}           — get session detail
DELETE /chat/sessions/{session_id}           — delete session + messages

POST   /chat/sessions/{session_id}/messages  — send message (streaming SSE)
GET    /chat/sessions/{session_id}/messages  — message history (paginated)

Todos os endpoints exigem autenticação; limites de uso por plano são aplicados pelo rate limiter (10/20/ilimitado msgs/dia).

Streaming endpoint
------------------
The POST /messages endpoint returns a Server-Sent Events stream by default.
Each event is a JSON object:

    data: {"event": "delta", "text": "..."}\n\n
    data: {"event": "done",  "tokens_used": 123, "crisis_level": "none"}\n\n

Rate limiting
-------------
The endpoint enforces a sliding-window limit via Redis before calling the
chat service. Limit values come from settings:
    free_chat_messages_per_day   (default: 20)
    premium_chat_messages_per_day (default: 9999)

A RateLimitError raised by the limiter is caught and returned as HTTP 429
with a Retry-After header when available.
"""
import io
import logging
import uuid
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_consented_user, get_db, get_redis
from app.core.exceptions import RateLimitError
from app.core.rate_limiter import RateLimiter
from app.models.user import User
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatSendResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.services import chat_service, storage_service


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000, description="Message text")

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _message_limit(user: User) -> int:
    """Return the daily message limit for the user's plan."""
    if user.plan_code == 2:
        return settings.premium_chat_messages_per_day  # completo = ilimitado
    if user.plan_code == 1:
        return settings.essencial_chat_messages_per_day  # essencial = 20/dia
    return settings.free_chat_messages_per_day  # free = 10/dia


# ── Sessions ───────────────────────────────────────────────────────────────────

@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    body: ChatSessionCreate,
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionResponse:
    return await chat_service.create_session(db, current_user, body)


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="List chat sessions (paginated, newest first)",
)
async def list_sessions(
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ChatSessionListResponse:
    return await chat_service.list_sessions(db, current_user, page, page_size)


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="Get a chat session",
)
async def get_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionResponse:
    return await chat_service.get_session(db, current_user, session_id)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session and all its messages",
)
async def delete_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await chat_service.delete_session(db, current_user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Messages ───────────────────────────────────────────────────────────────────

@router.get(
    "/sessions/{session_id}/messages",
    response_model=ChatHistoryResponse,
    summary="Get message history for a session (paginated)",
)
async def list_messages(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> ChatHistoryResponse:
    return await chat_service.list_messages(db, current_user, session_id, page, page_size)


@router.post(
    "/sessions/{session_id}/messages",
    summary="Send a message and receive a streaming AI response (SSE)",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Server-Sent Events stream",
            "content": {"text/event-stream": {}},
        },
        429: {"description": "Rate limit exceeded"},
    },
)
async def send_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> StreamingResponse:
    """
    Send a user message and stream the assistant reply as SSE.

    Message text is sent in the JSON body (not query string) to prevent
    sensitive clinical content from appearing in server access logs.

    Rate limit: enforced per user per day via Redis sorted set.
    Crisis detection: runs before the LLM call; CVV block appended for HIGH/CRITICAL.
    """
    limiter = RateLimiter(redis)
    limit = _message_limit(current_user)
    try:
        await limiter.check_and_increment(
            user_id=str(current_user.id),
            action="chat",
            limit=limit,
            window_seconds=86400,
        )
    except RateLimitError as exc:
        headers = {}
        if exc.retry_after is not None:
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Limite de mensagens diário atingido. Tente novamente amanhã."},
            headers=headers,
        )

    return StreamingResponse(
        chat_service.stream_message(db, current_user, session_id, body.content, background_tasks),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/sessions/{session_id}/audio-message",
    summary="Envia mensagem de ÁUDIO e recebe resposta da IA em streaming (SSE)",
    response_class=StreamingResponse,
    responses={
        200: {"description": "Server-Sent Events stream", "content": {"text/event-stream": {}}},
        422: {"description": "Áudio inválido ou sem fala detectada"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def send_audio_message(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    file: UploadFile = File(..., description="Áudio (.m4a/.mp3/.wav/.webm/.ogg, máx 25MB)"),
    duration_seconds: Optional[int] = Form(None, ge=0, le=600),
) -> StreamingResponse:
    """
    Chat F2 — áudio como mensagem:
      1. Valida e sobe o áudio para o S3 (chat-audio/{user}/{uuid}.ext)
      2. Transcreve com Whisper — a transcrição vira o `content` da mensagem
      3. Entra no MESMO pipeline do texto (crisis detection, RAG, SSE) —
         invariantes intocadas

    Rate limits: contador diário de chat (por plano) + 20 transcrições/hora
    (compartilhado com /media/transcribe).
    """
    from openai import AsyncOpenAI

    from app.api.v1.endpoints.media import (
        _ALLOWED_EXTENSIONS,
        _ALLOWED_MIME_TYPES,
        _MAX_FILE_SIZE,
        _RATE_LIMIT,
        _RATE_WINDOW,
        _file_extension,
    )

    limiter = RateLimiter(redis)

    # Rate limit diário do chat (mesmo contador das mensagens de texto)
    limit = _message_limit(current_user)
    try:
        await limiter.check_and_increment(
            user_id=str(current_user.id), action="chat", limit=limit, window_seconds=86400,
        )
    except RateLimitError as exc:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else {}
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Limite de mensagens diário atingido. Tente novamente amanhã."},
            headers=headers,
        )

    # Rate limit de transcrição (compartilhado com /media/transcribe)
    try:
        await limiter.check_and_increment(
            user_id=str(current_user.id), action="transcribe",
            limit=_RATE_LIMIT, window_seconds=_RATE_WINDOW,
        )
    except RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de áudios por hora atingido. Envie por texto ou tente mais tarde.",
        )

    # ── Validação do arquivo ─────────────────────────────────────────────────
    ext = _file_extension(file.filename)
    if ext not in _ALLOWED_EXTENSIONS or (
        file.content_type and file.content_type not in _ALLOWED_MIME_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Formato de áudio não suportado.",
        )
    audio_bytes = await file.read()
    if len(audio_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Áudio muito grande (máximo 25MB).",
        )
    if len(audio_bytes) < 1024:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Áudio muito curto. Tente gravar novamente.",
        )

    # ── Upload S3 (antes da transcrição — o áudio é parte da mensagem) ───────
    media_key = f"chat-audio/{current_user.id}/{uuid.uuid4()}{ext}"
    try:
        await storage_service.upload_bytes(
            media_key, audio_bytes, file.content_type or "audio/m4a"
        )
    except Exception as exc:
        logger.error("Chat audio upload failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível enviar o áudio. Tente novamente.",
        )

    # ── Transcrição (Whisper) — vira o content da mensagem ───────────────────
    try:
        client = AsyncOpenAI(api_key=settings.openai_config["api_key"])
        audio_file = (file.filename or f"audio{ext}", io.BytesIO(audio_bytes), "audio/mpeg")
        response = await client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, language="pt", response_format="text",
        )
        transcription = response.strip() if isinstance(response, str) else str(response).strip()
    except Exception as exc:
        logger.error("Chat audio transcription failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível processar o áudio. Tente novamente.",
        )

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não detectamos fala no áudio. Tente gravar novamente.",
        )

    # ── Mesmo pipeline SSE do texto (crisis → RAG → LLM) ─────────────────────
    return StreamingResponse(
        chat_service.stream_message(
            db, current_user, session_id, transcription, background_tasks,
            media_key=media_key, media_type="audio", duration_seconds=duration_seconds,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Chat F3/F4 — anexos (imagem/documento) ────────────────────────────────────

_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
_DOCUMENT_MIMES = {
    "application/pdf",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB
_MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post(
    "/sessions/{session_id}/media-message",
    summary="Envia anexo (imagem ou documento) com legenda opcional (SSE)",
    response_class=StreamingResponse,
    responses={
        200: {"description": "Server-Sent Events stream", "content": {"text/event-stream": {}}},
        422: {"description": "Arquivo inválido"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def send_media_message(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_consented_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None, max_length=4000),
) -> StreamingResponse:
    """
    Chat F3/F4 — anexo como registro da conversa:
      - O binário vai para o S3; o LLM NUNCA vê a imagem/documento (LGPD +
        crisis detection opera só sobre texto) — a IA responde à LEGENDA
      - content da mensagem = legenda (ou placeholder), então o pipeline
        (crisis, RAG, SSE) segue intocado
    """
    limiter = RateLimiter(redis)
    limit = _message_limit(current_user)
    try:
        await limiter.check_and_increment(
            user_id=str(current_user.id), action="chat", limit=limit, window_seconds=86400,
        )
    except RateLimitError as exc:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else {}
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Limite de mensagens diário atingido. Tente novamente amanhã."},
            headers=headers,
        )

    mime = file.content_type or ""
    if mime in _IMAGE_MIMES:
        kind, max_size, prefix = "image", _MAX_IMAGE_SIZE, "chat-media"
    elif mime in _DOCUMENT_MIMES:
        kind, max_size, prefix = "document", _MAX_DOCUMENT_SIZE, "chat-media"
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tipo de arquivo não suportado. Envie imagens (JPEG/PNG/WebP/HEIC) ou documentos (PDF/TXT/DOC).",
        )

    data = await file.read()
    if len(data) > max_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Arquivo muito grande (máximo {max_size // (1024*1024)}MB).",
        )
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Arquivo vazio.",
        )

    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin"
    media_key = f"{prefix}/{current_user.id}/{uuid.uuid4()}.{ext}"
    try:
        await storage_service.upload_bytes(media_key, data, mime)
    except Exception as exc:
        logger.error("Chat media upload failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível enviar o arquivo. Tente novamente.",
        )

    filename = (file.filename or f"arquivo.{ext}")[:200]
    content = (caption or "").strip() or (
        "[Enviei uma imagem]" if kind == "image" else f"[Enviei um documento: {filename}]"
    )

    return StreamingResponse(
        chat_service.stream_message(
            db, current_user, session_id, content, background_tasks,
            media_key=media_key, media_type=kind, media_filename=filename,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
