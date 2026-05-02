"""
Pydantic v2 schemas for journal endpoints.

JournalEntryCreate  — POST /journal
JournalEntryUpdate  — PATCH /journal/{id}  (all fields optional)
JournalEntryResponse — single entry
JournalListResponse  — paginated list

ai_reflection is always read-only from the client's perspective.
It is populated asynchronously by the AI Lambda (Phase 2).

Title behaviour:
  - Optional on create; if omitted, the API auto-derives it from the first
    non-empty line of content (truncated to 80 chars).
  - Can be explicitly set or cleared via PATCH.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Requests ───────────────────────────────────────────────────────────────────

class JournalEntryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)
    title: Optional[str] = Field(None, max_length=200, strip_whitespace=True)


class JournalEntryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=50_000)
    title: Optional[str] = Field(None, max_length=200, strip_whitespace=True)


# ── Responses ──────────────────────────────────────────────────────────────────

class JournalEntryResponse(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    content: str
    ai_reflection: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JournalListResponse(BaseModel):
    items: list[JournalEntryResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class JournalPromptSuggestionsResponse(BaseModel):
    prompts: list[str]
