"""Add crisis_events audit table.

Purpose: probatório — records each crisis detection event (level, CVV shown)
so Acollya can demonstrate protocol compliance in any legal or regulatory
proceeding. No raw message content is stored; only the severity level and
whether the CVV resource was presented to the user.
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE crisis_events (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID NOT NULL REFERENCES users(id),
            session_id      UUID,
            crisis_level    TEXT NOT NULL,
            cvv_shown       BOOLEAN NOT NULL DEFAULT FALSE,
            source          TEXT NOT NULL,
            source_message_id UUID,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX ix_crisis_events_user_id   ON crisis_events (user_id)")
    op.execute("CREATE INDEX ix_crisis_events_created_at ON crisis_events (created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crisis_events")
