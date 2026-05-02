"""Add embedding column and tsvector to chapters table for RAG retrieval.

Revision ID: 016
Revises: 015
Create Date: 2026-05-02

Adiciona suporte a busca semântica (vetorial) e lexical (BM25) na tabela
chapters, permitindo que o RAG service recupere conteúdo de programas
terapêuticos relevante ao contexto da conversa do usuário.

Características:
  - Embeddings 1536d (text-embedding-3-small) gerados pelo clinical_kb_service
    via embed_pending_chapters() após a migração rodar (idempotente).
  - IVFFlat lists=50 para busca cosseno; suficiente até ~500k registros.
  - GENERATED ALWAYS tsvector com stemmer português para BM25 híbrido.
  - Apenas chapters com content_type='text' são candidatos a embedding.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# ── Revision ──────────────────────────────────────────────────────────────────

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Upgrade ───────────────────────────────────────────────────────────────────


def upgrade() -> None:
    # Garantia de extensão (já criada em migrações anteriores; idempotente)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. Coluna de embedding (nullable — preenchida em background após migração)
    op.add_column(
        "chapters",
        sa.Column("embedding", Vector(1536), nullable=True),
    )

    # 2. Índice IVFFlat (cosine) — embeddings ainda nulos no momento da migração;
    #    o índice será efetivo após embed_pending_chapters() rodar.
    op.execute(
        """
        CREATE INDEX idx_chapters_embedding
        ON chapters
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
        """
    )

    # 3. tsvector gerado + GIN para BM25 (stemmer português)
    #    Combina title + content para cobertura total do capítulo.
    op.execute(
        """
        ALTER TABLE chapters
        ADD COLUMN ts_content tsvector
        GENERATED ALWAYS AS (
            to_tsvector('portuguese', coalesce(title, '') || ' ' || coalesce(content, ''))
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX idx_chapters_ts_content "
        "ON chapters USING gin(ts_content)"
    )


# ── Downgrade ─────────────────────────────────────────────────────────────────


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chapters_ts_content")
    op.execute("ALTER TABLE chapters DROP COLUMN IF EXISTS ts_content")
    op.execute("DROP INDEX IF EXISTS idx_chapters_embedding")
    op.drop_column("chapters", "embedding")
