"""
Tests for app/services/appointment_service.py

Strategy: seed Therapist rows directly in DB. Patch get_availability inside
appointment_service so we don't need to test availability algorithm here
(that lives in therapist_service and has its own test file).

Covers:
  create_appointment — success, therapist not found, slot not available
  list_appointments  — empty, pagination, upcoming_only filter, only own
  get_appointment    — success, not found, wrong owner
  cancel_appointment — success, already cancelled, completed, too late (< 2h), wrong owner
"""
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.models.appointment import Appointment
from app.models.therapist import Therapist
from app.schemas.appointment import AppointmentCreate
from app.schemas.therapist import AvailabilityResponse
from app.services import appointment_service


# ── Fixtures ───────────────────────────────────────────────────────────────────

async def _make_therapist(db, *, therapist_id: str = "terapeuta-teste") -> Therapist:
    t = Therapist(
        id=therapist_id,
        name="Dra. Teste",
        photo_key=None,
        bio="Bio de teste",
        specialties='["ansiedade"]',
        credentials='["CRP 01/00001"]',
        crp="01/00001",
        rating=Decimal("4.8"),
        review_count=10,
        hourly_rate=Decimal("150.00"),
        premium_discount_pct=10,
        working_days_mask=31,  # Mon–Fri
        slot_start="09:00",
        slot_end="17:00",
        is_active=True,
        sort_order=0,
    )
    db.add(t)
    await db.commit()
    return t


