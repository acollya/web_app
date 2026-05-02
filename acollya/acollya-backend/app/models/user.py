import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    apple_id: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    birth_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="trialing")
    revenue_cat_id: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    push_token_fcm: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    push_token_apns: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_anonymized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    anonymized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    terms_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    terms_accepted_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships — sem cascade delete: registros do usuário são preservados
    # para anonimização LGPD e eventual fine-tuning de SLMs.
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", cascade="save-update, merge")
    mood_checkins: Mapped[list["MoodCheckin"]] = relationship(back_populates="user", cascade="save-update, merge")
    journal_entries: Mapped[list["JournalEntry"]] = relationship(back_populates="user", cascade="save-update, merge")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", cascade="save-update, merge")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="user", cascade="save-update, merge")
    persona_facts: Mapped[list["UserPersonaFact"]] = relationship(back_populates="user", cascade="save-update, merge", lazy="noload")

    @property
    def is_premium(self) -> bool:
        if self.plan_code == 1 and self.subscription_status in ("active", "trialing"):
            return True
        return self.is_trial_active

    @property
    def is_trial_active(self) -> bool:
        if self.trial_ends_at is None:
            return False
        ends_at = self.trial_ends_at
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < ends_at
