"""
API v1 router — aggregates all endpoint modules.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    mood,
    journal,
    programs,
    therapists,
    appointments,
    subscriptions,
    analytics,
    chat,
    persona,
    media,
)

api_router = APIRouter()

# ── System ─────────────────────────────────────────────────────────────────────
@api_router.get("/ping", tags=["system"])
async def ping():
    return {"message": "pong"}


# ── Phase 1 endpoints ──────────────────────────────────────────────────────────
api_router.include_router(auth.router,           prefix="/auth",          tags=["auth"])
api_router.include_router(users.router,          prefix="/users",         tags=["users"])
api_router.include_router(mood.router,           prefix="/mood",          tags=["mood"])
api_router.include_router(journal.router,        prefix="/journal",       tags=["journal"])
api_router.include_router(programs.router,       prefix="/programs",      tags=["programs"])
api_router.include_router(therapists.router,     prefix="/therapists",    tags=["therapists"])
api_router.include_router(appointments.router,   prefix="/appointments",  tags=["appointments"])

# ── Phase 1 — Subscriptions ───────────────────────────────────────────────────
api_router.include_router(subscriptions.router,  prefix="/subscriptions", tags=["subscriptions"])

api_router.include_router(analytics.router,      prefix="/analytics",     tags=["analytics"])

# ── Phase 2 — AI + Streaming ───────────────────────────────────────────────────
api_router.include_router(chat.router,           prefix="/chat",          tags=["chat"])

# ── Phase 2 — Persona / Hyperpersonalization ───────────────────────────────────
api_router.include_router(persona.router,        prefix="/persona",       tags=["persona"])

# ── Phase 3 — Media (áudio, transcrição) ──────────────────────────────────────
api_router.include_router(media.router,          prefix="/media",         tags=["media"])
