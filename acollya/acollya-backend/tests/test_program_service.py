"""
Tests for app/services/program_service.py

Strategy: seed Program + Chapter rows directly in DB; use test_user fixture
for ownership-scoped operations.

Covers:
  list_programs     — empty catalog, returns active programs with progress overlay
  get_program       — success (chapters listed), not found
  get_chapter       — success (content returned), program not found, chapter not found
  complete_chapter  — marks chapter done; chapter not found raises error
  reset_chapter     — marks chapter undone; no-op if no progress row
  get_user_summary  — no programs, programs with partial/full progress
"""
import pytest

from app.core.exceptions import NotFoundError
from app.models.program import Chapter, Program
from app.models.program_progress import ProgramProgress
from app.services import program_service


# ── Helpers ─────────────────────────────────────────────────────────────────────

async def _make_program(
    db,
    *,
    program_id: str = "prog-001",
    title: str = "Ansiedade",
    is_active: bool = True,
) -> Program:
    prog = Program(
        id=program_id,
        title=title,
        description="Descrição do programa",
        category="saúde mental",
        duration_days=14,
        difficulty="beginner",
        cover_image_key=None,
        is_premium=False,
        is_active=is_active,
        sort_order=0,
    )
    db.add(prog)
    await db.commit()
    return prog


async def _make_chapter(
    db,
    *,
    chapter_id: str,
    program_id: str,
    order: int = 1,
    title: str = "Capítulo",
) -> Chapter:
    ch = Chapter(
        id=chapter_id,
        program_id=program_id,
        order=order,
        title=title,
        content="Conteúdo do capítulo.",
        content_type="text",
        duration_minutes=10,
        video_url=None,
    )
    db.add(ch)
    await db.commit()
    return ch


# ── list_programs ───────────────────────────────────────────────────────────────

async def test_list_programs_empty(db, test_user):
    result = await program_service.list_programs(db, test_user)
    assert result == []


async def test_list_programs_returns_active(db, test_user):
    await _make_program(db, program_id="prog-active", is_active=True)
    await _make_program(db, program_id="prog-inactive", title="Inativo", is_active=False)

    result = await program_service.list_programs(db, test_user)
    assert len(result) == 1
    assert result[0].id == "prog-active"


async def test_list_programs_shows_zero_progress_for_new_user(db, test_user):
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-002", program_id="prog-001", order=2)

    result = await program_service.list_programs(db, test_user)
    assert result[0].total_chapters == 2
    assert result[0].completed_chapters == 0


async def test_list_programs_reflects_user_progress(db, test_user):
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-002", program_id="prog-001", order=2)

    # Complete one chapter
    await program_service.complete_chapter(db, test_user, "prog-001", "ch-001")

    result = await program_service.list_programs(db, test_user)
    assert result[0].completed_chapters == 1


# ── get_program ─────────────────────────────────────────────────────────────────

async def test_get_program_success(db, test_user):
    await _make_program(db, program_id="prog-001", title="Mindfulness")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-002", program_id="prog-001", order=2)

    detail = await program_service.get_program(db, test_user, "prog-001")

    assert detail.id == "prog-001"
    assert detail.title == "Mindfulness"
    assert len(detail.chapters) == 2
    assert detail.total_chapters == 2
    assert detail.completed_chapters == 0


async def test_get_program_not_found(db, test_user):
    with pytest.raises(NotFoundError):
        await program_service.get_program(db, test_user, "nao-existe")


async def test_get_program_chapters_ordered(db, test_user):
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-B", program_id="prog-001", order=2, title="B")
    await _make_chapter(db, chapter_id="ch-A", program_id="prog-001", order=1, title="A")

    detail = await program_service.get_program(db, test_user, "prog-001")

    assert detail.chapters[0].title == "A"
    assert detail.chapters[1].title == "B"


# ── get_chapter ─────────────────────────────────────────────────────────────────

async def test_get_chapter_success(db, test_user):
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")

    ch = await program_service.get_chapter(db, test_user, "prog-001", "ch-001")

    assert ch.id == "ch-001"
    assert ch.content == "Conteúdo do capítulo."
    assert ch.completed is False


