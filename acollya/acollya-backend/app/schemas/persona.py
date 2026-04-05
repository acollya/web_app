"""Pydantic schemas para o endpoint /persona."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PersonaFactResponse(BaseModel):
    """Um fato individual da persona do usuário."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    fact_text: str
    confidence: float
    source: str
    source_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class PersonaProfileResponse(BaseModel):
    """
    Perfil completo da persona do usuário.

    `facts_by_category`  — fatos agrupados por categoria (para debug/UI)
    `context_preview`    — bloco de texto gerado para injeção nos prompts de IA
    `total_facts`        — total de fatos cadastrados
    """
    total_facts: int
    facts_by_category: dict[str, list[PersonaFactResponse]]
    context_preview: str


class PersonaExtractRequest(BaseModel):
    """
    Corpo para extração manual de fatos a partir de um texto.
    Útil para testes e para seed inicial de usuários.
    """
    text: str
    source: str = "manual"
