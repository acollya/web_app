"""ORM model for user_persona_facts — fatos extraídos para hiperpersonalização."""
import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


class PersonaCategory(str, enum.Enum):
    preferencia = "preferencia"   # o que o usuário gosta/prefere
    aversao     = "aversao"       # o que o usuário evita/não gosta
    rotina      = "rotina"        # padrões de comportamento e hábitos
    gatilho     = "gatilho"       # situações que causam estresse/ansiedade
    valor       = "valor"         # valores pessoais e crenças centrais
    contexto    = "contexto"      # informações de vida: profissão, família, etc.


class UserPersonaFact(Base):
    __tablename__ = "user_persona_facts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                     nullable=False, index=True)

    category   = Column(SAEnum(PersonaCategory, name="persona_category_enum"), nullable=False)
    fact_text  = Column(Text, nullable=False)
    embedding  = Column(Vector(1536), nullable=True)
    confidence = Column(Float, nullable=False, default=0.8)
    source     = Column(String(50), nullable=False)   # "chat" | "journal" | "mood_checkin" | "manual"
    source_id  = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Relacionamento reverso (opcional, para queries ORM)
    user = relationship("User", back_populates="persona_facts", lazy="noload")

    def __repr__(self) -> str:
        return f"<UserPersonaFact user={self.user_id} category={self.category} src={self.source}>"
