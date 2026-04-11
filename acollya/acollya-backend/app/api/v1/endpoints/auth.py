"""
Auth endpoints.

POST /auth/register    — email+password sign-up
POST /auth/login       — email+password sign-in
POST /auth/refresh     — rotate refresh token
POST /auth/logout      — revoke refresh token
POST /auth/google      — Google OAuth sign-in / sign-up
POST /auth/apple       — Apple Sign In sign-in / sign-up
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_redis
from app.schemas.auth import (
    AppleAuthRequest,
    GoogleAuthRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account with email and password",
)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    return await auth_service.register(db, redis, body)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in with email and password",
)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    return await auth_service.login(db, redis, body)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate access and refresh tokens",
)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    return await auth_service.refresh_tokens(db, redis, body.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke the current refresh token",
)
async def logout(
    body: RefreshRequest,
    redis: Annotated[Redis, Depends(get_redis)],
) -> MessageResponse:
    await auth_service.logout(redis, body.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Sign in or sign up with a Google ID token",
)
async def google_auth(
    body: GoogleAuthRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    return await auth_service.google_auth(db, redis, body)


@router.post(
    "/apple",
    response_model=TokenResponse,
    summary="Sign in or sign up with Apple identity token",
)
async def apple_auth(
    body: AppleAuthRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    return await auth_service.apple_auth(db, redis, body)
