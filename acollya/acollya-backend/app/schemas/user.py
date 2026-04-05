"""
Pydantic v2 schemas for user endpoints.

UserResponse  — GET /users/me
UserUpdate    — PATCH /users/me (all fields optional)
"""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    phone: Optional[str]
    birth_date: Optional[date]
    gender: Optional[str]
    plan_code: int
    subscription_status: Optional[str]
    trial_ends_at: Optional[datetime]
    is_trial_active: bool
    is_premium: bool
    terms_accepted: bool
    terms_accepted_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120, strip_whitespace=True)
    phone: Optional[str] = Field(None, max_length=20)
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=30)
    push_token_fcm: Optional[str] = None
    push_token_apns: Optional[str] = None
