"""
Program service — catalog reads + user progress writes.

list_programs     — all active programs with user's progress overlay
get_program       — single program + chapters + per-chapter completion
get_chapter       — chapter detail (content) with completion state
complete_chapter  — upsert ProgramProgress row (completed=True)
reset_chapter     — mark ProgramProgress row as completed=False
get_user_summary  — cross-program progress summary

Progress model:
  ProgramProgress has (user_id, program_id, chapter_id) unique constraint.
  We use select-then-insert/update pattern (async-safe upsert).
"""
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.program import Chapter, Program
from app.models.program_progress import ProgramProgress
from app.models.user import User
from app.schemas.program import (
    ChapterDetailResponse,
    ChapterResponse,
    ProgramDetailResponse,
    ProgramProgressResponse,
    ProgramResponse,
    ProgramSummaryItem,
    UserProgramsSummary,
)

logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_chapter_response(
    chapter: Chapter,
    progress_map: dict[str, ProgramProgress],
    detail: bool = False,
) -> ChapterResponse | ChapterDetailResponse:
    prog = progress_map.get(chapter.id)
    base: dict = {
        "id": chapter.id,
        "order": chapter.order,
        "title": chapter.title,
        "content_type": chapter.content_type,
        "duration_minutes": chapter.duration_minutes,
        "completed": prog.completed if prog else False,
        "completed_at": prog.completed_at if (prog and prog.completed) else None,
    }
    if detail:
        return ChapterDetailResponse(**base, content=chapter.content, video_url=chapter.video_url)
    return ChapterResponse(**base)


def _calc_progress(total: int, completed: int) -> int:
    return round(completed / total * 100) if total else 0


async def _chapter_count(db: AsyncSession, program_id: str) -> int:
    result = await db.execute(
        select(func.count()).select_from(Chapter).where(Chapter.program_id == program_id)
    )
    return result.scalar_one()


async def _build_progress_response(
    db: AsyncSession, user: User, program_id: str
) -> ProgramProgressResponse:
    total = await _chapter_count(db, program_id)

    prog_r = await db.execute(
        select(ProgramProgress).where(
            ProgramProgress.user_id == user.id,
            ProgramProgress.program_id == program_id,
        )
    )
    all_progress = prog_r.scalars().all()
    completed = sum(1 for p in all_progress if p.completed)

    return ProgramProgressResponse(
        program_id=program_id,
        total_chapters=total,
        completed_chapters=completed,
        progress_pct=_calc_progress(total, completed),
        started=len(all_progress) > 0,
        completed=(completed == total and total > 0),
    )


# ── List programs ─────────────────────────────────────────────────────────────

async def list_programs(db: AsyncSession, user: User) -> list[ProgramResponse]:
    prog_result = await db.execute(
        select(Program).where(Program.is_active == True).order_by(Program.sort_order)  # noqa: E712
    )
    programs = prog_result.scalars().all()

    # All chapter counts in one query
    counts_result = await db.execute(
        select(Chapter.program_id, func.count().label("total")).group_by(Chapter.program_id)
    )
    chapter_counts = {row.program_id: row.total for row in counts_result}

    # All user progress in one query
    user_prog_result = await db.execute(
        select(ProgramProgress).where(ProgramProgress.user_id == user.id)
    )
    by_program: dict[str, list[ProgramProgress]] = {}
    for p in user_prog_result.scalars().all():
        by_program.setdefault(p.program_id, []).append(p)

    output = []
    for program in programs:
        total = chapter_counts.get(program.id, 0)
        completed = sum(1 for p in by_program.get(program.id, []) if p.completed)
        output.append(ProgramResponse(
            id=program.id,
            title=program.title,
            description=program.description,
            category=program.category,
            duration_days=program.duration_days,
            difficulty=program.difficulty,
            cover_image_key=program.cover_image_key,
            is_premium=program.is_premium,
            total_chapters=total,
            completed_chapters=completed,
        ))
    return output


# ── Get program detail ────────────────────────────────────────────────────────

async def get_program(
    db: AsyncSession, user: User, program_id: str
) -> ProgramDetailResponse:
    result = await db.execute(
        select(Program).where(Program.id == program_id, Program.is_active == True)  # noqa: E712
    )
    program = result.scalar_one_or_none()
    if not program:
        raise NotFoundError("Program not found")

    chapters_result = await db.execute(
        select(Chapter).where(Chapter.program_id == program_id).order_by(Chapter.order)
    )
    chapters = chapters_result.scalars().all()

    prog_result = await db.execute(
        select(ProgramProgress).where(
            ProgramProgress.user_id == user.id,
            ProgramProgress.program_id == program_id,
        )
    )
    progress_rows = prog_result.scalars().all()
    progress_map = {p.chapter_id: p for p in progress_rows}
    completed_count = sum(1 for p in progress_rows if p.completed)

    return ProgramDetailResponse(
        id=program.id,
        title=program.title,
        description=program.description,
        category=program.category,
        duration_days=program.duration_days,
        difficulty=program.difficulty,
        cover_image_key=program.cover_image_key,
        is_premium=program.is_premium,
        total_chapters=len(chapters),
        completed_chapters=completed_count,
        chapters=[_build_chapter_response(c, progress_map) for c in chapters],
    )


