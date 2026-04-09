"""Add embedding columns for RAG semantic memory

Revision ID: 007
Revises: 006
Create Date: 2026-04-08

Adiciona coluna embedding Vector(1536) em chat_messages, journal_entries e
mood_checkins para recuperação semântica de contexto (RAG).

Os embeddings são gerados de forma assíncrona via rag_service.embed_and_store()
sempre que um novo registro é criado/atualizado. Registros antigos ficam com
embedding NULL — o RAG simplesmente os ignora até que sejam preenchidos.

Índice IVFFlat por tabela com vector_cosine_ops.
  lists = 50  →  adequado para até ~500 k linhas por tabela.
  Aumentar para lists = 100+ quando o volume de produção ultrapassar esse valor.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# ── Revision ──────────────────────────────────────────────────────────────────

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Helpers ───────────────────────────────────────────────────────────────────

_TABLES = ("chat_messages", "journal_entries", "mood_checkins")

# ── Upgrade ───────────────────────────────────────────────────────────────────


def upgrade() -> None:
    # pgvector deve estar ativa (criada na 006, mas garantimos idempotência)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    for table in _TABLES:
        # 1. Coluna nullable — registros existentes ficam com NULL
        op.add_column(
            table,
            sa.Column("embedding", Vector(1536), nullable=True),
        )

        # 2. Índice IVFFlat para busca por similaridade cosseno (filtrada por user_id na query)
        op.execute(
            f"""
            CREATE INDEX ix_{table}_embedding
            ON {table}
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50)
            """
        )


# ── Downgrade ─────────────────────────────────────────────────────────────────


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_embedding")
        op.drop_column(table, "embedding")
