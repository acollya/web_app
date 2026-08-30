"""Chat F3/F4 — nome original do arquivo para anexos (imagens/documentos).

Revision ID: 026
Revises: 025
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("media_filename", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "media_filename")
