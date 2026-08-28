"""programs: campos do catálogo Voeo + embedding vetorial.

Prepara a tabela para a carga do Catálogo de Produtos Digitais (migration 023):
  about           — descritivo longo estruturado (description continua sendo o resumo curto)
  format          — jornada_diaria | semanal | fases | modular | ferramenta | ao_vivo
  duration_label  — texto de exibição ("21 dias", "6 semanas", "3 fases · no seu ritmo"…)
  audience        — nicho [N] do catálogo ("mães", "concurseiros", "45+"…)
  min_plan_code   — 1 = incluso no Essencial+ · 2 = incluso no Completo · NULL = fora
                    dos planos (bloqueado → upgrade ou compra avulsa)
  price_min/max   — faixa de preço do catálogo (versões Essencial→Acompanhada)
  iap_product_id  — product id RevenueCat para venda avulsa (preenchido depois)
  embedding       — vetor do título+resumo+about; alimenta get_recommended para
                    programas sem capítulos e a base de conhecimento dos agentes

Revision ID: 022
Revises: 021
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("programs", sa.Column("about", sa.Text(), nullable=True))
    op.add_column("programs", sa.Column("format", sa.Text(), nullable=True))
    op.add_column("programs", sa.Column("duration_label", sa.Text(), nullable=True))
    op.add_column("programs", sa.Column("audience", sa.Text(), nullable=True))
    op.add_column("programs", sa.Column("min_plan_code", sa.Integer(), nullable=True))
    op.add_column("programs", sa.Column("price_min_brl", sa.Numeric(10, 2), nullable=True))
    op.add_column("programs", sa.Column("price_max_brl", sa.Numeric(10, 2), nullable=True))
    op.add_column("programs", sa.Column("iap_product_id", sa.Text(), nullable=True))
    op.execute("ALTER TABLE programs ADD COLUMN embedding vector(1536)")
    op.execute(
        "CREATE INDEX idx_programs_embedding ON programs "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_programs_embedding")
    op.drop_column("programs", "embedding")
    op.drop_column("programs", "iap_product_id")
    op.drop_column("programs", "price_max_brl")
    op.drop_column("programs", "price_min_brl")
    op.drop_column("programs", "min_plan_code")
    op.drop_column("programs", "audience")
    op.drop_column("programs", "duration_label")
    op.drop_column("programs", "format")
    op.drop_column("programs", "about")
