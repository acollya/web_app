"""
Pydantic v2 schemas for user endpoints.

UserResponse           — GET /users/me
UserUpdate             — PATCH /users/me (all fields optional)
PasswordChangeRequest  — PATCH /users/me/password
SessionResponse        — single active refresh-token session
SessionListResponse    — GET /users/me/sessions
"""
import re
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


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


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class SessionResponse(BaseModel):
    jti: str
    created_at: Optional[datetime] = Field(
        default=None,
        description="Approximate session creation time (derived from refresh-token TTL).",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Approximate refresh-token expiration time.",
    )


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int
