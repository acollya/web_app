"""LGPD: consentimento específico p/ dados de saúde + versão dos termos.

Art. 11 LGPD — dados de saúde são categoria especial e exigem consentimento
específico e destacado, separado do aceite geral de termos. Também adiciona
o rastreio de QUAL versão dos termos foi aceita (item #3 do legal-checklist).

Revision ID: 024
Revises: 023
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("terms_version", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("health_data_consent", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("health_data_consent_date", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "health_data_consent_date")
    op.drop_column("users", "health_data_consent")
    op.drop_column("users", "terms_version")
