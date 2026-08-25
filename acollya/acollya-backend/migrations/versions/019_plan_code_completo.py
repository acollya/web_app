"""Migrate existing premium users (plan_code=1) to Completo (plan_code=2)

Revision ID: 019
Revises: 018
Create Date: 2026-05-20
"""
from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET plan_code = 2
        WHERE plan_code = 1
          AND subscription_status = 'active'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET plan_code = 1
        WHERE plan_code = 2
          AND subscription_status = 'active'
        """
    )
