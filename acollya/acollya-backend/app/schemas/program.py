"""
Pydantic v2 schemas for programs endpoints.

ChapterResponse       — single chapter (without heavy content, for list views)
ChapterDetailResponse — single chapter with full content
ProgramResponse       — program card (for list — no chapters)
ProgramDetailResponse — program + chapters + user progress
ChapterProgressItem   — per-chapter completion state
ProgramProgressResponse — user progress summary for one program
UserProgramsSummary   — all programs progress for the /summary endpoint
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field


# ── Chapter ────────────────────────────────────────────────────────────────────

class ChapterResponse(BaseModel):
    id: str
    order: int
    title: str
    content_type: str
    duration_minutes: int
    # Injected from program_progress — not in Chapter model directly
    completed: bool = False
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChapterDetailResponse(ChapterResponse):
    content: str
    video_url: Optional[str] = None


# ── Program ────────────────────────────────────────────────────────────────────

class ProgramResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    duration_days: int
    difficulty: str
    cover_image_key: Optional[str]
    is_premium: bool
    total_chapters: int = 0
    completed_chapters: int = 0

    @computed_field
    @property
    def progress_pct(self) -> int:
        if self.total_chapters == 0:
            return 0
        return round(self.completed_chapters / self.total_chapters * 100)

    model_config = {"from_attributes": True}


class ProgramDetailResponse(ProgramResponse):
    chapters: list[ChapterResponse] = Field(default_factory=list)


# ── Progress ───────────────────────────────────────────────────────────────────

class ChapterProgressUpsert(BaseModel):
    """Body is empty — action is encoded in HTTP method (POST=complete, DELETE=reset)."""
    pass


class ProgramProgressResponse(BaseModel):
    program_id: str
    total_chapters: int
    completed_chapters: int
    progress_pct: int
    started: bool
    completed: bool  # all chapters done


# ── Summary ────────────────────────────────────────────────────────────────────

class ProgramSummaryItem(BaseModel):
    program_id: str
    program_title: str
    total_chapters: int
    completed_chapters: int
    progress_pct: int


class UserProgramsSummary(BaseModel):
    total_programs: int
    started_programs: int
    completed_programs: int
    items: list[ProgramSummaryItem]
