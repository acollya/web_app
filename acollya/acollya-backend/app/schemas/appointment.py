"""
Pydantic v2 schemas for appointment endpoints.

AppointmentCreate   — POST /appointments body
AppointmentResponse — single appointment record
AppointmentList     — paginated list
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.therapist import TherapistResponse


class AppointmentCreate(BaseModel):
    therapist_id: str
    date: date
    time: str = Field(
        description="Slot start time in HH:MM format (e.g. '09:00')",
        pattern=r"^\d{2}:\d{2}$",
    )

    @field_validator("date")
    @classmethod
    def date_must_be_future(cls, v: date) -> date:
        from datetime import date as date_type
        if v <= date_type.today():
            raise ValueError("Appointment date must be in the future")
        return v


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    therapist_id: str
    therapist_name: Optional[str] = None  # denormalised for convenience
    date: date
    time: str
    status: str
    payment_status: str
    amount: Decimal
    meeting_link: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppointmentListResponse(BaseModel):
    items: list[AppointmentResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
