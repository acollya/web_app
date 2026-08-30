"""Chat F2 — mensagens de áudio: colunas de mídia em chat_messages.

media_key         — chave S3 (chat-audio/{user_id}/{uuid}.m4a); NUNCA URL
media_type        — 'audio' (imagens/documentos nas fases F3/F4)
duration_seconds  — duração do áudio para o player

O content da mensagem de áudio É a transcrição (Whisper) — assim crisis
detection, RAG e o LLM continuam operando sobre texto sem mudança de pipeline.

Revision ID: 025
Revises: 024
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("media_key", sa.Text(), nullable=True))
    op.add_column("chat_messages", sa.Column("media_type", sa.Text(), nullable=True))
    op.add_column("chat_messages", sa.Column("duration_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "duration_seconds")
    op.drop_column("chat_messages", "media_type")
    op.drop_column("chat_messages", "media_key")