async def _make_appointment(
    db,
    user,
    *,
    therapist_id: str = "terapeuta-teste",
    appt_date: date | None = None,
    time: str = "10:00",
    status: str = "pending",
) -> Appointment:
    appt_date = appt_date or (datetime.now(UTC).date() + timedelta(days=3))
    appt = Appointment(
        user_id=user.id,
        therapist_id=therapist_id,
        date=appt_date,
        time=time,
        status=status,
        payment_status="pending",
        amount=Decimal("150.00"),
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return appt


def _availability_with(slots: list[str], therapist_id: str = "terapeuta-teste") -> AvailabilityResponse:
    return AvailabilityResponse(
        therapist_id=therapist_id,
        date=datetime.now(UTC).date() + timedelta(days=3),
        available_slots=slots,
    )


# ── create_appointment ─────────────────────────────────────────────────────────

async def test_create_appointment_success(db, test_user):
    await _make_therapist(db)
    slot_date = datetime.now(UTC).date() + timedelta(days=3)

    with patch(
        "app.services.appointment_service.get_availability",
        new=AsyncMock(return_value=_availability_with(["10:00"])),
    ):
        data = AppointmentCreate(therapist_id="terapeuta-teste", date=slot_date, time="10:00")
        resp = await appointment_service.create_appointment(db, test_user, data)

    assert resp.therapist_id == "terapeuta-teste"
    assert resp.time == "10:00"
    assert resp.status == "pending"
    assert resp.therapist_name == "Dra. Teste"
    assert float(resp.amount) == 150.00


async def test_create_appointment_therapist_not_found(db, test_user):
    slot_date = datetime.now(UTC).date() + timedelta(days=3)
    data = AppointmentCreate(therapist_id="nao-existe", date=slot_date, time="10:00")

    with pytest.raises(NotFoundError):
        await appointment_service.create_appointment(db, test_user, data)


async def test_create_appointment_slot_not_available(db, test_user):
    await _make_therapist(db)
    slot_date = datetime.now(UTC).date() + timedelta(days=3)

    with patch(
        "app.services.appointment_service.get_availability",
        new=AsyncMock(return_value=_availability_with(["14:00"])),  # "10:00" not in list
    ):
        data = AppointmentCreate(therapist_id="terapeuta-teste", date=slot_date, time="10:00")
        with pytest.raises(ConflictError):
            await appointment_service.create_appointment(db, test_user, data)


# ── list_appointments ──────────────────────────────────────────────────────────

async def test_list_appointments_empty(db, test_user):
    resp = await appointment_service.list_appointments(db, test_user)
    assert resp.total == 0
    assert resp.items == []


async def test_list_appointments_pagination(db, test_user):
    await _make_therapist(db)
    for i in range(5):
        await _make_appointment(db, test_user, time=f"0{i+9}:00")

    page1 = await appointment_service.list_appointments(db, test_user, page=1, page_size=3)
    page2 = await appointment_service.list_appointments(db, test_user, page=2, page_size=3)

    assert page1.total == 5
    assert len(page1.items) == 3
    assert page1.has_more is True
    assert len(page2.items) == 2
    assert page2.has_more is False


async def test_list_appointments_upcoming_only(db, test_user):
    await _make_therapist(db)
    future_date = datetime.now(UTC).date() + timedelta(days=5)
    past_date = datetime.now(UTC).date() - timedelta(days=5)

    await _make_appointment(db, test_user, appt_date=future_date, time="10:00")
    await _make_appointment(db, test_user, appt_date=past_date, time="11:00")

    resp = await appointment_service.list_appointments(db, test_user, upcoming_only=True)
    assert resp.total == 1
    assert resp.items[0].date == future_date


async def test_list_appointments_only_own(db, test_user, other_user):
    await _make_therapist(db)
    await _make_appointment(db, test_user, time="10:00")
    await _make_appointment(db, other_user, time="11:00")

    resp = await appointment_service.list_appointments(db, test_user)
    assert resp.total == 1


# ── get_appointment ────────────────────────────────────────────────────────────

async def test_get_appointment_success(db, test_user):
    await _make_therapist(db)
    created = await _make_appointment(db, test_user)

    resp = await appointment_service.get_appointment(db, test_user, str(created.id))
    assert resp.id == created.id


async def test_get_appointment_not_found(db, test_user):
    with pytest.raises(NotFoundError):
        await appointment_service.get_appointment(db, test_user, str(uuid.uuid4()))


async def test_get_appointment_wrong_owner(db, test_user, other_user):
    await _make_therapist(db)
    created = await _make_appointment(db, other_user)

    with pytest.raises(AuthorizationError):
        await appointment_service.get_appointment(db, test_user, str(created.id))


# ── cancel_appointment ─────────────────────────────────────────────────────────

async def test_cancel_appointment_success(db, test_user):
    await _make_therapist(db)
    # Far future — well outside 2h window
    future = datetime.now(UTC).date() + timedelta(days=7)
    created = await _make_appointment(db, test_user, appt_date=future, time="10:00")

    resp = await appointment_service.cancel_appointment(db, test_user, str(created.id))
    assert resp.status == "cancelled"


async def test_cancel_already_cancelled(db, test_user):
    await _make_therapist(db)
    future = datetime.now(UTC).date() + timedelta(days=7)
    created = await _make_appointment(db, test_user, appt_date=future, status="cancelled")

    with pytest.raises(ValidationError, match="already cancelled"):
        await appointment_service.cancel_appointment(db, test_user, str(created.id))


async def test_cancel_completed_appointment(db, test_user):
    await _make_therapist(db)
    past = datetime.now(UTC).date() - timedelta(days=1)
    created = await _make_appointment(db, test_user, appt_date=past, status="completed")

    with pytest.raises(ValidationError, match="completed"):
        await appointment_service.cancel_appointment(db, test_user, str(created.id))


async def test_cancel_too_late_raises(db, test_user):
    """Appointment within 2h window must raise ValidationError."""
    await _make_therapist(db)
    today = datetime.now(UTC).date()
    # Time 30 minutes from now — inside the 2h buffer
    soon = (datetime.now(UTC) + timedelta(minutes=30)).strftime("%H:%M")
    created = await _make_appointment(db, test_user, appt_date=today, time=soon)

    with pytest.raises(ValidationError, match="2 hours"):
        await appointment_service.cancel_appointment(db, test_user, str(created.id))


async def test_cancel_wrong_owner(db, test_user, other_user):
    await _make_therapist(db)
    future = datetime.now(UTC).date() + timedelta(days=7)
    created = await _make_appointment(db, other_user, appt_date=future)

    with pytest.raises(AuthorizationError):
        await appointment_service.cancel_appointment(db, test_user, str(created.id))
