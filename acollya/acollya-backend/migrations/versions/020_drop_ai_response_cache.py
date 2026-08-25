"""Drop ai_response_cache — tabela morta desde o schema inicial.

Criada na migration 001 para cache semântico de respostas da IA, mas nunca
foi implementada na aplicação (zero referências em app/). O caching real é
feito via prompt caching da Anthropic + Redis. Decisão de remoção: 2026-08-01.

Downgrade recria a tabela conforme 001 + user_id da 013 (vazia).

Revision ID: 020
Revises: 019
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("ai_response_cache")


def downgrade() -> None:
    op.create_table(
        "ai_response_cache",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("query_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("NOW() + INTERVAL '30 days'")),
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.execute("ALTER TABLE ai_response_cache ADD COLUMN query_embedding vector(1536)")
    op.execute(
        "CREATE INDEX idx_ai_cache_embedding ON ai_response_cache "
        "USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.create_index("idx_ai_cache_query_hash", "ai_response_cache", ["query_hash"])
    op.create_index("idx_ai_cache_expires_at", "ai_response_cache", ["expires_at"])
    op.create_index("idx_ai_cache_user_id", "ai_response_cache", ["user_id"])