async def test_get_chapter_program_not_found(db, test_user):
    with pytest.raises(NotFoundError):
        await program_service.get_chapter(db, test_user, "nao-existe", "ch-001")


async def test_get_chapter_chapter_not_found(db, test_user):
    await _make_program(db, program_id="prog-001")

    with pytest.raises(NotFoundError):
        await program_service.get_chapter(db, test_user, "prog-001", "nao-existe")


async def test_get_chapter_completed_shows_completed_true(db, test_user):
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")

    await program_service.complete_chapter(db, test_user, "prog-001", "ch-001")
    ch = await program_service.get_chapter(db, test_user, "prog-001", "ch-001")

    assert ch.completed is True
    assert ch.completed_at is not None


# ── complete_chapter ────────────────────────────────────────────────────────────

async def test_complete_chapter_updates_progress(db, test_user):
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")

    resp = await program_service.complete_chapter(db, test_user, "prog-001", "ch-001")

    assert resp.completed_chapters == 1
    assert resp.total_chapters == 1
    assert resp.progress_pct == 100
    assert resp.completed is True
    assert resp.started is True


async def test_complete_chapter_idempotent(db, test_user):
    """Completing the same chapter twice must not crash or double-count."""
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")

    await program_service.complete_chapter(db, test_user, "prog-001", "ch-001")
    resp = await program_service.complete_chapter(db, test_user, "prog-001", "ch-001")

    assert resp.completed_chapters == 1


async def test_complete_chapter_not_found(db, test_user):
    await _make_program(db, program_id="prog-001")

    with pytest.raises(NotFoundError):
        await program_service.complete_chapter(db, test_user, "prog-001", "nao-existe")


async def test_complete_partial_progress_pct(db, test_user):
    """2 of 4 chapters → 50%."""
    await _make_program(db, program_id="prog-001")
    for i in range(1, 5):
        await _make_chapter(db, chapter_id=f"ch-00{i}", program_id="prog-001", order=i)

    await program_service.complete_chapter(db, test_user, "prog-001", "ch-001")
    resp = await program_service.complete_chapter(db, test_user, "prog-001", "ch-002")

    assert resp.completed_chapters == 2
    assert resp.total_chapters == 4
    assert resp.progress_pct == 50


# ── reset_chapter ───────────────────────────────────────────────────────────────

async def test_reset_chapter_clears_completion(db, test_user):
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")

    await program_service.complete_chapter(db, test_user, "prog-001", "ch-001")
    resp = await program_service.reset_chapter(db, test_user, "prog-001", "ch-001")

    assert resp.completed_chapters == 0
    assert resp.completed is False


async def test_reset_chapter_no_op_when_no_progress(db, test_user):
    """reset_chapter must not crash when no progress row exists."""
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")

    resp = await program_service.reset_chapter(db, test_user, "prog-001", "ch-001")
    assert resp.completed_chapters == 0


# ── get_user_summary ────────────────────────────────────────────────────────────

async def test_get_user_summary_no_programs(db, test_user):
    summary = await program_service.get_user_summary(db, test_user)
    assert summary.total_programs == 0
    assert summary.started_programs == 0
    assert summary.completed_programs == 0
    assert summary.items == []


async def test_get_user_summary_partial_progress(db, test_user):
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-002", program_id="prog-001", order=2)

    await program_service.complete_chapter(db, test_user, "prog-001", "ch-001")
    summary = await program_service.get_user_summary(db, test_user)

    assert summary.total_programs == 1
    assert summary.started_programs == 1
    assert summary.completed_programs == 0
    assert summary.items[0].progress_pct == 50


async def test_get_user_summary_fully_completed(db, test_user):
    await _make_program(db, program_id="prog-001")
    await _make_chapter(db, chapter_id="ch-001", program_id="prog-001")

    await program_service.complete_chapter(db, test_user, "prog-001", "ch-001")
    summary = await program_service.get_user_summary(db, test_user)

    assert summary.completed_programs == 1
    assert summary.items[0].progress_pct == 100
