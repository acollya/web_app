"""
Programs endpoints.

GET  /programs                                        — catalog list + user progress
GET  /programs/summary                                — user's overall progress
GET  /programs/{program_id}                           — program detail + chapters
GET  /programs/{program_id}/chapters/{chapter_id}     — chapter content
POST /programs/{program_id}/chapters/{chapter_id}/complete   — mark complete
DELETE /programs/{program_id}/chapters/{chapter_id}/complete — reset

Note: /programs/summary must be registered BEFORE /programs/{program_id}
to avoid FastAPI matching "summary" as a program_id path parameter.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_premium
from app.models.user import User
from app.schemas.program import (
    ChapterDetailResponse,
    ProgramDetailResponse,
    ProgramProgressResponse,
    ProgramResponse,
    UserProgramsSummary,
)
from app.services import program_service

router = APIRouter()


@router.get(
    "",
    response_model=list[ProgramResponse],
    summary="List all programs with user progress",
)
async def list_programs(
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProgramResponse]:
    return await program_service.list_programs(db, current_user)


@router.get(
    "/summary",
    response_model=UserProgramsSummary,
    summary="User's overall progress across all programs",
)
async def get_user_summary(
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProgramsSummary:
    return await program_service.get_user_summary(db, current_user)


@router.get(
    "/{program_id}",
    response_model=ProgramDetailResponse,
    summary="Get program detail with chapters and user progress",
)
async def get_program(
    program_id: str,
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgramDetailResponse:
    return await program_service.get_program(db, current_user, program_id)


@router.get(
    "/{program_id}/chapters/{chapter_id}",
    response_model=ChapterDetailResponse,
    summary="Get chapter content",
)
async def get_chapter(
    program_id: str,
    chapter_id: str,
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChapterDetailResponse:
    return await program_service.get_chapter(db, current_user, program_id, chapter_id)


@router.post(
    "/{program_id}/chapters/{chapter_id}/complete",
    response_model=ProgramProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a chapter as completed",
)
async def complete_chapter(
    program_id: str,
    chapter_id: str,
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgramProgressResponse:
    return await program_service.complete_chapter(db, current_user, program_id, chapter_id)


@router.delete(
    "/{program_id}/chapters/{chapter_id}/complete",
    response_model=ProgramProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset a chapter completion",
)
async def reset_chapter(
    program_id: str,
    chapter_id: str,
    current_user: Annotated[User, Depends(require_premium)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgramProgressResponse:
    return await program_service.reset_chapter(db, current_user, program_id, chapter_id)
