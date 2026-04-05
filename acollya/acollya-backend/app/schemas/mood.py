"""
Pydantic v2 schemas for mood check-in endpoints.

MoodCheckinCreate  — POST /mood body
MoodCheckinResponse — single check-in record
MoodHistoryResponse — paginated list
MoodInsightsResponse — aggregated stats (period: week | month | year)

Intensity scale: 1–5 (matches DB constraint ck_mood_intensity).
  1 = very low / negative,  5 = very high / positive
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Supported mood labels ──────────────────────────────────────────────────────
# Kept as a plain list so mobile/web can freely extend labels without a breaking
# schema change — the DB stores any text value.
VALID_MOODS = {
    "muito-feliz",
    "feliz",
    "neutro",
    "triste",
    "muito-triste",
    "ansioso",
    "calmo",
    "irritado",
    "animado",
    "cansado",
    "esperancoso",
    "com-medo",
    "grato",
    "solitario",
    "sobrecarregado",
}


# ── Requests ───────────────────────────────────────────────────────────────────

class MoodCheckinCreate(BaseModel):
    mood: str = Field(
        description="Primary emotion label (e.g. 'feliz', 'ansioso')",
        min_length=1,
        max_length=50,
    )
    intensity: int = Field(
        ge=1,
        le=5,
        description="Intensity level from 1 (very low) to 5 (very high)",
    )
    note: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional free-text note from the user",
    )
    # Secondary emotions are stored in the note for now; the mobile UI can
    # concatenate them. A separate junction table can be added in a future
    # migration without breaking this API.
    secondary_moods: list[str] = Field(
        default_factory=list,
        description="Additional emotion labels selected by the user",
    )


# ── Responses ──────────────────────────────────────────────────────────────────

class MoodCheckinResponse(BaseModel):
    id: uuid.UUID
    mood: str
    intensity: int
    note: Optional[str]
    ai_insight: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MoodHistoryResponse(BaseModel):
    items: list[MoodCheckinResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ── Insights ───────────────────────────────────────────────────────────────────

class MoodInsightsResponse(BaseModel):
    period: str                              # "week" | "month" | "year"
    total_checkins: int
    average_intensity: Optional[float]       # None if no check-ins in period
    mood_distribution: dict[str, int]        # {"feliz": 5, "ansioso": 3, ...}
    most_common_mood: Optional[str]
    # Comparison with previous equal-length period (percentage change)
    intensity_change_pct: Optional[float]    # +12.5 means improved 12.5%
    checkin_count_change: Optional[int]      # delta vs previous period
    streak_days: int                         # consecutive days with a check-in
