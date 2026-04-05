"""Create user_persona_facts table for hyperpersonalization

Revision ID: 006
Revises: 005
Create Date: 2026-04-04

Armazena fatos extraídos sobre o usuário (preferências, rotinas, gatilhos,
valores, contexto) com embeddings vetoriais para busca semântica.
Alimenta o sistema de hiperpersonalização da IA em chat, mood insights e diário.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# ── Revision ──────────────────────────────────────────────────────────────────

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Upgrade ───────────────────────────────────────────────────────────────────

def upgrade() -> None:
    # Garante que a extensão pgvector esteja ativa
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "user_persona_facts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),

        # Categoria semântica do fato
        sa.Column(
            "category",
            sa.Enum(
                "preferencia",   # o que o usuário gosta/prefere
                "aversao",       # o que o usuário evita/não gosta
                "rotina",        # padrões de comportamento e hábitos
                "gatilho",       # situações que causam estresse/ansiedade
                "valor",         # valores pessoais e crenças centrais
                "contexto",      # informações de vida: profissão, família, etc.
                name="persona_category_enum",
            ),
            nullable=False,
        ),

        # Texto do fato em linguagem natural (ex: "Prefere sessões matinais")
        sa.Column("fact_text", sa.Text, nullable=False),

        # Embedding gerado por text-embedding-3-small (1536 dims)
        sa.Column("embedding", Vector(1536), nullable=True),

        # 0.0–1.0: quão confiante o modelo está neste fato
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.8"),

        # Origem do fato: "chat", "journal", "mood_checkin", "manual"
        sa.Column("source", sa.String(50), nullable=False),

        # ID do registro de origem (chat_message.id, journal_entry.id, etc.)
        sa.Column("source_id", sa.UUID(as_uuid=True), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    # Índice IVFFlat para busca vetorial por similaridade cosseno
    # lists=50 adequado para até ~500k registros; ajustar para lists=100+ em produção
    op.execute(
        """
        CREATE INDEX ix_user_persona_facts_embedding
        ON user_persona_facts
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50)
        """
    )

    # Índice composto para filtrar por usuário + categoria eficientemente
    op.create_index(
        "ix_user_persona_facts_user_category",
        "user_persona_facts",
        ["user_id", "category"],
    )

    # Trigger para atualizar updated_at automaticamente
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_user_persona_facts_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_user_persona_facts_updated_at
        BEFORE UPDATE ON user_persona_facts
        FOR EACH ROW EXECUTE FUNCTION update_user_persona_facts_updated_at();
        """
    )


# ── Downgrade ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_user_persona_facts_updated_at ON user_persona_facts")
    op.execute("DROP FUNCTION IF EXISTS update_user_persona_facts_updated_at()")
    op.drop_index("ix_user_persona_facts_user_category", table_name="user_persona_facts")
    op.execute("DROP INDEX IF EXISTS ix_user_persona_facts_embedding")
    op.drop_table("user_persona_facts")
    op.execute("DROP TYPE IF EXISTS persona_category_enum")
