"""
Journal endpoints.

POST   /journal                  — create an entry (requires trial/premium)
GET    /journal                  — paginated list
GET    /journal/{id}             — single entry
PATCH  /journal/{id}             — edit content/title
DELETE /journal/{id}             — delete entry
POST   /journal/{id}/reflect     — generate AI reflection (Phase 2)
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_premium
from app.models.user import User
from app.schemas.journal import (
    JournalEntryCreate,
    JournalEntryResponse,
    JournalEntryUpdate,
    JournalListResponse,
)
from app.services import journal_service
from app.services.persona_service import extract_and_upsert_facts

router = APIRouter()


@router.post(
    "",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new journal entry",
)
async def create_entry(
    body: JournalEntryCreate,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JournalEntryResponse:
    entry = await journal_service.create_entry(db, current_user, body)
    # Extrai fatos da entrada do diário em background
    background_tasks.add_task(
        extract_and_upsert_facts,
        db=db,
        user=current_user,
        text_input=body.content,
        source="journal",
        source_id=uuid.UUID(entry.id) if isinstance(entry.id, str) else entry.id,
    )
    return entry


@router.get(
    "",
    response_model=JournalListResponse,
    summary="List journal entries (paginated, newest first)",
)
async def list_entries(
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> JournalListResponse:
    return await journal_service.list_entries(db, current_user, page, page_size)


@router.get(
    "/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Get a single journal entry",
)
async def get_entry(
    entry_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JournalEntryResponse:
    return await journal_service.get_entry(db, current_user, str(entry_id))


@router.patch(
    "/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Edit a journal entry",
)
async def update_entry(
    entry_id: uuid.UUID,
    body: JournalEntryUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JournalEntryResponse:
    return await journal_service.update_entry(db, current_user, str(entry_id), body)


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a journal entry",
)
async def delete_entry(
    entry_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await journal_service.delete_entry(db, current_user, str(entry_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{entry_id}/reflect",
    response_model=JournalEntryResponse,
    summary="Generate an AI reflection for a journal entry (Phase 2)",
)
async def reflect(
    entry_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JournalEntryResponse:
    """
    Calls OpenAI to produce a short CBT-style reflection and persists it in
    JournalEntry.ai_reflection. Returns the updated entry.
    Idempotent — calling again overwrites the previous reflection.
    """
    return await journal_service.generate_reflection(db, current_user, str(entry_id))
