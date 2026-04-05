"""
Tests for app/services/therapist_service.py

Strategy: seed Therapist + Appointment rows directly in DB.
No external dependencies to mock.

Covers:
  list_therapists  — empty catalog, all active, specialty filter (JSON match)
  get_therapist    — success (detail fields), not found, inactive not found
  get_availability — non-working day → empty; working day → slots generated;
                     booked slots subtracted; cancelled slot NOT removed;
                     therapist not found
"""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError
from app.models.appointment import Appointment
from app.models.therapist import Therapist
from app.services import therapist_service


# ── Helpers ─────────────────────────────────────────────────────────────────────

async def _make_therapist(
    db,
    *,
    therapist_id: str = "t-001",
    name: str = "Dra. Teste",
    specialties: str = '["ansiedade", "depressão"]',
    working_days_mask: int = 31,  # Mon–Fri (bits 0-4)
    slot_start: str = "09:00",
    slot_end: str = "12:00",      # 3 slots: 09:00, 10:00, 11:00
    is_active: bool = True,
) -> Therapist:
    t = Therapist(
        id=therapist_id,
        name=name,
        photo_key=None,
        bio="Bio de teste",
        specialties=specialties,
        credentials='["CRP 01/00001"]',
        crp="01/00001",
        rating=Decimal("4.8"),
        review_count=10,
        hourly_rate=Decimal("150.00"),
        premium_discount_pct=10,
        working_days_mask=working_days_mask,
        slot_start=slot_start,
        slot_end=slot_end,
        is_active=is_active,
        sort_order=0,
    )
    db.add(t)
    await db.commit()
    return t


def _next_weekday(weekday: int) -> date:
    """Return the next occurrence of a weekday (0=Mon … 6=Sun), always in the future."""
    today = datetime.now(UTC).date()
    days_ahead = (weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


# ── list_therapists ─────────────────────────────────────────────────────────────

async def test_list_therapists_empty_catalog(db):
    result = await therapist_service.list_therapists(db)
    assert result == []


async def test_list_therapists_returns_only_active(db):
    await _make_therapist(db, therapist_id="t-active", is_active=True)
    await _make_therapist(db, therapist_id="t-inactive", name="Dr. Inativo", is_active=False)

    result = await therapist_service.list_therapists(db)
    assert len(result) == 1
    assert result[0].id == "t-active"


async def test_list_therapists_no_filter_returns_all_active(db):
    await _make_therapist(db, therapist_id="t-001")
    await _make_therapist(db, therapist_id="t-002", name="Dr. B")

    result = await therapist_service.list_therapists(db)
    assert len(result) == 2


async def test_list_therapists_specialty_filter_match(db):
    await _make_therapist(db, therapist_id="t-001", specialties='["ansiedade"]')
    await _make_therapist(db, therapist_id="t-002", name="Dr. B", specialties='["relacionamentos"]')

    result = await therapist_service.list_therapists(db, specialty="ansiedade")
    assert len(result) == 1
    assert result[0].id == "t-001"


async def test_list_therapists_specialty_filter_no_match(db):
    await _make_therapist(db, therapist_id="t-001", specialties='["ansiedade"]')

    result = await therapist_service.list_therapists(db, specialty="estresse")
    assert result == []


# ── get_therapist ───────────────────────────────────────────────────────────────

async def test_get_therapist_success(db):
    await _make_therapist(db, therapist_id="t-001", name="Dra. Detalhes")

    detail = await therapist_service.get_therapist(db, "t-001")

    assert detail.id == "t-001"
    assert detail.name == "Dra. Detalhes"
    assert detail.bio == "Bio de teste"
    assert "CRP 01/00001" in detail.credentials
    assert isinstance(detail.specialties, list)
    assert detail.slot_start == "09:00"
    assert detail.slot_end == "12:00"


async def test_get_therapist_not_found(db):
    with pytest.raises(NotFoundError):
        await therapist_service.get_therapist(db, "nao-existe")


async def test_get_therapist_inactive_raises_not_found(db):
    await _make_therapist(db, therapist_id="t-inativo", is_active=False)

    with pytest.raises(NotFoundError):
        await therapist_service.get_therapist(db, "t-inativo")


# ── get_availability ────────────────────────────────────────────────────────────

async def test_get_availability_non_working_day(db):
    """Saturday (weekday=5) is not in Mon–Fri mask → empty slots."""
    await _make_therapist(db, therapist_id="t-001", working_days_mask=31)

    saturday = _next_weekday(5)  # 5 = Saturday
    resp = await therapist_service.get_availability(db, "t-001", saturday)

    assert resp.available_slots == []
    assert resp.therapist_id == "t-001"
    assert resp.date == saturday


async def test_get_availability_working_day_generates_slots(db):
    """Mon–Fri therapist with 09:00–12:00 → 3 slots when nothing booked."""
    await _make_therapist(db, therapist_id="t-001", slot_start="09:00", slot_end="12:00")

    next_monday = _next_weekday(0)  # 0 = Monday
    resp = await therapist_service.get_availability(db, "t-001", next_monday)

    assert set(resp.available_slots) == {"09:00", "10:00", "11:00"}
    assert resp.therapist_id == "t-001"
    assert resp.date == next_monday


async def test_get_availability_booked_slot_excluded(db, test_user):
    """A pending appointment blocks that slot."""
    await _make_therapist(db, therapist_id="t-001", slot_start="09:00", slot_end="12:00")

    next_monday = _next_weekday(0)
    booked_appt = Appointment(
        user_id=test_user.id,
        therapist_id="t-001",
        date=next_monday,
        time="10:00",
        status="pending",
        payment_status="pending",
        amount=Decimal("150.00"),
    )
    db.add(booked_appt)
    await db.commit()

    resp = await therapist_service.get_availability(db, "t-001", next_monday)

    assert "10:00" not in resp.available_slots
    assert "09:00" in resp.available_slots
    assert "11:00" in resp.available_slots


async def test_get_availability_cancelled_slot_remains_available(db, test_user):
    """A cancelled appointment does NOT block the slot."""
    await _make_therapist(db, therapist_id="t-001", slot_start="09:00", slot_end="12:00")

    next_monday = _next_weekday(0)
    cancelled_appt = Appointment(
        user_id=test_user.id,
        therapist_id="t-001",
        date=next_monday,
        time="09:00",
        status="cancelled",
        payment_status="pending",
        amount=Decimal("150.00"),
    )
    db.add(cancelled_appt)
    await db.commit()

    resp = await therapist_service.get_availability(db, "t-001", next_monday)

    assert "09:00" in resp.available_slots


async def test_get_availability_therapist_not_found(db):
    with pytest.raises(NotFoundError):
        await therapist_service.get_availability(db, "nao-existe", datetime.now(UTC).date())
