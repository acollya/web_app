"""
ORM models for the program catalog.

Programs and chapters are static catalog data seeded via migration.
They are NOT user-generated content — only admins manage this table.

Relationships:
  Program  1──* Chapter
  Program  1──* ProgramProgress  (via program_id TEXT reference)
"""
import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)  # resumo curto (cards/carrossel)
    about: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # descritivo longo estruturado
    category: Mapped[str] = mapped_column(Text, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # "21 dias", "6 semanas"…
    format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # jornada_diaria|semanal|fases|modular|ferramenta|ao_vivo
    difficulty: Mapped[str] = mapped_column(Text, nullable=False)  # beginner | intermediate | advanced
    audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # nicho ("mães", "concurseiros"…)
    cover_image_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 1 = incluso no Essencial+ · 2 = incluso no Completo · NULL = fora dos planos
    # (bloqueado → upgrade ou compra avulsa via iap_product_id)
    min_plan_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_min_brl: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    price_max_brl: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    iap_product_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="program",
        order_by="Chapter.order",
        cascade="all, delete-orphan",
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False, default="text")  # text | video | audio
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    program: Mapped["Program"] = relationship(back_populates="chapters")