# ── Get chapter detail ────────────────────────────────────────────────────────

async def get_chapter(
    db: AsyncSession, user: User, program_id: str, chapter_id: str
) -> ChapterDetailResponse:
    prog_result = await db.execute(
        select(Program).where(Program.id == program_id, Program.is_active == True)  # noqa: E712
    )
    if not prog_result.scalar_one_or_none():
        raise NotFoundError("Program not found")

    ch_result = await db.execute(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.program_id == program_id)
    )
    chapter = ch_result.scalar_one_or_none()
    if not chapter:
        raise NotFoundError("Chapter not found")

    progress_result = await db.execute(
        select(ProgramProgress).where(
            ProgramProgress.user_id == user.id,
            ProgramProgress.program_id == program_id,
            ProgramProgress.chapter_id == chapter_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    progress_map = {chapter_id: progress} if progress else {}

    return _build_chapter_response(chapter, progress_map, detail=True)  # type: ignore[return-value]


# ── Complete / reset chapter ──────────────────────────────────────────────────

async def complete_chapter(
    db: AsyncSession, user: User, program_id: str, chapter_id: str
) -> ProgramProgressResponse:
    ch_result = await db.execute(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.program_id == program_id)
    )
    if not ch_result.scalar_one_or_none():
        raise NotFoundError("Chapter not found in this program")

    prog_result = await db.execute(
        select(ProgramProgress).where(
            ProgramProgress.user_id == user.id,
            ProgramProgress.program_id == program_id,
            ProgramProgress.chapter_id == chapter_id,
        )
    )
    progress = prog_result.scalar_one_or_none()

    if progress:
        progress.completed = True
        progress.completed_at = datetime.now(UTC)
    else:
        progress = ProgramProgress(
            user_id=user.id,
            program_id=program_id,
            chapter_id=chapter_id,
            completed=True,
            completed_at=datetime.now(UTC),
        )
        db.add(progress)

    await db.commit()
    logger.info("Chapter completed: user=%s program=%s chapter=%s", user.id, program_id, chapter_id)
    return await _build_progress_response(db, user, program_id)


async def reset_chapter(
    db: AsyncSession, user: User, program_id: str, chapter_id: str
) -> ProgramProgressResponse:
    prog_result = await db.execute(
        select(ProgramProgress).where(
            ProgramProgress.user_id == user.id,
            ProgramProgress.program_id == program_id,
            ProgramProgress.chapter_id == chapter_id,
        )
    )
    progress = prog_result.scalar_one_or_none()
    if progress:
        progress.completed = False
        progress.completed_at = None
        await db.commit()

    return await _build_progress_response(db, user, program_id)


# ── User summary ──────────────────────────────────────────────────────────────

async def get_user_summary(db: AsyncSession, user: User) -> UserProgramsSummary:
    progs_result = await db.execute(
        select(Program).where(Program.is_active == True).order_by(Program.sort_order)  # noqa: E712
    )
    programs = progs_result.scalars().all()

    counts_result = await db.execute(
        select(Chapter.program_id, func.count().label("total")).group_by(Chapter.program_id)
    )
    chapter_counts = {row.program_id: row.total for row in counts_result}

    all_prog_result = await db.execute(
        select(ProgramProgress).where(ProgramProgress.user_id == user.id)
    )
    by_program: dict[str, list[ProgramProgress]] = {}
    for p in all_prog_result.scalars().all():
        by_program.setdefault(p.program_id, []).append(p)

    items = []
    started = completed = 0

    for prog in programs:
        total = chapter_counts.get(prog.id, 0)
        done = sum(1 for p in by_program.get(prog.id, []) if p.completed)
        pct = _calc_progress(total, done)
        if done > 0:
            started += 1
        if done == total and total > 0:
            completed += 1
        items.append(ProgramSummaryItem(
            program_id=prog.id,
            program_title=prog.title,
            total_chapters=total,
            completed_chapters=done,
            progress_pct=pct,
        ))

    return UserProgramsSummary(
        total_programs=len(programs),
        started_programs=started,
        completed_programs=completed,
        items=items,
    )
