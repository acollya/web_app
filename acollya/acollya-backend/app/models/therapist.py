"""
ORM model for the therapist catalog.

Therapists are managed by Acollya staff — not user-generated content.
The `specialties` and `credentials` fields store JSON arrays as TEXT
(simple for now; can be migrated to JSONB in a future iteration).
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
import json

from sqlalchemy import Boolean, DateTime, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Therapist(Base):
    __tablename__ = "therapists"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    photo_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON-encoded list e.g. '["Ansiedade", "Depressao"]'
    specialties: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    credentials: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    crp: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # Brazilian psychologist reg.
    rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=5.0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    premium_discount_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Working days as bitmask: Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32
    working_days_mask: Mapped[int] = mapped_column(Integer, nullable=False, default=31)  # Mon-Fri
    # Slot window: first and last start times (24h format strings "09:00")
    slot_start: Mapped[str] = mapped_column(Text, nullable=False, default="09:00")
    slot_end: Mapped[str] = mapped_column(Text, nullable=False, default="18:00")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def specialties_list(self) -> list[str]:
        return json.loads(self.specialties)

    @property
    def credentials_list(self) -> list[str]:
        return json.loads(self.credentials)
