"""
Therapist service — catalog reads + availability generation.

list_therapists    — all active therapists
get_therapist      — single therapist profile
get_availability   — compute free slots for a given date

Availability algorithm:
  1. Generate all hourly slots between therapist.slot_start and slot_end
  2. Check working_days_mask against the requested weekday
  3. Query booked appointments for that therapist/date with non-cancelled status
  4. Subtract booked slots
  5. For today, also remove past slots (now + 2h buffer)
"""
import json
import logging
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.appointment import Appointment
from app.models.therapist import Therapist
from app.schemas.therapist import AvailabilityResponse, TherapistDetail, TherapistResponse

logger = logging.getLogger(__name__)

# Weekday bitmask: Monday=0 (Python) → bit 0, ..., Saturday=5 → bit 5
_DAY_BITS = {0: 1, 1: 2, 2: 4, 3: 8, 4: 16, 5: 32, 6: 64}


def _parse_time(t: str) -> time:
    h, m = t.split(":")
    return time(int(h), int(m))


def _generate_slots(slot_start: str, slot_end: str) -> list[str]:
    """Generate hourly slots from slot_start up to (not including) slot_end."""
    start = _parse_time(slot_start)
    end = _parse_time(slot_end)
    slots = []
    current = datetime(2000, 1, 1, start.hour, start.minute)
    limit = datetime(2000, 1, 1, end.hour, end.minute)
    while current < limit:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(hours=1)
    return slots


def _is_working_day(mask: int, weekday: int) -> bool:
    return bool(mask & _DAY_BITS.get(weekday, 0))


def _build_response(t: Therapist, detail: bool = False) -> TherapistResponse | TherapistDetail:
    base = {
        "id": t.id,
        "name": t.name,
        "photo_key": t.photo_key,
        "specialties": json.loads(t.specialties),
        "rating": float(t.rating),
        "review_count": t.review_count,
        "hourly_rate": t.hourly_rate,
        "premium_discount_pct": t.premium_discount_pct,
    }
    if detail:
        return TherapistDetail(
            **base,
            bio=t.bio,
            credentials=json.loads(t.credentials),
            crp=t.crp,
            slot_start=t.slot_start,
            slot_end=t.slot_end,
        )
    return TherapistResponse(**base)


# ── List ───────────────────────────────────────────────────────────────────────

async def list_therapists(
    db: AsyncSession,
    specialty: str | None = None,
) -> list[TherapistResponse]:
    result = await db.execute(
        select(Therapist)
        .where(Therapist.is_active == True)  # noqa: E712
        .order_by(Therapist.sort_order)
    )
    therapists = result.scalars().all()

    if specialty:
        # Filter in Python (JSON column search; sufficient for small catalog)
        therapists = [
            t for t in therapists
            if specialty.lower() in t.specialties.lower()
        ]

    return [_build_response(t) for t in therapists]  # type: ignore[return-value]


# ── Get single ─────────────────────────────────────────────────────────────────

async def get_therapist(db: AsyncSession, therapist_id: str) -> TherapistDetail:
    result = await db.execute(
        select(Therapist).where(Therapist.id == therapist_id, Therapist.is_active == True)  # noqa: E712
    )
    therapist = result.scalar_one_or_none()
    if not therapist:
        raise NotFoundError("Therapist not found")
    return _build_response(therapist, detail=True)  # type: ignore[return-value]


# ── Availability ───────────────────────────────────────────────────────────────

async def get_availability(
    db: AsyncSession, therapist_id: str, requested_date: date
) -> AvailabilityResponse:
    result = await db.execute(
        select(Therapist).where(Therapist.id == therapist_id, Therapist.is_active == True)  # noqa: E712
    )
    therapist = result.scalar_one_or_none()
    if not therapist:
        raise NotFoundError("Therapist not found")

    # Check working day
    weekday = requested_date.weekday()  # 0=Monday
    if not _is_working_day(therapist.working_days_mask, weekday):
        return AvailabilityResponse(
            therapist_id=therapist_id,
            date=requested_date,
            available_slots=[],
        )

    all_slots = _generate_slots(therapist.slot_start, therapist.slot_end)

    # Fetch booked (non-cancelled) slots for this date
    booked_result = await db.execute(
        select(Appointment.time).where(
            Appointment.therapist_id == therapist_id,
            Appointment.date == requested_date,
            Appointment.status.notin_(["cancelled"]),
        )
    )
    booked_times = {row[0] for row in booked_result.all()}

    # For today, remove slots within 2 hours from now
    now = datetime.now(UTC)
    cutoff: str | None = None
    if requested_date == now.date():
        cutoff_dt = now + timedelta(hours=2)
        cutoff = cutoff_dt.strftime("%H:%M")

    available = [
        s for s in all_slots
        if s not in booked_times and (cutoff is None or s > cutoff)
    ]

    return AvailabilityResponse(
        therapist_id=therapist_id,
        date=requested_date,
        available_slots=available,
    )
