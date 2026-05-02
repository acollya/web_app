"""
Chat endpoints.

POST   /chat/sessions                        — create session
GET    /chat/sessions                        — list sessions (paginated)
GET    /chat/sessions/{session_id}           — get session detail
DELETE /chat/sessions/{session_id}           — delete session + messages

POST   /chat/sessions/{session_id}/messages  — send message (streaming SSE)
GET    /chat/sessions/{session_id}/messages  — message history (paginated)

All endpoints require an active trial or subscription (require_premium).

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
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_db, get_redis, require_premium
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
from app.services import chat_service


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000, description="Message text")

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _message_limit(user: User) -> int:
    """Return the daily message limit for the user's plan."""
    return (
        settings.premium_chat_messages_per_day
        if user.is_premium
        else settings.free_chat_messages_per_day
    )


# ── Sessions ───────────────────────────────────────────────────────────────────

@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    body: ChatSessionCreate,
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionResponse:
    return await chat_service.create_session(db, current_user, body)


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="List chat sessions (paginated, newest first)",
)
async def list_sessions(
    current_user: Annotated[User, Depends(require_premium)],
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
    current_user: Annotated[User, Depends(require_premium)],
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
    current_user: Annotated[User, Depends(require_premium)],
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
    current_user: Annotated[User, Depends(require_premium)],
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
    current_user: Annotated[User, Depends(require_premium)],
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
            content={"detail": "Rate limit exceeded. Try again later."},
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
