"""
Pydantic v2 schemas for auth endpoints.

Request bodies:
  RegisterRequest, LoginRequest, RefreshRequest, GoogleAuthRequest, AppleAuthRequest

Responses:
  TokenResponse  — returned on login, register, refresh, google_auth, apple_auth
  MessageResponse — generic success message (e.g. logout)
"""
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserResponse


# ── Requests ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120, strip_whitespace=True)
    terms_accepted: bool

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("terms_accepted")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the terms of service")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(description="Google ID token from the client SDK")
    terms_accepted: bool = True


class AppleAuthRequest(BaseModel):
    identity_token: str = Field(description="Apple identity token (JWT) from Sign in with Apple")
    full_name: Optional[str] = Field(None, description="User's full name (only sent on first sign-in)")
    terms_accepted: bool = True


# ── Responses ──────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")
    user_id: str
    is_new_user: bool = False
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
