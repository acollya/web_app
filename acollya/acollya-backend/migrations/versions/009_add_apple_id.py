"""Add apple_id to users

Revision ID: 009
Revises: 008
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('apple_id', sa.Text(), nullable=True))
    op.create_unique_constraint('uq_users_apple_id', 'users', ['apple_id'])


def downgrade() -> None:
    op.drop_constraint('uq_users_apple_id', 'users', type_='unique')
    op.drop_column('users', 'apple_id')
