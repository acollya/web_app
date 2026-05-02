"""
Appointment service — booking lifecycle management.

create_appointment  — validate slot, create row, return response
list_appointments   — paginated history with therapist name overlay
get_appointment     — single appointment (ownership check)
cancel_appointment  — soft cancel (status → 'cancelled')

Business rules:
  - Slot must be in therapist's available slots (validated live)
  - Cannot book a slot that is already taken (conflict check with row lock)
  - Cancellation allowed only if appointment is ≥2h in the future AND
    status is 'pending' or 'confirmed'
  - Amount is set from therapist.hourly_rate at booking time (snapshot)
  - payment_status stays 'pending' — payment integration is handled externally
"""
import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, AuthorizationError, NotFoundError, ValidationError
from app.models.appointment import Appointment
from app.models.therapist import Therapist
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
)
from app.services.therapist_service import get_availability

logger = logging.getLogger(__name__)

_CANCEL_BUFFER_HOURS = 2


def _build_response(appt: Appointment, therapist_name: str | None = None) -> AppointmentResponse:
    return AppointmentResponse(
        id=appt.id,
        therapist_id=appt.therapist_id,
        therapist_name=therapist_name,
        date=appt.date,
        time=appt.time,
        status=appt.status,
        payment_status=appt.payment_status,
        amount=appt.amount,
        meeting_link=appt.meeting_link,
        created_at=appt.created_at,
        updated_at=appt.updated_at,
    )


# ── Create ─────────────────────────────────────────────────────────────────────

async def create_appointment(
    db: AsyncSession, user: User, data: AppointmentCreate
) -> AppointmentResponse:
    # Fetch therapist (validates existence)
    t_result = await db.execute(
        select(Therapist).where(Therapist.id == data.therapist_id, Therapist.is_active == True)  # noqa: E712
    )
    therapist = t_result.scalar_one_or_none()
    if not therapist:
        raise NotFoundError("Therapist not found")

    # Validate slot is actually available
    availability = await get_availability(db, data.therapist_id, data.date)
    if data.time not in availability.available_slots:
        raise ConflictError(
            f"The slot {data.time} on {data.date} is not available. "
            "Please choose another time."
        )

    appointment = Appointment(
        user_id=user.id,
        therapist_id=data.therapist_id,
        date=data.date,
        time=data.time,
        status="pending",
        payment_status="pending",
        amount=therapist.hourly_rate,
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    logger.info(
        "Appointment created: user=%s therapist=%s date=%s time=%s",
        user.id, data.therapist_id, data.date, data.time,
    )
    return _build_response(appointment, therapist_name=therapist.name)


# ── List ───────────────────────────────────────────────────────────────────────

async def list_appointments(
    db: AsyncSession,
    user: User,
    page: int = 1,
    page_size: int = 20,
    upcoming_only: bool = False,
) -> AppointmentListResponse:
    offset = (page - 1) * page_size

    base_where = [Appointment.user_id == user.id]
    if upcoming_only:
        today = datetime.now(UTC).date()
        base_where.append(Appointment.date >= today)
        base_where.append(Appointment.status.notin_(["cancelled"]))

    count_result = await db.execute(
        select(func.count()).where(*base_where)
    )
    total: int = count_result.scalar_one()

    result = await db.execute(
        select(Appointment)
        .where(*base_where)
        .order_by(Appointment.date.asc(), Appointment.time.asc())
        .offset(offset)
        .limit(page_size)
    )
    appointments = result.scalars().all()

    # Fetch therapist names in one query
    therapist_ids = list({a.therapist_id for a in appointments})
    names: dict[str, str] = {}
    if therapist_ids:
        t_result = await db.execute(
            select(Therapist.id, Therapist.name).where(Therapist.id.in_(therapist_ids))
        )
        names = {row.id: row.name for row in t_result.all()}

    return AppointmentListResponse(
        items=[_build_response(a, names.get(a.therapist_id)) for a in appointments],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(appointments)) < total,
    )


# ── Get single ─────────────────────────────────────────────────────────────────

async def get_appointment(
    db: AsyncSession, user: User, appointment_id: str
) -> AppointmentResponse:
    result = await db.execute(
        select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise NotFoundError("Appointment not found")
    if str(appt.user_id) != str(user.id):
        raise AuthorizationError("This appointment does not belong to you")

    t_result = await db.execute(
        select(Therapist.name).where(Therapist.id == appt.therapist_id)
    )
    row = t_result.first()
    return _build_response(appt, therapist_name=row[0] if row else None)


# ── Cancel ─────────────────────────────────────────────────────────────────────

async def cancel_appointment(
    db: AsyncSession, user: User, appointment_id: str
) -> AppointmentResponse:
    result = await db.execute(
        select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise NotFoundError("Appointment not found")
    if str(appt.user_id) != str(user.id):
        raise AuthorizationError("This appointment does not belong to you")

    if appt.status == "cancelled":
        raise ValidationError("Appointment is already cancelled")
    if appt.status == "completed":
        raise ValidationError("Cannot cancel a completed appointment")

    # Enforce 2h cancellation window
    appt_dt = datetime.combine(appt.date, _parse_time(appt.time))
    now = datetime.now(UTC).replace(tzinfo=None)
    if appt_dt - now < timedelta(hours=_CANCEL_BUFFER_HOURS):
        raise ValidationError(
            f"Cancellations must be made at least {_CANCEL_BUFFER_HOURS} hours in advance"
        )

    appt.status = "cancelled"
    await db.commit()
    await db.refresh(appt)

    logger.info("Appointment cancelled: user=%s appt=%s", user.id, appointment_id)

    t_result = await db.execute(
        select(Therapist.name).where(Therapist.id == appt.therapist_id)
    )
    row = t_result.first()
    return _build_response(appt, therapist_name=row[0] if row else None)


def _parse_time(t: str):
    from datetime import time
    h, m = t.split(":")
    return time(int(h), int(m))
