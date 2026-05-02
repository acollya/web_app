"""Clinical knowledge base — TCC/TRS content chunks for RAG retrieval.

Static, NOT user-specific. Retrieved globally by semantic similarity to the user
query. Categories: tcc | trs | regulacao | crise | relacionamento | autoconhecimento.

Embeddings are generated post-migration by clinical_kb_service.embed_all_pending().
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base


class ClinicalKnowledge(Base):
    __tablename__ = "clinical_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="internal")
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
