"""
Appointment endpoints.

POST   /appointments                     — book a new appointment
GET    /appointments                     — list user's appointments (paginated)
GET    /appointments/{id}               — single appointment detail
DELETE /appointments/{id}               — cancel appointment
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
)
from app.services import appointment_service

router = APIRouter()


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a new appointment with a therapist",
)
async def create_appointment(
    body: AppointmentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    return await appointment_service.create_appointment(db, current_user, body)


@router.get(
    "",
    response_model=AppointmentListResponse,
    summary="List user's appointments",
)
async def list_appointments(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    upcoming_only: bool = Query(False, description="Return only future non-cancelled appointments"),
) -> AppointmentListResponse:
    return await appointment_service.list_appointments(
        db, current_user, page, page_size, upcoming_only
    )


@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get a single appointment",
)
async def get_appointment(
    appointment_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    return await appointment_service.get_appointment(db, current_user, str(appointment_id))


@router.delete(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Cancel an appointment",
)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AppointmentResponse:
    return await appointment_service.cancel_appointment(db, current_user, str(appointment_id))
