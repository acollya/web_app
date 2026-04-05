"""
Therapist endpoints.

GET /therapists                          — catalog list (filter by specialty)
GET /therapists/{therapist_id}           — full profile
GET /therapists/{therapist_id}/availability?date=YYYY-MM-DD — free slots
"""
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.therapist import AvailabilityResponse, TherapistDetail, TherapistResponse
from app.services import therapist_service

router = APIRouter()


@router.get(
    "",
    response_model=list[TherapistResponse],
    summary="List therapists (optionally filter by specialty)",
)
async def list_therapists(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    specialty: Optional[str] = Query(None, description="Filter by specialty keyword"),
) -> list[TherapistResponse]:
    return await therapist_service.list_therapists(db, specialty=specialty)


@router.get(
    "/{therapist_id}",
    response_model=TherapistDetail,
    summary="Get therapist full profile",
)
async def get_therapist(
    therapist_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TherapistDetail:
    return await therapist_service.get_therapist(db, therapist_id)


@router.get(
    "/{therapist_id}/availability",
    response_model=AvailabilityResponse,
    summary="Get available time slots for a therapist on a given date",
)
async def get_availability(
    therapist_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date: date = Query(..., description="Date in YYYY-MM-DD format"),
) -> AvailabilityResponse:
    return await therapist_service.get_availability(db, therapist_id, date)
