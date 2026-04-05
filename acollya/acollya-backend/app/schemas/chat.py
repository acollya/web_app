"""
Pydantic v2 schemas for chat endpoints.

ChatSessionCreate      — POST /chat/sessions body
ChatSessionResponse    — single session record
ChatSessionListResponse — paginated session list

ChatMessageCreate      — POST /chat/sessions/{id}/messages body
ChatMessageResponse    — single message record
ChatHistoryResponse    — paginated message history

ChatStreamChunk        — individual SSE data payload during streaming
ChatSendResponse       — non-streaming fallback (used in tests / low-latency paths)

Role values: "user" | "assistant"  (matches DB check constraint)

Crisis detection result is surfaced in ChatSendResponse.crisis_level so the
frontend can show the CVV banner when level is "high" or "critical".
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Session ────────────────────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional session title; auto-derived from first message if omitted",
    )


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ── Messages ───────────────────────────────────────────────────────────────────

class ChatMessageCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=4000,
        description="User message text (PT-BR)",
    )


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: Optional[uuid.UUID]
    role: str                        # "user" | "assistant"
    content: str
    tokens_used: Optional[int]
    cached: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    session_id: uuid.UUID
    items: list[ChatMessageResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ── Streaming (SSE) ────────────────────────────────────────────────────────────

class ChatStreamChunk(BaseModel):
    """
    Payload for each `data:` line in a Server-Sent Events stream.

    event types:
      "delta"    — partial text chunk from the model
      "done"     — stream finished; includes total token count + crisis_level
      "error"    — unrecoverable error; client should stop reading

    On "done" the client assembles the full assistant message from all deltas.
    """
    event: str = Field(description='"delta" | "done" | "error"')
    text: Optional[str] = Field(None, description="Partial text (event=delta)")
    tokens_used: Optional[int] = Field(None, description="Total tokens (event=done)")
    crisis_level: Optional[str] = Field(
        None,
        description="none | medium | high | critical (event=done)",
    )
    error: Optional[str] = Field(None, description="Error message (event=error)")


# ── Non-streaming response (used in tests and /chat/sessions/{id}/messages
#    when Accept: application/json is preferred) ────────────────────────────────

class ChatSendResponse(BaseModel):
    """
    Returned when streaming is not used.
    Wraps both the persisted user message and the assistant reply.
    """
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    crisis_level: str = Field(
        default="none",
        description="Crisis level detected in the user message",
    )
    tokens_used: Optional[int] = None
