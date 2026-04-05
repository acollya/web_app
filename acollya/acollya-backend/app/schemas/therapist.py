"""
Pydantic v2 schemas for therapist endpoints.

TherapistResponse     — catalog card (list view)
TherapistDetail       — full profile (detail view)
AvailabilityResponse  — available time slots for a given date
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class TherapistResponse(BaseModel):
    id: str
    name: str
    photo_key: Optional[str]
    specialties: list[str]
    rating: float
    review_count: int
    hourly_rate: Decimal
    premium_discount_pct: int

    @computed_field
    @property
    def discounted_rate(self) -> Decimal:
        if self.premium_discount_pct == 0:
            return self.hourly_rate
        discount = self.hourly_rate * Decimal(self.premium_discount_pct) / Decimal(100)
        return (self.hourly_rate - discount).quantize(Decimal("0.01"))

    model_config = {"from_attributes": True}


class TherapistDetail(TherapistResponse):
    bio: Optional[str]
    credentials: list[str]
    crp: Optional[str]
    slot_start: str
    slot_end: str


class AvailabilityResponse(BaseModel):
    therapist_id: str
    date: date
    available_slots: list[str] = Field(
        description="List of available start times in HH:MM format"
    )
